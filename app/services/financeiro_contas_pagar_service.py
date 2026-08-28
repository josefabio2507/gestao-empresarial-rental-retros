from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import os
import re

from flask import current_app
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    agora_brasil,
    CentroCusto,
    FinanceiroCartaoCredito,
    FinanceiroCartaoFatura,
    FinanceiroContaPagarBaixa,
    FinanceiroContaPagarLoteBaixa,
    FinanceiroContaPagarTitulo,
    FiscalDocumento,
    SuprimentosFornecedor,
    SuprimentosOrdemCompra,
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
STATUS_BAIXA = ["Ativa", "Cancelada", "Estornada"]
EXTENSOES_COMPROVANTE = {"pdf", "jpg", "jpeg", "png", "webp"}
MAX_COMPROVANTE_BYTES = 10 * 1024 * 1024
STATUS_XML_FINANCEIRO = [
    "Pendente de geracao",
    "Pendente de conferencia",
    "Aguardando conferencia",
    "Titulos gerados",
    "Parcialmente gerado",
    "Ignorado",
    "Divergente",
    "Ja integrado via O.C.",
    "Cancelado",
]


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

def buscar_lote_baixa_por_id(lote_id):
    return FinanceiroContaPagarLoteBaixa.query.get(lote_id)



def buscar_baixa_por_id(baixa_id):
    return FinanceiroContaPagarBaixa.query.get(baixa_id)


def valor_decimal(valor):
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor or "0")).quantize(Decimal("0.01"))


def calcular_saldo_titulo(titulo):
    if not titulo:
        return Decimal("0.00")
    saldo = valor_decimal(titulo.valor_liquido_previsto) - valor_decimal(titulo.valor_pago)
    return saldo if saldo > 0 else Decimal("0.00")


def _somar_baixas_ativas(titulo):
    if not titulo or not titulo.id:
        return Decimal("0.00")
    total = FinanceiroContaPagarBaixa.query.filter(
        FinanceiroContaPagarBaixa.titulo_id == titulo.id,
        FinanceiroContaPagarBaixa.status == "Ativa",
    ).with_entities(func.coalesce(func.sum(FinanceiroContaPagarBaixa.valor_pago), 0)).scalar()
    return valor_decimal(total)


def _ultima_data_pagamento_ativa(titulo):
    return FinanceiroContaPagarBaixa.query.filter(
        FinanceiroContaPagarBaixa.titulo_id == titulo.id,
        FinanceiroContaPagarBaixa.status == "Ativa",
    ).with_entities(func.max(FinanceiroContaPagarBaixa.data_pagamento)).scalar()


def _status_aberto_por_vencimento(titulo, hoje=None):
    hoje = hoje or date.today()
    if titulo.status == "Aguardando conferencia":
        return "Aguardando conferencia"
    if titulo.data_vencimento and titulo.data_vencimento < hoje:
        return "Vencido"
    return "A vencer"


def recalcular_pagamento_titulo(titulo, usuario=None):
    if not titulo:
        return
    if titulo.status in ("Cancelado", "Estornado"):
        return

    total_pago = _somar_baixas_ativas(titulo)
    valor_liquido = valor_decimal(titulo.valor_liquido_previsto)
    status_anterior = titulo.status

    titulo.valor_pago = total_pago
    titulo.data_pagamento = _ultima_data_pagamento_ativa(titulo) if total_pago > 0 else None
    if total_pago <= 0:
        titulo.status = _status_aberto_por_vencimento(titulo)
    elif total_pago >= valor_liquido:
        titulo.status = "Pago"
    else:
        titulo.status = "Pago parcialmente"
    titulo.atualizado_por_usuario_id = getattr(usuario, "id", None)

    if status_anterior != titulo.status:
        _registrar_log(
            "financeiro_contas_pagar_status_alterado",
            f"Status do titulo a pagar alterado por baixa. ID: {titulo.id}. {status_anterior} -> {titulo.status}.",
        )


def _extensao_comprovante(arquivo):
    nome = secure_filename(arquivo.filename or "")
    if "." not in nome:
        return None
    return nome.rsplit(".", 1)[1].lower()


def _tamanho_arquivo(arquivo):
    posicao = arquivo.stream.tell()
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(posicao)
    return tamanho


def _salvar_comprovante(baixa, arquivo):
    if not arquivo or not arquivo.filename:
        return

    extensao = _extensao_comprovante(arquivo)
    if extensao not in EXTENSOES_COMPROVANTE:
        raise ValueError("Formato de comprovante invalido. Use PDF, JPG, JPEG, PNG ou WEBP.")

    tamanho = _tamanho_arquivo(arquivo)
    if tamanho > MAX_COMPROVANTE_BYTES:
        raise ValueError("Comprovante maior que 10 MB.")

    pasta = os.path.join(current_app.instance_path, "financeiro", "comprovantes")
    os.makedirs(pasta, exist_ok=True)
    data_nome = agora_brasil().strftime("%Y%m%d-%H%M%S")
    nome_armazenado = f"CP-{baixa.titulo_id}_BAIXA-{baixa.id}_{data_nome}.{extensao}"
    caminho = os.path.join(pasta, nome_armazenado)
    arquivo.stream.seek(0)
    arquivo.save(caminho)

    baixa.comprovante_nome_original = arquivo.filename
    baixa.comprovante_nome_armazenado = nome_armazenado
    baixa.comprovante_path = caminho
    baixa.comprovante_extensao = extensao
    baixa.comprovante_tamanho = tamanho
    _registrar_log("financeiro_comprovante_upload", f"Comprovante anexado. Baixa: {baixa.id}. Titulo: {baixa.titulo_id}.")


