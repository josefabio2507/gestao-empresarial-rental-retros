from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import func

from app.extensions import db
from app.models import (
    CentroCusto,
    FinanceiroCartaoCredito,
    FinanceiroCartaoFatura,
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
STATUS_FATURA = ["Aberta", "Fechada", "Agendada", "Paga", "Vencida", "Cancelada"]
STATUS_FATURA_EDITAVEIS = ["Aberta", "Fechada", "Agendada"]


def _registrar_log(evento, mensagem):
    try:
        from app.services.logs_service import registrar_log

        registrar_log(evento, mensagem)
    except Exception:
        pass


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


def parse_decimal(valor, obrigatorio=False, nome_campo="Valor", permitir_nulo=False):
    valor = (valor or "").strip()
    if not valor:
        if obrigatorio:
            raise ValueError(f"{nome_campo} e obrigatorio.")
        if permitir_nulo:
            return None
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


def _data_com_dia_valido(ano, mes, dia):
    return date(ano, mes, min(dia, monthrange(ano, mes)[1]))


def _proximo_mes(ano, mes):
    if mes == 12:
        return ano + 1, 1
    return ano, mes + 1


def calcular_ciclo_fatura(cartao, data_compra):
    if data_compra.day <= cartao.dia_fechamento:
        ano, mes = data_compra.year, data_compra.month
    else:
        ano, mes = _proximo_mes(data_compra.year, data_compra.month)

    competencia = date(ano, mes, 1)
    data_fechamento = _data_com_dia_valido(ano, mes, cartao.dia_fechamento)
    data_vencimento = _data_com_dia_valido(ano, mes, cartao.dia_vencimento)
    return competencia, data_fechamento, data_vencimento


def buscar_opcoes_formulario(titulo=None):
    cartoes_query = FinanceiroCartaoCredito.query.filter_by(ativo=True)
    if titulo and titulo.cartao_credito_id:
        cartoes_query = FinanceiroCartaoCredito.query.filter(
            (FinanceiroCartaoCredito.ativo.is_(True))
            | (FinanceiroCartaoCredito.id == titulo.cartao_credito_id)
        )
    return {
        "fornecedores": SuprimentosFornecedor.query.filter_by(ativo=True).order_by(
            SuprimentosFornecedor.razao_social.asc()
        ).all(),
        "centros_custo": CentroCusto.query.filter_by(ativo=True).order_by(
            CentroCusto.nome.asc()
        ).all(),
        "cartoes_credito": cartoes_query.order_by(
            FinanceiroCartaoCredito.nome.asc(), FinanceiroCartaoCredito.banco.asc()
        ).all(),
        "origens": ORIGENS_LANCAMENTO,
        "tipos_pagamento": TIPOS_PAGAMENTO,
        "formas_pagamento": FORMAS_PAGAMENTO,
        "status": STATUS_TITULO,
        "status_fatura": STATUS_FATURA,
    }


def buscar_titulo_por_id(titulo_id):
    return FinanceiroContaPagarTitulo.query.get(titulo_id)


def buscar_cartao_por_id(cartao_id):
    return FinanceiroCartaoCredito.query.get(cartao_id)


def buscar_fatura_por_id(fatura_id):
    return FinanceiroCartaoFatura.query.get(fatura_id)


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

    faturas_abertas = FinanceiroCartaoFatura.query.filter(
        FinanceiroCartaoFatura.status.in_(["Aberta", "Fechada", "Agendada"])
    )
    total_faturas_abertas = faturas_abertas.with_entities(
        func.coalesce(func.sum(FinanceiroCartaoFatura.valor_total - FinanceiroCartaoFatura.valor_pago), 0)
    ).scalar()
    faturas_7_dias = faturas_abertas.filter(
        FinanceiroCartaoFatura.data_vencimento >= hoje,
        FinanceiroCartaoFatura.data_vencimento <= em_7_dias,
    ).count()
    compras_cartao_mes = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.tipo_pagamento == "Cartao de Credito",
        FinanceiroContaPagarTitulo.status.notin_(["Cancelado", "Estornado"]),
        FinanceiroContaPagarTitulo.data_compra_cartao >= inicio_mes,
        FinanceiroContaPagarTitulo.data_compra_cartao < inicio_proximo_mes,
    ).with_entities(
        func.coalesce(func.sum(FinanceiroContaPagarTitulo.valor_original), 0)
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
        "qtd_faturas_abertas": faturas_abertas.count(),
        "total_faturas_abertas": total_faturas_abertas or Decimal("0.00"),
        "qtd_faturas_7_dias": faturas_7_dias,
        "qtd_cartoes_ativos": FinanceiroCartaoCredito.query.filter_by(ativo=True).count(),
        "compras_cartao_mes": compras_cartao_mes or Decimal("0.00"),
    }


