from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import func, or_

from app.extensions import db
from app.models import (
    CentroCusto,
    FinanceiroContaPagarTitulo,
    SuprimentosFornecedor,
)

ORIGENS_LANCAMENTO = [
    "Manual",
    "Ordem de Compra",
    "XML Fiscal",
    "Cartao de Credito",
]
TIPOS_PAGAMENTO = ["Faturado", "Cartao de Credito"]
FORMAS_PAGAMENTO = [
    "Boleto",
    "Pix",
    "Transferencia",
    "Deposito",
    "Cartao de Credito",
    "Outro",
]
STATUS_TITULO = [
    "Rascunho",
    "Aguardando conferencia",
    "Agendado",
    "A vencer",
    "Vencido",
    "Pago",
    "Pago parcialmente",
    "Cancelado",
    "Estornado",
]
STATUS_ABERTOS = [
    "Rascunho",
    "Aguardando conferencia",
    "Agendado",
    "A vencer",
    "Vencido",
    "Pago parcialmente",
]
STATUS_FINAIS = ["Pago", "Cancelado", "Estornado"]


def normalizar_documento(valor):
    return re.sub(r"\D", "", (valor or "")) or None


def normalizar_texto(valor, upper=True):
    valor = (valor or "").strip()
    if upper:
        return valor.upper()
    return valor


def parse_data(valor, obrigatorio=False, nome_campo="Data"):
    valor = (valor or "").strip()
    if not valor:
        if obrigatorio:
            raise ValueError(f"{nome_campo} e obrigatoria.")
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{nome_campo} invalida.") from exc


def parse_competencia(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(f"{valor}-01", "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Competencia invalida.") from exc


def parse_decimal(valor, obrigatorio=False, nome_campo="Valor"):
    valor = (valor or "").strip()
    if not valor:
        if obrigatorio:
            raise ValueError(f"{nome_campo} e obrigatorio.")
        return Decimal("0.00")
    valor = valor.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(valor).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"{nome_campo} invalido.") from exc
    if numero < 0:
        raise ValueError(f"{nome_campo} nao pode ser negativo.")
    return numero


def parse_int(valor, padrao=1, nome_campo="Numero"):
    valor = (valor or "").strip()
    if not valor:
        return padrao
    try:
        numero = int(valor)
    except ValueError as exc:
        raise ValueError(f"{nome_campo} invalido.") from exc
    return numero


def buscar_opcoes_formulario():
    return {
        "fornecedores": SuprimentosFornecedor.query.filter_by(ativo=True).order_by(
            SuprimentosFornecedor.razao_social.asc()
        ).all(),
        "centros_custo": CentroCusto.query.filter_by(ativo=True).order_by(
            CentroCusto.nome.asc()
        ).all(),
        "origens": ORIGENS_LANCAMENTO,
        "tipos_pagamento": TIPOS_PAGAMENTO,
        "formas_pagamento": FORMAS_PAGAMENTO,
        "status": STATUS_TITULO,
    }


def buscar_titulo_por_id(titulo_id):
    return FinanceiroContaPagarTitulo.query.get(titulo_id)


def _aplicar_filtros(query, filtros):
    fornecedor = (filtros.get("fornecedor") or "").strip()
    documento = normalizar_documento(filtros.get("cnpj_cpf"))
    status = (filtros.get("status") or "").strip()
    origem = (filtros.get("origem_lancamento") or "").strip()
    tipo = (filtros.get("tipo_pagamento") or "").strip()
    forma = (filtros.get("forma_pagamento") or "").strip()
    numero_documento = (filtros.get("numero_documento") or "").strip()
    numero_nfe = (filtros.get("numero_nfe") or "").strip()
    ordem_compra = (filtros.get("ordem_compra") or "").strip()
    centro_custo_id = (filtros.get("centro_custo_id") or "").strip()

    if fornecedor:
        query = query.filter(FinanceiroContaPagarTitulo.fornecedor_nome_snapshot.ilike(f"%{fornecedor}%"))
    if documento:
        query = query.filter(FinanceiroContaPagarTitulo.fornecedor_cnpj_cpf_snapshot.ilike(f"%{documento}%"))
    if status:
        query = query.filter(FinanceiroContaPagarTitulo.status == status)
    if origem:
        query = query.filter(FinanceiroContaPagarTitulo.origem_lancamento == origem)
    if tipo:
        query = query.filter(FinanceiroContaPagarTitulo.tipo_pagamento == tipo)
    if forma:
        query = query.filter(FinanceiroContaPagarTitulo.forma_pagamento == forma)
    if numero_documento:
        query = query.filter(FinanceiroContaPagarTitulo.numero_documento.ilike(f"%{numero_documento}%"))
    if numero_nfe:
        query = query.filter(FinanceiroContaPagarTitulo.numero_nfe.ilike(f"%{numero_nfe}%"))
    if ordem_compra.isdigit():
        query = query.filter(FinanceiroContaPagarTitulo.ordem_compra_id == int(ordem_compra))
    if centro_custo_id.isdigit():
        query = query.filter(FinanceiroContaPagarTitulo.centro_custo_id == int(centro_custo_id))

    try:
        vencimento_inicio = parse_data(filtros.get("vencimento_inicio"), nome_campo="Vencimento inicial")
        vencimento_fim = parse_data(filtros.get("vencimento_fim"), nome_campo="Vencimento final")
    except ValueError:
        vencimento_inicio = None
        vencimento_fim = None

    if vencimento_inicio:
        query = query.filter(FinanceiroContaPagarTitulo.data_vencimento >= vencimento_inicio)
    if vencimento_fim:
        query = query.filter(FinanceiroContaPagarTitulo.data_vencimento <= vencimento_fim)

    return query


