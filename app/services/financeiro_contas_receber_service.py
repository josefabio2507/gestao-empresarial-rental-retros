from datetime import date, timedelta
import calendar
from decimal import Decimal, InvalidOperation
import os
import re

from flask import current_app
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import CentroCusto, Equipe, FinanceiroContaReceberBaixa, FinanceiroContaReceberLoteBaixa, FinanceiroContaReceberTitulo, FinanceiroNotaFiscalEmitida, FinanceiroContratoCliente, FinanceiroContratoMedicao, FinanceiroContaReceberCobranca
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
STATUS_BAIXA_ATIVA = "Ativa"
STATUS_BAIXA_CANCELADA = "Cancelada"
STATUS_BAIXA_ESTORNADA = "Estornada"
STATUS_BAIXAS_RECEBER = [STATUS_BAIXA_ATIVA, STATUS_BAIXA_CANCELADA, STATUS_BAIXA_ESTORNADA]
STATUS_LOTE_ATIVO = "Ativo"
STATUS_LOTE_CANCELADO = "Cancelado"
STATUS_LOTE_ESTORNADO = "Estornado"
STATUS_LOTES_RECEBER = [STATUS_LOTE_ATIVO, STATUS_LOTE_CANCELADO, STATUS_LOTE_ESTORNADO]
FORMAS_RECEBIMENTO = ["Pix", "Transferência", "Depósito", "Boleto", "Dinheiro", "Cartão", "Outro"]
EXTENSOES_COMPROVANTE = {"pdf", "jpg", "jpeg", "png", "webp"}
EXTENSOES_NOTA_PDF = {"pdf", "jpg", "jpeg", "png", "webp"}
EXTENSOES_NOTA_XML = {"xml"}
MAX_COMPROVANTE_BYTES = 10 * 1024 * 1024
MAX_ARQUIVO_NOTA_BYTES = 10 * 1024 * 1024

ORIGEM_MANUAL = "Manual"
ORIGEM_NOTA_FISCAL_EMITIDA = "Nota Fiscal Emitida"
ORIGENS_LANCAMENTO = [
    ORIGEM_MANUAL,
    ORIGEM_NOTA_FISCAL_EMITIDA,
    "Medição",
    "Contrato",
    "Reembolso",
    "Outro",
]

TIPOS_NOTA_EMITIDA = ["NFS-e", "NF-e", "Recibo", "Fatura", "Outro"]
STATUS_FISCAIS_NOTA_EMITIDA = ["Rascunho", "Emitida", "Enviada ao cliente", "Cancelada", "Substituída"]
STATUS_FINANCEIROS_NOTA_EMITIDA = ["Não integrado", "Pendente de geração", "Título gerado", "Parcialmente vinculado", "Vinculado a título existente", "Cancelado"]
STATUS_NOTA_NAO_INTEGRADA = "Não integrado"
STATUS_NOTA_TITULO_GERADO = "Título gerado"
STATUS_NOTA_VINCULADO = "Vinculado a título existente"
STATUS_NOTA_CANCELADO = "Cancelado"

