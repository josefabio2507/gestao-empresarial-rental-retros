from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import CentroCusto, Equipe, FinanceiroContaReceberTitulo
from app.utils.datas import agora_brasil


STATUS_RASCUNHO = "Rascunho"
STATUS_AGUARDANDO_FATURAMENTO = "Aguardando faturamento"
STATUS_FATURADO = "Faturado"
STATUS_AGENDADO = "Agendado"
STATUS_A_VENCER = "A vencer"
STATUS_VENCIDO = "Vencido"
STATUS_RECEBIDO = "Recebido"
STATUS_RECEBIDO_PARCIALMENTE = "Recebido parcialmente"
STATUS_CANCELADO = "Cancelado"
STATUS_ESTORNADO = "Estornado"
STATUS_INADIMPLENTE = "Inadimplente"

STATUS_TITULOS_RECEBER = [
    STATUS_RASCUNHO,
    STATUS_AGUARDANDO_FATURAMENTO,
    STATUS_FATURADO,
    STATUS_AGENDADO,
    STATUS_A_VENCER,
    STATUS_VENCIDO,
    STATUS_RECEBIDO,
    STATUS_RECEBIDO_PARCIALMENTE,
    STATUS_CANCELADO,
    STATUS_ESTORNADO,
    STATUS_INADIMPLENTE,
]
STATUS_INATIVOS = {STATUS_CANCELADO, STATUS_ESTORNADO}
STATUS_RECEBIDOS = {STATUS_RECEBIDO}

ORIGEM_MANUAL = "Manual"
ORIGENS_LANCAMENTO = [
    ORIGEM_MANUAL,
    "Nota Fiscal Emitida",
    "Medição",
    "Contrato",
    "Reembolso",
    "Outro",
]


def texto(valor):
    return valor.strip() if valor else ""


def texto_maiusculo(valor):
    valor = texto(valor)
    return valor.upper() if valor else ""


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def decimal_ou_zero(valor):
    valor = texto(str(valor)) if valor is not None else ""

    if not valor:
        return Decimal("0.00")

    valor = valor.replace("R$", "").replace(" ", "")
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")

    try:
        return Decimal(valor).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def inteiro_ou_none(valor):
    valor = texto(str(valor)) if valor is not None else ""
    if not valor:
        return None
    try:
        return int(valor)
    except ValueError:
        return None


def data_ou_none(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        ano, mes, dia = [int(parte) for parte in valor.split("-")]
        return date(ano, mes, dia)
    except (TypeError, ValueError):
        return None


def formatar_moeda_brl(valor):
    if valor is None:
        return "R$ 0,00"

    try:
        valor_decimal = Decimal(valor).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return "R$ 0,00"

    texto_valor = f"{valor_decimal:,.2f}"
    texto_valor = texto_valor.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto_valor}"


def formatar_data_brasil(valor):
    return valor.strftime("%d/%m/%Y") if valor else "-"


def _aplicar_dados(titulo, form_data, usuario=None, novo=False):
    titulo.cliente_nome_snapshot = texto_maiusculo(form_data.get("cliente_nome_snapshot"))
    titulo.cliente_cnpj_cpf_snapshot = somente_digitos(form_data.get("cliente_cnpj_cpf_snapshot"))
    titulo.cliente_email_financeiro_snapshot = texto(form_data.get("cliente_email_financeiro_snapshot")).lower()
    titulo.cliente_telefone_snapshot = somente_digitos(form_data.get("cliente_telefone_snapshot"))
    titulo.descricao = texto_maiusculo(form_data.get("descricao"))
    titulo.numero_documento = texto_maiusculo(form_data.get("numero_documento"))
    titulo.numero_nota_fiscal = texto_maiusculo(form_data.get("numero_nota_fiscal"))
    titulo.chave_acesso_nfe_nfse = texto_maiusculo(form_data.get("chave_acesso_nfe_nfse"))
    titulo.contrato_id = inteiro_ou_none(form_data.get("contrato_id"))
    titulo.medicao_id = inteiro_ou_none(form_data.get("medicao_id"))
    titulo.origem_lancamento = texto(form_data.get("origem_lancamento")) or ORIGEM_MANUAL
    titulo.competencia = texto(form_data.get("competencia"))
    titulo.data_emissao = data_ou_none(form_data.get("data_emissao"))
    titulo.data_vencimento = data_ou_none(form_data.get("data_vencimento"))
    titulo.data_recebimento = data_ou_none(form_data.get("data_recebimento"))
    titulo.valor_original = decimal_ou_zero(form_data.get("valor_original"))
    titulo.valor_desconto = decimal_ou_zero(form_data.get("valor_desconto"))
    titulo.valor_acrescimo = decimal_ou_zero(form_data.get("valor_acrescimo"))
    titulo.valor_juros_multa = decimal_ou_zero(form_data.get("valor_juros_multa"))
    titulo.valor_recebido = decimal_ou_zero(form_data.get("valor_recebido"))
    titulo.parcela_numero = inteiro_ou_none(form_data.get("parcela_numero")) or 1
    titulo.total_parcelas = inteiro_ou_none(form_data.get("total_parcelas")) or 1
    titulo.centro_custo_id = inteiro_ou_none(form_data.get("centro_custo_id"))
    titulo.sub_centro_custo_equipe_id = inteiro_ou_none(form_data.get("sub_centro_custo_equipe_id"))
    titulo.sub_centro_custo_veiculo_id = inteiro_ou_none(form_data.get("sub_centro_custo_veiculo_id"))
    titulo.status = texto(form_data.get("status")) or STATUS_A_VENCER
    titulo.observacoes = texto_maiusculo(form_data.get("observacoes"))

    if novo:
        titulo.criado_por_usuario_id = getattr(usuario, "id", None)
    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)