def listar_titulos(filtros):
    query = FinanceiroContaPagarTitulo.query
    query = _aplicar_filtros(query, filtros)
    return query.order_by(
        FinanceiroContaPagarTitulo.data_vencimento.asc(),
        FinanceiroContaPagarTitulo.id.desc(),
    ).all()


def indicadores_dashboard(hoje=None):
    hoje = hoje or date.today()
    inicio_mes = hoje.replace(day=1)
    if hoje.month == 12:
        inicio_proximo_mes = hoje.replace(year=hoje.year + 1, month=1, day=1)
    else:
        inicio_proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
    em_7_dias = hoje + timedelta(days=7)

    query_abertos = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.status.notin_(STATUS_FINAIS)
    )

    total_aberto = query_abertos.with_entities(
        func.coalesce(func.sum(FinanceiroContaPagarTitulo.valor_original - FinanceiroContaPagarTitulo.valor_pago), 0)
    ).scalar()
    total_vencido = query_abertos.filter(
        FinanceiroContaPagarTitulo.data_vencimento < hoje
    ).with_entities(
        func.coalesce(func.sum(FinanceiroContaPagarTitulo.valor_original - FinanceiroContaPagarTitulo.valor_pago), 0)
    ).scalar()
    total_7_dias = query_abertos.filter(
        FinanceiroContaPagarTitulo.data_vencimento >= hoje,
        FinanceiroContaPagarTitulo.data_vencimento <= em_7_dias,
    ).with_entities(
        func.coalesce(func.sum(FinanceiroContaPagarTitulo.valor_original - FinanceiroContaPagarTitulo.valor_pago), 0)
    ).scalar()
    total_mes = query_abertos.filter(
        FinanceiroContaPagarTitulo.data_vencimento >= inicio_mes,
        FinanceiroContaPagarTitulo.data_vencimento < inicio_proximo_mes,
    ).with_entities(
        func.coalesce(func.sum(FinanceiroContaPagarTitulo.valor_original - FinanceiroContaPagarTitulo.valor_pago), 0)
    ).scalar()

    return {
        "total_aberto": total_aberto or Decimal("0.00"),
        "total_vencido": total_vencido or Decimal("0.00"),
        "total_7_dias": total_7_dias or Decimal("0.00"),
        "total_mes": total_mes or Decimal("0.00"),
        "qtd_aguardando_conferencia": query_abertos.filter(
            FinanceiroContaPagarTitulo.status == "Aguardando conferencia"
        ).count(),
        "qtd_manuais": FinanceiroContaPagarTitulo.query.filter(
            FinanceiroContaPagarTitulo.origem_lancamento == "Manual"
        ).count(),
    }