TIPOS_COBRANCA_CONTRATO = ["Medição variável", "Valor fixo mensal", "Por evento", "Por ordem de serviço", "Reembolso", "Outro"]
PERIODICIDADES_MEDICAO = ["Mensal", "Quinzenal", "Semanal", "Por demanda", "Única", "Outra"]
STATUS_CONTRATOS_CLIENTES = ["Rascunho", "Ativo", "Suspenso", "Encerrado", "Cancelado"]
STATUS_MEDICOES = ["Rascunho", "Medida", "Aguardando aprovação", "Aprovada", "Faturada", "Gerada no Contas a Receber", "Cancelada"]
STATUS_FINANCEIROS_MEDICAO = ["Não integrado", "Pendente de geração", "Título gerado", "Vinculado a título existente", "Vinculado à nota emitida", "Cancelado"]
STATUS_MEDICAO_NAO_INTEGRADA = "Não integrado"
STATUS_MEDICAO_TITULO_GERADO = "Título gerado"
STATUS_MEDICAO_VINCULADO_TITULO = "Vinculado a título existente"
STATUS_MEDICAO_VINCULADO_NOTA = "Vinculado à nota emitida"
STATUS_MEDICAO_CANCELADO = "Cancelado"
ORIGEM_MEDICAO = "Medição"
EXTENSOES_ANEXO_MEDICAO = {"pdf", "jpg", "jpeg", "png", "webp", "xlsx", "csv"}
MAX_ANEXO_MEDICAO_BYTES = 10 * 1024 * 1024


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
    titulo.codigo_verificacao_nfse = texto_maiusculo(form_data.get("codigo_verificacao_nfse"))
    titulo.nota_emitida_id = inteiro_ou_none(form_data.get("nota_emitida_id"))
    titulo.tipo_nota_emitida = texto(form_data.get("tipo_nota_emitida")) or None
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
        joinedload(FinanceiroContaReceberTitulo.nota_emitida),
        joinedload(FinanceiroContaReceberTitulo.contrato),
        joinedload(FinanceiroContaReceberTitulo.medicao),
        joinedload(FinanceiroContaReceberTitulo.criado_por),
        joinedload(FinanceiroContaReceberTitulo.atualizado_por),
        joinedload(FinanceiroContaReceberTitulo.cancelado_por),
        joinedload(FinanceiroContaReceberTitulo.baixas).joinedload(FinanceiroContaReceberBaixa.registrado_por),
        joinedload(FinanceiroContaReceberTitulo.baixas).joinedload(FinanceiroContaReceberBaixa.cancelado_por),
        joinedload(FinanceiroContaReceberTitulo.cobrancas).joinedload(FinanceiroContaReceberCobranca.responsavel),
        joinedload(FinanceiroContaReceberTitulo.cobrancas).joinedload(FinanceiroContaReceberCobranca.criado_por),
        joinedload(FinanceiroContaReceberTitulo.cobrancas).joinedload(FinanceiroContaReceberCobranca.cancelado_por),
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
    if status == "em_aberto":
        query = query.filter(~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS | STATUS_RECEBIDOS), _saldo_expr() > 0)
    elif status:
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

    recebimento_inicio = data_ou_none(filtros.get("recebimento_inicio"))
    recebimento_fim = data_ou_none(filtros.get("recebimento_fim"))
    if recebimento_inicio:
        query = query.filter(FinanceiroContaReceberTitulo.data_recebimento >= recebimento_inicio)
    if recebimento_fim:
        query = query.filter(FinanceiroContaReceberTitulo.data_recebimento <= recebimento_fim)

    comprovante = texto(filtros.get("comprovante"))
    if comprovante in {"com", "sem"}:
        baixas_ativas = FinanceiroContaReceberBaixa.query.filter(
            FinanceiroContaReceberBaixa.titulo_id == FinanceiroContaReceberTitulo.id,
            FinanceiroContaReceberBaixa.status == STATUS_BAIXA_ATIVA,
        )
        baixa_com_comprovante = baixas_ativas.filter(
            or_(
                FinanceiroContaReceberBaixa.comprovante_path.isnot(None),
                FinanceiroContaReceberBaixa.comprovante_drive_file_id.isnot(None),
                FinanceiroContaReceberLoteBaixa.query.filter(
                    FinanceiroContaReceberLoteBaixa.id == FinanceiroContaReceberBaixa.lote_baixa_id,
                    or_(
                        FinanceiroContaReceberLoteBaixa.comprovante_path.isnot(None),
                        FinanceiroContaReceberLoteBaixa.comprovante_drive_file_id.isnot(None),
                    ),
                ).exists(),
            )
        )
        if comprovante == "com":
            query = query.filter(baixa_com_comprovante.exists())
        else:
            query = query.filter(baixas_ativas.exists(), ~baixa_com_comprovante.exists())
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
    hoje_query = abertos.filter(FinanceiroContaReceberTitulo.data_vencimento == hoje)
    inadimplentes_query = abertos.filter(FinanceiroContaReceberTitulo.data_vencimento < hoje)
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
    notas_mes = FinanceiroNotaFiscalEmitida.query.filter(
        FinanceiroNotaFiscalEmitida.status_fiscal != "Cancelada",
        FinanceiroNotaFiscalEmitida.data_emissao >= inicio_mes,
        FinanceiroNotaFiscalEmitida.data_emissao < inicio_proximo_mes,
    )
    notas_sem_titulo = FinanceiroNotaFiscalEmitida.query.filter(
        FinanceiroNotaFiscalEmitida.status_fiscal != "Cancelada",
        ~FinanceiroContaReceberTitulo.query.filter(
            FinanceiroContaReceberTitulo.nota_emitida_id == FinanceiroNotaFiscalEmitida.id,
            ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS),
        ).exists(),
    )
    titulos_gerados_por_nota = ativos.filter(FinanceiroContaReceberTitulo.nota_emitida_id.isnot(None))

    recebimentos_mes = FinanceiroContaReceberBaixa.query.filter(
        FinanceiroContaReceberBaixa.status == STATUS_BAIXA_ATIVA,
        FinanceiroContaReceberBaixa.data_recebimento >= inicio_mes,
        FinanceiroContaReceberBaixa.data_recebimento < inicio_proximo_mes,
    )
    total_recebido_mes = Decimal(recebimentos_mes.with_entities(func.coalesce(func.sum(FinanceiroContaReceberBaixa.valor_recebido), 0)).scalar() or 0).quantize(Decimal("0.01"))
    titulos_recebidos_mes = ativos.filter(
        FinanceiroContaReceberTitulo.status == STATUS_RECEBIDO,
        FinanceiroContaReceberTitulo.data_recebimento >= inicio_mes,
        FinanceiroContaReceberTitulo.data_recebimento < inicio_proximo_mes,
    )
    titulos_sem_comprovante = ativos.filter(
        FinanceiroContaReceberTitulo.valor_recebido > 0,
        FinanceiroContaReceberBaixa.query.filter(
            FinanceiroContaReceberBaixa.titulo_id == FinanceiroContaReceberTitulo.id,
            FinanceiroContaReceberBaixa.status == STATUS_BAIXA_ATIVA,
        ).exists(),
        ~FinanceiroContaReceberBaixa.query.filter(
            FinanceiroContaReceberBaixa.titulo_id == FinanceiroContaReceberTitulo.id,
            FinanceiroContaReceberBaixa.status == STATUS_BAIXA_ATIVA,
            or_(
                FinanceiroContaReceberBaixa.comprovante_path.isnot(None),
                FinanceiroContaReceberBaixa.comprovante_drive_file_id.isnot(None),
            ),
        ).exists(),
    )

    cards = {
        "total_recebido_mes": total_recebido_mes,
        "total_recebido_parcialmente": Decimal(ativos.filter(FinanceiroContaReceberTitulo.status == STATUS_RECEBIDO_PARCIALMENTE).with_entities(func.coalesce(func.sum(FinanceiroContaReceberTitulo.valor_recebido), 0)).scalar() or 0).quantize(Decimal("0.01")),
        "titulos_recebidos_mes": titulos_recebidos_mes.count(),
        "titulos_sem_comprovante": titulos_sem_comprovante.count(),
        "total_mes": _somar_saldo(mes_query),
        "total_aberto": _somar_saldo(abertos),
        "total_vencido": _somar_saldo(vencidos),
        "total_inadimplente": _somar_saldo(inadimplentes_query),
        "total_vence_hoje": _somar_saldo(hoje_query),
        "total_7_dias": _somar_saldo(proximos_7),
        "total_30_dias": _somar_saldo(proximos_30),
        "total_aguardando_faturamento": _somar_saldo(aguardando),
        "total_faturado": _somar_saldo(faturados),
        "quantidade_abertos": abertos.count(),
        "quantidade_vencidos": vencidos.count(),
        "saldo_geral_aberto": _somar_saldo(abertos),
        "notas_emitidas_mes": notas_mes.count(),
        "valor_notas_emitidas_mes": Decimal(notas_mes.with_entities(func.coalesce(func.sum(FinanceiroNotaFiscalEmitida.valor_total), 0)).scalar() or 0).quantize(Decimal("0.01")),
        "notas_sem_titulo": notas_sem_titulo.count(),
        "valor_notas_sem_titulo": Decimal(notas_sem_titulo.with_entities(func.coalesce(func.sum(FinanceiroNotaFiscalEmitida.valor_total), 0)).scalar() or 0).quantize(Decimal("0.01")),
        "notas_vinculadas": FinanceiroNotaFiscalEmitida.query.filter(FinanceiroNotaFiscalEmitida.status_financeiro.in_([STATUS_NOTA_TITULO_GERADO, STATUS_NOTA_VINCULADO, "Parcialmente vinculado"])).count(),
        "titulos_gerados_por_nota": titulos_gerados_por_nota.count(),
        "valor_originado_notas": _somar_saldo(ativos.filter(FinanceiroContaReceberTitulo.nota_emitida_id.isnot(None))),
        "valor_originado_contratos": _somar_saldo(ativos.filter(FinanceiroContaReceberTitulo.contrato_id.isnot(None))),
        "valor_originado_medicoes": _somar_saldo(ativos.filter(FinanceiroContaReceberTitulo.medicao_id.isnot(None))),
        "contratos_ativos": FinanceiroContratoCliente.query.filter(FinanceiroContratoCliente.status == "Ativo").count(),
        "valor_contratual_ativo": Decimal(FinanceiroContratoCliente.query.filter(FinanceiroContratoCliente.status == "Ativo").with_entities(func.coalesce(func.sum(FinanceiroContratoCliente.valor_contratual), 0)).scalar() or 0).quantize(Decimal("0.01")),
        "medicoes_pendentes": FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.status_medicao.in_(["Medida", "Aguardando aprovação", "Aprovada"]), FinanceiroContratoMedicao.status_financeiro.in_([STATUS_MEDICAO_NAO_INTEGRADA, "Pendente de geração", STATUS_MEDICAO_VINCULADO_NOTA])).count(),
        "medicoes_aprovadas_sem_titulo": FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.status_medicao == "Aprovada", ~FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.medicao_id == FinanceiroContratoMedicao.id, ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS)).exists()).count(),
        "valor_medicoes_pendentes_financeiro": Decimal(FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.status_medicao != "Cancelada", ~FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.medicao_id == FinanceiroContratoMedicao.id, ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS)).exists()).with_entities(func.coalesce(func.sum(FinanceiroContratoMedicao.valor_liquido_medido), 0)).scalar() or 0).quantize(Decimal("0.01")),
        "titulos_gerados_por_medicao": ativos.filter(FinanceiroContaReceberTitulo.medicao_id.isnot(None)).count(),
        "valor_a_receber_originado_medicoes": _somar_saldo(ativos.filter(FinanceiroContaReceberTitulo.medicao_id.isnot(None))),
        "medicoes_vinculadas_notas": FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.nota_emitida_id.isnot(None), FinanceiroContratoMedicao.status_medicao != "Cancelada").count(),
    }

    proximos_vencimentos = abertos.filter(
        FinanceiroContaReceberTitulo.data_vencimento >= hoje,
    ).order_by(FinanceiroContaReceberTitulo.data_vencimento.asc()).limit(50).all()
    recebiveis_vencidos = vencidos.order_by(FinanceiroContaReceberTitulo.data_vencimento.asc()).limit(50).all()
    titulos_inadimplentes = inadimplentes_query.order_by(FinanceiroContaReceberTitulo.data_vencimento.asc()).limit(50).all()
    maiores_abertos = abertos.order_by(_saldo_expr().desc()).limit(50).all()
    recebimentos_recentes = ativos.filter(
        FinanceiroContaReceberTitulo.valor_recebido > 0,
    ).order_by(
        FinanceiroContaReceberTitulo.data_recebimento.desc().nullslast(),
        FinanceiroContaReceberTitulo.atualizado_em.desc(),
    ).limit(50).all()
    recebidos_por_forma = recebimentos_mes.with_entities(
        FinanceiroContaReceberBaixa.forma_recebimento.label("forma"),
        func.coalesce(func.sum(FinanceiroContaReceberBaixa.valor_recebido), 0).label("total"),
    ).group_by(FinanceiroContaReceberBaixa.forma_recebimento).order_by(func.coalesce(func.sum(FinanceiroContaReceberBaixa.valor_recebido), 0).desc()).all()

    notas_recentes = FinanceiroNotaFiscalEmitida.query.order_by(FinanceiroNotaFiscalEmitida.data_emissao.desc(), FinanceiroNotaFiscalEmitida.id.desc()).limit(50).all()
    contratos_recentes = FinanceiroContratoCliente.query.order_by(FinanceiroContratoCliente.criado_em.desc(), FinanceiroContratoCliente.id.desc()).limit(50).all()
    medicoes_recentes = FinanceiroContratoMedicao.query.options(joinedload(FinanceiroContratoMedicao.contrato)).order_by(FinanceiroContratoMedicao.data_medicao.desc(), FinanceiroContratoMedicao.id.desc()).limit(50).all()
    medicoes_aprovadas_sem_titulo = FinanceiroContratoMedicao.query.options(joinedload(FinanceiroContratoMedicao.contrato)).filter(FinanceiroContratoMedicao.status_medicao.in_(["Aprovada", "Faturada", "Medida"]), ~FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.medicao_id == FinanceiroContratoMedicao.id, ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS)).exists()).order_by(FinanceiroContratoMedicao.data_medicao.desc()).limit(50).all()
    notas_sem_titulo_recentes = notas_sem_titulo.order_by(FinanceiroNotaFiscalEmitida.data_emissao.desc(), FinanceiroNotaFiscalEmitida.id.desc()).limit(50).all()

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
        "titulos_inadimplentes": titulos_inadimplentes,
        "maiores_abertos": maiores_abertos,
        "recebimentos_recentes": recebimentos_recentes,
        "clientes_saldo": clientes_saldo,
        "recebidos_por_forma": recebidos_por_forma,
        "notas_recentes": notas_recentes,
        "notas_sem_titulo_recentes": notas_sem_titulo_recentes,
        "contratos_recentes": contratos_recentes,
        "medicoes_recentes": medicoes_recentes,
        "medicoes_aprovadas_sem_titulo": medicoes_aprovadas_sem_titulo,
    }



def _registrar_log(acao, descricao):
    try:
        from app.services.logs_service import registrar_log

        registrar_log(acao, descricao)
    except Exception:
        current_app.logger.exception("Falha ao registrar log de Contas a Receber.")


def _total_baixas_ativas(titulo):
    if not titulo or not titulo.id:
        return Decimal("0.00")
    total = FinanceiroContaReceberBaixa.query.filter_by(
        titulo_id=titulo.id,
        status=STATUS_BAIXA_ATIVA,
    ).with_entities(func.coalesce(func.sum(FinanceiroContaReceberBaixa.valor_recebido), 0)).scalar()
    return Decimal(total or 0).quantize(Decimal("0.01"))


def recalcular_recebimento_titulo(titulo, usuario=None):
    if not titulo:
        return None

    total = _total_baixas_ativas(titulo)
    status_anterior = titulo.status
    titulo.valor_recebido = total
    titulo.data_recebimento = None

    ultima_baixa = FinanceiroContaReceberBaixa.query.filter_by(
        titulo_id=titulo.id,
        status=STATUS_BAIXA_ATIVA,
    ).order_by(FinanceiroContaReceberBaixa.data_recebimento.desc(), FinanceiroContaReceberBaixa.id.desc()).first()
    if ultima_baixa:
        titulo.data_recebimento = ultima_baixa.data_recebimento

    if titulo.status not in STATUS_INATIVOS:
        if total >= titulo.valor_liquido:
            titulo.status = STATUS_RECEBIDO
        elif total > 0:
            titulo.status = STATUS_RECEBIDO_PARCIALMENTE
        elif titulo.status in {STATUS_RECEBIDO, STATUS_RECEBIDO_PARCIALMENTE}:
            titulo.status = STATUS_FATURADO if titulo.numero_nota_fiscal else STATUS_A_VENCER

    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
    if status_anterior != titulo.status:
        _registrar_log(
            "financeiro_contas_receber_status_alterado",
            f"Status do titulo a receber alterado automaticamente. ID: {titulo.id}. {status_anterior} -> {titulo.status}.",
        )
    return titulo


def _extensao_comprovante(arquivo):
    nome = arquivo.filename or ""
    if "." not in nome:
        return ""
    return nome.rsplit(".", 1)[1].lower()


def _tamanho_arquivo(arquivo):
    posicao = arquivo.stream.tell()
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(posicao)
    return tamanho