def _validar_titulo(titulo):
    if not titulo.cliente_nome_snapshot:
        return False, "Informe o cliente."

    if not titulo.data_vencimento:
        return False, "Informe a data de vencimento."

    if titulo.valor_original is None or titulo.valor_original <= 0:
        return False, "Informe um valor maior que zero."

    valores_nao_negativos = [
        titulo.valor_desconto,
        titulo.valor_acrescimo,
        titulo.valor_juros_multa,
        titulo.valor_recebido,
    ]
    if any(valor is None or valor < 0 for valor in valores_nao_negativos):
        return False, "Valores de desconto, acréscimo, juros/multa e recebido não podem ser negativos."

    if titulo.valor_recebido > titulo.valor_liquido:
        return False, "Saldo em aberto não pode ficar negativo nesta fase."

    if titulo.origem_lancamento not in ORIGENS_LANCAMENTO:
        return False, "Origem do lançamento inválida."

    if titulo.status not in STATUS_TITULOS_RECEBER:
        return False, "Status inválido."

    return True, ""


def salvar_titulo_receber(form_data, titulo=None, usuario=None):
    novo = titulo is None
    titulo = titulo or FinanceiroContaReceberTitulo()
    status_anterior = titulo.status

    _aplicar_dados(titulo, form_data, usuario=usuario, novo=novo)
    valido, mensagem = _validar_titulo(titulo)

    if not valido:
        db.session.rollback()
        return False, mensagem, titulo, False

    db.session.add(titulo)
    db.session.commit()

    status_alterado = (not novo) and status_anterior != titulo.status
    mensagem = "Título a receber cadastrado com sucesso." if novo else "Título a receber atualizado com sucesso."
    return True, mensagem, titulo, status_alterado


def cancelar_titulo_receber(titulo, motivo=None, usuario=None):
    if titulo.status in STATUS_INATIVOS:
        return False, "Título já está cancelado ou estornado."

    titulo.status = STATUS_CANCELADO
    titulo.cancelado_em = agora_brasil()
    titulo.cancelado_por_usuario_id = getattr(usuario, "id", None)
    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
    titulo.motivo_cancelamento = texto_maiusculo(motivo) or "CANCELAMENTO MANUAL"
    db.session.commit()
    return True, "Título a receber cancelado com sucesso."


def buscar_titulo_por_id(titulo_id):
    return FinanceiroContaReceberTitulo.query.options(
        joinedload(FinanceiroContaReceberTitulo.centro_custo),
        joinedload(FinanceiroContaReceberTitulo.sub_centro_custo_equipe),
        joinedload(FinanceiroContaReceberTitulo.criado_por),
        joinedload(FinanceiroContaReceberTitulo.atualizado_por),
        joinedload(FinanceiroContaReceberTitulo.cancelado_por),
    ).get(titulo_id)


