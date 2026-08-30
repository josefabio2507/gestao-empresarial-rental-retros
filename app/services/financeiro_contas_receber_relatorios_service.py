import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models import (
    CentroCusto,
    Equipe,
    FinanceiroContaReceberBaixa,
    FinanceiroContaReceberCobranca,
    FinanceiroContaReceberLoteBaixa,
    FinanceiroContaReceberTitulo,
    FinanceiroContratoCliente,
    FinanceiroContratoMedicao,
    FinanceiroNotaFiscalEmitida,
    Usuario,
)
from app.services.financeiro_contas_receber_service import (
    FORMAS_RECEBIMENTO,
    ORIGENS_LANCAMENTO,
    STATUS_BAIXA_ATIVA,
    STATUS_CANCELADO,
    STATUS_ESTORNADO,
    STATUS_INATIVOS,
    STATUS_RECEBIDO,
    STATUS_RECEBIDO_PARCIALMENTE,
    STATUS_TITULOS_RECEBER,
    formatar_moeda_brl,
    somente_digitos,
    texto,
    texto_maiusculo,
)
from app.services.logs_service import registrar_log
from app.utils.datas import agora_brasil

STATUS_COBRANCA = [
    "Sem cobrança",
    "A cobrar",
    "Cobrança enviada",
    "Em negociação",
    "Promessa de pagamento",
    "Aguardando retorno",
    "Recebido parcialmente",
    "Resolvido",
    "Suspenso",
    "Inadimplência encerrada",
]
TIPOS_CONTATO_COBRANCA = ["Telefone", "WhatsApp", "E-mail", "Reunião", "Presencial", "Outro"]
STATUS_REGISTRO_COBRANCA_ATIVO = "Ativo"

TIPOS_RELATORIO_CR = [
    ("cr_periodo", "Contas a receber por período"),
    ("cr_vencidos", "Recebíveis vencidos"),
    ("cr_a_vencer", "Recebíveis a vencer"),
    ("cr_recebimentos", "Recebimentos realizados"),
    ("cr_cliente", "Recebíveis por cliente"),
    ("cr_origem", "Recebíveis por origem"),
    ("cr_contrato", "Recebíveis por contrato"),
    ("cr_medicao", "Recebíveis por medição"),
    ("cr_notas_sem_titulo", "Notas emitidas sem título"),
    ("cr_medicoes_sem_titulo", "Medições aprovadas sem título"),
    ("cr_sem_comprovante", "Títulos sem comprovante"),
    ("cr_inadimplencia", "Inadimplência"),
    ("cr_lotes", "Lotes de recebimento"),
]
TIPOS_RELATORIO_CR_DICT = dict(TIPOS_RELATORIO_CR)
TIPOS_DATA_CR = [
    ("vencimento", "Vencimento"),
    ("emissao", "Emissão"),
    ("recebimento", "Recebimento"),
    ("criacao", "Criação"),
    ("medicao", "Medição"),
]