def _salvar_comprovante_recebimento(baixa, arquivo):
    if not arquivo or not arquivo.filename:
        return

    extensao = _extensao_comprovante(arquivo)
    if extensao not in EXTENSOES_COMPROVANTE:
        raise ValueError("Formato de comprovante inválido. Use PDF, JPG, JPEG, PNG ou WEBP.")

    tamanho = _tamanho_arquivo(arquivo)
    if tamanho > MAX_COMPROVANTE_BYTES:
        raise ValueError("Comprovante maior que 10 MB.")

    pasta = os.path.join(current_app.instance_path, "financeiro", "recebimentos")
    os.makedirs(pasta, exist_ok=True)
    data_nome = agora_brasil().strftime("%Y%m%d-%H%M%S")
    nome_armazenado = f"CR-{baixa.titulo_id}_RECEBIMENTO-{baixa.id}_{data_nome}.{extensao}"
    caminho = os.path.abspath(os.path.join(pasta, nome_armazenado))
    pasta_base = os.path.abspath(pasta)
    if not caminho.startswith(pasta_base):
        raise ValueError("Caminho de comprovante inválido.")

    arquivo.stream.seek(0)
    arquivo.save(caminho)

    baixa.comprovante_nome_original = arquivo.filename
    baixa.comprovante_nome_armazenado = nome_armazenado
    baixa.comprovante_path = caminho
    baixa.comprovante_extensao = extensao
    baixa.comprovante_tamanho = tamanho
    _registrar_log("financeiro_contas_receber_comprovante_upload", f"Comprovante anexado. Baixa: {baixa.id}. Titulo: {baixa.titulo_id}.")


def registrar_recebimento_titulo(titulo, dados, arquivo=None, usuario=None):
    if not titulo:
        return False, "Título a receber não encontrado.", None
    if titulo.status == STATUS_CANCELADO:
        return False, "Título cancelado não pode receber baixa.", None
    if titulo.status == STATUS_ESTORNADO:
        return False, "Título estornado não pode receber baixa.", None

    try:
        recalcular_recebimento_titulo(titulo, usuario=usuario)
        saldo = Decimal(titulo.saldo_aberto).quantize(Decimal("0.01"))
        if saldo <= 0 or titulo.status == STATUS_RECEBIDO:
            raise ValueError("Título já está totalmente recebido.")

        data_recebimento = data_ou_none(dados.get("data_recebimento"))
        if not data_recebimento:
            raise ValueError("Informe a data do recebimento.")

        valor_recebido = decimal_ou_zero(dados.get("valor_recebido"))
        if valor_recebido is None or valor_recebido <= 0:
            raise ValueError("Informe o valor recebido.")
        if valor_recebido > saldo:
            raise ValueError("O valor informado excede o saldo em aberto.")

        forma_recebimento = texto(dados.get("forma_recebimento"))
        if not forma_recebimento:
            raise ValueError("Informe a forma de recebimento.")
        if forma_recebimento not in FORMAS_RECEBIMENTO:
            raise ValueError("Forma de recebimento inválida.")

        baixa = FinanceiroContaReceberBaixa(
            titulo_id=titulo.id,
            data_recebimento=data_recebimento,
            valor_recebido=valor_recebido,
            forma_recebimento=forma_recebimento,
            conta_recebimento_descricao=texto(dados.get("conta_recebimento_descricao")) or None,
            observacoes=texto(dados.get("observacoes")) or None,
            status=STATUS_BAIXA_ATIVA,
            registrado_por_usuario_id=getattr(usuario, "id", None),
        )
        db.session.add(baixa)
        db.session.flush()
        _salvar_comprovante_recebimento(baixa, arquivo)
        recalcular_recebimento_titulo(titulo, usuario=usuario)
        db.session.commit()

        acao = "financeiro_contas_receber_recebimento_total" if titulo.status == STATUS_RECEBIDO else "financeiro_contas_receber_recebimento_parcial"
        mensagem = "Título recebido com sucesso." if titulo.status == STATUS_RECEBIDO else "Recebimento parcial registrado com sucesso."
        _registrar_log(acao, f"Recebimento registrado. Baixa: {baixa.id}. Titulo: {titulo.id}. Valor: {valor_recebido}.")
        return True, mensagem, baixa
    except ValueError as exc:
        db.session.rollback()
        return False, str(exc), None


def buscar_baixa_recebimento_por_id(baixa_id):
    return FinanceiroContaReceberBaixa.query.options(
        joinedload(FinanceiroContaReceberBaixa.titulo),
        joinedload(FinanceiroContaReceberBaixa.registrado_por),
        joinedload(FinanceiroContaReceberBaixa.cancelado_por),
    ).get(baixa_id)


def cancelar_recebimento_titulo(baixa, motivo, usuario=None):
    if not baixa:
        return False, "Recebimento não encontrado."
    if baixa.status != STATUS_BAIXA_ATIVA:
        return False, "Recebimento já foi cancelado ou estornado."

    motivo = texto(motivo)
    if not motivo:
        return False, "Informe o motivo do estorno."

    titulo = baixa.titulo
    baixa.status = STATUS_BAIXA_ESTORNADA
    baixa.cancelado_por_usuario_id = getattr(usuario, "id", None)
    baixa.cancelado_em = agora_brasil()
    baixa.motivo_cancelamento = motivo
    recalcular_recebimento_titulo(titulo, usuario=usuario)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_recebimento_estornado", f"Recebimento estornado. Baixa: {baixa.id}. Titulo: {baixa.titulo_id}.")
    return True, "Recebimento cancelado/estornado com sucesso. O saldo do título foi recalculado."


def caminho_comprovante_recebimento(baixa):
    if not baixa or baixa.status != STATUS_BAIXA_ATIVA or not baixa.comprovante_path:
        return None
    caminho = os.path.abspath(baixa.comprovante_path)
    pasta_base = os.path.abspath(os.path.join(current_app.instance_path, "financeiro", "recebimentos"))
    if not caminho.startswith(pasta_base):
        return None
    if not os.path.exists(caminho):
        return None
    return caminho

def titulo_elegivel_recebimento(titulo):
    if not titulo:
        return False
    recalcular_recebimento_titulo(titulo)
    return titulo.status not in STATUS_INATIVOS | STATUS_RECEBIDOS and titulo.saldo_aberto > 0


def buscar_titulos_elegiveis_por_ids(ids):
    ids_limpos = []
    for item in ids or []:
        valor = inteiro_ou_none(item)
        if valor and valor not in ids_limpos:
            ids_limpos.append(valor)
    if not ids_limpos:
        return []
    titulos = FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.id.in_(ids_limpos)).all()
    ordenados = {titulo.id: titulo for titulo in titulos}
    return [ordenados[item] for item in ids_limpos if item in ordenados and titulo_elegivel_recebimento(ordenados[item])]


def preparar_baixa_em_massa(ids):
    titulos = buscar_titulos_elegiveis_por_ids(ids)
    total = sum((Decimal(titulo.saldo_aberto).quantize(Decimal("0.01")) for titulo in titulos), Decimal("0.00"))
    return titulos, total.quantize(Decimal("0.01"))


def _salvar_comprovante_lote_recebimento(lote, arquivo):
    if not arquivo or not arquivo.filename:
        return

    extensao = _extensao_comprovante(arquivo)
    if extensao not in EXTENSOES_COMPROVANTE:
        raise ValueError("Formato de comprovante inválido. Use PDF, JPG, JPEG, PNG ou WEBP.")

    tamanho = _tamanho_arquivo(arquivo)
    if tamanho > MAX_COMPROVANTE_BYTES:
        raise ValueError("Comprovante maior que 10 MB.")

    pasta = os.path.join(current_app.instance_path, "financeiro", "recebimentos")
    os.makedirs(pasta, exist_ok=True)
    data_nome = agora_brasil().strftime("%Y%m%d-%H%M%S")
    nome_armazenado = f"CR-LOTE-{lote.id}_RECEBIMENTO_{data_nome}.{extensao}"
    caminho = os.path.abspath(os.path.join(pasta, nome_armazenado))
    pasta_base = os.path.abspath(pasta)
    if not caminho.startswith(pasta_base):
        raise ValueError("Caminho de comprovante inválido.")

    arquivo.stream.seek(0)
    arquivo.save(caminho)

    lote.comprovante_nome_original = arquivo.filename
    lote.comprovante_nome_armazenado = nome_armazenado
    lote.comprovante_path = caminho
    lote.comprovante_extensao = extensao
    lote.comprovante_tamanho = tamanho
    _registrar_log("financeiro_contas_receber_lote_comprovante_upload", f"Comprovante de lote anexado. Lote: {lote.id}.")


def registrar_recebimento_em_massa(dados, arquivo=None, usuario=None):
    ids = dados.getlist("titulos_ids") if hasattr(dados, "getlist") else dados.get("titulos_ids", [])
    if isinstance(ids, str):
        ids = [ids]
    ids_limpos = [inteiro_ou_none(item) for item in ids]
    ids_limpos = [item for item in ids_limpos if item]
    if not ids_limpos:
        return False, "Nenhum título selecionado.", None

    data_recebimento = data_ou_none(dados.get("data_recebimento"))
    if not data_recebimento:
        return False, "Informe a data do recebimento.", None

    forma_recebimento = texto(dados.get("forma_recebimento"))
    if not forma_recebimento:
        return False, "Informe a forma de recebimento.", None
    if forma_recebimento not in FORMAS_RECEBIMENTO:
        return False, "Forma de recebimento inválida.", None

    titulos = FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.id.in_(ids_limpos)).all()
    titulos_por_id = {titulo.id: titulo for titulo in titulos}
    if len(titulos_por_id) != len(set(ids_limpos)):
        return False, "Um ou mais títulos não estão elegíveis para recebimento.", None

    itens = []
    valor_total = Decimal("0.00")
    for titulo_id in ids_limpos:
        titulo = titulos_por_id.get(titulo_id)
        if not titulo or not titulo_elegivel_recebimento(titulo):
            _registrar_log("financeiro_contas_receber_lote_titulo_rejeitado", f"Titulo rejeitado na baixa em massa. ID: {titulo_id}.")
            return False, "Um ou mais títulos não estão elegíveis para recebimento.", None
        valor = decimal_ou_zero(dados.get(f"valor_receber_{titulo_id}"))
        if valor is None or valor <= 0:
            return False, "Informe o valor recebido.", None
        saldo = Decimal(titulo.saldo_aberto).quantize(Decimal("0.01"))
        if valor > saldo:
            return False, "O valor informado excede o saldo de um dos títulos.", None
        itens.append((titulo, valor))
        valor_total += valor

    if not itens:
        return False, "Nenhum título selecionado.", None

    try:
        lote = FinanceiroContaReceberLoteBaixa(
            data_recebimento=data_recebimento,
            forma_recebimento=forma_recebimento,
            conta_recebimento_descricao=texto(dados.get("conta_recebimento_descricao")) or None,
            observacoes=texto(dados.get("observacoes")) or None,
            total_titulos=len(itens),
            valor_total_recebido=valor_total.quantize(Decimal("0.01")),
            status=STATUS_LOTE_ATIVO,
            criado_por_usuario_id=getattr(usuario, "id", None),
        )
        db.session.add(lote)
        db.session.flush()
        _salvar_comprovante_lote_recebimento(lote, arquivo)

        for titulo, valor in itens:
            baixa = FinanceiroContaReceberBaixa(
                titulo_id=titulo.id,
                lote_baixa_id=lote.id,
                data_recebimento=data_recebimento,
                valor_recebido=valor,
                forma_recebimento=forma_recebimento,
                conta_recebimento_descricao=lote.conta_recebimento_descricao,
                observacoes=lote.observacoes,
                status=STATUS_BAIXA_ATIVA,
                registrado_por_usuario_id=getattr(usuario, "id", None),
            )
            db.session.add(baixa)
            db.session.flush()
            recalcular_recebimento_titulo(titulo, usuario=usuario)
            _registrar_log("financeiro_contas_receber_lote_titulo_incluido", f"Titulo {titulo.id} incluido no lote {lote.id}.")

        db.session.commit()
        _registrar_log("financeiro_contas_receber_lote_criado", f"Lote de recebimento criado. ID: {lote.id}. Valor: {lote.valor_total_recebido}.")
        _registrar_log("financeiro_contas_receber_baixa_em_massa_confirmada", f"Baixa em massa confirmada. Lote: {lote.id}.")
        return True, "Recebimento em massa registrado com sucesso.", lote
    except ValueError as exc:
        db.session.rollback()
        return False, str(exc), None