def listar_titulos_receber(filtros=None):
    filtros = filtros or {}
    query = FinanceiroContaReceberTitulo.query.options(
        joinedload(FinanceiroContaReceberTitulo.centro_custo),
    )

    cliente = texto(filtros.get("cliente"))
    if cliente:
        query = query.filter(FinanceiroContaReceberTitulo.cliente_nome_snapshot.ilike(f"%{cliente}%"))

    cnpj_cpf = somente_digitos(filtros.get("cnpj_cpf"))
    if cnpj_cpf:
        query = query.filter(FinanceiroContaReceberTitulo.cliente_cnpj_cpf_snapshot.ilike(f"%{cnpj_cpf}%"))

    status = texto(filtros.get("status"))
    if status:
        query = query.filter(FinanceiroContaReceberTitulo.status == status)

    origem = texto(filtros.get("origem"))
    if origem:
        query = query.filter(FinanceiroContaReceberTitulo.origem_lancamento == origem)

    competencia = texto(filtros.get("competencia"))
    if competencia:
        query = query.filter(FinanceiroContaReceberTitulo.competencia == competencia)

    numero_documento = texto(filtros.get("numero_documento"))
    if numero_documento:
        query = query.filter(FinanceiroContaReceberTitulo.numero_documento.ilike(f"%{numero_documento}%"))

    numero_nota_fiscal = texto(filtros.get("numero_nota_fiscal"))
    if numero_nota_fiscal:
        query = query.filter(FinanceiroContaReceberTitulo.numero_nota_fiscal.ilike(f"%{numero_nota_fiscal}%"))

    contrato_id = inteiro_ou_none(filtros.get("contrato_id"))
    if contrato_id:
        query = query.filter(FinanceiroContaReceberTitulo.contrato_id == contrato_id)

    centro_custo_id = inteiro_ou_none(filtros.get("centro_custo_id"))
    if centro_custo_id:
        query = query.filter(FinanceiroContaReceberTitulo.centro_custo_id == centro_custo_id)

    emissao_inicio = data_ou_none(filtros.get("emissao_inicio"))
    emissao_fim = data_ou_none(filtros.get("emissao_fim"))
    vencimento_inicio = data_ou_none(filtros.get("vencimento_inicio"))
    vencimento_fim = data_ou_none(filtros.get("vencimento_fim"))

    if emissao_inicio:
        query = query.filter(FinanceiroContaReceberTitulo.data_emissao >= emissao_inicio)
    if emissao_fim:
        query = query.filter(FinanceiroContaReceberTitulo.data_emissao <= emissao_fim)
    if vencimento_inicio:
        query = query.filter(FinanceiroContaReceberTitulo.data_vencimento >= vencimento_inicio)
    if vencimento_fim:
        query = query.filter(FinanceiroContaReceberTitulo.data_vencimento <= vencimento_fim)

    hoje = agora_brasil().date()
    if filtros.get("vencidos"):
        query = query.filter(
            FinanceiroContaReceberTitulo.data_vencimento < hoje,
            ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS | STATUS_RECEBIDOS),
            FinanceiroContaReceberTitulo.valor_recebido < (
                FinanceiroContaReceberTitulo.valor_original
                + FinanceiroContaReceberTitulo.valor_acrescimo
                + FinanceiroContaReceberTitulo.valor_juros_multa
                - FinanceiroContaReceberTitulo.valor_desconto
            ),
        )

    if filtros.get("a_vencer"):
        query = query.filter(
            FinanceiroContaReceberTitulo.data_vencimento >= hoje,
            ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS | STATUS_RECEBIDOS),
            FinanceiroContaReceberTitulo.valor_recebido < (
                FinanceiroContaReceberTitulo.valor_original
                + FinanceiroContaReceberTitulo.valor_acrescimo
                + FinanceiroContaReceberTitulo.valor_juros_multa
                - FinanceiroContaReceberTitulo.valor_desconto
            ),
        )

    return query.order_by(
        FinanceiroContaReceberTitulo.data_vencimento.asc(),
        FinanceiroContaReceberTitulo.id.desc(),
    ).all()


def buscar_centros_custo_ativos():
    return CentroCusto.query.filter_by(ativo=True).order_by(CentroCusto.nome.asc()).all()


def buscar_equipes_ativas():
    return Equipe.query.filter_by(ativo=True).order_by(Equipe.nome.asc()).all()


def _saldo_expr():
    return (
        FinanceiroContaReceberTitulo.valor_original
        + FinanceiroContaReceberTitulo.valor_acrescimo
        + FinanceiroContaReceberTitulo.valor_juros_multa
        - FinanceiroContaReceberTitulo.valor_desconto
        - FinanceiroContaReceberTitulo.valor_recebido
    )