def registrar_baixa_titulo(titulo, dados, arquivo=None, usuario=None):
    if not titulo:
        return False, "Titulo nao encontrado.", None
    if titulo.status in ("Cancelado", "Estornado"):
        return False, "Titulo cancelado nao pode receber baixa.", None

    try:
        data_pagamento = parse_data(dados.get("data_pagamento"), obrigatorio=True, nome_campo="Data do pagamento")
        valor_pago = parse_decimal(dados.get("valor_pago"), obrigatorio=True, nome_campo="Valor pago")
        if valor_pago <= 0:
            raise ValueError("Valor pago deve ser maior que zero.")
        forma_pagamento = dados.get("forma_pagamento") or ""
        if forma_pagamento not in FORMAS_PAGAMENTO:
            raise ValueError("Forma de pagamento invalida.")

        recalcular_pagamento_titulo(titulo, usuario=usuario)
        saldo = calcular_saldo_titulo(titulo)
        if valor_pago > saldo:
            raise ValueError("O valor informado excede o saldo em aberto.")

        baixa = FinanceiroContaPagarBaixa(
            titulo_id=titulo.id,
            data_pagamento=data_pagamento,
            valor_pago=valor_pago,
            forma_pagamento=forma_pagamento,
            conta_pagamento_descricao=normalizar_texto(dados.get("conta_pagamento_descricao"), upper=False) or None,
            observacoes=normalizar_texto(dados.get("observacoes"), upper=False) or None,
            status="Ativa",
            registrado_por_usuario_id=getattr(usuario, "id", None),
        )
        db.session.add(baixa)
        db.session.flush()
        _salvar_comprovante(baixa, arquivo)
        recalcular_pagamento_titulo(titulo, usuario=usuario)
        if titulo.fatura_cartao:
            recalcular_fatura(titulo.fatura_cartao)
        db.session.commit()

        mensagem = "Titulo quitado com sucesso." if titulo.status == "Pago" else "Pagamento parcial registrado com sucesso."
        _registrar_log("financeiro_baixa_registrada", f"Baixa registrada. ID: {baixa.id}. Titulo: {titulo.id}. Valor: {valor_pago}.")
        return True, mensagem, baixa
    except ValueError as exc:
        db.session.rollback()
        return False, str(exc), None


def cancelar_baixa_titulo(baixa, motivo, usuario=None):
    if not baixa:
        return False, "Baixa nao encontrada."
    if baixa.status != "Ativa":
        return False, "Baixa ja foi cancelada ou estornada."
    motivo = normalizar_texto(motivo, upper=False)
    if not motivo:
        return False, "Informe o motivo do estorno."

    titulo = baixa.titulo
    baixa.status = "Estornada"
    baixa.cancelado_por_usuario_id = getattr(usuario, "id", None)
    baixa.cancelado_em = agora_brasil()
    baixa.motivo_cancelamento = motivo
    recalcular_pagamento_titulo(titulo, usuario=usuario)
    if titulo and titulo.fatura_cartao:
        recalcular_fatura(titulo.fatura_cartao)
    db.session.commit()
    _registrar_log("financeiro_baixa_estornada", f"Baixa estornada. ID: {baixa.id}. Titulo: {baixa.titulo_id}.")
    return True, "Baixa cancelada/estornada com sucesso. O saldo do titulo foi recalculado."


def caminho_comprovante_baixa(baixa):
    if not baixa or baixa.status != "Ativa" or not baixa.comprovante_path:
        return None
    caminho = os.path.abspath(baixa.comprovante_path)
    pasta_base = os.path.abspath(os.path.join(current_app.instance_path, "financeiro", "comprovantes"))
    if not caminho.startswith(pasta_base):
        return None
    if not os.path.exists(caminho):
        return None
    return caminho


def titulo_elegivel_baixa(titulo):
    if not titulo:
        return False
    if titulo.status in ("Pago", "Cancelado", "Estornado"):
        return False
    return calcular_saldo_titulo(titulo) > 0


def titulos_para_baixa_em_massa(ids):
    ids_validos = []
    for item in ids or []:
        try:
            ids_validos.append(int(item))
        except (TypeError, ValueError):
            continue
    if not ids_validos:
        return []
    return FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.id.in_(ids_validos)
    ).order_by(FinanceiroContaPagarTitulo.data_vencimento.asc()).all()