def listar_cartoes(filtros=None):
    filtros = filtros or {}
    query = FinanceiroCartaoCredito.query
    status = (filtros.get("status") or "").strip()
    busca = normalizar_texto(filtros.get("busca"), upper=False)
    if status == "ativos":
        query = query.filter(FinanceiroCartaoCredito.ativo.is_(True))
    elif status == "inativos":
        query = query.filter(FinanceiroCartaoCredito.ativo.is_(False))
    if busca:
        query = query.filter(
            (FinanceiroCartaoCredito.nome.ilike(f"%{busca}%"))
            | (FinanceiroCartaoCredito.banco.ilike(f"%{busca}%"))
            | (FinanceiroCartaoCredito.bandeira.ilike(f"%{busca}%"))
        )
    return query.order_by(FinanceiroCartaoCredito.ativo.desc(), FinanceiroCartaoCredito.nome.asc()).all()


def salvar_cartao(dados, cartao=None, usuario=None):
    cartao = cartao or FinanceiroCartaoCredito()
    try:
        nome = normalizar_texto(dados.get("nome"))
        banco = normalizar_texto(dados.get("banco"))
        if not nome:
            raise ValueError("Nome do cartao e obrigatorio.")
        if not banco:
            raise ValueError("Banco/instituicao e obrigatorio.")

        ultimos = normalizar_documento(dados.get("ultimos_4_digitos"))
        if ultimos and len(ultimos) != 4:
            raise ValueError("Ultimos 4 digitos devem conter 4 digitos.")

        dia_fechamento = parse_int(dados.get("dia_fechamento"), padrao=0, nome_campo="Dia de fechamento")
        dia_vencimento = parse_int(dados.get("dia_vencimento"), padrao=0, nome_campo="Dia de vencimento")
        if dia_fechamento < 1 or dia_fechamento > 31:
            raise ValueError("Dia de fechamento deve estar entre 1 e 31.")
        if dia_vencimento < 1 or dia_vencimento > 31:
            raise ValueError("Dia de vencimento deve estar entre 1 e 31.")

        cartao.nome = nome
        cartao.banco = banco
        cartao.bandeira = normalizar_texto(dados.get("bandeira")) or None
        cartao.ultimos_4_digitos = ultimos
        cartao.titular_responsavel = normalizar_texto(dados.get("titular_responsavel")) or None
        cartao.dia_fechamento = dia_fechamento
        cartao.dia_vencimento = dia_vencimento
        cartao.limite = parse_decimal(dados.get("limite"), nome_campo="Limite", permitir_nulo=True)
        cartao.centro_custo_id = parse_int(dados.get("centro_custo_id"), padrao=0, nome_campo="Centro de custo") or None
        cartao.observacoes = normalizar_texto(dados.get("observacoes")) or None
        cartao.ativo = dados.get("ativo") == "on" or dados.get("ativo") == "true" or dados.get("ativo") == "1"
        cartao.atualizado_por_usuario_id = getattr(usuario, "id", None)
        if not cartao.id:
            cartao.ativo = True if dados.get("ativo") is None else cartao.ativo
            cartao.criado_por_usuario_id = getattr(usuario, "id", None)
            db.session.add(cartao)

        db.session.commit()
        return True, "Cartao salvo com sucesso.", cartao
    except ValueError as exc:
        db.session.rollback()
        return False, str(exc), cartao


def alterar_status_cartao(cartao, ativo, usuario=None):
    if not cartao:
        return False, "Cartao nao encontrado."
    cartao.ativo = bool(ativo)
    cartao.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    return True, "Cartao reativado com sucesso." if ativo else "Cartao inativado com sucesso."