def listar_lotes_recebimento():
    return FinanceiroContaReceberLoteBaixa.query.options(
        joinedload(FinanceiroContaReceberLoteBaixa.criado_por),
    ).order_by(FinanceiroContaReceberLoteBaixa.data_recebimento.desc(), FinanceiroContaReceberLoteBaixa.id.desc()).all()


def buscar_lote_recebimento_por_id(lote_id):
    return FinanceiroContaReceberLoteBaixa.query.options(
        joinedload(FinanceiroContaReceberLoteBaixa.criado_por),
        joinedload(FinanceiroContaReceberLoteBaixa.cancelado_por),
        joinedload(FinanceiroContaReceberLoteBaixa.baixas).joinedload(FinanceiroContaReceberBaixa.titulo),
    ).get(lote_id)


def cancelar_lote_recebimento(lote, motivo, usuario=None):
    if not lote:
        return False, "Lote de recebimento não encontrado."
    if lote.status != STATUS_LOTE_ATIVO:
        return False, "Lote de recebimento já foi cancelado ou estornado."
    motivo = texto(motivo)
    if not motivo:
        return False, "Informe o motivo do estorno."

    lote.status = STATUS_LOTE_ESTORNADO
    lote.cancelado_por_usuario_id = getattr(usuario, "id", None)
    lote.cancelado_em = agora_brasil()
    lote.motivo_cancelamento = motivo
    for baixa in lote.baixas:
        if baixa.status == STATUS_BAIXA_ATIVA:
            baixa.status = STATUS_BAIXA_ESTORNADA
            baixa.cancelado_por_usuario_id = getattr(usuario, "id", None)
            baixa.cancelado_em = agora_brasil()
            baixa.motivo_cancelamento = motivo
            recalcular_recebimento_titulo(baixa.titulo, usuario=usuario)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_lote_estornado", f"Lote de recebimento estornado. ID: {lote.id}.")
    return True, "Lote de recebimento estornado com sucesso."


def caminho_comprovante_lote_recebimento(lote):
    if not lote or lote.status != STATUS_LOTE_ATIVO or not lote.comprovante_path:
        return None
    caminho = os.path.abspath(lote.comprovante_path)
    pasta_base = os.path.abspath(os.path.join(current_app.instance_path, "financeiro", "recebimentos"))
    if not caminho.startswith(pasta_base):
        return None
    if not os.path.exists(caminho):
        return None
    return caminho


def _arquivo_extensao(arquivo):
    nome = arquivo.filename or ""
    if "." not in nome:
        return ""
    return nome.rsplit(".", 1)[1].lower()


def _salvar_arquivo_nota(nota, arquivo, tipo):
    if not arquivo or not arquivo.filename:
        return
    extensao = _arquivo_extensao(arquivo)
    permitidas = EXTENSOES_NOTA_XML if tipo == "xml" else EXTENSOES_NOTA_PDF
    if extensao not in permitidas:
        raise ValueError("Formato de arquivo da nota inválido.")
    tamanho = _tamanho_arquivo(arquivo)
    if tamanho > MAX_ARQUIVO_NOTA_BYTES:
        raise ValueError("Arquivo da nota maior que 10 MB.")
    pasta = os.path.join(current_app.instance_path, "financeiro", "notas_emitidas")
    os.makedirs(pasta, exist_ok=True)
    numero = re.sub(r"[^A-Za-z0-9_-]", "-", nota.numero_nota or str(nota.id))[:60]
    data_nome = agora_brasil().strftime("%Y%m%d-%H%M%S")
    nome_armazenado = f"CR-NOTA-{nota.id}_{tipo.upper()}_{numero}_{data_nome}.{extensao}"
    caminho = os.path.abspath(os.path.join(pasta, nome_armazenado))
    pasta_base = os.path.abspath(pasta)
    if not caminho.startswith(pasta_base):
        raise ValueError("Caminho de arquivo da nota inválido.")
    arquivo.stream.seek(0)
    arquivo.save(caminho)
    if tipo == "xml":
        nota.arquivo_xml_nome_original = arquivo.filename
        nota.arquivo_xml_nome_armazenado = nome_armazenado
        nota.arquivo_xml_path = caminho
        _registrar_log("financeiro_contas_receber_nota_xml_upload", f"XML de nota emitida anexado. Nota: {nota.id}.")
    else:
        nota.arquivo_pdf_nome_original = arquivo.filename
        nota.arquivo_pdf_nome_armazenado = nome_armazenado
        nota.arquivo_pdf_path = caminho
        _registrar_log("financeiro_contas_receber_nota_pdf_upload", f"PDF de nota emitida anexado. Nota: {nota.id}.")


def _aplicar_dados_nota(nota, dados, usuario=None, novo=False):
    nota.tipo_nota = texto(dados.get("tipo_nota")) or "NFS-e"
    nota.numero_nota = texto_maiusculo(dados.get("numero_nota"))
    nota.serie = texto_maiusculo(dados.get("serie")) or None
    nota.chave_acesso = texto_maiusculo(dados.get("chave_acesso")) or None
    nota.codigo_verificacao_nfse = texto_maiusculo(dados.get("codigo_verificacao_nfse")) or None
    nota.cliente_nome_snapshot = texto_maiusculo(dados.get("cliente_nome_snapshot"))
    nota.cliente_cnpj_cpf_snapshot = somente_digitos(dados.get("cliente_cnpj_cpf_snapshot"))
    nota.cliente_email_financeiro_snapshot = texto(dados.get("cliente_email_financeiro_snapshot")).lower()
    nota.cliente_telefone_snapshot = somente_digitos(dados.get("cliente_telefone_snapshot"))
    nota.data_emissao = data_ou_none(dados.get("data_emissao"))
    nota.competencia = texto(dados.get("competencia"))
    nota.descricao = texto_maiusculo(dados.get("descricao"))
    nota.valor_bruto = decimal_ou_zero(dados.get("valor_bruto"))
    nota.valor_desconto = decimal_ou_zero(dados.get("valor_desconto"))
    nota.valor_impostos_retidos = decimal_ou_zero(dados.get("valor_impostos_retidos"))
    nota.valor_liquido = decimal_ou_zero(dados.get("valor_liquido"))
    nota.valor_total = decimal_ou_zero(dados.get("valor_total"))
    nota.data_vencimento_padrao = data_ou_none(dados.get("data_vencimento_padrao"))
    nota.numero_parcelas = inteiro_ou_none(dados.get("numero_parcelas")) or 1
    nota.condicao_recebimento = texto(dados.get("condicao_recebimento")) or None
    nota.status_fiscal = texto(dados.get("status_fiscal")) or "Emitida"
    nota.status_financeiro = texto(dados.get("status_financeiro")) or STATUS_NOTA_NAO_INTEGRADA
    nota.observacoes_fiscais = texto(dados.get("observacoes_fiscais")) or None
    nota.observacoes_financeiras = texto(dados.get("observacoes_financeiras")) or None
    if novo:
        nota.criado_por_usuario_id = getattr(usuario, "id", None)
    nota.atualizado_por_usuario_id = getattr(usuario, "id", None)


def _nota_duplicada(nota):
    query = FinanceiroNotaFiscalEmitida.query.filter(
        FinanceiroNotaFiscalEmitida.numero_nota == nota.numero_nota,
        FinanceiroNotaFiscalEmitida.cliente_cnpj_cpf_snapshot == nota.cliente_cnpj_cpf_snapshot,
    )
    if nota.serie:
        query = query.filter(FinanceiroNotaFiscalEmitida.serie == nota.serie)
    else:
        query = query.filter(FinanceiroNotaFiscalEmitida.serie.is_(None))
    if nota.id:
        query = query.filter(FinanceiroNotaFiscalEmitida.id != nota.id)
    if query.first():
        return True
    if nota.chave_acesso:
        chave_query = FinanceiroNotaFiscalEmitida.query.filter(FinanceiroNotaFiscalEmitida.chave_acesso == nota.chave_acesso)
        if nota.id:
            chave_query = chave_query.filter(FinanceiroNotaFiscalEmitida.id != nota.id)
        if chave_query.first():
            return True
    return False


def _validar_nota(nota):
    if not nota.numero_nota:
        return False, "Informe o número da nota."
    if not nota.cliente_nome_snapshot:
        return False, "Informe o cliente."
    if not nota.cliente_cnpj_cpf_snapshot:
        return False, "Informe o CNPJ/CPF do cliente."
    if not nota.data_emissao:
        return False, "Informe a data de emissão."
    if nota.valor_total is None or nota.valor_total <= 0:
        return False, "Informe um valor maior que zero."
    if any(valor is None or valor < 0 for valor in [nota.valor_bruto, nota.valor_desconto, nota.valor_impostos_retidos, nota.valor_liquido]):
        return False, "Valores da nota não podem ser negativos."
    if nota.tipo_nota not in TIPOS_NOTA_EMITIDA:
        return False, "Tipo de nota inválido."
    if nota.status_fiscal not in STATUS_FISCAIS_NOTA_EMITIDA:
        return False, "Status fiscal inválido."
    if nota.status_financeiro not in STATUS_FINANCEIROS_NOTA_EMITIDA:
        return False, "Status financeiro inválido."
    if nota.numero_parcelas < 1:
        return False, "Número de parcelas inválido."
    if _nota_duplicada(nota):
        _registrar_log("financeiro_contas_receber_nota_duplicidade_bloqueada", f"Duplicidade bloqueada para nota {nota.numero_nota}.")
        return False, "Já existe nota fiscal emitida cadastrada para este número, série e cliente."
    return True, ""