def salvar_titulo(dados, titulo=None, usuario=None):
    titulo = titulo or FinanceiroContaPagarTitulo()

    try:
        fornecedor_id = parse_int(dados.get("fornecedor_id"), padrao=0, nome_campo="Fornecedor")
        fornecedor = SuprimentosFornecedor.query.get(fornecedor_id) if fornecedor_id else None
        fornecedor_nome = normalizar_texto(dados.get("fornecedor_nome_snapshot"))
        fornecedor_documento = normalizar_documento(dados.get("fornecedor_cnpj_cpf_snapshot"))

        if fornecedor:
            fornecedor_nome = fornecedor.razao_social
            fornecedor_documento = fornecedor.cnpj_cpf or fornecedor_documento

        if not fornecedor_nome:
            raise ValueError("Fornecedor ou nome do fornecedor e obrigatorio.")

        descricao = normalizar_texto(dados.get("descricao"))
        if not descricao:
            raise ValueError("Descricao e obrigatoria.")

        valor_original = parse_decimal(dados.get("valor_original"), obrigatorio=True, nome_campo="Valor original")
        if valor_original <= 0:
            raise ValueError("Valor original deve ser maior que zero.")

        origem = dados.get("origem_lancamento") or "Manual"
        if origem not in ORIGENS_LANCAMENTO:
            raise ValueError("Origem do lancamento invalida.")
        if not titulo.id:
            origem = "Manual"

        tipo = dados.get("tipo_pagamento") or ""
        if tipo not in TIPOS_PAGAMENTO:
            raise ValueError("Tipo de pagamento invalido.")

        forma = dados.get("forma_pagamento") or ""
        if forma not in FORMAS_PAGAMENTO:
            raise ValueError("Forma de pagamento invalida.")

        status = dados.get("status") or "Agendado"
        if status not in STATUS_TITULO:
            raise ValueError("Status invalido.")

        parcela_numero = parse_int(dados.get("parcela_numero"), nome_campo="Numero da parcela")
        total_parcelas = parse_int(dados.get("total_parcelas"), nome_campo="Total de parcelas")
        if total_parcelas < 1:
            raise ValueError("Total de parcelas deve ser no minimo 1.")
        if parcela_numero < 1:
            raise ValueError("Numero da parcela deve ser no minimo 1.")
        if parcela_numero > total_parcelas:
            raise ValueError("Parcela atual nao pode ser maior que total de parcelas.")

        titulo.fornecedor_id = fornecedor.id if fornecedor else None
        titulo.fornecedor_nome_snapshot = fornecedor_nome
        titulo.fornecedor_cnpj_cpf_snapshot = fornecedor_documento
        titulo.descricao = descricao
        titulo.numero_documento = normalizar_texto(dados.get("numero_documento"), upper=False) or None
        titulo.numero_nfe = normalizar_texto(dados.get("numero_nfe"), upper=False) or None
        titulo.chave_acesso_nfe = normalizar_documento(dados.get("chave_acesso_nfe"))
        titulo.origem_lancamento = origem
        titulo.tipo_pagamento = tipo
        titulo.forma_pagamento = forma
        titulo.competencia = parse_competencia(dados.get("competencia"))
        titulo.data_emissao = parse_data(dados.get("data_emissao"), nome_campo="Data de emissao")
        titulo.data_vencimento = parse_data(dados.get("data_vencimento"), obrigatorio=True, nome_campo="Data de vencimento")
        titulo.valor_original = valor_original
        titulo.valor_desconto = parse_decimal(dados.get("valor_desconto"), nome_campo="Valor de desconto")
        titulo.valor_acrescimo = parse_decimal(dados.get("valor_acrescimo"), nome_campo="Valor de acrescimo")
        titulo.valor_juros_multa = parse_decimal(dados.get("valor_juros_multa"), nome_campo="Valor de juros/multa")
        titulo.valor_pago = parse_decimal(dados.get("valor_pago"), nome_campo="Valor pago")
        titulo.parcela_numero = parcela_numero
        titulo.total_parcelas = total_parcelas
        titulo.centro_custo_id = parse_int(dados.get("centro_custo_id"), padrao=0, nome_campo="Centro de custo") or None
        titulo.status = status
        titulo.observacoes = normalizar_texto(dados.get("observacoes")) or None
        titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
        if not titulo.id:
            titulo.criado_por_usuario_id = getattr(usuario, "id", None)
            db.session.add(titulo)

        db.session.commit()
        return True, "Titulo salvo com sucesso.", titulo
    except ValueError as exc:
        db.session.rollback()
        return False, str(exc), titulo


def cancelar_titulo(titulo, usuario=None):
    if not titulo:
        return False, "Titulo nao encontrado."
    if titulo.status in STATUS_FINAIS:
        return False, "Titulo nao pode ser cancelado neste status."

    titulo.status = "Cancelado"
    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    return True, "Titulo cancelado com sucesso."