def _buscar_ou_criar_fatura(cartao, competencia, data_fechamento, data_vencimento, usuario=None):
    fatura = FinanceiroCartaoFatura.query.filter_by(
        cartao_credito_id=cartao.id,
        competencia=competencia,
    ).first()
    if fatura:
        return fatura, False

    fatura = FinanceiroCartaoFatura(
        cartao_credito_id=cartao.id,
        competencia=competencia,
        data_fechamento=data_fechamento,
        data_vencimento=data_vencimento,
        valor_total=Decimal("0.00"),
        valor_pago=Decimal("0.00"),
        status="Aberta",
        criado_por_usuario_id=getattr(usuario, "id", None),
        atualizado_por_usuario_id=getattr(usuario, "id", None),
    )
    db.session.add(fatura)
    db.session.flush()
    _registrar_log(
        "financeiro_cartao_fatura_criada",
        f"Fatura criada automaticamente. ID: {fatura.id}. Cartao: {cartao.id}. Competencia: {competencia:%m/%Y}.",
    )
    return fatura, True


def recalcular_fatura(fatura):
    if not fatura:
        return
    total = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.fatura_cartao_id == fatura.id,
        FinanceiroContaPagarTitulo.status.notin_(["Cancelado", "Estornado"]),
    ).with_entities(func.coalesce(func.sum(FinanceiroContaPagarTitulo.valor_original), 0)).scalar()
    fatura.valor_total = total or Decimal("0.00")


def _desvincular_fatura_anterior(titulo):
    fatura_anterior = titulo.fatura_cartao
    if fatura_anterior:
        titulo.fatura_cartao_id = None
        titulo.competencia_fatura_cartao = None
        recalcular_fatura(fatura_anterior)
    return fatura_anterior


def vincular_titulo_a_fatura_cartao(titulo, usuario=None):
    fatura_anterior = titulo.fatura_cartao
    if titulo.tipo_pagamento != "Cartao de Credito":
        _desvincular_fatura_anterior(titulo)
        titulo.cartao_credito_id = None
        titulo.data_compra_cartao = None
        return fatura_anterior, None

    if not titulo.cartao_credito_id:
        raise ValueError("Selecione um cartao de credito ativo para este titulo.")

    cartao = FinanceiroCartaoCredito.query.get(titulo.cartao_credito_id)
    if not cartao:
        raise ValueError("Cartao de credito nao encontrado.")
    if not cartao.ativo and (not titulo.id or not fatura_anterior):
        raise ValueError("Cartao de credito inativo nao pode ser usado em novo lancamento.")

    data_compra = titulo.data_compra_cartao or titulo.data_emissao or titulo.data_vencimento
    titulo.data_compra_cartao = data_compra
    competencia, data_fechamento, data_vencimento = calcular_ciclo_fatura(cartao, data_compra)
    fatura, criada = _buscar_ou_criar_fatura(cartao, competencia, data_fechamento, data_vencimento, usuario=usuario)

    mudou_fatura = titulo.fatura_cartao_id != fatura.id
    if mudou_fatura and fatura_anterior:
        titulo.fatura_cartao_id = None
        titulo.competencia_fatura_cartao = None
        recalcular_fatura(fatura_anterior)

    titulo.fatura_cartao_id = fatura.id
    titulo.competencia_fatura_cartao = competencia
    recalcular_fatura(fatura)
    if mudou_fatura or criada:
        _registrar_log(
            "financeiro_titulo_vinculado_fatura",
            f"Titulo a pagar vinculado a fatura. Titulo: {titulo.id}. Fatura: {fatura.id}.",
        )
    return fatura_anterior, fatura


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
        forma = dados.get("forma_pagamento") or ""
        if forma == "Cartao de Credito" and not tipo:
            tipo = "Cartao de Credito"
        if tipo not in TIPOS_PAGAMENTO:
            raise ValueError("Tipo de pagamento invalido.")
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
        titulo.data_compra_cartao = parse_data(dados.get("data_compra_cartao"), nome_campo="Data da compra no cartao")
        titulo.valor_original = valor_original
        titulo.valor_desconto = parse_decimal(dados.get("valor_desconto"), nome_campo="Valor de desconto")
        titulo.valor_acrescimo = parse_decimal(dados.get("valor_acrescimo"), nome_campo="Valor de acrescimo")
        titulo.valor_juros_multa = parse_decimal(dados.get("valor_juros_multa"), nome_campo="Valor de juros/multa")
        titulo.valor_pago = parse_decimal(dados.get("valor_pago"), nome_campo="Valor pago")
        titulo.parcela_numero = parcela_numero
        titulo.total_parcelas = total_parcelas
        titulo.centro_custo_id = parse_int(dados.get("centro_custo_id"), padrao=0, nome_campo="Centro de custo") or None
        titulo.cartao_credito_id = parse_int(dados.get("cartao_credito_id"), padrao=0, nome_campo="Cartao de credito") or None
        titulo.status = status
        titulo.observacoes = normalizar_texto(dados.get("observacoes")) or None
        titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
        if not titulo.id:
            titulo.criado_por_usuario_id = getattr(usuario, "id", None)
            db.session.add(titulo)
        db.session.flush()

        fatura_anterior, fatura_atual = vincular_titulo_a_fatura_cartao(titulo, usuario=usuario)
        if fatura_anterior and (not fatura_atual or fatura_anterior.id != fatura_atual.id):
            _registrar_log(
                "financeiro_titulo_fatura_alterada",
                f"Fatura do titulo alterada. Titulo: {titulo.id}. Fatura anterior: {fatura_anterior.id}.",
            )

        db.session.flush()
        if fatura_atual:
            recalcular_fatura(fatura_atual)
        if fatura_anterior and (not fatura_atual or fatura_anterior.id != fatura_atual.id):
            recalcular_fatura(fatura_anterior)

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

    fatura = titulo.fatura_cartao
    titulo.status = "Cancelado"
    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)
    recalcular_fatura(fatura)
    db.session.commit()
    return True, "Titulo cancelado com sucesso."