def salvar_nota_emitida(dados, nota=None, arquivos=None, usuario=None):
    novo = nota is None
    nota = nota or FinanceiroNotaFiscalEmitida()
    _aplicar_dados_nota(nota, dados, usuario=usuario, novo=novo)
    valido, mensagem = _validar_nota(nota)
    if not valido:
        db.session.rollback()
        return False, mensagem, nota
    try:
        db.session.add(nota)
        db.session.flush()
        arquivos = arquivos or {}
        _salvar_arquivo_nota(nota, arquivos.get("arquivo_pdf"), "pdf")
        _salvar_arquivo_nota(nota, arquivos.get("arquivo_xml"), "xml")
        db.session.commit()
        _registrar_log("financeiro_contas_receber_nota_criada" if novo else "financeiro_contas_receber_nota_atualizada", f"Nota emitida salva. ID: {nota.id}.")
        return True, "Nota fiscal emitida cadastrada com sucesso." if novo else "Nota fiscal emitida atualizada com sucesso.", nota
    except ValueError as exc:
        db.session.rollback()
        return False, str(exc), nota


def listar_notas_emitidas(filtros=None):
    filtros = filtros or {}
    query = FinanceiroNotaFiscalEmitida.query.options(joinedload(FinanceiroNotaFiscalEmitida.titulos))
    cliente = texto(filtros.get("cliente"))
    if cliente:
        query = query.filter(FinanceiroNotaFiscalEmitida.cliente_nome_snapshot.ilike(f"%{cliente}%"))
    cnpj_cpf = somente_digitos(filtros.get("cnpj_cpf"))
    if cnpj_cpf:
        query = query.filter(FinanceiroNotaFiscalEmitida.cliente_cnpj_cpf_snapshot.ilike(f"%{cnpj_cpf}%"))
    numero = texto(filtros.get("numero_nota"))
    if numero:
        query = query.filter(FinanceiroNotaFiscalEmitida.numero_nota.ilike(f"%{numero}%"))
    serie = texto(filtros.get("serie"))
    if serie:
        query = query.filter(FinanceiroNotaFiscalEmitida.serie.ilike(f"%{serie}%"))
    tipo = texto(filtros.get("tipo_nota"))
    if tipo:
        query = query.filter(FinanceiroNotaFiscalEmitida.tipo_nota == tipo)
    competencia = texto(filtros.get("competencia"))
    if competencia:
        query = query.filter(FinanceiroNotaFiscalEmitida.competencia == competencia)
    status_fiscal = texto(filtros.get("status_fiscal"))
    if status_fiscal:
        query = query.filter(FinanceiroNotaFiscalEmitida.status_fiscal == status_fiscal)
    status_financeiro = texto(filtros.get("status_financeiro"))
    if status_financeiro:
        query = query.filter(FinanceiroNotaFiscalEmitida.status_financeiro == status_financeiro)
    emissao_inicio = data_ou_none(filtros.get("emissao_inicio"))
    emissao_fim = data_ou_none(filtros.get("emissao_fim"))
    if emissao_inicio:
        query = query.filter(FinanceiroNotaFiscalEmitida.data_emissao >= emissao_inicio)
    if emissao_fim:
        query = query.filter(FinanceiroNotaFiscalEmitida.data_emissao <= emissao_fim)
    titulos_ativos = FinanceiroContaReceberTitulo.query.filter(
        FinanceiroContaReceberTitulo.nota_emitida_id == FinanceiroNotaFiscalEmitida.id,
        ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS),
    )
    vinculo = texto(filtros.get("vinculo"))
    if vinculo == "com":
        query = query.filter(titulos_ativos.exists())
    elif vinculo == "sem":
        query = query.filter(~titulos_ativos.exists())
    elif vinculo == "parcial":
        query = query.filter(FinanceiroNotaFiscalEmitida.status_financeiro == "Parcialmente vinculado")
    elif vinculo == "cancelada":
        query = query.filter(FinanceiroNotaFiscalEmitida.status_fiscal == "Cancelada")
    return query.order_by(FinanceiroNotaFiscalEmitida.data_emissao.desc(), FinanceiroNotaFiscalEmitida.id.desc()).all()


def buscar_nota_emitida_por_id(nota_id):
    return FinanceiroNotaFiscalEmitida.query.options(
        joinedload(FinanceiroNotaFiscalEmitida.titulos).joinedload(FinanceiroContaReceberTitulo.centro_custo),
        joinedload(FinanceiroNotaFiscalEmitida.contrato),
        joinedload(FinanceiroNotaFiscalEmitida.medicao),
        joinedload(FinanceiroNotaFiscalEmitida.criado_por),
        joinedload(FinanceiroNotaFiscalEmitida.atualizado_por),
        joinedload(FinanceiroNotaFiscalEmitida.cancelado_por),
    ).get(nota_id)


def _titulos_ativos_nota(nota):
    if not nota or not nota.id:
        return []
    return FinanceiroContaReceberTitulo.query.filter(
        FinanceiroContaReceberTitulo.nota_emitida_id == nota.id,
        ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS),
    ).all()


def _adicionar_meses(data_base, meses):
    mes_total = data_base.month - 1 + meses
    ano = data_base.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def _parcelas(valor_total, quantidade):
    base = (valor_total / quantidade).quantize(Decimal("0.01"))
    valores = [base for _ in range(quantidade)]
    diferenca = valor_total - sum(valores, Decimal("0.00"))
    valores[-1] = (valores[-1] + diferenca).quantize(Decimal("0.01"))
    return valores


def gerar_titulos_da_nota(nota, dados, usuario=None):
    if not nota:
        return False, "Nota fiscal emitida não encontrada.", []
    if nota.status_fiscal == "Cancelada" or nota.status_financeiro == STATUS_NOTA_CANCELADO:
        return False, "Nota fiscal cancelada não pode gerar Contas a Receber.", []
    if _titulos_ativos_nota(nota):
        _registrar_log("financeiro_contas_receber_nota_duplicidade_bloqueada", f"Geração bloqueada para nota já vinculada. Nota: {nota.id}.")
        return False, "Esta nota fiscal já possui título(s) a receber vinculado(s).", []
    primeiro_vencimento = data_ou_none(dados.get("data_primeiro_vencimento")) or nota.data_vencimento_padrao
    if not primeiro_vencimento:
        return False, "Informe a data do primeiro vencimento.", []
    parcelas = inteiro_ou_none(dados.get("numero_parcelas")) or nota.numero_parcelas or 1
    if parcelas < 1:
        return False, "Número de parcelas inválido.", []
    descricao = texto_maiusculo(dados.get("descricao")) or nota.descricao or f"NOTA FISCAL EMITIDA {nota.numero_nota}"
    competencia = texto(dados.get("competencia")) or nota.competencia
    centro_custo_id = inteiro_ou_none(dados.get("centro_custo_id"))
    equipe_id = inteiro_ou_none(dados.get("sub_centro_custo_equipe_id"))
    veiculo_id = inteiro_ou_none(dados.get("sub_centro_custo_veiculo_id"))
    observacoes = texto_maiusculo(dados.get("observacoes_financeiras")) or nota.observacoes_financeiras
    valores = _parcelas(Decimal(nota.valor_total).quantize(Decimal("0.01")), parcelas)
    titulos = []
    for indice, valor in enumerate(valores, start=1):
        vencimento = _adicionar_meses(primeiro_vencimento, indice - 1)
        titulo = FinanceiroContaReceberTitulo(
            cliente_nome_snapshot=nota.cliente_nome_snapshot,
            cliente_cnpj_cpf_snapshot=nota.cliente_cnpj_cpf_snapshot,
            cliente_email_financeiro_snapshot=nota.cliente_email_financeiro_snapshot,
            cliente_telefone_snapshot=nota.cliente_telefone_snapshot,
            descricao=descricao,
            numero_documento=f"{nota.numero_nota}-{indice:02d}" if parcelas > 1 else nota.numero_nota,
            numero_nota_fiscal=nota.numero_nota,
            chave_acesso_nfe_nfse=nota.chave_acesso,
            codigo_verificacao_nfse=nota.codigo_verificacao_nfse,
            nota_emitida_id=nota.id,
            tipo_nota_emitida=nota.tipo_nota,
            origem_lancamento=ORIGEM_NOTA_FISCAL_EMITIDA,
            competencia=competencia,
            data_emissao=nota.data_emissao,
            data_vencimento=vencimento,
            valor_original=valor,
            valor_desconto=Decimal("0.00"),
            valor_acrescimo=Decimal("0.00"),
            valor_juros_multa=Decimal("0.00"),
            valor_recebido=Decimal("0.00"),
            parcela_numero=indice,
            total_parcelas=parcelas,
            centro_custo_id=centro_custo_id,
            sub_centro_custo_equipe_id=equipe_id,
            sub_centro_custo_veiculo_id=veiculo_id,
            status=STATUS_FATURADO,
            observacoes=observacoes,
            criado_por_usuario_id=getattr(usuario, "id", None),
            atualizado_por_usuario_id=getattr(usuario, "id", None),
        )
        db.session.add(titulo)
        titulos.append(titulo)
    nota.status_financeiro = STATUS_NOTA_TITULO_GERADO
    nota.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    for titulo in titulos:
        _registrar_log("financeiro_contas_receber_titulo_gerado_por_nota", f"Título {titulo.id} gerado pela nota emitida {nota.id}.")
    return True, "Título(s) a receber gerado(s) com sucesso.", titulos