def _salvar_comprovante_lote(lote, arquivo):
    if not arquivo or not arquivo.filename:
        return

    extensao = _extensao_comprovante(arquivo)
    if extensao not in EXTENSOES_COMPROVANTE:
        raise ValueError("Formato de comprovante invalido. Use PDF, JPG, JPEG, PNG ou WEBP.")
    tamanho = _tamanho_arquivo(arquivo)
    if tamanho > MAX_COMPROVANTE_BYTES:
        raise ValueError("Comprovante maior que 10 MB.")

    pasta = os.path.join(current_app.instance_path, "financeiro", "comprovantes")
    os.makedirs(pasta, exist_ok=True)
    data_nome = agora_brasil().strftime("%Y%m%d-%H%M%S")
    nome_armazenado = f"CP-LOTE-{lote.id}_{data_nome}.{extensao}"
    caminho = os.path.join(pasta, nome_armazenado)
    arquivo.stream.seek(0)
    arquivo.save(caminho)

    lote.comprovante_nome_original = arquivo.filename
    lote.comprovante_nome_armazenado = nome_armazenado
    lote.comprovante_path = caminho
    lote.comprovante_extensao = extensao
    lote.comprovante_tamanho = tamanho
    _registrar_log("financeiro_lote_baixa_comprovante_upload", f"Comprovante anexado ao lote de baixa. Lote: {lote.id}.")


def registrar_baixa_em_massa(dados, arquivo=None, usuario=None):
    ids = dados.getlist("titulos_ids") if hasattr(dados, "getlist") else dados.get("titulos_ids", [])
    titulos = titulos_para_baixa_em_massa(ids)
    if not titulos:
        return False, "Nenhum titulo selecionado.", None

    try:
        data_pagamento = parse_data(dados.get("data_pagamento"), obrigatorio=True, nome_campo="Data do pagamento")
        forma_pagamento = dados.get("forma_pagamento") or ""
        if forma_pagamento not in FORMAS_PAGAMENTO:
            raise ValueError("Forma de pagamento invalida.")

        itens = []
        valor_total = Decimal("0.00")
        for titulo in titulos:
            if not titulo_elegivel_baixa(titulo):
                _registrar_log("financeiro_lote_baixa_titulo_rejeitado", f"Titulo rejeitado no lote por inelegibilidade. Titulo: {titulo.id}.")
                raise ValueError("Um ou mais titulos nao estao elegiveis para baixa.")
            valor = parse_decimal(dados.get(f"valor_baixa_{titulo.id}"), obrigatorio=True, nome_campo="Valor a baixar")
            if valor <= 0:
                raise ValueError("Valor a baixar deve ser maior que zero.")
            saldo = calcular_saldo_titulo(titulo)
            if valor > saldo:
                raise ValueError("O valor informado excede o saldo de um dos titulos.")
            itens.append((titulo, valor))
            valor_total += valor

        lote = FinanceiroContaPagarLoteBaixa(
            data_pagamento=data_pagamento,
            forma_pagamento=forma_pagamento,
            conta_pagamento_descricao=normalizar_texto(dados.get("conta_pagamento_descricao"), upper=False) or None,
            observacoes=normalizar_texto(dados.get("observacoes"), upper=False) or None,
            total_titulos=len(itens),
            valor_total_baixado=valor_total,
            status="Ativo",
            criado_por_usuario_id=getattr(usuario, "id", None),
        )
        db.session.add(lote)
        db.session.flush()
        _salvar_comprovante_lote(lote, arquivo)

        faturas_afetadas = set()
        baixas = []
        for titulo, valor in itens:
            baixa = FinanceiroContaPagarBaixa(
                titulo_id=titulo.id,
                lote_baixa_id=lote.id,
                data_pagamento=data_pagamento,
                valor_pago=valor,
                forma_pagamento=forma_pagamento,
                conta_pagamento_descricao=lote.conta_pagamento_descricao,
                observacoes=lote.observacoes,
                status="Ativa",
                comprovante_nome_original=lote.comprovante_nome_original,
                comprovante_nome_armazenado=lote.comprovante_nome_armazenado,
                comprovante_path=lote.comprovante_path,
                comprovante_drive_file_id=lote.comprovante_drive_file_id,
                comprovante_drive_link=lote.comprovante_drive_link,
                comprovante_extensao=lote.comprovante_extensao,
                comprovante_tamanho=lote.comprovante_tamanho,
                registrado_por_usuario_id=getattr(usuario, "id", None),
            )
            db.session.add(baixa)
            baixas.append(baixa)
            db.session.flush()
            recalcular_pagamento_titulo(titulo, usuario=usuario)
            if titulo.fatura_cartao_id:
                faturas_afetadas.add(titulo.fatura_cartao)
            _registrar_log("financeiro_lote_baixa_titulo_incluido", f"Titulo incluido em lote de baixa. Lote: {lote.id}. Titulo: {titulo.id}. Valor: {valor}.")

        for fatura in faturas_afetadas:
            recalcular_fatura(fatura)
        db.session.commit()
        _registrar_log("financeiro_lote_baixa_criado", f"Lote de baixa criado. ID: {lote.id}. Titulos: {lote.total_titulos}. Valor: {lote.valor_total_baixado}.")
        return True, "Baixa em massa registrada com sucesso.", lote
    except ValueError as exc:
        db.session.rollback()
        return False, str(exc), None