def _query_ativos():
    return FinanceiroContaReceberTitulo.query.filter(
        ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS),
    )


def _somar_saldo(query):
    total = query.with_entities(func.coalesce(func.sum(_saldo_expr()), 0)).scalar()
    return Decimal(total or 0).quantize(Decimal("0.01"))


def gerar_dashboard(filtros=None):
    filtros = filtros or {}
    hoje = agora_brasil().date()
    mes_ref = texto(filtros.get("mes")) or hoje.strftime("%Y-%m")
    try:
        ano, mes = [int(parte) for parte in mes_ref.split("-")]
        inicio_mes = date(ano, mes, 1)
    except ValueError:
        mes_ref = hoje.strftime("%Y-%m")
        inicio_mes = date(hoje.year, hoje.month, 1)

    if inicio_mes.month == 12:
        inicio_proximo_mes = date(inicio_mes.year + 1, 1, 1)
    else:
        inicio_proximo_mes = date(inicio_mes.year, inicio_mes.month + 1, 1)

    ativos = _query_ativos()
    abertos = ativos.filter(
        ~FinanceiroContaReceberTitulo.status.in_(STATUS_RECEBIDOS),
        _saldo_expr() > 0,
    )
    vencidos = abertos.filter(FinanceiroContaReceberTitulo.data_vencimento < hoje)
    proximos_7 = abertos.filter(
        FinanceiroContaReceberTitulo.data_vencimento >= hoje,
        FinanceiroContaReceberTitulo.data_vencimento <= hoje + timedelta(days=7),
    )
    proximos_30 = abertos.filter(
        FinanceiroContaReceberTitulo.data_vencimento >= hoje,
        FinanceiroContaReceberTitulo.data_vencimento <= hoje + timedelta(days=30),
    )
    mes_query = abertos.filter(
        FinanceiroContaReceberTitulo.data_vencimento >= inicio_mes,
        FinanceiroContaReceberTitulo.data_vencimento < inicio_proximo_mes,
    )
    aguardando = ativos.filter(FinanceiroContaReceberTitulo.status == STATUS_AGUARDANDO_FATURAMENTO)
    faturados = ativos.filter(
        or_(
            FinanceiroContaReceberTitulo.status == STATUS_FATURADO,
            FinanceiroContaReceberTitulo.numero_nota_fiscal.isnot(None),
        )
    )

    cards = {
        "total_mes": _somar_saldo(mes_query),
        "total_aberto": _somar_saldo(abertos),
        "total_vencido": _somar_saldo(vencidos),
        "total_7_dias": _somar_saldo(proximos_7),
        "total_30_dias": _somar_saldo(proximos_30),
        "total_aguardando_faturamento": _somar_saldo(aguardando),
        "total_faturado": _somar_saldo(faturados),
        "quantidade_abertos": abertos.count(),
        "quantidade_vencidos": vencidos.count(),
        "saldo_geral_aberto": _somar_saldo(abertos),
    }

    proximos_vencimentos = abertos.filter(
        FinanceiroContaReceberTitulo.data_vencimento >= hoje,
    ).order_by(FinanceiroContaReceberTitulo.data_vencimento.asc()).limit(50).all()
    recebiveis_vencidos = vencidos.order_by(FinanceiroContaReceberTitulo.data_vencimento.asc()).limit(50).all()
    maiores_abertos = abertos.order_by(_saldo_expr().desc()).limit(50).all()
    recebimentos_recentes = ativos.filter(
        FinanceiroContaReceberTitulo.valor_recebido > 0,
    ).order_by(
        FinanceiroContaReceberTitulo.data_recebimento.desc().nullslast(),
        FinanceiroContaReceberTitulo.atualizado_em.desc(),
    ).limit(50).all()
    clientes_saldo = abertos.with_entities(
        FinanceiroContaReceberTitulo.cliente_nome_snapshot.label("cliente"),
        func.coalesce(func.sum(_saldo_expr()), 0).label("saldo"),
    ).group_by(
        FinanceiroContaReceberTitulo.cliente_nome_snapshot,
    ).order_by(func.coalesce(func.sum(_saldo_expr()), 0).desc()).limit(50).all()

    return {
        "mes_ref": mes_ref,
        "cards": cards,
        "proximos_vencimentos": proximos_vencimentos,
        "recebiveis_vencidos": recebiveis_vencidos,
        "maiores_abertos": maiores_abertos,
        "recebimentos_recentes": recebimentos_recentes,
        "clientes_saldo": clientes_saldo,
    }

