import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.models import (
    CentroCusto,
    FinanceiroCartaoCredito,
    FinanceiroCartaoFatura,
    FinanceiroContaPagarBaixa,
    FinanceiroContaPagarLoteBaixa,
    FinanceiroContaPagarTitulo,
    SuprimentosFornecedor,
)
from app.services.financeiro_contas_pagar_service import (
    FORMAS_PAGAMENTO,
    ORIGENS_LANCAMENTO,
    STATUS_ABERTOS,
    STATUS_BAIXA,
    STATUS_FATURA,
    STATUS_FINAIS,
    STATUS_TITULO,
    TIPOS_PAGAMENTO,
    calcular_saldo_titulo,
)

TIPOS_RELATORIO = [
    ("periodo", "Contas a pagar por periodo"),
    ("vencidas", "Contas vencidas"),
    ("a_vencer", "Contas a vencer"),
    ("pagamentos", "Pagamentos realizados"),
    ("fornecedor", "Contas por fornecedor"),
    ("centro_custo", "Contas por centro de custo"),
    ("origem", "Contas por origem"),
    ("pagamento", "Contas por tipo/forma de pagamento"),
    ("cartoes_faturas", "Cartoes e faturas"),
    ("previsao", "Previsao de desembolso"),
    ("sem_comprovante", "Titulos sem comprovante"),
    ("lotes_baixa", "Baixas em massa / Lotes de baixa"),
]
TIPOS_RELATORIO_DICT = dict(TIPOS_RELATORIO)
TIPOS_DATA = [
    ("vencimento", "Vencimento"),
    ("emissao", "Emissao"),
    ("pagamento", "Pagamento"),
    ("criacao", "Criacao"),
]
STATUS_NAO_PREVISAO = ["Pago", "Cancelado", "Estornado"]