def estornar_lote_baixa(lote, motivo, usuario=None):
    if not lote:
        return False, "Lote de baixa nao encontrado."
    if lote.status != "Ativo":
        return False, "Lote ja foi cancelado ou estornado."
    motivo = normalizar_texto(motivo, upper=False)
    if not motivo:
        return False, "Informe o motivo do estorno."

    lote.status = "Estornado"
    lote.cancelado_por_usuario_id = getattr(usuario, "id", None)
    lote.cancelado_em = agora_brasil()
    lote.motivo_cancelamento = motivo
    faturas_afetadas = set()
    for baixa in lote.baixas:
        if baixa.status == "Ativa":
            baixa.status = "Estornada"
            baixa.cancelado_por_usuario_id = getattr(usuario, "id", None)
            baixa.cancelado_em = lote.cancelado_em
            baixa.motivo_cancelamento = motivo
            recalcular_pagamento_titulo(baixa.titulo, usuario=usuario)
            if baixa.titulo and baixa.titulo.fatura_cartao_id:
                faturas_afetadas.add(baixa.titulo.fatura_cartao)
    for fatura in faturas_afetadas:
        recalcular_fatura(fatura)
    db.session.commit()
    _registrar_log("financeiro_lote_baixa_estornado", f"Lote de baixa estornado. ID: {lote.id}.")
    return True, "Lote de baixa estornado com sucesso."


def caminho_comprovante_lote(lote):
    if not lote or lote.status != "Ativo" or not lote.comprovante_path:
        return None
    caminho = os.path.abspath(lote.comprovante_path)
    pasta_base = os.path.abspath(os.path.join(current_app.instance_path, "financeiro", "comprovantes"))
    if not caminho.startswith(pasta_base):
        return None
    if not os.path.exists(caminho):
        return None
    return caminho

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
    status_pagamento = (filtros.get("status_pagamento") or "").strip()

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
    if status_pagamento == "em_aberto":
        query = query.filter(FinanceiroContaPagarTitulo.status.notin_(["Pago", "Cancelado", "Estornado"]))
    elif status_pagamento == "pago":
        query = query.filter(FinanceiroContaPagarTitulo.status == "Pago")
    elif status_pagamento == "parcial":
        query = query.filter(FinanceiroContaPagarTitulo.status == "Pago parcialmente")

    try:
        vencimento_inicio = parse_data(filtros.get("vencimento_inicio"), nome_campo="Vencimento inicial")
        vencimento_fim = parse_data(filtros.get("vencimento_fim"), nome_campo="Vencimento final")
        pagamento_inicio = parse_data(filtros.get("pagamento_inicio"), nome_campo="Pagamento inicial")
        pagamento_fim = parse_data(filtros.get("pagamento_fim"), nome_campo="Pagamento final")
    except ValueError:
        vencimento_inicio = vencimento_fim = pagamento_inicio = pagamento_fim = None

    if vencimento_inicio:
        query = query.filter(FinanceiroContaPagarTitulo.data_vencimento >= vencimento_inicio)
    if vencimento_fim:
        query = query.filter(FinanceiroContaPagarTitulo.data_vencimento <= vencimento_fim)
    if pagamento_inicio:
        query = query.filter(FinanceiroContaPagarTitulo.data_pagamento >= pagamento_inicio)
    if pagamento_fim:
        query = query.filter(FinanceiroContaPagarTitulo.data_pagamento <= pagamento_fim)

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

    total_pago_mes = FinanceiroContaPagarBaixa.query.filter(
        FinanceiroContaPagarBaixa.status == "Ativa",
        FinanceiroContaPagarBaixa.data_pagamento >= inicio_mes,
        FinanceiroContaPagarBaixa.data_pagamento < inicio_proximo_mes,
    ).with_entities(func.coalesce(func.sum(FinanceiroContaPagarBaixa.valor_pago), 0)).scalar()
    titulos_pagos_mes = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.status == "Pago",
        FinanceiroContaPagarTitulo.data_pagamento >= inicio_mes,
        FinanceiroContaPagarTitulo.data_pagamento < inicio_proximo_mes,
    ).count()
    total_parcialmente_pago = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.status == "Pago parcialmente",
    ).with_entities(func.coalesce(func.sum(FinanceiroContaPagarTitulo.valor_pago), 0)).scalar()
    titulos_sem_comprovante = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.valor_pago > 0,
        ~FinanceiroContaPagarTitulo.baixas.any(
            (FinanceiroContaPagarBaixa.status == "Ativa")
            & (FinanceiroContaPagarBaixa.comprovante_path.isnot(None))
        ),
    ).count()
    pago_por_forma = FinanceiroContaPagarBaixa.query.filter(
        FinanceiroContaPagarBaixa.status == "Ativa",
        FinanceiroContaPagarBaixa.data_pagamento >= inicio_mes,
        FinanceiroContaPagarBaixa.data_pagamento < inicio_proximo_mes,
    ).with_entities(
        FinanceiroContaPagarBaixa.forma_pagamento,
        func.coalesce(func.sum(FinanceiroContaPagarBaixa.valor_pago), 0),
    ).group_by(FinanceiroContaPagarBaixa.forma_pagamento).all()

    try:
        from app.services.suprimentos_service import indicadores_financeiro_ordens_compra

        indicadores_oc = indicadores_financeiro_ordens_compra(hoje=hoje)
    except Exception:
        indicadores_oc = {
            "titulos_oc_conferencia": 0,
            "valor_oc_integrado_mes": Decimal("0.00"),
            "ocs_prontas_gerar": 0,
            "ocs_pendencia_financeira": 0,
        }

    try:
        indicadores_xml = indicadores_financeiro_xml(hoje=hoje)
    except Exception:
        indicadores_xml = {
            "xml_pendentes_geracao": 0,
            "xml_aguardando_conferencia": 0,
            "valor_xml_pendente": Decimal("0.00"),
            "xml_integrados_mes": 0,
            "xml_integrados_via_oc": 0,
        }

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
        "total_pago_mes": total_pago_mes or Decimal("0.00"),
        "total_parcialmente_pago": total_parcialmente_pago or Decimal("0.00"),
        "titulos_pagos_mes": titulos_pagos_mes,
        "titulos_sem_comprovante": titulos_sem_comprovante,
        "pago_por_forma": {forma: valor_decimal(total) for forma, total in pago_por_forma},
        "titulos_oc_conferencia": indicadores_oc["titulos_oc_conferencia"],
        "valor_oc_integrado_mes": indicadores_oc["valor_oc_integrado_mes"],
        "ocs_prontas_gerar": indicadores_oc["ocs_prontas_gerar"],
        "ocs_pendencia_financeira": indicadores_oc["ocs_pendencia_financeira"],
        "xml_pendentes_geracao": indicadores_xml["xml_pendentes_geracao"],
        "xml_aguardando_conferencia": indicadores_xml["xml_aguardando_conferencia"],
        "valor_xml_pendente": indicadores_xml["valor_xml_pendente"],
        "xml_integrados_mes": indicadores_xml["xml_integrados_mes"],
        "xml_integrados_via_oc": indicadores_xml["xml_integrados_via_oc"],
    }




