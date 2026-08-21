import os

from flask import current_app

from app.services.google_drive_service import (
    GOOGLE_DRIVE_UPLOAD_SCOPES,
    GoogleDriveConfiguracaoErro,
    criar_google_drive_client_upload,
    erro_cota_storage_service_account,
    mensagem_cota_storage_service_account,
    upload_arquivo_google_drive,
)


MIME_XML = "application/xml"
MIME_PDF = "application/pdf"


def _valor_config(chave):
    return (current_app.config.get(chave) or "").strip()


def _parece_pasta_drive(valor):
    if not valor:
        return False
    if os.path.isabs(valor):
        return False
    if ":" in valor or "/" in valor or "\\" in valor:
        return False
    return len(valor) >= 10


def _upload_fiscal_drive(caminho, chave_config_pasta, mime_type, drive_service=None):
    folder_id = _valor_config(chave_config_pasta)
    if not _parece_pasta_drive(folder_id):
        return True, ""

    if not caminho or not os.path.exists(caminho):
        return False, f"Arquivo fiscal nao encontrado para envio ao Drive: {os.path.basename(caminho or '')}."

    nome_arquivo = os.path.basename(caminho)
    with open(caminho, "rb") as origem:
        conteudo = origem.read()

    try:
        service = drive_service or criar_google_drive_client_upload(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)
        arquivo = upload_arquivo_google_drive(
            service,
            folder_id,
            nome_arquivo,
            conteudo,
            mime_type,
        )
    except GoogleDriveConfiguracaoErro as exc:
        return False, str(exc)
    except Exception as exc:
        if erro_cota_storage_service_account(exc):
            return False, mensagem_cota_storage_service_account().replace(
                "GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID",
                chave_config_pasta,
            )
        current_app.logger.exception(
            "[fiscal_drive] Falha ao enviar arquivo fiscal ao Google Drive. Pasta config: %s. Arquivo: %s",
            chave_config_pasta,
            nome_arquivo,
        )
        return False, "Nao foi possivel enviar o arquivo fiscal ao Google Drive. Confira as credenciais e o compartilhamento da pasta."

    current_app.logger.warning(
        "[fiscal_drive] Arquivo fiscal enviado ao Drive. Pasta config: %s. Nome: %s. Drive file ID: %s",
        chave_config_pasta,
        nome_arquivo,
        arquivo.get("id"),
    )
    return True, ""


def sincronizar_documento_fiscal_drive(documento, drive_service=None):
    if not documento:
        return True, ""

    uploads = [
        (documento.xml_path, "FISCAL_XML_DIR", MIME_XML),
        (documento.danfe_path, "FISCAL_DANFE_DIR", MIME_PDF),
    ]

    for caminho, chave_config, mime_type in uploads:
        sucesso, mensagem = _upload_fiscal_drive(
            caminho,
            chave_config,
            mime_type,
            drive_service=drive_service,
        )
        if not sucesso:
            return False, mensagem

    return True, ""


def aplicar_upload_drive_fiscal(app):
    from app.services import fiscal_service

    if getattr(fiscal_service, "_upload_drive_fiscal_aplicado", False):
        return

    original_salvar_xml = fiscal_service.salvar_xml_documento_bytes

    def salvar_xml_documento_bytes_com_drive(xml_bytes, nsu=None, drive_service=None):
        sucesso, mensagem, documento = original_salvar_xml(xml_bytes, nsu=nsu)
        if not sucesso or not documento:
            return sucesso, mensagem, documento

        sucesso_drive, mensagem_drive = sincronizar_documento_fiscal_drive(
            documento,
            drive_service=drive_service,
        )
        if not sucesso_drive:
            return False, f"{mensagem} Porem, {mensagem_drive}", documento

        return sucesso, mensagem, documento

    fiscal_service.salvar_xml_documento_bytes = salvar_xml_documento_bytes_com_drive
    fiscal_service._upload_drive_fiscal_aplicado = True
    app.logger.warning("[fiscal_drive] Upload fiscal para Drive configurado.")