def moeda(valor):
    valor = Decimal(valor or 0).quantize(Decimal("0.01"))
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def valor_decimal(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"))


def _parse_data(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(valor):
    try:
        return int(valor) if valor not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _fim_mes(data_base):
    if data_base.month == 12:
        return data_base.replace(year=data_base.year + 1, month=1, day=1) - timedelta(days=1)
    return data_base.replace(month=data_base.month + 1, day=1) - timedelta(days=1)


def _inicio_mes(data_base):
    return data_base.replace(day=1)


def _saldo_expr():
    return (
        FinanceiroContaPagarTitulo.valor_original
        - FinanceiroContaPagarTitulo.valor_desconto
        + FinanceiroContaPagarTitulo.valor_acrescimo
        + FinanceiroContaPagarTitulo.valor_juros_multa
        - FinanceiroContaPagarTitulo.valor_pago
    )


def _valor_liquido_expr():
    return (
        FinanceiroContaPagarTitulo.valor_original
        - FinanceiroContaPagarTitulo.valor_desconto
        + FinanceiroContaPagarTitulo.valor_acrescimo
        + FinanceiroContaPagarTitulo.valor_juros_multa
    )


def filtros_padrao(args=None):
    args = args or {}
    hoje = date.today()
    inicio = _parse_data(args.get("data_inicio"))
    fim = _parse_data(args.get("data_fim"))
    if not inicio and not fim and not args.get("sem_periodo"):
        inicio = _inicio_mes(hoje)
        fim = _fim_mes(hoje)
    return {
        "tipo_relatorio": args.get("tipo_relatorio") or "periodo",
        "tipo_data": args.get("tipo_data") or "vencimento",
        "data_inicio": inicio,
        "data_fim": fim,
        "fornecedor": (args.get("fornecedor") or "").strip(),
        "cnpj_cpf": "".join(ch for ch in (args.get("cnpj_cpf") or "") if ch.isdigit()),
        "status": args.get("status") or "",
        "status_baixa": args.get("status_baixa") or "",
        "origem_lancamento": args.get("origem_lancamento") or "",
        "tipo_pagamento": args.get("tipo_pagamento") or "",
        "forma_pagamento": args.get("forma_pagamento") or "",
        "centro_custo_id": _parse_int(args.get("centro_custo_id")),
        "sub_centro_custo_equipe_id": _parse_int(args.get("sub_centro_custo_equipe_id")),
        "sub_centro_custo_veiculo_id": _parse_int(args.get("sub_centro_custo_veiculo_id")),
        "cartao_credito_id": _parse_int(args.get("cartao_credito_id")),
        "fatura_cartao_id": _parse_int(args.get("fatura_cartao_id")),
        "ordem_compra": (args.get("ordem_compra") or "").strip(),
        "numero_nfe": (args.get("numero_nfe") or "").strip(),
        "chave_acesso": "".join(ch for ch in (args.get("chave_acesso") or "") if ch.isdigit()),
        "comprovante": args.get("comprovante") or "",
        "dias_a_vencer": _parse_int(args.get("dias_a_vencer")) or 30,
        "agrupamento_previsao": args.get("agrupamento_previsao") or "mes",
    }


def filtros_para_template(filtros):
    dados = dict(filtros)
    dados["data_inicio"] = filtros["data_inicio"].isoformat() if filtros.get("data_inicio") else ""
    dados["data_fim"] = filtros["data_fim"].isoformat() if filtros.get("data_fim") else ""
    return dados


def periodo_valido(filtros):
    inicio = filtros.get("data_inicio")
    fim = filtros.get("data_fim")
    return not (inicio and fim and inicio > fim)


def opcoes_relatorios():
    return {
        "tipos_relatorio": TIPOS_RELATORIO,
        "tipos_data": TIPOS_DATA,
        "status_titulo": STATUS_TITULO,
        "status_baixa": STATUS_BAIXA,
        "origens": ORIGENS_LANCAMENTO,
        "tipos_pagamento": TIPOS_PAGAMENTO,
        "formas_pagamento": FORMAS_PAGAMENTO,
        "status_fatura": STATUS_FATURA,
        "centros_custo": CentroCusto.query.filter_by(ativo=True).order_by(CentroCusto.nome.asc()).all(),
        "cartoes": FinanceiroCartaoCredito.query.order_by(FinanceiroCartaoCredito.nome.asc()).all(),
        "faturas": FinanceiroCartaoFatura.query.order_by(FinanceiroCartaoFatura.competencia.desc()).all(),
        "dias_a_vencer": [7, 15, 30, 60, 90],
        "agrupamentos_previsao": [("mes", "Mensal"), ("semana", "Semanal")],
    }


def _query_titulos_base():
    return FinanceiroContaPagarTitulo.query.options(
        joinedload(FinanceiroContaPagarTitulo.cartao_credito),
        joinedload(FinanceiroContaPagarTitulo.fatura_cartao),
        joinedload(FinanceiroContaPagarTitulo.centro_custo),
        joinedload(FinanceiroContaPagarTitulo.ordem_compra),
        joinedload(FinanceiroContaPagarTitulo.fiscal_documento),
    )


def aplicar_filtros_titulos(query, filtros):
    tipo_data = filtros.get("tipo_data") or "vencimento"
    data_colunas = {
        "vencimento": FinanceiroContaPagarTitulo.data_vencimento,
        "emissao": FinanceiroContaPagarTitulo.data_emissao,
        "pagamento": FinanceiroContaPagarTitulo.data_pagamento,
        "criacao": func.date(FinanceiroContaPagarTitulo.criado_em),
    }
    coluna_data = data_colunas.get(tipo_data, FinanceiroContaPagarTitulo.data_vencimento)
    if filtros.get("data_inicio"):
        query = query.filter(coluna_data >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(coluna_data <= filtros["data_fim"])
    if filtros.get("fornecedor"):
        query = query.filter(FinanceiroContaPagarTitulo.fornecedor_nome_snapshot.ilike(f"%{filtros['fornecedor']}%"))
    if filtros.get("cnpj_cpf"):
        query = query.filter(FinanceiroContaPagarTitulo.fornecedor_cnpj_cpf_snapshot.ilike(f"%{filtros['cnpj_cpf']}%"))
    if filtros.get("status"):
        query = query.filter(FinanceiroContaPagarTitulo.status == filtros["status"])
    if filtros.get("origem_lancamento"):
        query = query.filter(FinanceiroContaPagarTitulo.origem_lancamento == filtros["origem_lancamento"])
    if filtros.get("tipo_pagamento"):
        query = query.filter(FinanceiroContaPagarTitulo.tipo_pagamento == filtros["tipo_pagamento"])
    if filtros.get("forma_pagamento"):
        query = query.filter(FinanceiroContaPagarTitulo.forma_pagamento == filtros["forma_pagamento"])
    if filtros.get("centro_custo_id"):
        query = query.filter(FinanceiroContaPagarTitulo.centro_custo_id == filtros["centro_custo_id"])
    if filtros.get("sub_centro_custo_equipe_id"):
        query = query.filter(FinanceiroContaPagarTitulo.sub_centro_custo_equipe_id == filtros["sub_centro_custo_equipe_id"])
    if filtros.get("sub_centro_custo_veiculo_id"):
        query = query.filter(FinanceiroContaPagarTitulo.sub_centro_custo_veiculo_id == filtros["sub_centro_custo_veiculo_id"])
    if filtros.get("cartao_credito_id"):
        query = query.filter(FinanceiroContaPagarTitulo.cartao_credito_id == filtros["cartao_credito_id"])
    if filtros.get("fatura_cartao_id"):
        query = query.filter(FinanceiroContaPagarTitulo.fatura_cartao_id == filtros["fatura_cartao_id"])
    if filtros.get("ordem_compra"):
        query = query.join(FinanceiroContaPagarTitulo.ordem_compra).filter_by(numero=filtros["ordem_compra"])
    if filtros.get("numero_nfe"):
        query = query.filter(FinanceiroContaPagarTitulo.numero_nfe.ilike(f"%{filtros['numero_nfe']}%"))
    if filtros.get("chave_acesso"):
        query = query.filter(FinanceiroContaPagarTitulo.chave_acesso_nfe.ilike(f"%{filtros['chave_acesso']}%"))
    if filtros.get("comprovante") == "com":
        query = query.filter(FinanceiroContaPagarTitulo.baixas.any(
            (FinanceiroContaPagarBaixa.status == "Ativa")
            & (FinanceiroContaPagarBaixa.comprovante_path.isnot(None))
        ))
    if filtros.get("comprovante") == "sem":
        query = query.filter(~FinanceiroContaPagarTitulo.baixas.any(
            (FinanceiroContaPagarBaixa.status == "Ativa")
            & (FinanceiroContaPagarBaixa.comprovante_path.isnot(None))
        ))
    return query


def _titulos_filtrados(filtros):
    return aplicar_filtros_titulos(_query_titulos_base(), filtros).order_by(
        FinanceiroContaPagarTitulo.data_vencimento.asc(),
        FinanceiroContaPagarTitulo.id.asc(),
    ).all()


def _query_baixas_base():
    return FinanceiroContaPagarBaixa.query.options(
        joinedload(FinanceiroContaPagarBaixa.titulo).joinedload(FinanceiroContaPagarTitulo.cartao_credito),
        joinedload(FinanceiroContaPagarBaixa.lote_baixa),
        joinedload(FinanceiroContaPagarBaixa.registrado_por),
    )


def aplicar_filtros_baixas(query, filtros):
    if filtros.get("data_inicio"):
        query = query.filter(FinanceiroContaPagarBaixa.data_pagamento >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(FinanceiroContaPagarBaixa.data_pagamento <= filtros["data_fim"])
    if filtros.get("status_baixa"):
        query = query.filter(FinanceiroContaPagarBaixa.status == filtros["status_baixa"])
    else:
        query = query.filter(FinanceiroContaPagarBaixa.status == "Ativa")
    if any(filtros.get(campo) for campo in ["fornecedor", "cnpj_cpf", "origem_lancamento", "tipo_pagamento", "forma_pagamento", "centro_custo_id", "cartao_credito_id", "fatura_cartao_id", "numero_nfe", "chave_acesso"]):
        query = query.join(FinanceiroContaPagarBaixa.titulo)
        if filtros.get("fornecedor"):
            query = query.filter(FinanceiroContaPagarTitulo.fornecedor_nome_snapshot.ilike(f"%{filtros['fornecedor']}%"))
        if filtros.get("cnpj_cpf"):
            query = query.filter(FinanceiroContaPagarTitulo.fornecedor_cnpj_cpf_snapshot.ilike(f"%{filtros['cnpj_cpf']}%"))
        if filtros.get("origem_lancamento"):
            query = query.filter(FinanceiroContaPagarTitulo.origem_lancamento == filtros["origem_lancamento"])
        if filtros.get("tipo_pagamento"):
            query = query.filter(FinanceiroContaPagarTitulo.tipo_pagamento == filtros["tipo_pagamento"])
        if filtros.get("forma_pagamento"):
            query = query.filter(FinanceiroContaPagarTitulo.forma_pagamento == filtros["forma_pagamento"])
        if filtros.get("centro_custo_id"):
            query = query.filter(FinanceiroContaPagarTitulo.centro_custo_id == filtros["centro_custo_id"])
        if filtros.get("cartao_credito_id"):
            query = query.filter(FinanceiroContaPagarTitulo.cartao_credito_id == filtros["cartao_credito_id"])
        if filtros.get("fatura_cartao_id"):
            query = query.filter(FinanceiroContaPagarTitulo.fatura_cartao_id == filtros["fatura_cartao_id"])
        if filtros.get("numero_nfe"):
            query = query.filter(FinanceiroContaPagarTitulo.numero_nfe.ilike(f"%{filtros['numero_nfe']}%"))
        if filtros.get("chave_acesso"):
            query = query.filter(FinanceiroContaPagarTitulo.chave_acesso_nfe.ilike(f"%{filtros['chave_acesso']}%"))
    return query
def _totais_titulos(titulos):
    valor_original = sum((valor_decimal(t.valor_original) for t in titulos), Decimal("0.00"))
    valor_pago = sum((valor_decimal(t.valor_pago) for t in titulos), Decimal("0.00"))
    saldo = sum((valor_decimal(calcular_saldo_titulo(t)) for t in titulos), Decimal("0.00"))
    vencido = sum((valor_decimal(calcular_saldo_titulo(t)) for t in titulos if t.data_vencimento < date.today() and t.status not in STATUS_FINAIS), Decimal("0.00"))
    return {
        "quantidade": len(titulos),
        "valor_original": valor_original,
        "valor_pago": valor_pago,
        "saldo_aberto": saldo,
        "valor_vencido": vencido,
    }


def _linha_titulo(titulo):
    saldo = valor_decimal(calcular_saldo_titulo(titulo))
    return {
        "id": titulo.id,
        "fornecedor": titulo.fornecedor_nome_snapshot,
        "cnpj_cpf": titulo.fornecedor_cnpj_cpf_snapshot or "-",
        "descricao": titulo.descricao,
        "documento": titulo.numero_documento or "-",
        "nfe": titulo.numero_nfe or "-",
        "vencimento": titulo.data_vencimento,
        "emissao": titulo.data_emissao,
        "origem": titulo.origem_lancamento,
        "tipo_pagamento": titulo.tipo_pagamento,
        "forma_pagamento": titulo.forma_pagamento,
        "cartao": titulo.cartao_credito.identificacao_segura if titulo.cartao_credito else "-",
        "fatura": titulo.fatura_cartao.competencia_formatada if titulo.fatura_cartao else "-",
        "centro_custo": titulo.centro_custo.nome if titulo.centro_custo else "-",
        "valor_original": valor_decimal(titulo.valor_original),
        "valor_pago": valor_decimal(titulo.valor_pago),
        "saldo_aberto": saldo,
        "status": titulo.status_exibicao(),
        "dias_atraso": max((date.today() - titulo.data_vencimento).days, 0),
        "titulo_id": titulo.id,
        "ordem_compra_id": titulo.ordem_compra_id,
        "fiscal_documento_id": titulo.fiscal_documento_id,
        "fatura_cartao_id": titulo.fatura_cartao_id,
    }


def _relatorio_titulos(tipo, filtros):
    titulos = _titulos_filtrados(filtros)
    hoje = date.today()
    if tipo == "vencidas":
        titulos = [t for t in titulos if t.data_vencimento < hoje and t.status not in STATUS_FINAIS and calcular_saldo_titulo(t) > 0]
    elif tipo == "a_vencer":
        limite = hoje + timedelta(days=filtros.get("dias_a_vencer") or 30)
        titulos = [t for t in titulos if hoje <= t.data_vencimento <= limite and t.status not in STATUS_FINAIS and calcular_saldo_titulo(t) > 0]
    elif tipo == "previsao":
        titulos = [t for t in titulos if t.status not in STATUS_NAO_PREVISAO and calcular_saldo_titulo(t) > 0]
    elif tipo == "sem_comprovante":
        titulos = [t for t in titulos if valor_decimal(t.valor_pago) > 0 and not any(b.status == "Ativa" and b.comprovante_disponivel for b in t.baixas)]
    return [_linha_titulo(titulo) for titulo in titulos], _totais_titulos(titulos)


def _agrupar_titulos(titulos, chave_fn):
    grupos = {}
    for titulo in titulos:
        chave = chave_fn(titulo) or "Sem classificacao"
        item = grupos.setdefault(chave, {"grupo": chave, "quantidade": 0, "valor_original": Decimal("0.00"), "valor_pago": Decimal("0.00"), "saldo_aberto": Decimal("0.00"), "valor_vencido": Decimal("0.00")})
        item["quantidade"] += 1
        item["valor_original"] += valor_decimal(titulo.valor_original)
        item["valor_pago"] += valor_decimal(titulo.valor_pago)
        saldo = valor_decimal(calcular_saldo_titulo(titulo))
        item["saldo_aberto"] += saldo
        if titulo.data_vencimento < date.today() and titulo.status not in STATUS_FINAIS:
            item["valor_vencido"] += saldo
    return sorted(grupos.values(), key=lambda item: item["saldo_aberto"], reverse=True)


def _relatorio_agrupado(tipo, filtros):
    titulos = _titulos_filtrados(filtros)
    if tipo == "fornecedor":
        linhas = _agrupar_titulos(titulos, lambda t: t.fornecedor_nome_snapshot)
    elif tipo == "centro_custo":
        linhas = _agrupar_titulos(titulos, lambda t: t.centro_custo.nome if t.centro_custo else "Sem centro de custo")
    elif tipo == "origem":
        linhas = _agrupar_titulos(titulos, lambda t: t.origem_lancamento)
    else:
        linhas = _agrupar_titulos(titulos, lambda t: f"{t.tipo_pagamento} / {t.forma_pagamento}")
    return linhas, _totais_titulos(titulos)


def _relatorio_pagamentos(filtros):
    baixas = aplicar_filtros_baixas(_query_baixas_base(), filtros).order_by(FinanceiroContaPagarBaixa.data_pagamento.desc()).all()
    linhas = []
    total = Decimal("0.00")
    for baixa in baixas:
        titulo = baixa.titulo
        total += valor_decimal(baixa.valor_pago)
        linhas.append({
            "id": baixa.id,
            "titulo_id": baixa.titulo_id,
            "fornecedor": titulo.fornecedor_nome_snapshot if titulo else "-",
            "documento": titulo.numero_documento if titulo else "-",
            "data_pagamento": baixa.data_pagamento,
            "valor_pago": valor_decimal(baixa.valor_pago),
            "forma_pagamento": baixa.forma_pagamento,
            "usuario": baixa.registrado_por.nome if baixa.registrado_por else "-",
            "comprovante": "Sim" if baixa.comprovante_disponivel else "Nao",
            "lote_id": baixa.lote_baixa_id,
            "status": baixa.status,
        })
    return linhas, {"quantidade": len(linhas), "valor_pago": total, "valor_original": Decimal("0.00"), "saldo_aberto": Decimal("0.00"), "valor_vencido": Decimal("0.00")}


def _relatorio_cartoes_faturas(filtros):
    query = FinanceiroCartaoFatura.query.options(joinedload(FinanceiroCartaoFatura.cartao_credito), joinedload(FinanceiroCartaoFatura.titulos))
    if filtros.get("cartao_credito_id"):
        query = query.filter(FinanceiroCartaoFatura.cartao_credito_id == filtros["cartao_credito_id"])
    if filtros.get("fatura_cartao_id"):
        query = query.filter(FinanceiroCartaoFatura.id == filtros["fatura_cartao_id"])
    if filtros.get("data_inicio"):
        query = query.filter(FinanceiroCartaoFatura.data_vencimento >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(FinanceiroCartaoFatura.data_vencimento <= filtros["data_fim"])
    faturas = query.order_by(FinanceiroCartaoFatura.data_vencimento.desc()).all()
    linhas = []
    total = Decimal("0.00")
    pago = Decimal("0.00")
    for fatura in faturas:
        saldo = valor_decimal((fatura.valor_total or 0) - (fatura.valor_pago or 0))
        total += valor_decimal(fatura.valor_total)
        pago += valor_decimal(fatura.valor_pago)
        linhas.append({
            "id": fatura.id,
            "fatura_cartao_id": fatura.id,
            "cartao": fatura.cartao_credito.identificacao_segura if fatura.cartao_credito else "-",
            "competencia": fatura.competencia_formatada,
            "fechamento": fatura.data_fechamento,
            "vencimento": fatura.data_vencimento,
            "valor_total": valor_decimal(fatura.valor_total),
            "valor_pago": valor_decimal(fatura.valor_pago),
            "saldo_aberto": saldo,
            "status": fatura.status_exibicao(),
            "quantidade_titulos": len(fatura.titulos),
        })
    return linhas, {"quantidade": len(linhas), "valor_original": total, "valor_pago": pago, "saldo_aberto": total - pago, "valor_vencido": Decimal("0.00")}


def _relatorio_previsao(filtros):
    linhas_titulos, totais = _relatorio_titulos("previsao", filtros)
    grupos = {}
    for linha in linhas_titulos:
        data_vencimento = linha["vencimento"]
        if filtros.get("agrupamento_previsao") == "semana":
            inicio_semana = data_vencimento - timedelta(days=data_vencimento.weekday())
            chave = inicio_semana.strftime("Semana de %d/%m/%Y")
        else:
            chave = data_vencimento.strftime("%m/%Y")
        item = grupos.setdefault(chave, {"grupo": chave, "quantidade": 0, "saldo_aberto": Decimal("0.00"), "valor_original": Decimal("0.00"), "valor_pago": Decimal("0.00"), "valor_vencido": Decimal("0.00")})
        item["quantidade"] += 1
        item["saldo_aberto"] += linha["saldo_aberto"]
        item["valor_original"] += linha["valor_original"]
        item["valor_pago"] += linha["valor_pago"]
    return list(grupos.values()), totais


def _relatorio_lotes_baixa(filtros):
    query = FinanceiroContaPagarLoteBaixa.query.options(joinedload(FinanceiroContaPagarLoteBaixa.criado_por), joinedload(FinanceiroContaPagarLoteBaixa.baixas))
    if filtros.get("data_inicio"):
        query = query.filter(FinanceiroContaPagarLoteBaixa.data_pagamento >= filtros["data_inicio"])
    if filtros.get("data_fim"):
        query = query.filter(FinanceiroContaPagarLoteBaixa.data_pagamento <= filtros["data_fim"])
    if filtros.get("forma_pagamento"):
        query = query.filter(FinanceiroContaPagarLoteBaixa.forma_pagamento == filtros["forma_pagamento"])
    if filtros.get("status_baixa"):
        status = "Estornado" if filtros["status_baixa"] == "Estornada" else filtros["status_baixa"]
        query = query.filter(FinanceiroContaPagarLoteBaixa.status == status)
    lotes = query.order_by(FinanceiroContaPagarLoteBaixa.data_pagamento.desc()).all()
    linhas = []
    total = Decimal("0.00")
    for lote in lotes:
        total += valor_decimal(lote.valor_total_baixado)
        linhas.append({
            "id": lote.id,
            "lote_id": lote.id,
            "data_pagamento": lote.data_pagamento,
            "forma_pagamento": lote.forma_pagamento,
            "usuario": lote.criado_por.nome if lote.criado_por else "-",
            "total_titulos": lote.total_titulos,
            "valor_total": valor_decimal(lote.valor_total_baixado),
            "status": lote.status,
            "comprovante": "Sim" if lote.comprovante_disponivel else "Nao",
        })
    return linhas, {"quantidade": len(linhas), "valor_original": total, "valor_pago": total, "saldo_aberto": Decimal("0.00"), "valor_vencido": Decimal("0.00")}


def montar_relatorio(tipo_relatorio, filtros):
    tipo = tipo_relatorio if tipo_relatorio in TIPOS_RELATORIO_DICT else "periodo"
    if tipo in ("periodo", "vencidas", "a_vencer", "sem_comprovante"):
        linhas, totais = _relatorio_titulos(tipo, filtros)
        colunas = ["id", "fornecedor", "documento", "nfe", "vencimento", "origem", "forma_pagamento", "valor_original", "valor_pago", "saldo_aberto", "status"]
        if tipo == "vencidas":
            colunas.insert(5, "dias_atraso")
    elif tipo in ("fornecedor", "centro_custo", "origem", "pagamento"):
        linhas, totais = _relatorio_agrupado(tipo, filtros)
        colunas = ["grupo", "quantidade", "valor_original", "valor_pago", "saldo_aberto", "valor_vencido"]
    elif tipo == "pagamentos":
        linhas, totais = _relatorio_pagamentos(filtros)
        colunas = ["id", "titulo_id", "fornecedor", "documento", "data_pagamento", "valor_pago", "forma_pagamento", "usuario", "comprovante", "lote_id", "status"]
    elif tipo == "cartoes_faturas":
        linhas, totais = _relatorio_cartoes_faturas(filtros)
        colunas = ["id", "cartao", "competencia", "fechamento", "vencimento", "valor_total", "valor_pago", "saldo_aberto", "status", "quantidade_titulos"]
    elif tipo == "previsao":
        linhas, totais = _relatorio_previsao(filtros)
        colunas = ["grupo", "quantidade", "valor_original", "valor_pago", "saldo_aberto"]
    else:
        linhas, totais = _relatorio_lotes_baixa(filtros)
        colunas = ["id", "data_pagamento", "forma_pagamento", "usuario", "total_titulos", "valor_total", "status", "comprovante"]
    return {
        "tipo": tipo,
        "titulo": TIPOS_RELATORIO_DICT[tipo],
        "colunas": colunas,
        "linhas": linhas,
        "totais": totais,
    }


def dashboard_avancado(filtros):
    titulos = _titulos_filtrados(filtros)
    hoje = date.today()
    em_7 = hoje + timedelta(days=7)
    em_30 = hoje + timedelta(days=30)
    abertos = [t for t in titulos if t.status not in STATUS_FINAIS and calcular_saldo_titulo(t) > 0]
    vencidos = [t for t in abertos if t.data_vencimento < hoje]
    a_vencer_hoje = [t for t in abertos if t.data_vencimento == hoje]
    a_vencer_7 = [t for t in abertos if hoje <= t.data_vencimento <= em_7]
    a_vencer_30 = [t for t in abertos if hoje <= t.data_vencimento <= em_30]
    pagos = [t for t in titulos if t.status == "Pago"]
    parciais = [t for t in titulos if t.status == "Pago parcialmente"]
    sem_comprovante = [t for t in titulos if valor_decimal(t.valor_pago) > 0 and not any(b.status == "Ativa" and b.comprovante_disponivel for b in t.baixas)]

    def somar_saldo(lista):
        return sum((valor_decimal(calcular_saldo_titulo(t)) for t in lista), Decimal("0.00"))

    pagamentos, total_pagamentos = _relatorio_pagamentos({**filtros, "status_baixa": filtros.get("status_baixa") or "Ativa"})
    valor_cartoes_abertos = FinanceiroCartaoFatura.query.filter(FinanceiroCartaoFatura.status.in_(["Aberta", "Fechada", "Agendada"])).with_entities(func.coalesce(func.sum(FinanceiroCartaoFatura.valor_total - FinanceiroCartaoFatura.valor_pago), 0)).scalar()
    return {
        "cards": {
            "total_aberto": somar_saldo(abertos),
            "total_vencido": somar_saldo(vencidos),
            "total_vence_hoje": somar_saldo(a_vencer_hoje),
            "total_vence_7": somar_saldo(a_vencer_7),
            "total_vence_30": somar_saldo(a_vencer_30),
            "total_pago_periodo": total_pagamentos["valor_pago"],
            "total_pago_parcial": sum((valor_decimal(t.valor_pago) for t in parciais), Decimal("0.00")),
            "total_aguardando_conferencia": somar_saldo([t for t in abertos if t.status == "Aguardando conferencia"]),
            "qtd_abertos": len(abertos),
            "qtd_pagos": len(pagos),
            "qtd_vencidos": len(vencidos),
            "qtd_sem_comprovante": len(sem_comprovante),
            "previsao_periodo": somar_saldo(abertos),
            "valor_cartoes_abertos": valor_decimal(valor_cartoes_abertos),
            "valor_oc_integrada": sum((valor_decimal(t.valor_original) for t in titulos if t.origem_lancamento == "Ordem de Compra"), Decimal("0.00")),
            "valor_xml_integrado": sum((valor_decimal(t.valor_original) for t in titulos if t.origem_lancamento == "XML Fiscal"), Decimal("0.00")),
        },
        "resumos": {
            "por_status": _agrupar_titulos(titulos, lambda t: t.status_exibicao()),
            "por_fornecedor": _agrupar_titulos(titulos, lambda t: t.fornecedor_nome_snapshot)[:8],
            "por_centro_custo": _agrupar_titulos(titulos, lambda t: t.centro_custo.nome if t.centro_custo else "Sem centro de custo")[:8],
            "por_origem": _agrupar_titulos(titulos, lambda t: t.origem_lancamento),
            "por_forma": _agrupar_titulos(titulos, lambda t: t.forma_pagamento),
        },
        "tabelas": {
            "proximos_vencimentos": [_linha_titulo(t) for t in sorted(a_vencer_30, key=lambda t: t.data_vencimento)[:10]],
            "vencidos_antigos": [_linha_titulo(t) for t in sorted(vencidos, key=lambda t: t.data_vencimento)[:10]],
            "maiores_abertos": [_linha_titulo(t) for t in sorted(abertos, key=lambda t: calcular_saldo_titulo(t), reverse=True)[:10]],
            "faturas_proximas": _relatorio_cartoes_faturas({"data_inicio": hoje, "data_fim": em_30})[0][:10],
        },
    }


def valor_coluna(linha, coluna):
    valor = linha.get(coluna)
    if isinstance(valor, Decimal):
        return moeda(valor)
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    if valor is None:
        return "-"
    return valor


def gerar_csv_relatorio(relatorio):
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow([relatorio["titulo"]])
    escritor.writerow([])
    escritor.writerow(relatorio["colunas"])
    for linha in relatorio["linhas"]:
        escritor.writerow([valor_coluna(linha, coluna) for coluna in relatorio["colunas"]])
    escritor.writerow([])
    escritor.writerow(["Quantidade", relatorio["totais"].get("quantidade", 0)])
    escritor.writerow(["Valor original", moeda(relatorio["totais"].get("valor_original"))])
    escritor.writerow(["Valor pago", moeda(relatorio["totais"].get("valor_pago"))])
    escritor.writerow(["Saldo em aberto", moeda(relatorio["totais"].get("saldo_aberto"))])
    escritor.writerow(["Valor vencido", moeda(relatorio["totais"].get("valor_vencido"))])
    return saida.getvalue()


def nome_arquivo_relatorio(tipo):
    sufixo = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"contas_a_pagar_{tipo}_{sufixo}.csv"