def _somar_meses_data(data_base, meses):
    mes_zero = data_base.month - 1 + meses
    ano = data_base.year + mes_zero // 12
    mes = mes_zero % 12 + 1
    return _data_com_dia_valido(ano, mes, data_base.day)


def _calcular_parcelas(valor_total, quantidade_parcelas):
    quantidade_parcelas = int(quantidade_parcelas or 1)
    valor_total = Decimal(valor_total or 0).quantize(Decimal("0.01"))
    if quantidade_parcelas <= 1:
        return [valor_total]
    valor_base = (valor_total / Decimal(quantidade_parcelas)).quantize(Decimal("0.01"))
    parcelas = [valor_base for _ in range(quantidade_parcelas)]
    diferenca = valor_total - sum(parcelas, Decimal("0.00"))
    parcelas[-1] = (parcelas[-1] + diferenca).quantize(Decimal("0.01"))
    return parcelas


def buscar_documento_fiscal_por_id(documento_id):
    return FiscalDocumento.query.get(documento_id)


def titulos_ativos_documento_fiscal(documento):
    if not documento or not documento.id:
        return []
    return (
        FinanceiroContaPagarTitulo.query
        .filter(
            FinanceiroContaPagarTitulo.fiscal_documento_id == documento.id,
            FinanceiroContaPagarTitulo.status.notin_(["Cancelado", "Estornado"]),
        )
        .order_by(FinanceiroContaPagarTitulo.parcela_numero.asc())
        .all()
    )


def _titulos_ativos_ordem_xml(documento):
    if not documento or not documento.ordem_compra_id:
        return []
    return (
        FinanceiroContaPagarTitulo.query
        .filter(
            FinanceiroContaPagarTitulo.ordem_compra_id == documento.ordem_compra_id,
            FinanceiroContaPagarTitulo.status.notin_(["Cancelado", "Estornado"]),
        )
        .order_by(FinanceiroContaPagarTitulo.parcela_numero.asc())
        .all()
    )


def status_financeiro_xml(documento):
    if not documento:
        return "Nao localizado"
    if documento.status == "Cancelada":
        return "Cancelado"
    if getattr(documento, "financeiro_ignorado", False):
        return "Ignorado"
    titulos_xml = titulos_ativos_documento_fiscal(documento)
    if titulos_xml:
        if any(titulo.status == "Aguardando conferencia" for titulo in titulos_xml):
            return "Aguardando conferencia"
        return "Titulos gerados"
    titulos_ordem = _titulos_ativos_ordem_xml(documento)
    if titulos_ordem:
        return "Ja integrado via O.C."
    if getattr(documento, "financeiro_integrado", False):
        return documento.financeiro_status or "Titulos gerados"
    if documento.ordem_compra_id:
        return "Pendente de geracao"
    return "Pendente de conferencia"


def _documento_fiscal_apto_base(query):
    return query.filter(
        FiscalDocumento.tem_xml_completo.is_(True),
        FiscalDocumento.chave_acesso.isnot(None),
        FiscalDocumento.emitente_nome.isnot(None),
        FiscalDocumento.emitente_cnpj.isnot(None),
        FiscalDocumento.valor_total > 0,
        FiscalDocumento.status != "Cancelada",
    )


