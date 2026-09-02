import json
import time
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

def erro_temporario_google_drive(exc):
    mensagem = str(exc).lower()
    return (
        "rate limit" in mensagem
        or "ratelimit" in mensagem
        or "user rate limit exceeded" in mensagem
        or "backend error" in mensagem
        or "internal error" in mensagem
        or "timeout" in mensagem
        or "429" in mensagem
        or "500" in mensagem
        or "502" in mensagem
        or "503" in mensagem
        or "504" in mensagem
    )

def mensagem_cota_storage_service_account():
    return (
        "O Google Drive recusou o upload por falta de cota de armazenamento na conta conectada. "
        "Se estiver usando conta de servico, configure GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID com uma pasta "
        "dentro de um Drive compartilhado e adicione a conta de servico como membro desse Drive."
    )

def mensagem_erro_upload_google_drive(exc, chave_config_pasta, descricao_arquivo="arquivo"):
    mensagem = str(exc).lower()

    if erro_cota_storage_service_account(exc):
        return mensagem_cota_storage_service_account().replace(
            "GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID",
            chave_config_pasta,
        )

    if "file not found" in mensagem or "notfound" in mensagem or "404" in mensagem:
        return (
            f"O Google Drive nao encontrou a pasta configurada em {chave_config_pasta}. "
            "Confira se o ID da pasta esta correto e se a conta conectada tem acesso a ela."
        )

    if (
        "insufficientfilepermissions" in mensagem
        or "insufficient permissions" in mensagem
        or "forbidden" in mensagem
        or "403" in mensagem
    ):
        return (
            f"O Google Drive recusou o envio do {descricao_arquivo} por falta de permissao na pasta "
            f"configurada em {chave_config_pasta}. Compartilhe a pasta com a conta conectada ao sistema "
            "ou use uma pasta de um Drive compartilhado."
        )

    if "invalid_grant" in mensagem or "unauthorized" in mensagem or "401" in mensagem:
        return (
            "A credencial do Google Drive usada pelo sistema nao esta autorizada. "
            "Atualize as credenciais OAuth/refresh token ou a conta de servico configurada."
        )

    return (
        f"Nao foi possivel enviar o {descricao_arquivo} para o Google Drive. "
        f"Confira as credenciais e o compartilhamento da pasta configurada em {chave_config_pasta}."
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


def _valor_config_oauth(chave_principal, chave_alternativa):
    return (
        current_app.config.get(chave_principal)
        or current_app.config.get(chave_alternativa)
        or ""
    ).strip()


def credenciais_oauth_configuradas():
    return all(
        [
            _valor_config_oauth("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_CLIENT_ID"),
            _valor_config_oauth("GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET"),
            _valor_config_oauth("GOOGLE_OAUTH_REFRESH_TOKEN", "GOOGLE_REFRESH_TOKEN"),
        ]
    )


def carregar_credenciais_oauth(scopes=None):
    try:
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise GoogleDriveConfiguracaoErro(
            "Bibliotecas do Google Drive não instaladas."
        ) from exc

    client_id = _valor_config_oauth("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_CLIENT_ID")
    client_secret = _valor_config_oauth("GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET")
    refresh_token = _valor_config_oauth("GOOGLE_OAUTH_REFRESH_TOKEN", "GOOGLE_REFRESH_TOKEN")
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


    metadados = {
        "name": nome_arquivo,
        "parents": [folder_id],
    }

    ultima_excecao = None
    for tentativa in range(3):
        media = MediaIoBaseUpload(
            BytesIO(conteudo),
            mimetype=mime_type,
            resumable=False,
        )
        try:
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
        except Exception as exc:
            ultima_excecao = exc
            if not erro_temporario_google_drive(exc) or tentativa == 2:
                raise
            time.sleep(2 ** tentativa)

    raise ultima_excecao


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
