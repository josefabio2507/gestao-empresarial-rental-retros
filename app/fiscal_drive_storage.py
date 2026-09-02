import os
from io import BytesIO

from flask import current_app

from app.services.google_drive_service import (
    GOOGLE_DRIVE_UPLOAD_SCOPES,
    GoogleDriveConfiguracaoErro,
    criar_google_drive_client_upload,
    mensagem_erro_upload_google_drive,
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


def _escapar_query_drive(valor):
    return valor.replace("\\", "\\\\").replace("'", "\\'")


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
        current_app.logger.exception(
            "[fiscal_drive] Falha ao enviar arquivo fiscal ao Google Drive. Pasta config: %s. Arquivo: %s",
            chave_config_pasta,
            nome_arquivo,
        )
        return False, mensagem_erro_upload_google_drive(
            exc,
            chave_config_pasta,
            descricao_arquivo="arquivo fiscal",
        )

    current_app.logger.warning(
        "[fiscal_drive] Arquivo fiscal enviado ao Drive. Pasta config: %s. Nome: %s. Drive file ID: %s",
        chave_config_pasta,
        nome_arquivo,
        arquivo.get("id"),
    )
    return True, ""


def baixar_arquivo_fiscal_drive(nome_arquivo, chave_config_pasta, mime_type, drive_service=None):
    folder_id = _valor_config(chave_config_pasta)
    if not _parece_pasta_drive(folder_id):
        return None

    try:
        service = drive_service or criar_google_drive_client_upload(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)
        query = " and ".join(
            [
                f"'{_escapar_query_drive(folder_id)}' in parents",
                f"name = '{_escapar_query_drive(nome_arquivo)}'",
                "trashed = false",
            ]
        )
        resposta = (
            service.files()
            .list(
                q=query,
                fields="files(id,name,createdTime)",
                pageSize=10,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        arquivos = resposta.get("files", [])
        if not arquivos:
            return None

        arquivo = sorted(
            arquivos,
            key=lambda item: item.get("createdTime") or "",
            reverse=True,
        )[0]
        conteudo = service.files().get_media(fileId=arquivo["id"]).execute()
    except Exception:
        current_app.logger.exception(
            "[fiscal_drive] Falha ao baixar arquivo fiscal do Google Drive. Pasta config: %s. Nome: %s",
            chave_config_pasta,
            nome_arquivo,
        )
        return None

    buffer = BytesIO(conteudo)
    buffer.seek(0)
    return buffer


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


def _mensagem_com_falha_drive(mensagem, mensagem_drive):
    return f"{mensagem} Porem, {mensagem_drive}"


def aplicar_upload_drive_fiscal(app):
    from app.services import fiscal_service

    if getattr(fiscal_service, "_upload_drive_fiscal_aplicado", False):
        return

    original_salvar_xml = fiscal_service.salvar_xml_documento_bytes
    original_baixar_xml_completo = fiscal_service.baixar_xml_completo_documento

    def salvar_xml_documento_bytes_com_drive(xml_bytes, nsu=None, drive_service=None):
        sucesso, mensagem, documento = original_salvar_xml(xml_bytes, nsu=nsu)
        if not sucesso or not documento:
            return sucesso, mensagem, documento

        sucesso_drive, mensagem_drive = sincronizar_documento_fiscal_drive(
            documento,
            drive_service=drive_service,
        )
        if not sucesso_drive:
            return False, _mensagem_com_falha_drive(mensagem, mensagem_drive), documento

        return sucesso, mensagem, documento

    def baixar_xml_completo_documento_com_drive(documento_id, usuario, cliente_cls=None, drive_service=None):
        sucesso, mensagem, documento = original_baixar_xml_completo(
            documento_id,
            usuario,
            cliente_cls=cliente_cls,
        )
        if not sucesso or not documento or not getattr(documento, "tem_xml_completo", False):
            return sucesso, mensagem, documento

        sucesso_drive, mensagem_drive = sincronizar_documento_fiscal_drive(
            documento,
            drive_service=drive_service,
        )
        if not sucesso_drive:
            return False, _mensagem_com_falha_drive(mensagem, mensagem_drive), documento

        return sucesso, mensagem, documento

    fiscal_service.salvar_xml_documento_bytes = salvar_xml_documento_bytes_com_drive
    fiscal_service.baixar_xml_completo_documento = baixar_xml_completo_documento_com_drive
    fiscal_service._upload_drive_fiscal_aplicado = True
    app.logger.warning("[fiscal_drive] Upload fiscal para Drive configurado.")