def listar_titulos_elegiveis_vinculo_nota(nota, filtros=None):
    filtros = filtros or {}
    query = FinanceiroContaReceberTitulo.query.filter(
        FinanceiroContaReceberTitulo.nota_emitida_id.is_(None),
        ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS),
    )
    if nota and nota.cliente_cnpj_cpf_snapshot:
        query = query.filter(FinanceiroContaReceberTitulo.cliente_cnpj_cpf_snapshot == nota.cliente_cnpj_cpf_snapshot)
    cliente = texto(filtros.get("cliente"))
    if cliente:
        query = query.filter(FinanceiroContaReceberTitulo.cliente_nome_snapshot.ilike(f"%{cliente}%"))
    documento = texto(filtros.get("numero_documento"))
    if documento:
        query = query.filter(FinanceiroContaReceberTitulo.numero_documento.ilike(f"%{documento}%"))
    status = texto(filtros.get("status"))
    if status:
        query = query.filter(FinanceiroContaReceberTitulo.status == status)
    vencimento = data_ou_none(filtros.get("vencimento"))
    if vencimento:
        query = query.filter(FinanceiroContaReceberTitulo.data_vencimento == vencimento)
    valor = decimal_ou_zero(filtros.get("valor")) if filtros.get("valor") else None
    if valor is not None:
        query = query.filter(FinanceiroContaReceberTitulo.valor_original == valor)
    return query.order_by(FinanceiroContaReceberTitulo.data_vencimento.asc(), FinanceiroContaReceberTitulo.id.desc()).limit(100).all()


def vincular_nota_a_titulo(nota, titulo_id, usuario=None):
    if not nota:
        return False, "Nota fiscal emitida não encontrada.", None
    if nota.status_fiscal == "Cancelada" or nota.status_financeiro == STATUS_NOTA_CANCELADO:
        return False, "Nota fiscal cancelada não pode ser vinculada.", None
    if _titulos_ativos_nota(nota):
        _registrar_log("financeiro_contas_receber_nota_duplicidade_bloqueada", f"Vínculo bloqueado para nota já vinculada. Nota: {nota.id}.")
        return False, "Esta nota fiscal já possui título(s) a receber vinculado(s).", None
    titulo = FinanceiroContaReceberTitulo.query.get(titulo_id)
    if not titulo or titulo.status in STATUS_INATIVOS:
        return False, "Título a receber não encontrado ou inelegível.", None
    if titulo.nota_emitida_id:
        return False, "Título a receber já possui nota fiscal vinculada.", None
    titulo.nota_emitida_id = nota.id
    titulo.tipo_nota_emitida = nota.tipo_nota
    titulo.numero_nota_fiscal = nota.numero_nota
    titulo.chave_acesso_nfe_nfse = nota.chave_acesso
    titulo.codigo_verificacao_nfse = nota.codigo_verificacao_nfse
    titulo.origem_lancamento = ORIGEM_NOTA_FISCAL_EMITIDA
    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
    nota.status_financeiro = STATUS_NOTA_VINCULADO
    nota.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_nota_vinculada_titulo", f"Nota emitida {nota.id} vinculada ao título {titulo.id}.")
    return True, "Nota fiscal vinculada ao título com sucesso.", titulo


def cancelar_nota_emitida(nota, motivo=None, usuario=None):
    if not nota:
        return False, "Nota fiscal emitida não encontrada."
    if nota.status_fiscal == "Cancelada":
        return False, "Nota fiscal emitida já está cancelada."
    nota.status_fiscal = "Cancelada"
    nota.status_financeiro = STATUS_NOTA_CANCELADO
    nota.cancelado_por_usuario_id = getattr(usuario, "id", None)
    nota.cancelado_em = agora_brasil()
    nota.motivo_cancelamento = texto(motivo) or "Cancelamento interno"
    nota.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_nota_cancelada", f"Registro interno de nota emitida cancelado. Nota: {nota.id}.")
    return True, "Registro interno da nota fiscal cancelado com sucesso."


def caminho_arquivo_nota_emitida(nota, tipo):
    if not nota:
        return None
    caminho = nota.arquivo_xml_path if tipo == "xml" else nota.arquivo_pdf_path
    if not caminho:
        return None
    caminho = os.path.abspath(caminho)
    pasta_base = os.path.abspath(os.path.join(current_app.instance_path, "financeiro", "notas_emitidas"))
    if not caminho.startswith(pasta_base):
        return None
    if not os.path.exists(caminho):
        return None
    return caminho



def salvar_contrato_cliente(dados, contrato=None, usuario=None):
    contrato = contrato or FinanceiroContratoCliente()
    novo = contrato.id is None
    contrato.numero_contrato = texto_maiusculo(dados.get("numero_contrato"))
    contrato.cliente_nome_snapshot = texto_maiusculo(dados.get("cliente_nome_snapshot"))
    contrato.cliente_cnpj_cpf_snapshot = somente_digitos(dados.get("cliente_cnpj_cpf_snapshot"))
    contrato.cliente_email_financeiro_snapshot = texto(dados.get("cliente_email_financeiro_snapshot")).lower()
    contrato.cliente_telefone_snapshot = somente_digitos(dados.get("cliente_telefone_snapshot"))
    contrato.descricao_objeto = texto_maiusculo(dados.get("descricao_objeto"))
    contrato.data_inicio = data_ou_none(dados.get("data_inicio"))
    contrato.data_fim = data_ou_none(dados.get("data_fim"))
    contrato.valor_contratual = decimal_ou_zero(dados.get("valor_contratual"))
    contrato.tipo_cobranca = texto(dados.get("tipo_cobranca")) or "Medição variável"
    contrato.periodicidade_medicao = texto(dados.get("periodicidade_medicao")) or "Mensal"
    contrato.dia_padrao_vencimento = inteiro_ou_none(dados.get("dia_padrao_vencimento"))
    contrato.condicao_recebimento = texto(dados.get("condicao_recebimento"))
    contrato.centro_custo_id = inteiro_ou_none(dados.get("centro_custo_id"))
    contrato.sub_centro_custo_equipe_id = inteiro_ou_none(dados.get("sub_centro_custo_equipe_id"))
    contrato.responsavel_interno_id = inteiro_ou_none(dados.get("responsavel_interno_id"))
    contrato.status = texto(dados.get("status")) or "Ativo"
    contrato.observacoes = texto_maiusculo(dados.get("observacoes"))
    if novo:
        contrato.criado_por_usuario_id = getattr(usuario, "id", None)
    contrato.atualizado_por_usuario_id = getattr(usuario, "id", None)
    if not contrato.numero_contrato:
        return False, "Informe o número do contrato.", contrato
    if not contrato.cliente_nome_snapshot:
        return False, "Informe o cliente.", contrato
    if not contrato.cliente_cnpj_cpf_snapshot:
        return False, "Informe o CNPJ/CPF do cliente.", contrato
    if not contrato.data_inicio:
        return False, "Informe a data de início.", contrato
    if contrato.valor_contratual is None or contrato.valor_contratual < 0:
        return False, "Informe um valor contratual maior ou igual a zero.", contrato
    if contrato.status not in STATUS_CONTRATOS_CLIENTES:
        return False, "Status do contrato inválido.", contrato
    duplicado = FinanceiroContratoCliente.query.filter(
        FinanceiroContratoCliente.numero_contrato == contrato.numero_contrato,
        FinanceiroContratoCliente.cliente_cnpj_cpf_snapshot == contrato.cliente_cnpj_cpf_snapshot,
    )
    if contrato.id:
        duplicado = duplicado.filter(FinanceiroContratoCliente.id != contrato.id)
    if duplicado.first():
        return False, "Já existe contrato cadastrado para este cliente com o mesmo número.", contrato
    db.session.add(contrato)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_contrato_salvo", f"Contrato de cliente salvo. Contrato: {contrato.id}.")
    return True, "Contrato salvo com sucesso.", contrato


def listar_contratos_clientes(filtros=None):
    filtros = filtros or {}
    query = FinanceiroContratoCliente.query.options(joinedload(FinanceiroContratoCliente.medicoes), joinedload(FinanceiroContratoCliente.titulos), joinedload(FinanceiroContratoCliente.notas_emitidas))
    cliente = texto(filtros.get("cliente"))
    if cliente:
        query = query.filter(FinanceiroContratoCliente.cliente_nome_snapshot.ilike(f"%{cliente}%"))
    cnpj_cpf = somente_digitos(filtros.get("cnpj_cpf"))
    if cnpj_cpf:
        query = query.filter(FinanceiroContratoCliente.cliente_cnpj_cpf_snapshot.ilike(f"%{cnpj_cpf}%"))
    numero = texto(filtros.get("numero_contrato"))
    if numero:
        query = query.filter(FinanceiroContratoCliente.numero_contrato.ilike(f"%{numero}%"))
    status = texto(filtros.get("status"))
    if status:
        query = query.filter(FinanceiroContratoCliente.status == status)
    inicio_de = data_ou_none(filtros.get("inicio_de"))
    inicio_ate = data_ou_none(filtros.get("inicio_ate"))
    fim_de = data_ou_none(filtros.get("fim_de"))
    fim_ate = data_ou_none(filtros.get("fim_ate"))
    if inicio_de:
        query = query.filter(FinanceiroContratoCliente.data_inicio >= inicio_de)
    if inicio_ate:
        query = query.filter(FinanceiroContratoCliente.data_inicio <= inicio_ate)
    if fim_de:
        query = query.filter(FinanceiroContratoCliente.data_fim >= fim_de)
    if fim_ate:
        query = query.filter(FinanceiroContratoCliente.data_fim <= fim_ate)
    marcador = texto(filtros.get("marcador"))
    if marcador == "ativos":
        query = query.filter(FinanceiroContratoCliente.status == "Ativo")
    elif marcador == "encerrados":
        query = query.filter(FinanceiroContratoCliente.status.in_(["Encerrado", "Cancelado"]))
    elif marcador == "sem_medicao":
        query = query.filter(~FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.contrato_id == FinanceiroContratoCliente.id, FinanceiroContratoMedicao.status_medicao != "Cancelada").exists())
    elif marcador == "medicoes_pendentes":
        query = query.filter(FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.contrato_id == FinanceiroContratoCliente.id, FinanceiroContratoMedicao.status_financeiro.in_([STATUS_MEDICAO_NAO_INTEGRADA, "Pendente de geração", STATUS_MEDICAO_VINCULADO_NOTA])).exists())
    return query.order_by(FinanceiroContratoCliente.data_inicio.desc(), FinanceiroContratoCliente.id.desc()).all()


def buscar_contrato_cliente_por_id(contrato_id):
    return FinanceiroContratoCliente.query.options(
        joinedload(FinanceiroContratoCliente.medicoes).joinedload(FinanceiroContratoMedicao.nota_emitida),
        joinedload(FinanceiroContratoCliente.titulos).joinedload(FinanceiroContaReceberTitulo.nota_emitida),
        joinedload(FinanceiroContratoCliente.notas_emitidas),
        joinedload(FinanceiroContratoCliente.centro_custo),
        joinedload(FinanceiroContratoCliente.sub_centro_custo_equipe),
        joinedload(FinanceiroContratoCliente.criado_por),
        joinedload(FinanceiroContratoCliente.atualizado_por),
        joinedload(FinanceiroContratoCliente.cancelado_por),
    ).get(contrato_id)