def listar_agendamentos_xml_contas_pagar(filtros=None):
    filtros = filtros or {}
    query = _documento_fiscal_apto_base(FiscalDocumento.query)

    fornecedor = normalizar_texto(filtros.get("fornecedor"), upper=False)
    cnpj = normalizar_documento(filtros.get("cnpj"))
    numero = normalizar_texto(filtros.get("numero_nfe"), upper=False)
    chave = normalizar_documento(filtros.get("chave_acesso"))
    status = normalizar_texto(filtros.get("status_financeiro"), upper=False)
    vinculo_oc = normalizar_texto(filtros.get("vinculo_oc"), upper=False)

    if fornecedor:
        query = query.filter(FiscalDocumento.emitente_nome.ilike(f"%{fornecedor}%"))
    if cnpj:
        query = query.filter(FiscalDocumento.emitente_cnpj.ilike(f"%{cnpj}%"))
    if numero:
        query = query.filter(FiscalDocumento.numero.ilike(f"%{numero}%"))
    if chave:
        query = query.filter(FiscalDocumento.chave_acesso.ilike(f"%{chave}%"))
    if vinculo_oc == "com_oc":
        query = query.filter(FiscalDocumento.ordem_compra_id.isnot(None))
    elif vinculo_oc == "sem_oc":
        query = query.filter(FiscalDocumento.ordem_compra_id.is_(None))

    try:
        emissao_inicio = parse_data(filtros.get("emissao_inicio"), nome_campo="Emissao inicial")
        emissao_fim = parse_data(filtros.get("emissao_fim"), nome_campo="Emissao final")
    except ValueError:
        emissao_inicio = None
        emissao_fim = None
    if emissao_inicio:
        query = query.filter(FiscalDocumento.data_emissao >= emissao_inicio)
    if emissao_fim:
        query = query.filter(FiscalDocumento.data_emissao < emissao_fim + timedelta(days=1))

    documentos = query.order_by(FiscalDocumento.data_emissao.desc().nullslast(), FiscalDocumento.id.desc()).all()
    if status:
        documentos = [doc for doc in documentos if status_financeiro_xml(doc).lower() == status.lower()]
    if filtros.get("somente_pendentes"):
        documentos = [doc for doc in documentos if status_financeiro_xml(doc) in ["Pendente de geracao", "Pendente de conferencia"]]
    return documentos


def opcoes_conferencia_xml(documento=None):
    opcoes = buscar_opcoes_formulario()
    try:
        from app.services.suprimentos_service import CONDICOES_PAGAMENTO_FINANCEIRO_OC
        opcoes["condicoes_pagamento"] = CONDICOES_PAGAMENTO_FINANCEIRO_OC
    except Exception:
        opcoes["condicoes_pagamento"] = ["A vista", "7 dias", "14 dias", "21 dias", "28 dias", "30 dias", "45 dias", "60 dias", "Parcelado", "Personalizado"]
    return opcoes


def dados_padrao_conferencia_xml(documento):
    ordem = getattr(documento, "ordem_compra", None)
    emissao = documento.data_emissao.date() if getattr(documento, "data_emissao", None) else date.today()
    vencimento = getattr(ordem, "data_primeiro_vencimento_financeiro", None) or emissao
    return {
        "tipo_pagamento": getattr(ordem, "tipo_pagamento_financeiro", None) or "Faturado",
        "forma_pagamento": getattr(ordem, "forma_pagamento_financeiro", None) or "Boleto",
        "condicao_pagamento": getattr(ordem, "condicao_pagamento_financeiro", None) or "A vista",
        "numero_parcelas": getattr(ordem, "numero_parcelas_financeiro", None) or 1,
        "data_primeiro_vencimento": vencimento,
        "cartao_credito_id": getattr(ordem, "cartao_credito_id", None),
        "centro_custo_id": getattr(getattr(ordem, "requisicao", None), "centro_custo_id", None),
        "sub_centro_custo_equipe_id": getattr(getattr(ordem, "requisicao", None), "sub_centro_custo_equipe_id", None),
        "sub_centro_custo_veiculo_id": getattr(getattr(ordem, "requisicao", None), "sub_centro_custo_veiculo_id", None),
        "observacoes": getattr(documento, "financeiro_observacoes", None) or "",
    }


def _validar_documento_fiscal_para_financeiro(documento):
    if not documento:
        return False, "Documento fiscal nao encontrado."
    if documento.status == "Cancelada":
        return False, "XML cancelado nao pode gerar Contas a Pagar."
    if not documento.tem_xml_completo or not documento.chave_acesso:
        return False, "XML completo e chave de acesso sao obrigatorios."
    if not documento.emitente_nome or not documento.emitente_cnpj:
        return False, "XML sem fornecedor identificado nao pode gerar Contas a Pagar."
    if not documento.valor_total or Decimal(documento.valor_total or 0) <= 0:
        return False, "XML sem valor total nao pode gerar Contas a Pagar."
    return True, None


def _duplicidade_documento_fiscal(documento):
    titulos_xml = titulos_ativos_documento_fiscal(documento)
    if titulos_xml:
        return "Este XML ja possui titulos financeiros gerados.", titulos_xml
    titulos_ordem = _titulos_ativos_ordem_xml(documento)
    if titulos_ordem:
        return "Este XML ja foi integrado via Ordem de Compra.", titulos_ordem
    similares = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.status.notin_(["Cancelado", "Estornado"]),
        FinanceiroContaPagarTitulo.chave_acesso_nfe == documento.chave_acesso,
    ).all()
    if similares:
        return "Este XML ja possui titulos financeiros gerados ou ja foi integrado por meio da Ordem de Compra vinculada.", similares
    return None, []