def listar_faturas(filtros=None):
    filtros = filtros or {}
    query = FinanceiroCartaoFatura.query.join(FinanceiroCartaoCredito)
    cartao_id = (filtros.get("cartao_id") or "").strip()
    competencia = parse_competencia(filtros.get("competencia")) if filtros.get("competencia") else None
    status = (filtros.get("status") or "").strip()
    if cartao_id.isdigit():
        query = query.filter(FinanceiroCartaoFatura.cartao_credito_id == int(cartao_id))
    if competencia:
        query = query.filter(FinanceiroCartaoFatura.competencia == competencia)
    if status:
        query = query.filter(FinanceiroCartaoFatura.status == status)
    try:
        vencimento_inicio = parse_data(filtros.get("vencimento_inicio"), nome_campo="Vencimento inicial")
        vencimento_fim = parse_data(filtros.get("vencimento_fim"), nome_campo="Vencimento final")
        fechamento_inicio = parse_data(filtros.get("fechamento_inicio"), nome_campo="Fechamento inicial")
        fechamento_fim = parse_data(filtros.get("fechamento_fim"), nome_campo="Fechamento final")
    except ValueError:
        vencimento_inicio = vencimento_fim = fechamento_inicio = fechamento_fim = None
    if vencimento_inicio:
        query = query.filter(FinanceiroCartaoFatura.data_vencimento >= vencimento_inicio)
    if vencimento_fim:
        query = query.filter(FinanceiroCartaoFatura.data_vencimento <= vencimento_fim)
    if fechamento_inicio:
        query = query.filter(FinanceiroCartaoFatura.data_fechamento >= fechamento_inicio)
    if fechamento_fim:
        query = query.filter(FinanceiroCartaoFatura.data_fechamento <= fechamento_fim)
    return query.order_by(FinanceiroCartaoFatura.data_vencimento.desc()).all()


def atualizar_status_fatura(fatura, novo_status, usuario=None):
    if not fatura:
        return False, "Fatura nao encontrada."
    if novo_status not in STATUS_FATURA:
        return False, "Status de fatura invalido."
    if fatura.status == "Paga":
        return False, "Fatura paga nao pode ser alterada nesta fase."
    if novo_status == "Cancelada" and (fatura.valor_pago or 0) > 0:
        return False, "Fatura com pagamento registrado nao pode ser cancelada."
    if novo_status == "Aberta" and fatura.status == "Paga":
        return False, "Fatura paga nao pode ser reaberta."
    fatura.status = novo_status
    fatura.atualizado_por_usuario_id = getattr(usuario, "id", None)
    recalcular_fatura(fatura)
    db.session.commit()
    return True, "Fatura atualizada com sucesso."
