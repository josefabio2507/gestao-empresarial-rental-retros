import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

from flask import current_app

from app.extensions import db
from app.models import OperacaoAbastecimento, OperacaoAbastecimentoCustoExtra, OperacaoVeiculoEquipamento, OperacaoVeiculoResponsavel
from app.services.google_drive_service import (
    GOOGLE_DRIVE_UPLOAD_SCOPES,
    GoogleDriveConfiguracaoErro,
    criar_google_drive_client_upload,
    mensagem_erro_upload_google_drive,
    upload_arquivo_google_drive,
)
from app.services.operacao_pool_service import decimal_ou_none, texto, veiculos_vinculados_ao_colaborador
from app.services.permissoes_service import usuario_eh_administrador
from app.services.suprimentos_service import _normalizar_imagem_para_jpg
from app.utils.datas import agora_brasil

TIPOS_COMBUSTIVEL = ["Diesel S10", "Etanol", "Etanol aditivado", "Gasolina comum", "Gasolina aditivada", "Gasolina Premium"]
CATEGORIAS_CUSTO_EXTRA = ["Arla", "Óleo/Lubrificante", "Lavagem", "Produto de Conveniência", "Acessório", "Alimentação", "Serviço", "Outros"]
STATUS_CUSTO_EXTRA_ATIVO = "Ativo"
STATUS_CUSTO_EXTRA_CANCELADO = "Cancelado"
MIME_CUPOM_ABASTECIMENTO = "image/jpeg"