def gerar_contas_pagar_xml(documento, dados, usuario=None):
    sucesso, mensagem = _validar_documento_fiscal_para_financeiro(documento)
    if not sucesso:
        _registrar_log("financeiro_xml_validacao_falhou", f"{mensagem} Documento fiscal: {getattr(documento, 'id', None)}.")
        return False, mensagem, []

    mensagem_dup, titulos_dup = _duplicidade_documento_fiscal(documento)
    if mensagem_dup:
        _registrar_log("financeiro_xml_duplicidade", f"{mensagem_dup} Documento fiscal: {documento.id}.")
        return False, mensagem_dup, titulos_dup

    padrao = dados_padrao_conferencia_xml(documento)
    dados = dados or {}
    tipo = dados.get("tipo_pagamento") or padrao["tipo_pagamento"]
    forma = dados.get("forma_pagamento") or padrao["forma_pagamento"]
    condicao = dados.get("condicao_pagamento") or padrao["condicao_pagamento"]
    parcelas = parse_int(str(dados.get("numero_parcelas") or padrao["numero_parcelas"]), nome_campo="Numero de parcelas")
    primeiro_vencimento = parse_data(
        dados.get("data_primeiro_vencimento") or (padrao["data_primeiro_vencimento"].strftime("%Y-%m-%d") if padrao["data_primeiro_vencimento"] else ""),
        obrigatorio=True,
        nome_campo="Data do primeiro vencimento",
    )
    cartao_credito_id = parse_int(str(dados.get("cartao_credito_id") or padrao["cartao_credito_id"] or ""), padrao=0, nome_campo="Cartao de credito") or None
    centro_custo_id = parse_int(str(dados.get("centro_custo_id") or padrao["centro_custo_id"] or ""), padrao=0, nome_campo="Centro de custo") or None
    observacoes = normalizar_texto(dados.get("observacoes") or padrao["observacoes"]) or None

    if tipo not in TIPOS_PAGAMENTO:
        return False, "Tipo de pagamento invalido.", []
    if forma not in FORMAS_PAGAMENTO:
        return False, "Forma de pagamento invalida.", []
    if parcelas < 1:
        return False, "Numero de parcelas deve ser no minimo 1.", []
    if tipo == "Cartao de Credito":
        if not cartao_credito_id:
            return False, "Informe o cartao de credito para compras pagas com cartao.", []
        cartao = FinanceiroCartaoCredito.query.get(cartao_credito_id)
        if not cartao or not cartao.ativo:
            return False, "Cartao de credito ativo nao encontrado.", []
        forma = "Cartao de Credito"
    else:
        cartao_credito_id = None

    ordem = getattr(documento, "ordem_compra", None)
    valores = _calcular_parcelas(documento.valor_total, parcelas)
    emissao = documento.data_emissao.date() if getattr(documento, "data_emissao", None) else date.today()
    titulos = []
    faturas_afetadas = set()

    for indice, valor in enumerate(valores, start=1):
        vencimento = _somar_meses_data(primeiro_vencimento, indice - 1)
        titulo = FinanceiroContaPagarTitulo(
            fornecedor_id=getattr(ordem, "fornecedor_id", None),
            fornecedor_nome_snapshot=documento.emitente_nome,
            fornecedor_cnpj_cpf_snapshot=normalizar_documento(documento.emitente_cnpj),
            descricao=f"NF-e {documento.numero} - {documento.emitente_nome}",
            numero_documento=f"{documento.numero}-{indice:02d}/{parcelas:02d}",
            numero_nfe=documento.numero,
            chave_acesso_nfe=documento.chave_acesso,
            ordem_compra_id=documento.ordem_compra_id,
            fiscal_documento_id=documento.id,
            origem_lancamento="XML Fiscal",
            tipo_pagamento=tipo,
            forma_pagamento=forma,
            competencia=vencimento.replace(day=1),
            data_emissao=emissao,
            data_vencimento=vencimento,
            valor_original=valor,
            valor_desconto=Decimal("0.00"),
            valor_acrescimo=Decimal("0.00"),
            valor_juros_multa=Decimal("0.00"),
            valor_pago=Decimal("0.00"),
            parcela_numero=indice,
            total_parcelas=parcelas,
            centro_custo_id=centro_custo_id,
            sub_centro_custo_equipe_id=padrao["sub_centro_custo_equipe_id"],
            sub_centro_custo_veiculo_id=padrao["sub_centro_custo_veiculo_id"],
            status="Aguardando conferencia",
            observacoes=observacoes,
            criado_por_usuario_id=getattr(usuario, "id", None),
            atualizado_por_usuario_id=getattr(usuario, "id", None),
        )
        if tipo == "Cartao de Credito":
            titulo.cartao_credito_id = cartao_credito_id
            titulo.data_compra_cartao = _somar_meses_data(emissao, indice - 1)
        db.session.add(titulo)
        db.session.flush()
        if titulo.tipo_pagamento == "Cartao de Credito":
            _, fatura = vincular_titulo_a_fatura_cartao(titulo, usuario=usuario)
            if fatura:
                titulo.data_vencimento = fatura.data_vencimento
                titulo.competencia = fatura.competencia
                faturas_afetadas.add(fatura.id)
                _registrar_log("financeiro_xml_titulo_vinculado_fatura", f"Titulo {titulo.id} vinculado a fatura {fatura.id}. XML: {documento.id}.")
        titulos.append(titulo)

    for fatura_id in faturas_afetadas:
        fatura = next((titulo.fatura_cartao for titulo in titulos if titulo.fatura_cartao_id == fatura_id), None)
        recalcular_fatura(fatura)

    documento.financeiro_status = "Aguardando conferencia"
    documento.financeiro_integrado = True
    documento.financeiro_integrado_em = agora_brasil()
    documento.financeiro_integrado_por_usuario_id = getattr(usuario, "id", None)
    documento.financeiro_ignorado = False
    documento.financeiro_observacoes = observacoes
    if ordem:
        ordem.financeiro_integrado = True
        ordem.financeiro_integrado_em = documento.financeiro_integrado_em
        ordem.financeiro_integrado_por_usuario_id = getattr(usuario, "id", None)
        if hasattr(ordem, "status_financeiro"):
            ordem.status_financeiro = "Integrado ao Financeiro"

    db.session.commit()
    _registrar_log("financeiro_xml_titulos_gerados", f"Gerados {len(titulos)} titulos por XML fiscal. Documento fiscal: {documento.id}.")
    return True, "Titulos financeiros gerados com sucesso a partir do XML.", titulos