def cancelar_contrato_cliente(contrato, motivo=None, usuario=None):
    if not contrato:
        return False, "Contrato não encontrado."
    if contrato.status == "Cancelado":
        return False, "Contrato já está cancelado."
    contrato.status = "Cancelado"
    contrato.cancelado_por_usuario_id = getattr(usuario, "id", None)
    contrato.cancelado_em = agora_brasil()
    contrato.motivo_cancelamento = texto(motivo) or "Cancelamento interno"
    contrato.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_contrato_cancelado", f"Contrato cancelado. Contrato: {contrato.id}.")
    return True, "Contrato cancelado/inativado com sucesso."


def _salvar_anexo_medicao(medicao, arquivo):
    if not arquivo or not getattr(arquivo, "filename", ""):
        return True, None
    nome_original = arquivo.filename
    extensao = nome_original.rsplit(".", 1)[-1].lower() if "." in nome_original else ""
    if extensao not in EXTENSOES_ANEXO_MEDICAO:
        return False, "Formato de anexo não permitido."
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(0)
    if tamanho > MAX_ANEXO_MEDICAO_BYTES:
        return False, "Anexo maior que o limite permitido."
    pasta = os.path.join(current_app.instance_path, "financeiro", "medicoes")
    os.makedirs(pasta, exist_ok=True)
    nome_armazenado = f"MED-{medicao.id or 'novo'}-{agora_brasil().strftime('%Y%m%d-%H%M%S')}.{extensao}"
    caminho = os.path.join(pasta, nome_armazenado)
    arquivo.save(caminho)
    medicao.anexo_nome_original = nome_original
    medicao.anexo_nome_armazenado = nome_armazenado
    medicao.anexo_path = caminho
    _registrar_log("financeiro_contas_receber_medicao_anexo_upload", f"Anexo de medição salvo. Medição: {medicao.id}.")
    return True, None


def salvar_medicao_contrato(dados, medicao=None, arquivos=None, usuario=None):
    medicao = medicao or FinanceiroContratoMedicao()
    novo = medicao.id is None
    contrato = FinanceiroContratoCliente.query.get(inteiro_ou_none(dados.get("contrato_id")))
    medicao.contrato = contrato
    medicao.nota_emitida_id = inteiro_ou_none(dados.get("nota_emitida_id"))
    medicao.numero_medicao = texto_maiusculo(dados.get("numero_medicao"))
    medicao.competencia = texto(dados.get("competencia"))
    medicao.data_medicao = data_ou_none(dados.get("data_medicao"))
    medicao.periodo_inicio = data_ou_none(dados.get("periodo_inicio"))
    medicao.periodo_fim = data_ou_none(dados.get("periodo_fim"))
    medicao.descricao = texto_maiusculo(dados.get("descricao"))
    medicao.valor_bruto_medido = decimal_ou_zero(dados.get("valor_bruto_medido"))
    medicao.valor_desconto = decimal_ou_zero(dados.get("valor_desconto"))
    medicao.valor_acrescimo = decimal_ou_zero(dados.get("valor_acrescimo"))
    medicao.valor_retencoes = decimal_ou_zero(dados.get("valor_retencoes"))
    liquido = decimal_ou_zero(dados.get("valor_liquido_medido"))
    if liquido in (None, Decimal("0.00")):
        liquido = (medicao.valor_bruto_medido + medicao.valor_acrescimo - medicao.valor_desconto - medicao.valor_retencoes).quantize(Decimal("0.01")) if None not in [medicao.valor_bruto_medido, medicao.valor_acrescimo, medicao.valor_desconto, medicao.valor_retencoes] else Decimal("0.00")
    medicao.valor_liquido_medido = liquido
    medicao.data_prevista_faturamento = data_ou_none(dados.get("data_prevista_faturamento"))
    medicao.data_prevista_vencimento = data_ou_none(dados.get("data_prevista_vencimento"))
    medicao.status_medicao = texto(dados.get("status_medicao")) or "Medida"
    medicao.status_financeiro = texto(dados.get("status_financeiro")) or STATUS_MEDICAO_NAO_INTEGRADA
    medicao.observacoes_tecnicas = texto_maiusculo(dados.get("observacoes_tecnicas"))
    medicao.observacoes_financeiras = texto_maiusculo(dados.get("observacoes_financeiras"))
    if novo:
        medicao.criado_por_usuario_id = getattr(usuario, "id", None)
    medicao.atualizado_por_usuario_id = getattr(usuario, "id", None)
    if not contrato:
        return False, "Informe o contrato.", medicao
    if contrato.status == "Cancelado":
        return False, "Contrato cancelado não pode receber medição.", medicao
    if not medicao.numero_medicao:
        return False, "Informe o número da medição.", medicao
    if not medicao.competencia:
        return False, "Informe a competência.", medicao
    if not medicao.data_medicao:
        return False, "Informe a data da medição.", medicao
    if not medicao.periodo_inicio or not medicao.periodo_fim:
        return False, "Informe o período medido.", medicao
    if medicao.periodo_fim < medicao.periodo_inicio:
        return False, "Período final não pode ser menor que o período inicial.", medicao
    if medicao.valor_liquido_medido is None or medicao.valor_liquido_medido <= 0:
        return False, "Informe um valor maior que zero.", medicao
    if medicao.status_medicao not in STATUS_MEDICOES:
        return False, "Status da medição inválido.", medicao
    duplicada = FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.contrato_id == contrato.id, FinanceiroContratoMedicao.numero_medicao == medicao.numero_medicao)
    if medicao.id:
        duplicada = duplicada.filter(FinanceiroContratoMedicao.id != medicao.id)
    if duplicada.first():
        return False, "Já existe medição com este número para o contrato.", medicao
    db.session.add(medicao)
    db.session.flush()
    arquivo = (arquivos or {}).get("anexo") if arquivos else None
    ok, erro = _salvar_anexo_medicao(medicao, arquivo)
    if not ok:
        db.session.rollback()
        return False, erro, medicao
    if medicao.nota_emitida_id:
        nota = FinanceiroNotaFiscalEmitida.query.get(medicao.nota_emitida_id)
        if nota:
            nota.contrato_id = contrato.id
            nota.medicao_id = medicao.id
            if medicao.status_financeiro == STATUS_MEDICAO_NAO_INTEGRADA:
                medicao.status_financeiro = STATUS_MEDICAO_VINCULADO_NOTA
    db.session.commit()
    _registrar_log("financeiro_contas_receber_medicao_salva", f"Medição salva. Medição: {medicao.id}.")
    return True, "Medição salva com sucesso.", medicao


def listar_medicoes_contratos(filtros=None):
    filtros = filtros or {}
    query = FinanceiroContratoMedicao.query.options(joinedload(FinanceiroContratoMedicao.contrato), joinedload(FinanceiroContratoMedicao.nota_emitida), joinedload(FinanceiroContratoMedicao.titulos))
    contrato_id = inteiro_ou_none(filtros.get("contrato_id"))
    if contrato_id:
        query = query.filter(FinanceiroContratoMedicao.contrato_id == contrato_id)
    cliente = texto(filtros.get("cliente"))
    if cliente:
        query = query.join(FinanceiroContratoCliente).filter(FinanceiroContratoCliente.cliente_nome_snapshot.ilike(f"%{cliente}%"))
    cnpj_cpf = somente_digitos(filtros.get("cnpj_cpf"))
    if cnpj_cpf:
        query = query.join(FinanceiroContratoCliente, FinanceiroContratoMedicao.contrato).filter(FinanceiroContratoCliente.cliente_cnpj_cpf_snapshot.ilike(f"%{cnpj_cpf}%"))
    numero = texto(filtros.get("numero_medicao"))
    if numero:
        query = query.filter(FinanceiroContratoMedicao.numero_medicao.ilike(f"%{numero}%"))
    competencia = texto(filtros.get("competencia"))
    if competencia:
        query = query.filter(FinanceiroContratoMedicao.competencia == competencia)
    status_medicao = texto(filtros.get("status_medicao"))
    if status_medicao:
        query = query.filter(FinanceiroContratoMedicao.status_medicao == status_medicao)
    status_financeiro = texto(filtros.get("status_financeiro"))
    if status_financeiro:
        query = query.filter(FinanceiroContratoMedicao.status_financeiro == status_financeiro)
    marcador = texto(filtros.get("marcador"))
    if marcador == "com_nota":
        query = query.filter(FinanceiroContratoMedicao.nota_emitida_id.isnot(None))
    elif marcador == "sem_nota":
        query = query.filter(FinanceiroContratoMedicao.nota_emitida_id.is_(None))
    elif marcador == "com_titulo":
        query = query.filter(FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.medicao_id == FinanceiroContratoMedicao.id, ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS)).exists())
    elif marcador == "sem_titulo":
        query = query.filter(~FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.medicao_id == FinanceiroContratoMedicao.id, ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS)).exists())
    return query.order_by(FinanceiroContratoMedicao.data_medicao.desc(), FinanceiroContratoMedicao.id.desc()).all()


def buscar_medicao_contrato_por_id(medicao_id):
    return FinanceiroContratoMedicao.query.options(
        joinedload(FinanceiroContratoMedicao.contrato).joinedload(FinanceiroContratoCliente.centro_custo),
        joinedload(FinanceiroContratoMedicao.nota_emitida),
        joinedload(FinanceiroContratoMedicao.titulos).joinedload(FinanceiroContaReceberTitulo.nota_emitida),
        joinedload(FinanceiroContratoMedicao.notas_emitidas),
        joinedload(FinanceiroContratoMedicao.criado_por),
        joinedload(FinanceiroContratoMedicao.atualizado_por),
        joinedload(FinanceiroContratoMedicao.cancelado_por),
    ).get(medicao_id)


def _titulos_ativos_medicao(medicao):
    if not medicao or not medicao.id:
        return []
    return FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.medicao_id == medicao.id, ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS)).all()