def valor_decimal(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"))


def _parse_data(valor):
    if not valor:
        return None
    if hasattr(valor, "isoformat"):
        return valor
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(valor):
    try:
        return int(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _inicio_mes(data_base):
    return data_base.replace(day=1)


def _fim_mes(data_base):
    if data_base.month == 12:
        return data_base.replace(year=data_base.year + 1, month=1, day=1) - timedelta(days=1)
    return data_base.replace(month=data_base.month + 1, day=1) - timedelta(days=1)


def filtros_padrao_cr(args=None):
    args = args or {}
    hoje = agora_brasil().date()
    inicio = _parse_data(args.get("data_inicio"))
    fim = _parse_data(args.get("data_fim"))
    if not inicio and not fim and not args.get("sem_periodo"):
        inicio = _inicio_mes(hoje)
        fim = _fim_mes(hoje)
    return {
        "tipo_relatorio": args.get("tipo_relatorio") or "cr_periodo",
        "tipo_data": args.get("tipo_data") or "vencimento",
        "data_inicio": inicio,
        "data_fim": fim,
        "cliente": texto(args.get("cliente")),
        "cnpj_cpf": somente_digitos(args.get("cnpj_cpf")),
        "status": args.get("status") or "",
        "status_cobranca": args.get("status_cobranca") or "",
        "origem_lancamento": args.get("origem_lancamento") or "",
        "forma_recebimento": args.get("forma_recebimento") or "",
        "centro_custo_id": _parse_int(args.get("centro_custo_id")),
        "sub_centro_custo_equipe_id": _parse_int(args.get("sub_centro_custo_equipe_id")),
        "sub_centro_custo_veiculo_id": _parse_int(args.get("sub_centro_custo_veiculo_id")),
        "contrato_id": _parse_int(args.get("contrato_id")),
        "medicao_id": _parse_int(args.get("medicao_id")),
        "nota_emitida_id": _parse_int(args.get("nota_emitida_id")),
        "numero_documento": texto(args.get("numero_documento")),
        "numero_nota_fiscal": texto(args.get("numero_nota_fiscal")),
        "comprovante": args.get("comprovante") or "",
        "cobranca": args.get("cobranca") or "",
        "dias_a_vencer": _parse_int(args.get("dias_a_vencer")) or 30,
        "dias_atraso_min": _parse_int(args.get("dias_atraso_min")),
        "dias_atraso_max": _parse_int(args.get("dias_atraso_max")),
    }


def filtros_para_template_cr(filtros):
    dados = dict(filtros)
    dados["data_inicio"] = filtros["data_inicio"].isoformat() if filtros.get("data_inicio") else ""
    dados["data_fim"] = filtros["data_fim"].isoformat() if filtros.get("data_fim") else ""
    return dados


def periodo_valido_cr(filtros):
    inicio = filtros.get("data_inicio")
    fim = filtros.get("data_fim")
    return not (inicio and fim and inicio > fim)


def opcoes_relatorios_cr():
    return {
        "tipos_relatorio": TIPOS_RELATORIO_CR,
        "tipos_data": TIPOS_DATA_CR,
        "status_titulo": STATUS_TITULOS_RECEBER,
        "status_cobranca": STATUS_COBRANCA,
        "origens": ORIGENS_LANCAMENTO,
        "formas_recebimento": FORMAS_RECEBIMENTO,
        "centros_custo": CentroCusto.query.filter_by(ativo=True).order_by(CentroCusto.nome.asc()).all(),
        "equipes": Equipe.query.filter_by(ativo=True).order_by(Equipe.nome.asc()).all(),
        "contratos": FinanceiroContratoCliente.query.order_by(FinanceiroContratoCliente.numero_contrato.asc()).limit(200).all(),
        "medicoes": FinanceiroContratoMedicao.query.order_by(FinanceiroContratoMedicao.numero_medicao.asc()).limit(200).all(),
        "notas": FinanceiroNotaFiscalEmitida.query.order_by(FinanceiroNotaFiscalEmitida.numero_nota.asc()).limit(200).all(),
        "dias_a_vencer": [7, 15, 30, 60, 90],
    }


def _query_titulos_base():
    return FinanceiroContaReceberTitulo.query.options(
        joinedload(FinanceiroContaReceberTitulo.centro_custo),
        joinedload(FinanceiroContaReceberTitulo.contrato),
        joinedload(FinanceiroContaReceberTitulo.medicao),
        joinedload(FinanceiroContaReceberTitulo.nota_emitida),
        selectinload(FinanceiroContaReceberTitulo.baixas).joinedload(FinanceiroContaReceberBaixa.lote_baixa),
        selectinload(FinanceiroContaReceberTitulo.cobrancas).joinedload(FinanceiroContaReceberCobranca.responsavel),
    )


def _titulo_ativo(titulo):
    return titulo.status not in {STATUS_CANCELADO, STATUS_ESTORNADO}


def _saldo_titulo(titulo):
    return valor_decimal(titulo.saldo_aberto)


def _ultima_cobranca(titulo):
    ativas = [c for c in titulo.cobrancas if c.status == STATUS_REGISTRO_COBRANCA_ATIVO]
    return ativas[0] if ativas else None


def _tem_comprovante(titulo):
    return any(baixa.status == STATUS_BAIXA_ATIVA and baixa.comprovante_disponivel for baixa in titulo.baixas)


def _tem_baixa_ativa(titulo):
    return any(baixa.status == STATUS_BAIXA_ATIVA for baixa in titulo.baixas)


def aplicar_filtros_titulos_cr(query, filtros):
    tipo_data = filtros.get("tipo_data") or "vencimento"
    data_colunas = {
        "vencimento": FinanceiroContaReceberTitulo.data_vencimento,
        "emissao": FinanceiroContaReceberTitulo.data_emissao,
        "recebimento": FinanceiroContaReceberTitulo.data_recebimento,
        "criacao": FinanceiroContaReceberTitulo.criado_em,
    }
    coluna = data_colunas.get(tipo_data, FinanceiroContaReceberTitulo.data_vencimento)
    if filtros.get("data_inicio"):
        query = query.filter(coluna >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(coluna <= filtros["data_fim"])
    if filtros.get("cliente"):
        query = query.filter(FinanceiroContaReceberTitulo.cliente_nome_snapshot.ilike(f"%{filtros['cliente']}%"))
    if filtros.get("cnpj_cpf"):
        query = query.filter(FinanceiroContaReceberTitulo.cliente_cnpj_cpf_snapshot.ilike(f"%{filtros['cnpj_cpf']}%"))
    if filtros.get("status"):
        query = query.filter(FinanceiroContaReceberTitulo.status == filtros["status"])
    if filtros.get("origem_lancamento"):
        query = query.filter(FinanceiroContaReceberTitulo.origem_lancamento == filtros["origem_lancamento"])
    if filtros.get("centro_custo_id"):
        query = query.filter(FinanceiroContaReceberTitulo.centro_custo_id == filtros["centro_custo_id"])
    if filtros.get("sub_centro_custo_equipe_id"):
        query = query.filter(FinanceiroContaReceberTitulo.sub_centro_custo_equipe_id == filtros["sub_centro_custo_equipe_id"])
    if filtros.get("sub_centro_custo_veiculo_id"):
        query = query.filter(FinanceiroContaReceberTitulo.sub_centro_custo_veiculo_id == filtros["sub_centro_custo_veiculo_id"])
    if filtros.get("contrato_id"):
        query = query.filter(FinanceiroContaReceberTitulo.contrato_id == filtros["contrato_id"])
    if filtros.get("medicao_id"):
        query = query.filter(FinanceiroContaReceberTitulo.medicao_id == filtros["medicao_id"])
    if filtros.get("nota_emitida_id"):
        query = query.filter(FinanceiroContaReceberTitulo.nota_emitida_id == filtros["nota_emitida_id"])
    if filtros.get("numero_documento"):
        query = query.filter(FinanceiroContaReceberTitulo.numero_documento.ilike(f"%{filtros['numero_documento']}%"))
    if filtros.get("numero_nota_fiscal"):
        query = query.filter(FinanceiroContaReceberTitulo.numero_nota_fiscal.ilike(f"%{filtros['numero_nota_fiscal']}%"))
    return query


def titulos_filtrados_cr(filtros):
    titulos = aplicar_filtros_titulos_cr(_query_titulos_base(), filtros).order_by(FinanceiroContaReceberTitulo.data_vencimento.asc(), FinanceiroContaReceberTitulo.id.asc()).all()
    hoje = agora_brasil().date()
    if filtros.get("tipo_data") == "medicao" and (filtros.get("data_inicio") or filtros.get("data_fim")):
        inicio = filtros.get("data_inicio") or date.min
        fim = filtros.get("data_fim") or date.max
        titulos = [t for t in titulos if t.medicao and t.medicao.data_medicao and inicio <= t.medicao.data_medicao <= fim]
    if filtros.get("status_cobranca"):
        titulos = [t for t in titulos if _ultima_cobranca(t) and _ultima_cobranca(t).status_cobranca == filtros["status_cobranca"]]
    if filtros.get("forma_recebimento"):
        titulos = [t for t in titulos if any(b.status == STATUS_BAIXA_ATIVA and b.forma_recebimento == filtros["forma_recebimento"] for b in t.baixas)]
    if filtros.get("comprovante") == "com":
        titulos = [t for t in titulos if _tem_comprovante(t)]
    elif filtros.get("comprovante") == "sem":
        titulos = [t for t in titulos if _tem_baixa_ativa(t) and not _tem_comprovante(t)]
    if filtros.get("cobranca") == "com":
        titulos = [t for t in titulos if _ultima_cobranca(t)]
    elif filtros.get("cobranca") == "sem":
        titulos = [t for t in titulos if not _ultima_cobranca(t)]
    if filtros.get("dias_atraso_min") is not None:
        titulos = [t for t in titulos if max((hoje - t.data_vencimento).days, 0) >= filtros["dias_atraso_min"]]
    if filtros.get("dias_atraso_max") is not None:
        titulos = [t for t in titulos if max((hoje - t.data_vencimento).days, 0) <= filtros["dias_atraso_max"]]
    return titulos


def titulo_inadimplente(titulo, hoje=None):
    hoje = hoje or agora_brasil().date()
    return _titulo_ativo(titulo) and titulo.status != STATUS_RECEBIDO and titulo.data_vencimento < hoje and _saldo_titulo(titulo) > 0


def listar_inadimplencia(filtros=None):
    filtros = filtros_padrao_cr(filtros or {})
    hoje = agora_brasil().date()
    titulos = [t for t in titulos_filtrados_cr({**filtros, "tipo_data": "vencimento"}) if titulo_inadimplente(t, hoje)]
    return [_linha_inadimplencia(t, hoje) for t in titulos]


def _linha_titulo(titulo):
    ultima = _ultima_cobranca(titulo)
    return {
        "id": titulo.id,
        "titulo_id": titulo.id,
        "cliente": titulo.cliente_nome_snapshot,
        "cnpj_cpf": titulo.cliente_cnpj_cpf_snapshot or "-",
        "documento": titulo.numero_documento or "-",
        "nota_fiscal": titulo.numero_nota_fiscal or "-",
        "contrato": titulo.contrato.numero_contrato if titulo.contrato else "-",
        "medicao": titulo.medicao.numero_medicao if titulo.medicao else "-",
        "vencimento": titulo.data_vencimento,
        "emissao": titulo.data_emissao,
        "recebimento": titulo.data_recebimento,
        "origem": titulo.origem_lancamento,
        "valor_original": valor_decimal(titulo.valor_original),
        "valor_recebido": valor_decimal(titulo.valor_recebido),
        "saldo_aberto": _saldo_titulo(titulo),
        "status": titulo.status_visual(),
        "dias_atraso": max((agora_brasil().date() - titulo.data_vencimento).days, 0),
        "status_cobranca": ultima.status_cobranca if ultima else "Sem cobrança",
        "ultima_cobranca": ultima.data_contato if ultima else None,
        "proxima_acao": ultima.proxima_acao if ultima else "-",
        "data_proxima_acao": ultima.data_proxima_acao if ultima else None,
        "responsavel": ultima.responsavel.nome if ultima and ultima.responsavel else "-",
        "comprovante": "Sim" if _tem_comprovante(titulo) else "Não",
        "contrato_id": titulo.contrato_id,
        "medicao_id": titulo.medicao_id,
        "nota_emitida_id": titulo.nota_emitida_id,
    }


def _linha_inadimplencia(titulo, hoje=None):
    linha = _linha_titulo(titulo)
    hoje = hoje or agora_brasil().date()
    linha["dias_atraso"] = max((hoje - titulo.data_vencimento).days, 0)
    return linha


def _totais_titulos(titulos):
    vencidos = [t for t in titulos if titulo_inadimplente(t)]
    return {
        "quantidade": len(titulos),
        "valor_original": sum((valor_decimal(t.valor_original) for t in titulos), Decimal("0.00")),
        "valor_recebido": sum((valor_decimal(t.valor_recebido) for t in titulos), Decimal("0.00")),
        "saldo_aberto": sum((_saldo_titulo(t) for t in titulos), Decimal("0.00")),
        "valor_vencido": sum((_saldo_titulo(t) for t in vencidos), Decimal("0.00")),
    }


def _agrupar_titulos(titulos, chave_fn, extras_fn=None):
    grupos = {}
    for titulo in titulos:
        chave = chave_fn(titulo) or "Sem classificação"
        item = grupos.setdefault(chave, {"grupo": chave, "quantidade": 0, "valor_original": Decimal("0.00"), "valor_recebido": Decimal("0.00"), "saldo_aberto": Decimal("0.00"), "valor_vencido": Decimal("0.00")})
        item["quantidade"] += 1
        item["valor_original"] += valor_decimal(titulo.valor_original)
        item["valor_recebido"] += valor_decimal(titulo.valor_recebido)
        item["saldo_aberto"] += _saldo_titulo(titulo)
        if titulo_inadimplente(titulo):
            item["valor_vencido"] += _saldo_titulo(titulo)
        if extras_fn:
            item.update(extras_fn(titulo))
    return sorted(grupos.values(), key=lambda item: item["saldo_aberto"], reverse=True)


def _relatorio_titulos(tipo, filtros):
    titulos = titulos_filtrados_cr(filtros)
    hoje = agora_brasil().date()
    if tipo == "cr_vencidos":
        titulos = [t for t in titulos if titulo_inadimplente(t, hoje)]
    elif tipo == "cr_a_vencer":
        limite = hoje + timedelta(days=filtros.get("dias_a_vencer") or 30)
        titulos = [t for t in titulos if _titulo_ativo(t) and t.status != STATUS_RECEBIDO and hoje <= t.data_vencimento <= limite and _saldo_titulo(t) > 0]
    elif tipo == "cr_sem_comprovante":
        titulos = [t for t in titulos if _tem_baixa_ativa(t) and not _tem_comprovante(t)]
    elif tipo == "cr_inadimplencia":
        titulos = [t for t in titulos if titulo_inadimplente(t, hoje)]
    return [_linha_titulo(t) for t in titulos], _totais_titulos(titulos)


def _relatorio_recebimentos(filtros):
    query = FinanceiroContaReceberBaixa.query.options(joinedload(FinanceiroContaReceberBaixa.titulo), joinedload(FinanceiroContaReceberBaixa.lote_baixa), joinedload(FinanceiroContaReceberBaixa.registrado_por))
    if filtros.get("data_inicio"):
        query = query.filter(FinanceiroContaReceberBaixa.data_recebimento >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(FinanceiroContaReceberBaixa.data_recebimento <= filtros["data_fim"])
    query = query.filter(FinanceiroContaReceberBaixa.status == STATUS_BAIXA_ATIVA)
    if filtros.get("forma_recebimento"):
        query = query.filter(FinanceiroContaReceberBaixa.forma_recebimento == filtros["forma_recebimento"])
    baixas = query.order_by(FinanceiroContaReceberBaixa.data_recebimento.desc(), FinanceiroContaReceberBaixa.id.desc()).all()
    linhas = []
    total = Decimal("0.00")
    for baixa in baixas:
        titulo = baixa.titulo
        if not titulo:
            continue
        if filtros.get("cliente") and filtros["cliente"].lower() not in (titulo.cliente_nome_snapshot or "").lower():
            continue
        if filtros.get("cnpj_cpf") and filtros["cnpj_cpf"] not in (titulo.cliente_cnpj_cpf_snapshot or ""):
            continue
        total += valor_decimal(baixa.valor_recebido)
        linhas.append({
            "id": baixa.id,
            "titulo_id": baixa.titulo_id,
            "cliente": titulo.cliente_nome_snapshot,
            "documento": titulo.numero_documento or "-",
            "data_recebimento": baixa.data_recebimento,
            "valor_recebido": valor_decimal(baixa.valor_recebido),
            "forma_recebimento": baixa.forma_recebimento,
            "usuario": baixa.registrado_por.nome if baixa.registrado_por else "-",
            "comprovante": "Sim" if baixa.comprovante_disponivel else "Não",
            "lote_id": baixa.lote_baixa_id,
            "status": baixa.status,
        })
    return linhas, {"quantidade": len(linhas), "valor_original": Decimal("0.00"), "valor_recebido": total, "saldo_aberto": Decimal("0.00"), "valor_vencido": Decimal("0.00")}


def _relatorio_lotes(filtros):
    query = FinanceiroContaReceberLoteBaixa.query.options(joinedload(FinanceiroContaReceberLoteBaixa.criado_por), selectinload(FinanceiroContaReceberLoteBaixa.baixas))
    if filtros.get("data_inicio"):
        query = query.filter(FinanceiroContaReceberLoteBaixa.data_recebimento >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(FinanceiroContaReceberLoteBaixa.data_recebimento <= filtros["data_fim"])
    if filtros.get("forma_recebimento"):
        query = query.filter(FinanceiroContaReceberLoteBaixa.forma_recebimento == filtros["forma_recebimento"])
    lotes = query.order_by(FinanceiroContaReceberLoteBaixa.data_recebimento.desc(), FinanceiroContaReceberLoteBaixa.id.desc()).all()
    linhas = []
    total = Decimal("0.00")
    for lote in lotes:
        total += valor_decimal(lote.valor_total_recebido)
        linhas.append({
            "id": lote.id,
            "lote_id": lote.id,
            "data_recebimento": lote.data_recebimento,
            "forma_recebimento": lote.forma_recebimento,
            "total_titulos": lote.total_titulos,
            "valor_total": valor_decimal(lote.valor_total_recebido),
            "usuario": lote.criado_por.nome if lote.criado_por else "-",
            "status": lote.status,
            "comprovante": "Sim" if lote.comprovante_disponivel else "Não",
        })
    return linhas, {"quantidade": len(linhas), "valor_original": total, "valor_recebido": total, "saldo_aberto": Decimal("0.00"), "valor_vencido": Decimal("0.00")}


def _relatorio_notas_sem_titulo(filtros):
    query = FinanceiroNotaFiscalEmitida.query.options(selectinload(FinanceiroNotaFiscalEmitida.titulos))
    if filtros.get("data_inicio"):
        query = query.filter(FinanceiroNotaFiscalEmitida.data_emissao >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(FinanceiroNotaFiscalEmitida.data_emissao <= filtros["data_fim"])
    notas = [n for n in query.order_by(FinanceiroNotaFiscalEmitida.data_emissao.desc()).all() if n.status_fiscal != "Cancelada" and not n.titulos_ativos]
    linhas = [{"id": n.id, "nota_emitida_id": n.id, "numero_nota": n.numero_nota, "cliente": n.cliente_nome_snapshot, "emissao": n.data_emissao, "valor_total": valor_decimal(n.valor_total), "status_fiscal": n.status_fiscal, "status_financeiro": n.status_financeiro} for n in notas]
    total = sum((linha["valor_total"] for linha in linhas), Decimal("0.00"))
    return linhas, {"quantidade": len(linhas), "valor_original": total, "valor_recebido": Decimal("0.00"), "saldo_aberto": total, "valor_vencido": Decimal("0.00")}


def _relatorio_medicoes_sem_titulo(filtros):
    query = FinanceiroContratoMedicao.query.options(joinedload(FinanceiroContratoMedicao.contrato), selectinload(FinanceiroContratoMedicao.titulos), joinedload(FinanceiroContratoMedicao.nota_emitida))
    if filtros.get("data_inicio"):
        query = query.filter(FinanceiroContratoMedicao.data_medicao >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(FinanceiroContratoMedicao.data_medicao <= filtros["data_fim"])
    medicoes = [m for m in query.order_by(FinanceiroContratoMedicao.data_medicao.desc()).all() if m.status_medicao in {"Aprovada", "Faturada", "Medida"} and not m.titulos_ativos and m.status_medicao != "Cancelada"]
    linhas = [{"id": m.id, "medicao_id": m.id, "numero_medicao": m.numero_medicao, "contrato": m.contrato.numero_contrato if m.contrato else "-", "cliente": m.contrato.cliente_nome_snapshot if m.contrato else "-", "competencia": m.competencia, "data_medicao": m.data_medicao, "valor_medido": valor_decimal(m.valor_liquido_medido), "nota": m.nota_emitida.numero_nota if m.nota_emitida else "-", "status_financeiro": m.status_financeiro} for m in medicoes]
    total = sum((linha["valor_medido"] for linha in linhas), Decimal("0.00"))
    return linhas, {"quantidade": len(linhas), "valor_original": total, "valor_recebido": Decimal("0.00"), "saldo_aberto": total, "valor_vencido": Decimal("0.00")}


def montar_relatorio_cr(tipo_relatorio, filtros):
    tipo = tipo_relatorio if tipo_relatorio in TIPOS_RELATORIO_CR_DICT else "cr_periodo"
    if tipo in {"cr_periodo", "cr_vencidos", "cr_a_vencer", "cr_sem_comprovante", "cr_inadimplencia"}:
        linhas, totais = _relatorio_titulos(tipo, filtros)
        colunas = ["id", "cliente", "documento", "nota_fiscal", "contrato", "medicao", "vencimento", "dias_atraso", "origem", "valor_original", "valor_recebido", "saldo_aberto", "status", "status_cobranca"]
    elif tipo == "cr_recebimentos":
        linhas, totais = _relatorio_recebimentos(filtros)
        colunas = ["id", "titulo_id", "cliente", "documento", "data_recebimento", "valor_recebido", "forma_recebimento", "usuario", "comprovante", "lote_id", "status"]
    elif tipo == "cr_cliente":
        titulos = titulos_filtrados_cr(filtros)
        linhas, totais = _agrupar_titulos(titulos, lambda t: t.cliente_nome_snapshot), _totais_titulos(titulos)
        colunas = ["grupo", "quantidade", "valor_original", "valor_recebido", "saldo_aberto", "valor_vencido"]
    elif tipo == "cr_origem":
        titulos = titulos_filtrados_cr(filtros)
        linhas, totais = _agrupar_titulos(titulos, lambda t: t.origem_lancamento), _totais_titulos(titulos)
        colunas = ["grupo", "quantidade", "valor_original", "valor_recebido", "saldo_aberto", "valor_vencido"]
    elif tipo == "cr_contrato":
        titulos = titulos_filtrados_cr(filtros)
        linhas, totais = _agrupar_titulos(titulos, lambda t: t.contrato.numero_contrato if t.contrato else "Sem contrato", lambda t: {"valor_contratual": valor_decimal(t.contrato.valor_contratual) if t.contrato else Decimal("0.00"), "valor_medido": valor_decimal(t.contrato.valor_medido_acumulado) if t.contrato else Decimal("0.00")}), _totais_titulos(titulos)
        colunas = ["grupo", "quantidade", "valor_contratual", "valor_medido", "valor_original", "valor_recebido", "saldo_aberto", "valor_vencido"]
    elif tipo == "cr_medicao":
        titulos = titulos_filtrados_cr(filtros)
        linhas, totais = _agrupar_titulos(titulos, lambda t: t.medicao.numero_medicao if t.medicao else "Sem medição", lambda t: {"valor_medido": valor_decimal(t.medicao.valor_liquido_medido) if t.medicao else Decimal("0.00"), "nota": t.nota_emitida.numero_nota if t.nota_emitida else "-"}), _totais_titulos(titulos)
        colunas = ["grupo", "quantidade", "valor_medido", "nota", "valor_original", "valor_recebido", "saldo_aberto", "valor_vencido"]
    elif tipo == "cr_notas_sem_titulo":
        linhas, totais = _relatorio_notas_sem_titulo(filtros)
        colunas = ["id", "numero_nota", "cliente", "emissao", "valor_total", "status_fiscal", "status_financeiro"]
    elif tipo == "cr_medicoes_sem_titulo":
        linhas, totais = _relatorio_medicoes_sem_titulo(filtros)
        colunas = ["id", "numero_medicao", "contrato", "cliente", "competencia", "data_medicao", "valor_medido", "nota", "status_financeiro"]
    else:
        linhas, totais = _relatorio_lotes(filtros)
        colunas = ["id", "data_recebimento", "forma_recebimento", "total_titulos", "valor_total", "usuario", "status", "comprovante"]
    return {"tipo": tipo, "titulo": TIPOS_RELATORIO_CR_DICT[tipo], "colunas": colunas, "linhas": linhas, "totais": totais, "escopo": "contas_receber"}


def valor_coluna_cr(linha, coluna):
    valor = linha.get(coluna)
    if isinstance(valor, Decimal):
        return formatar_moeda_brl(valor)
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    if valor is None:
        return "-"
    return valor


def gerar_csv_relatorio_cr(relatorio):
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow([relatorio["titulo"]])
    escritor.writerow([])
    escritor.writerow(relatorio["colunas"])
    for linha in relatorio["linhas"]:
        escritor.writerow([valor_coluna_cr(linha, coluna) for coluna in relatorio["colunas"]])
    escritor.writerow([])
    escritor.writerow(["Quantidade", relatorio["totais"].get("quantidade", 0)])
    escritor.writerow(["Valor original", formatar_moeda_brl(relatorio["totais"].get("valor_original"))])
    escritor.writerow(["Valor recebido", formatar_moeda_brl(relatorio["totais"].get("valor_recebido"))])
    escritor.writerow(["Saldo em aberto", formatar_moeda_brl(relatorio["totais"].get("saldo_aberto"))])
    escritor.writerow(["Valor vencido", formatar_moeda_brl(relatorio["totais"].get("valor_vencido"))])
    return saida.getvalue()


def nome_arquivo_relatorio_cr(tipo):
    return f"contas_a_receber_{tipo.replace('cr_', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def salvar_cobranca_titulo(titulo, dados, usuario=None, cobranca=None):
    if not titulo:
        return False, "Título a receber não encontrado.", None
    if not titulo_inadimplente(titulo):
        return False, "Somente títulos vencidos com saldo em aberto aceitam acompanhamento de cobrança.", cobranca
    cobranca = cobranca or FinanceiroContaReceberCobranca()
    novo = cobranca.id is None
    data_contato = _parse_data(dados.get("data_contato"))
    if not data_contato:
        return False, "Informe a data do contato.", cobranca
    tipo_contato = texto(dados.get("tipo_contato"))
    if tipo_contato not in TIPOS_CONTATO_COBRANCA:
        return False, "Informe o tipo de contato.", cobranca
    status_cobranca = texto(dados.get("status_cobranca")) or "A cobrar"
    if status_cobranca not in STATUS_COBRANCA:
        return False, "Informe o status de cobrança.", cobranca
    cobranca.titulo = titulo
    cobranca.data_contato = data_contato
    cobranca.tipo_contato = tipo_contato
    cobranca.responsavel_usuario_id = _parse_int(dados.get("responsavel_usuario_id")) or getattr(usuario, "id", None)
    cobranca.status_cobranca = status_cobranca
    cobranca.previsao_pagamento = _parse_data(dados.get("previsao_pagamento"))
    cobranca.observacao = texto_maiusculo(dados.get("observacao"))
    cobranca.proxima_acao = texto_maiusculo(dados.get("proxima_acao"))
    cobranca.data_proxima_acao = _parse_data(dados.get("data_proxima_acao"))
    cobranca.status = STATUS_REGISTRO_COBRANCA_ATIVO
    if novo:
        cobranca.criado_por_usuario_id = getattr(usuario, "id", None)
    cobranca.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.add(cobranca)
    db.session.commit()
    registrar_log("financeiro_contas_receber_cobranca_registrada", f"Cobrança registrada. Título: {titulo.id}. Cobrança: {cobranca.id}.")
    return True, "Acompanhamento de cobrança registrado com sucesso.", cobranca


def cancelar_cobranca_titulo(cobranca, motivo=None, usuario=None):
    if not cobranca:
        return False, "Acompanhamento de cobrança não encontrado."
    if cobranca.status == "Cancelado":
        return False, "Acompanhamento de cobrança já está cancelado."
    if not texto(motivo):
        return False, "Informe o motivo do cancelamento."
    cobranca.status = "Cancelado"
    cobranca.cancelado_em = agora_brasil()
    cobranca.cancelado_por_usuario_id = getattr(usuario, "id", None)
    cobranca.motivo_cancelamento = texto_maiusculo(motivo)
    db.session.commit()
    registrar_log("financeiro_contas_receber_cobranca_cancelada", f"Cobrança cancelada. Cobrança: {cobranca.id}.")
    return True, "Acompanhamento de cobrança cancelado com sucesso."


def buscar_cobranca_por_id(cobranca_id):
    return FinanceiroContaReceberCobranca.query.get(cobranca_id)


def usuarios_ativos():
    return Usuario.query.filter_by(ativo=True).order_by(Usuario.nome.asc()).all()