def ignorar_xml_financeiro(documento, usuario=None, observacoes=None):
    sucesso, mensagem = _validar_documento_fiscal_para_financeiro(documento)
    if not sucesso and mensagem != "XML sem valor total nao pode gerar Contas a Pagar.":
        return False, mensagem
    if titulos_ativos_documento_fiscal(documento):
        return False, "XML com titulos ativos nao pode ser ignorado financeiramente."
    documento.financeiro_ignorado = True
    documento.financeiro_ignorado_em = agora_brasil()
    documento.financeiro_ignorado_por_usuario_id = getattr(usuario, "id", None)
    documento.financeiro_status = "Ignorado"
    documento.financeiro_observacoes = normalizar_texto(observacoes) or documento.financeiro_observacoes
    db.session.commit()
    _registrar_log("financeiro_xml_ignorado", f"XML ignorado financeiramente. Documento fiscal: {documento.id}.")
    return True, "XML ignorado financeiramente."


def reativar_xml_financeiro(documento, usuario=None):
    if not documento:
        return False, "Documento fiscal nao encontrado."
    documento.financeiro_ignorado = False
    documento.financeiro_ignorado_em = None
    documento.financeiro_ignorado_por_usuario_id = None
    documento.financeiro_status = status_financeiro_xml(documento)
    db.session.commit()
    _registrar_log("financeiro_xml_reativado", f"XML reativado para processamento financeiro. Documento fiscal: {documento.id}.")
    return True, "XML reativado para processamento financeiro."


def indicadores_financeiro_xml(hoje=None):
    hoje = hoje or date.today()
    inicio_mes = hoje.replace(day=1)
    inicio_proximo_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) if hoje.month == 12 else hoje.replace(month=hoje.month + 1, day=1)
    documentos = listar_agendamentos_xml_contas_pagar({})
    pendentes = [doc for doc in documentos if status_financeiro_xml(doc) in ["Pendente de geracao", "Pendente de conferencia"]]
    aguardando = [doc for doc in documentos if status_financeiro_xml(doc) == "Aguardando conferencia"]
    via_oc = [doc for doc in documentos if status_financeiro_xml(doc) == "Ja integrado via O.C."]
    integrados_mes = FiscalDocumento.query.filter(
        FiscalDocumento.financeiro_integrado.is_(True),
        FiscalDocumento.financeiro_integrado_em >= inicio_mes,
        FiscalDocumento.financeiro_integrado_em < inicio_proximo_mes,
    ).count()
    valor_pendente = sum((Decimal(doc.valor_total or 0) for doc in pendentes), Decimal("0.00"))
    return {
        "xml_pendentes_geracao": len(pendentes),
        "xml_aguardando_conferencia": len(aguardando),
        "valor_xml_pendente": valor_pendente,
        "xml_integrados_mes": integrados_mes,
        "xml_integrados_via_oc": len(via_oc),
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
    titulos = FinanceiroContaPagarTitulo.query.filter(
        FinanceiroContaPagarTitulo.fatura_cartao_id == fatura.id,
        FinanceiroContaPagarTitulo.status.notin_(["Cancelado", "Estornado"]),
    ).all()
    fatura.valor_total = sum((valor_decimal(titulo.valor_original) for titulo in titulos), Decimal("0.00"))
    fatura.valor_pago = sum((valor_decimal(titulo.valor_pago) for titulo in titulos), Decimal("0.00"))
    if fatura.valor_pago <= 0:
        fatura.data_pagamento = None
    else:
        fatura.data_pagamento = max((titulo.data_pagamento for titulo in titulos if titulo.data_pagamento), default=None)
    if fatura.status != "Cancelada" and fatura.valor_total > 0:
        if fatura.valor_pago >= fatura.valor_total:
            fatura.status = "Paga"
        elif fatura.status == "Paga":
            fatura.status = "Fechada"


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
        if not titulo.id:
            titulo.valor_pago = Decimal("0.00")
        else:
            recalcular_pagamento_titulo(titulo, usuario=usuario)
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
