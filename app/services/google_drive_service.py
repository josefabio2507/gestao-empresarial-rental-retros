import json
from io import BytesIO

from flask import current_app


GOOGLE_DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_DRIVE_PDF_MIME_TYPE = "application/pdf"
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
GOOGLE_DRIVE_UPLOAD_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
GOOGLE_DRIVE_LIST_FIELDS = (
    "nextPageToken,"
    "files(id,name,mimeType,webViewLink,webContentLink,createdTime)"
)
GOOGLE_DRIVE_UPLOAD_FIELDS = "id,name,webViewLink,webContentLink"
GOOGLE_OAUTH_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleDriveConfiguracaoErro(Exception):
    pass


def erro_cota_storage_service_account(exc):
    mensagem = str(exc).lower()
    return (
        "storagequotaexceeded" in mensagem
        or "service accounts do not have storage quota" in mensagem
        or "service accounts don't have storage quota" in mensagem
    )


def mensagem_cota_storage_service_account():
    return (
        "O Google Drive recusou o upload porque a conta de servico nao possui cota de armazenamento. "
        "Configure GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID com uma pasta dentro de um Drive compartilhado "
        "e adicione a conta de servico como membro desse Drive."
    )


def carregar_credenciais_service_account(scopes=None):
    try:
        from google.oauth2 import service_account
    except ImportError as exc:
        raise GoogleDriveConfiguracaoErro(
            "Bibliotecas do Google Drive não instaladas."
        ) from exc

    dados_json = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    arquivo_json = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")

    if dados_json:
        try:
            dados = json.loads(dados_json)
        except json.JSONDecodeError as exc:
            raise GoogleDriveConfiguracaoErro(
                "GOOGLE_SERVICE_ACCOUNT_JSON inválido."
            ) from exc

        return service_account.Credentials.from_service_account_info(
            dados,
            scopes=scopes or GOOGLE_DRIVE_SCOPES,
        )

    if arquivo_json:
        return service_account.Credentials.from_service_account_file(
            arquivo_json,
            scopes=scopes or GOOGLE_DRIVE_SCOPES,
        )

    raise GoogleDriveConfiguracaoErro(
        "Configure GOOGLE_SERVICE_ACCOUNT_JSON ou GOOGLE_SERVICE_ACCOUNT_FILE."
    )


def credenciais_oauth_configuradas():
    return all(
        current_app.config.get(chave)
        for chave in (
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "GOOGLE_OAUTH_REFRESH_TOKEN",
        )
    )


def carregar_credenciais_oauth(scopes=None):
    try:
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise GoogleDriveConfiguracaoErro(
            "Bibliotecas do Google Drive não instaladas."
        ) from exc

    client_id = current_app.config.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = current_app.config.get("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = current_app.config.get("GOOGLE_OAUTH_REFRESH_TOKEN")
    token_uri = current_app.config.get("GOOGLE_OAUTH_TOKEN_URI") or GOOGLE_OAUTH_TOKEN_URI

    if not all([client_id, client_secret, refresh_token]):
        raise GoogleDriveConfiguracaoErro(
            "Configure GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET e GOOGLE_OAUTH_REFRESH_TOKEN."
        )

    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes or GOOGLE_DRIVE_UPLOAD_SCOPES,
    )


def criar_google_drive_client(scopes=None):
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleDriveConfiguracaoErro(
            "Bibliotecas do Google Drive não instaladas."
        ) from exc

    credenciais = carregar_credenciais_service_account(scopes=scopes)
    return build("drive", "v3", credentials=credenciais, cache_discovery=False)


def criar_google_drive_client_oauth(scopes=None):
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleDriveConfiguracaoErro(
            "Bibliotecas do Google Drive não instaladas."
        ) from exc

    credenciais = carregar_credenciais_oauth(scopes=scopes)
    return build("drive", "v3", credentials=credenciais, cache_discovery=False)


def criar_google_drive_client_upload(scopes=None):
    if credenciais_oauth_configuradas():
        return criar_google_drive_client_oauth(scopes=scopes or GOOGLE_DRIVE_UPLOAD_SCOPES)
    return criar_google_drive_client(scopes=scopes or GOOGLE_DRIVE_UPLOAD_SCOPES)


def upload_arquivo_google_drive(service, folder_id, nome_arquivo, conteudo, mime_type):
    try:
        from googleapiclient.http import MediaIoBaseUpload
    except ImportError as exc:
        raise GoogleDriveConfiguracaoErro(
            "Bibliotecas do Google Drive não instaladas."
        ) from exc

    media = MediaIoBaseUpload(
        BytesIO(conteudo),
        mimetype=mime_type,
        resumable=False,
    )
    metadados = {
        "name": nome_arquivo,
        "parents": [folder_id],
    }

    return (
        service.files()
        .create(
            body=metadados,
            media_body=media,
            fields=GOOGLE_DRIVE_UPLOAD_FIELDS,
            supportsAllDrives=True,
        )
        .execute()
    )


def _escapar_query_drive(valor):
    return valor.replace("\\", "\\\\").replace("'", "\\'")


def _montar_query_itens(folder_id, mime_type=None):
    query = [
        f"'{_escapar_query_drive(folder_id)}' in parents",
        "trashed = false",
    ]

    if mime_type:
        query.append(f"mimeType = '{_escapar_query_drive(mime_type)}'")

    return " and ".join(query)


def listar_itens_da_pasta_pagina(
    service,
    folder_id,
    mime_type=None,
    page_token=None,
    page_size=100,
):
    resposta = (
        service.files()
        .list(
            q=_montar_query_itens(folder_id, mime_type=mime_type),
            fields=GOOGLE_DRIVE_LIST_FIELDS,
            pageToken=page_token,
            pageSize=page_size,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )

    return resposta.get("files", []), resposta.get("nextPageToken")


def listar_itens_da_pasta(service, folder_id, mime_type=None):
    itens = []
    page_token = None

    while True:
        resposta = (
            service.files()
            .list(
                q=_montar_query_itens(folder_id, mime_type=mime_type),
                fields=GOOGLE_DRIVE_LIST_FIELDS,
                pageToken=page_token,
                pageSize=1000,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        itens.extend(resposta.get("files", []))
        page_token = resposta.get("nextPageToken")

        if not page_token:
            break

    return itens


def listar_pastas_da_pasta(service, folder_id):
    return listar_itens_da_pasta(
        service,
        folder_id,
        mime_type=GOOGLE_DRIVE_FOLDER_MIME_TYPE,
    )


def listar_pdfs_da_pasta(service, folder_id):
    arquivos = listar_itens_da_pasta(service, folder_id)

    return [
        arquivo
        for arquivo in arquivos
        if (
            arquivo.get("mimeType") == GOOGLE_DRIVE_PDF_MIME_TYPE
            or (arquivo.get("name") or "").lower().endswith(".pdf")
        )
    ]
