import json

from flask import current_app


GOOGLE_DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_DRIVE_PDF_MIME_TYPE = "application/pdf"
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleDriveConfiguracaoErro(Exception):
    pass


def carregar_credenciais_service_account():
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
            scopes=GOOGLE_DRIVE_SCOPES,
        )

    if arquivo_json:
        return service_account.Credentials.from_service_account_file(
            arquivo_json,
            scopes=GOOGLE_DRIVE_SCOPES,
        )

    raise GoogleDriveConfiguracaoErro(
        "Configure GOOGLE_SERVICE_ACCOUNT_JSON ou GOOGLE_SERVICE_ACCOUNT_FILE."
    )


def criar_google_drive_client():
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleDriveConfiguracaoErro(
            "Bibliotecas do Google Drive não instaladas."
        ) from exc

    credenciais = carregar_credenciais_service_account()
    return build("drive", "v3", credentials=credenciais, cache_discovery=False)


def _escapar_query_drive(valor):
    return valor.replace("\\", "\\\\").replace("'", "\\'")


def listar_itens_da_pasta(service, folder_id, mime_type=None):
    query = [
        f"'{_escapar_query_drive(folder_id)}' in parents",
        "trashed = false",
    ]

    if mime_type:
        query.append(f"mimeType = '{_escapar_query_drive(mime_type)}'")

    campos = (
        "nextPageToken,"
        "files(id,name,mimeType,webViewLink,webContentLink)"
    )
    itens = []
    page_token = None

    while True:
        resposta = (
            service.files()
            .list(
                q=" and ".join(query),
                fields=campos,
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