def gerar_titulos_da_medicao(medicao, dados, usuario=None):
    if not medicao:
        return False, "Medição não encontrada.", []
    if medicao.status_medicao == "Cancelada" or medicao.status_financeiro == STATUS_MEDICAO_CANCELADO:
        return False, "Medição cancelada não pode gerar Contas a Receber.", []
    if _titulos_ativos_medicao(medicao):
        _registrar_log("financeiro_contas_receber_medicao_duplicidade_bloqueada", f"Geração bloqueada para medição já vinculada. Medição: {medicao.id}.")
        return False, "Esta medição já possui título(s) a receber vinculado(s).", []
    nota = medicao.nota_emitida
    if nota and _titulos_ativos_nota(nota):
        return False, "A nota emitida vinculada já possui título(s) a receber.", []
    primeiro_vencimento = data_ou_none(dados.get("data_vencimento")) or medicao.data_prevista_vencimento
    if not primeiro_vencimento:
        return False, "Informe a data de vencimento.", []
    data_emissao = data_ou_none(dados.get("data_emissao")) or medicao.data_medicao
    parcelas = inteiro_ou_none(dados.get("numero_parcelas")) or 1
    if parcelas < 1:
        return False, "Número de parcelas inválido.", []
    contrato = medicao.contrato
    descricao = texto_maiusculo(dados.get("descricao")) or medicao.descricao or f"MEDIÇÃO {medicao.numero_medicao}"
    competencia = texto(dados.get("competencia")) or medicao.competencia
    centro_custo_id = inteiro_ou_none(dados.get("centro_custo_id")) or getattr(contrato, "centro_custo_id", None)
    equipe_id = inteiro_ou_none(dados.get("sub_centro_custo_equipe_id")) or getattr(contrato, "sub_centro_custo_equipe_id", None)
    veiculo_id = inteiro_ou_none(dados.get("sub_centro_custo_veiculo_id"))
    observacoes = texto_maiusculo(dados.get("observacoes_financeiras")) or medicao.observacoes_financeiras
    valores = _parcelas(Decimal(medicao.valor_liquido_medido).quantize(Decimal("0.01")), parcelas)
    titulos = []
    for indice, valor in enumerate(valores, start=1):
        vencimento = _adicionar_meses(primeiro_vencimento, indice - 1)
        titulo = FinanceiroContaReceberTitulo(
            cliente_nome_snapshot=contrato.cliente_nome_snapshot,
            cliente_cnpj_cpf_snapshot=contrato.cliente_cnpj_cpf_snapshot,
            cliente_email_financeiro_snapshot=contrato.cliente_email_financeiro_snapshot,
            cliente_telefone_snapshot=contrato.cliente_telefone_snapshot,
            descricao=descricao,
            numero_documento=f"{medicao.numero_medicao}-{indice:02d}" if parcelas > 1 else medicao.numero_medicao,
            numero_nota_fiscal=(nota.numero_nota if nota else texto_maiusculo(dados.get("numero_nota_fiscal"))),
            chave_acesso_nfe_nfse=(nota.chave_acesso if nota else None),
            codigo_verificacao_nfse=(nota.codigo_verificacao_nfse if nota else None),
            nota_emitida_id=(nota.id if nota else None),
            tipo_nota_emitida=(nota.tipo_nota if nota else None),
            contrato_id=contrato.id,
            medicao_id=medicao.id,
            origem_lancamento=ORIGEM_MEDICAO,
            competencia=competencia,
            data_emissao=data_emissao,
            data_vencimento=vencimento,
            valor_original=valor,
            valor_desconto=Decimal("0.00"),
            valor_acrescimo=Decimal("0.00"),
            valor_juros_multa=Decimal("0.00"),
            valor_recebido=Decimal("0.00"),
            parcela_numero=indice,
            total_parcelas=parcelas,
            centro_custo_id=centro_custo_id,
            sub_centro_custo_equipe_id=equipe_id,
            sub_centro_custo_veiculo_id=veiculo_id,
            status=STATUS_FATURADO if nota else STATUS_AGENDADO,
            observacoes=observacoes,
            criado_por_usuario_id=getattr(usuario, "id", None),
            atualizado_por_usuario_id=getattr(usuario, "id", None),
        )
        db.session.add(titulo)
        titulos.append(titulo)
    medicao.status_financeiro = STATUS_MEDICAO_TITULO_GERADO
    medicao.status_medicao = "Gerada no Contas a Receber"
    medicao.atualizado_por_usuario_id = getattr(usuario, "id", None)
    if nota:
        nota.status_financeiro = STATUS_NOTA_TITULO_GERADO
        nota.contrato_id = contrato.id
        nota.medicao_id = medicao.id
        nota.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    for titulo in titulos:
        _registrar_log("financeiro_contas_receber_titulo_gerado_por_medicao", f"Título {titulo.id} gerado pela medição {medicao.id}.")
    return True, "Título(s) a receber gerado(s) com sucesso.", titulos


def listar_titulos_elegiveis_vinculo_medicao(medicao, filtros=None):
    filtros = filtros or {}
    contrato = medicao.contrato if medicao else None
    query = FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.medicao_id.is_(None), ~FinanceiroContaReceberTitulo.status.in_(STATUS_INATIVOS))
    if contrato and contrato.cliente_cnpj_cpf_snapshot:
        query = query.filter(FinanceiroContaReceberTitulo.cliente_cnpj_cpf_snapshot == contrato.cliente_cnpj_cpf_snapshot)
    cliente = texto(filtros.get("cliente"))
    if cliente:
        query = query.filter(FinanceiroContaReceberTitulo.cliente_nome_snapshot.ilike(f"%{cliente}%"))
    documento = texto(filtros.get("numero_documento"))
    if documento:
        query = query.filter(FinanceiroContaReceberTitulo.numero_documento.ilike(f"%{documento}%"))
    status = texto(filtros.get("status"))
    if status:
        query = query.filter(FinanceiroContaReceberTitulo.status == status)
    valor = decimal_ou_zero(filtros.get("valor")) if filtros.get("valor") else None
    if valor is not None:
        query = query.filter(FinanceiroContaReceberTitulo.valor_original == valor)
    return query.order_by(FinanceiroContaReceberTitulo.data_vencimento.asc(), FinanceiroContaReceberTitulo.id.desc()).limit(100).all()


def vincular_medicao_a_titulo(medicao, titulo_id, usuario=None):
    if not medicao:
        return False, "Medição não encontrada.", None
    if medicao.status_medicao == "Cancelada":
        return False, "Medição cancelada não pode ser vinculada.", None
    if _titulos_ativos_medicao(medicao):
        return False, "Esta medição já possui título(s) a receber vinculado(s).", None
    titulo = FinanceiroContaReceberTitulo.query.get(titulo_id)
    if not titulo or titulo.status in STATUS_INATIVOS:
        return False, "Título a receber não encontrado ou inelegível.", None
    if titulo.medicao_id:
        return False, "Título a receber já possui medição vinculada.", None
    titulo.contrato_id = medicao.contrato_id
    titulo.medicao_id = medicao.id
    titulo.origem_lancamento = ORIGEM_MEDICAO
    if medicao.nota_emitida:
        titulo.nota_emitida_id = medicao.nota_emitida.id
        titulo.tipo_nota_emitida = medicao.nota_emitida.tipo_nota
        titulo.numero_nota_fiscal = medicao.nota_emitida.numero_nota
        titulo.chave_acesso_nfe_nfse = medicao.nota_emitida.chave_acesso
        titulo.codigo_verificacao_nfse = medicao.nota_emitida.codigo_verificacao_nfse
    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
    medicao.status_financeiro = STATUS_MEDICAO_VINCULADO_TITULO
    medicao.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_medicao_vinculada_titulo", f"Medição {medicao.id} vinculada ao título {titulo.id}.")
    return True, "Medição vinculada ao título com sucesso.", titulo


def listar_notas_elegiveis_vinculo_medicao(medicao, filtros=None):
    filtros = filtros or {}
    contrato = medicao.contrato if medicao else None
    query = FinanceiroNotaFiscalEmitida.query.filter(FinanceiroNotaFiscalEmitida.status_fiscal != "Cancelada")
    if contrato and contrato.cliente_cnpj_cpf_snapshot:
        query = query.filter(FinanceiroNotaFiscalEmitida.cliente_cnpj_cpf_snapshot == contrato.cliente_cnpj_cpf_snapshot)
    numero = texto(filtros.get("numero_nota"))
    if numero:
        query = query.filter(FinanceiroNotaFiscalEmitida.numero_nota.ilike(f"%{numero}%"))
    valor = decimal_ou_zero(filtros.get("valor")) if filtros.get("valor") else None
    if valor is not None:
        query = query.filter(FinanceiroNotaFiscalEmitida.valor_total == valor)
    status_financeiro = texto(filtros.get("status_financeiro"))
    if status_financeiro:
        query = query.filter(FinanceiroNotaFiscalEmitida.status_financeiro == status_financeiro)
    return query.order_by(FinanceiroNotaFiscalEmitida.data_emissao.desc(), FinanceiroNotaFiscalEmitida.id.desc()).limit(100).all()


def vincular_medicao_a_nota(medicao, nota_id, usuario=None):
    if not medicao:
        return False, "Medição não encontrada.", None
    if medicao.status_medicao == "Cancelada":
        return False, "Medição cancelada não pode ser vinculada.", None
    nota = FinanceiroNotaFiscalEmitida.query.get(nota_id)
    if not nota or nota.status_fiscal == "Cancelada":
        return False, "Nota emitida não encontrada ou inelegível.", None
    medicao.nota_emitida_id = nota.id
    medicao.status_financeiro = STATUS_MEDICAO_VINCULADO_NOTA if not _titulos_ativos_medicao(medicao) else medicao.status_financeiro
    medicao.atualizado_por_usuario_id = getattr(usuario, "id", None)
    nota.contrato_id = medicao.contrato_id
    nota.medicao_id = medicao.id
    nota.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_medicao_vinculada_nota", f"Medição {medicao.id} vinculada à nota {nota.id}.")
    return True, "Medição vinculada à nota emitida com sucesso.", nota


def cancelar_medicao_contrato(medicao, motivo=None, usuario=None):
    if not medicao:
        return False, "Medição não encontrada."
    if medicao.status_medicao == "Cancelada":
        return False, "Medição já está cancelada."
    medicao.status_medicao = "Cancelada"
    medicao.status_financeiro = STATUS_MEDICAO_CANCELADO
    medicao.cancelado_por_usuario_id = getattr(usuario, "id", None)
    medicao.cancelado_em = agora_brasil()
    medicao.motivo_cancelamento = texto(motivo) or "Cancelamento interno"
    medicao.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    _registrar_log("financeiro_contas_receber_medicao_cancelada", f"Medição cancelada. Medição: {medicao.id}.")
    return True, "Medição cancelada com sucesso."


def caminho_anexo_medicao(medicao):
    if not medicao or not medicao.anexo_path:
        return None
    caminho = os.path.abspath(medicao.anexo_path)
    pasta_base = os.path.abspath(os.path.join(current_app.instance_path, "financeiro", "medicoes"))
    if not caminho.startswith(pasta_base):
        return None
    if not os.path.exists(caminho):
        return None
    return caminho
