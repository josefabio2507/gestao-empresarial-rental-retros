import re
from datetime import date, datetime

from flask import current_app

from app.extensions import db
from app.models import OperacaoAbastecimento, OperacaoVeiculoResponsavel
from app.services.google_drive_service import (
    GOOGLE_DRIVE_UPLOAD_SCOPES,
    GoogleDriveConfiguracaoErro,
    criar_google_drive_client_upload,
    erro_cota_storage_service_account,
    mensagem_cota_storage_service_account,
    upload_arquivo_google_drive,
)
from app.services.operacao_pool_service import decimal_ou_none, texto, veiculos_vinculados_ao_colaborador
from app.services.suprimentos_service import _normalizar_imagem_para_jpg
from app.utils.datas import agora_brasil

TIPOS_COMBUSTIVEL = ["Diesel", "Diesel S10", "Gasolina", "Etanol", "Arla 32", "Outro"]
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
    colaborador = colaborador_do_usuario(usuario)
    if not colaborador:
        return []
    return veiculos_vinculados_ao_colaborador(colaborador.id)


def listar_abastecimentos_usuario(usuario):
    colaborador = colaborador_do_usuario(usuario)
    if not colaborador:
        return []
    return (
        OperacaoAbastecimento.query.filter_by(colaborador_id=colaborador.id)
        .order_by(OperacaoAbastecimento.data_abastecimento.desc(), OperacaoAbastecimento.id.desc())
        .all()
    )


def buscar_abastecimento_usuario(abastecimento_id, usuario):
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
        if erro_cota_storage_service_account(exc):
            return None, mensagem_cota_storage_service_account()
        return None, "Nao foi possivel enviar o cupom para o Google Drive."

    return {
        "id": arquivo_drive.get("id"),
        "nome": arquivo_drive.get("name") or _nome_arquivo_cupom(veiculo, data_abastecimento),
        "link": arquivo_drive.get("webViewLink") or arquivo_drive.get("webContentLink"),
    }, None


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
    abastecimento.observacoes = texto(form_data.get("observacoes")) or None
    abastecimento.vinculo_id = vinculo.id
    abastecimento.equipe_id = equipe.id if equipe else None

    if upload:
        abastecimento.cupom_drive_file_id = upload["id"]
        abastecimento.cupom_nome_arquivo = upload["nome"]
        abastecimento.cupom_link = upload["link"]

    db.session.commit()
    return True, "Abastecimento salvo com sucesso.", abastecimento


def data_padrao_form():
    return date.today().isoformat()