def data_ou_none(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def colaborador_do_usuario(usuario):
    colaborador = getattr(usuario, "colaborador", None)
    if colaborador and colaborador.ativo:
        return colaborador
    return None


def vinculo_ativo_usuario_veiculo(usuario, veiculo_id):
    colaborador = colaborador_do_usuario(usuario)
    if not colaborador or not veiculo_id:
        return None
    return OperacaoVeiculoResponsavel.query.filter_by(
        veiculo_id=veiculo_id,
        colaborador_id=colaborador.id,
        status="Ativo",
        encerrado_em=None,
    ).first()


def listar_veiculos_abastecimento_usuario(usuario):
    if usuario_eh_administrador(usuario):
        return (
            OperacaoVeiculoEquipamento.query.filter_by(ativo=True)
            .order_by(OperacaoVeiculoEquipamento.identificacao.asc())
            .all()
        )
    colaborador = colaborador_do_usuario(usuario)
    if not colaborador:
        return []
    return veiculos_vinculados_ao_colaborador(colaborador.id)


def listar_abastecimentos_usuario(usuario):
    if usuario_eh_administrador(usuario):
        return (
            OperacaoAbastecimento.query
            .order_by(OperacaoAbastecimento.data_abastecimento.desc(), OperacaoAbastecimento.id.desc())
            .all()
        )
    colaborador = colaborador_do_usuario(usuario)
    if not colaborador:
        return []
    return (
        OperacaoAbastecimento.query.filter_by(colaborador_id=colaborador.id)
        .order_by(OperacaoAbastecimento.data_abastecimento.desc(), OperacaoAbastecimento.id.desc())
        .all()
    )


def buscar_abastecimento_usuario(abastecimento_id, usuario):
    if usuario_eh_administrador(usuario):
        return OperacaoAbastecimento.query.get(abastecimento_id)
    colaborador = colaborador_do_usuario(usuario)
    if not colaborador:
        return None
    return OperacaoAbastecimento.query.filter_by(id=abastecimento_id, colaborador_id=colaborador.id).first()


def _nome_arquivo_cupom(veiculo, data_abastecimento):
    identificacao = re.sub(r"[^A-Za-z0-9_-]+", "-", veiculo.identificacao or str(veiculo.id))
    data_texto = data_abastecimento.strftime("%Y%m%d")
    timestamp = agora_brasil().strftime("%H%M%S")
    return f"ABAST-{identificacao}-{data_texto}-{timestamp}.jpg"


def _upload_cupom(arquivo, veiculo, data_abastecimento, drive_service=None):
    if not arquivo or not texto(arquivo.filename):
        return None, None

    conteudo, erro = _normalizar_imagem_para_jpg(arquivo)
    if erro:
        return None, erro

    folder_id = current_app.config.get("GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID", "").strip()
    if not folder_id:
        return None, "Configure GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID para salvar os cupons no Google Drive."

    try:
        service = drive_service or criar_google_drive_client_upload(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)
        arquivo_drive = upload_arquivo_google_drive(
            service,
            folder_id,
            _nome_arquivo_cupom(veiculo, data_abastecimento),
            conteudo,
            MIME_CUPOM_ABASTECIMENTO,
        )
    except GoogleDriveConfiguracaoErro as exc:
        return None, str(exc)
    except Exception as exc:
        current_app.logger.exception("Falha ao enviar cupom de abastecimento para o Google Drive.")
        return None, mensagem_erro_upload_google_drive(
            exc,
            "GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID",
            descricao_arquivo="cupom",
        )

    return {
        "id": arquivo_drive.get("id"),
        "nome": arquivo_drive.get("name") or _nome_arquivo_cupom(veiculo, data_abastecimento),
        "link": arquivo_drive.get("webViewLink") or arquivo_drive.get("webContentLink"),
    }, None

def _lista_form(form_data, campo):
    if hasattr(form_data, "getlist"):
        return form_data.getlist(campo)
    valor = form_data.get(campo) if form_data else None
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def _moeda(valor):
    valor = valor or Decimal("0.00")
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calcular_valor_total_extra(quantidade, valor_unitario):
    return _moeda(quantidade * valor_unitario)


def _registrar_log_abastecimento(evento, mensagem):
    try:
        from app.services.logs_service import registrar_log

        registrar_log(evento, mensagem)
    except Exception:
        current_app.logger.exception("Falha ao registrar log de abastecimento.")


def _sincronizar_custos_extras(abastecimento, form_data, usuario):
    categorias = _lista_form(form_data, "custo_extra_categoria")
    descricoes = _lista_form(form_data, "custo_extra_descricao")
    quantidades = _lista_form(form_data, "custo_extra_quantidade")
    valores_unitarios = _lista_form(form_data, "custo_extra_valor_unitario")
    observacoes = _lista_form(form_data, "custo_extra_observacoes")
    ids = _lista_form(form_data, "custo_extra_id")

    if not any(categorias + descricoes + quantidades + valores_unitarios + observacoes):
        return True, None

    extras_por_id = {str(extra.id): extra for extra in abastecimento.custos_extras}
    total_linhas = max(len(categorias), len(descricoes), len(quantidades), len(valores_unitarios), len(observacoes), len(ids))

    for indice in range(total_linhas):
        categoria = texto(categorias[indice] if indice < len(categorias) else None)
        descricao = texto(descricoes[indice] if indice < len(descricoes) else None)
        quantidade = decimal_ou_none(quantidades[indice] if indice < len(quantidades) else None)
        valor_unitario = decimal_ou_none(valores_unitarios[indice] if indice < len(valores_unitarios) else None)
        observacao = texto(observacoes[indice] if indice < len(observacoes) else None)
        custo_id = texto(ids[indice] if indice < len(ids) else None)

        if not any([categoria, descricao, quantidade, valor_unitario, observacao, custo_id]):
            continue
        if categoria not in CATEGORIAS_CUSTO_EXTRA:
            return False, "Categoria do custo extra e obrigatoria."
        if not descricao:
            return False, "Descricao do custo extra e obrigatoria."
        if quantidade is None or quantidade <= 0:
            return False, "Quantidade do custo extra deve ser maior que zero."
        if valor_unitario is None or valor_unitario < 0:
            return False, "Valor unitario do custo extra deve ser maior ou igual a zero."

        custo = extras_por_id.get(custo_id)
        novo = custo is None
        if novo:
            custo = OperacaoAbastecimentoCustoExtra(
                abastecimento=abastecimento,
                criado_por_usuario_id=getattr(usuario, "id", None),
                status=STATUS_CUSTO_EXTRA_ATIVO,
            )
            db.session.add(custo)

        if custo.status != STATUS_CUSTO_EXTRA_ATIVO:
            continue

        custo.categoria = categoria
        custo.descricao = descricao
        custo.quantidade = quantidade
        custo.valor_unitario = _moeda(valor_unitario)
        custo.valor_total = _calcular_valor_total_extra(quantidade, custo.valor_unitario)
        custo.observacoes = observacao or None
        custo.atualizado_por_usuario_id = getattr(usuario, "id", None)

        if novo:
            _registrar_log_abastecimento("operacao_abastecimento_custo_extra_criado", "Custo extra criado em abastecimento.")
        else:
            _registrar_log_abastecimento("operacao_abastecimento_custo_extra_atualizado", f"Custo extra atualizado. ID: {custo.id}.")

    return True, None


def cancelar_custo_extra_abastecimento(custo_extra_id, usuario, motivo):
    custo = OperacaoAbastecimentoCustoExtra.query.get(custo_extra_id)
    if not custo:
        return False, "Custo extra nao encontrado.", None
    if custo.status != STATUS_CUSTO_EXTRA_ATIVO:
        return False, "Custo extra ja esta cancelado.", custo
    motivo = texto(motivo)
    if not motivo:
        return False, "Informe o motivo do cancelamento.", custo

    custo.status = STATUS_CUSTO_EXTRA_CANCELADO
    custo.cancelado_por_usuario_id = getattr(usuario, "id", None)
    custo.cancelado_em = agora_brasil()
    custo.motivo_cancelamento = motivo
    custo.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    _registrar_log_abastecimento("operacao_abastecimento_custo_extra_cancelado", f"Custo extra cancelado. ID: {custo.id}. Abastecimento: {custo.abastecimento_id}.")
    return True, "Custo extra cancelado com sucesso.", custo


def salvar_abastecimento(form_data, files_data, usuario, veiculo=None, abastecimento=None, drive_service=None):
    veiculo_id = veiculo.id if veiculo else getattr(abastecimento, "veiculo_id", None)
    vinculo = vinculo_ativo_usuario_veiculo(usuario, veiculo_id)
    if not vinculo:
        return False, "Usuario nao possui vinculo ativo com este veiculo/equipamento.", abastecimento

    veiculo = veiculo or vinculo.veiculo
    colaborador = colaborador_do_usuario(usuario)
    equipe = colaborador.equipe if colaborador else None
    data_abastecimento = data_ou_none(form_data.get("data_abastecimento"))
    tipo_combustivel = texto(form_data.get("tipo_combustivel"))
    qtd_litros = decimal_ou_none(form_data.get("qtd_litros"))
    preco = decimal_ou_none(form_data.get("preco"))
    arquivo_cupom = files_data.get("cupom_fiscal") if files_data else None
    valor_total_nota_fiscal = decimal_ou_none(form_data.get("valor_total_nota_fiscal"))
    numero_nota_fiscal = texto(form_data.get("numero_nota_fiscal"))
    chave_acesso_nfe = re.sub(r"\D+", "", texto(form_data.get("chave_acesso_nfe")) or "")

    if not data_abastecimento:
        return False, "Data do abastecimento e obrigatoria.", abastecimento
    if tipo_combustivel not in TIPOS_COMBUSTIVEL:
        return False, "Tipo de combustivel invalido.", abastecimento
    if qtd_litros is None or qtd_litros <= 0:
        return False, "Quantidade de litros e obrigatoria.", abastecimento
    if preco is None or preco < 0:
        return False, "Preco e obrigatorio.", abastecimento
    if not abastecimento and not (arquivo_cupom and texto(arquivo_cupom.filename)):
        return False, "Foto do cupom fiscal e obrigatoria.", abastecimento
    if valor_total_nota_fiscal is not None and valor_total_nota_fiscal < 0:
        return False, "Valor total da nota fiscal deve ser maior ou igual a zero.", abastecimento
    if chave_acesso_nfe and len(chave_acesso_nfe) != 44:
        return False, "Chave de acesso da NF-e deve conter 44 digitos.", abastecimento

    upload = None
    if arquivo_cupom and texto(arquivo_cupom.filename):
        upload, erro = _upload_cupom(arquivo_cupom, veiculo, data_abastecimento, drive_service=drive_service)
        if erro:
            return False, erro, abastecimento

    if not abastecimento:
        abastecimento = OperacaoAbastecimento(
            veiculo_id=veiculo.id,
            vinculo_id=vinculo.id,
            colaborador_id=colaborador.id,
            equipe_id=equipe.id if equipe else None,
            usuario_id=getattr(usuario, "id", None),
        )
        db.session.add(abastecimento)

    abastecimento.data_abastecimento = data_abastecimento
    abastecimento.tipo_combustivel = tipo_combustivel
    abastecimento.qtd_litros = qtd_litros
    abastecimento.preco = preco
    abastecimento.numero_nota_fiscal = numero_nota_fiscal or None
    abastecimento.chave_acesso_nfe = chave_acesso_nfe or None
    abastecimento.valor_total_nota_fiscal = _moeda(valor_total_nota_fiscal) if valor_total_nota_fiscal is not None else None
    abastecimento.observacoes_conferencia = texto(form_data.get("observacoes_conferencia")) or None
    abastecimento.observacoes = texto(form_data.get("observacoes")) or None
    abastecimento.vinculo_id = vinculo.id
    abastecimento.equipe_id = equipe.id if equipe else None

    if upload:
        abastecimento.cupom_drive_file_id = upload["id"]
        abastecimento.cupom_nome_arquivo = upload["nome"]
        abastecimento.cupom_link = upload["link"]

    sucesso_extras, erro_extras = _sincronizar_custos_extras(abastecimento, form_data, usuario)
    if not sucesso_extras:
        db.session.rollback()
        return False, erro_extras, abastecimento

    db.session.flush()
    if abastecimento.valor_total_nota_fiscal is not None:
        if abastecimento.status_conferencia_nota_fiscal == "Conferido":
            _registrar_log_abastecimento("operacao_abastecimento_nf_conferida", f"Valor da NF confere. Abastecimento: {abastecimento.id}.")
        else:
            _registrar_log_abastecimento("operacao_abastecimento_nf_divergente", f"Divergencia na NF. Abastecimento: {abastecimento.id}. Diferenca: {abastecimento.diferenca_nota_fiscal}.")

    db.session.commit()
    return True, "Abastecimento salvo com sucesso.", abastecimento


def data_padrao_form():
    return date.today().isoformat()
