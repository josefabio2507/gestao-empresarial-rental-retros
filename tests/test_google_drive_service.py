import unittest
from unittest.mock import patch

from flask import Flask
from app.services.google_drive_service import (
    GOOGLE_DRIVE_UPLOAD_SCOPES,
    GOOGLE_OAUTH_TOKEN_URI,
    carregar_credenciais_oauth,
    credenciais_oauth_configuradas,
    criar_google_drive_client_upload,
    mensagem_erro_upload_google_drive,
)


class GoogleDriveServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            GOOGLE_OAUTH_CLIENT_ID="",
            GOOGLE_OAUTH_CLIENT_SECRET="",
            GOOGLE_OAUTH_REFRESH_TOKEN="",
            GOOGLE_CLIENT_ID="",
            GOOGLE_CLIENT_SECRET="",
            GOOGLE_REFRESH_TOKEN="",
            GOOGLE_OAUTH_TOKEN_URI="",
        )
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_credenciais_oauth_configuradas_exige_tres_variaveis(self):
        self.assertFalse(credenciais_oauth_configuradas())

        self.app.config.update(
            GOOGLE_OAUTH_CLIENT_ID="client-id",
            GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
            GOOGLE_OAUTH_REFRESH_TOKEN="refresh-token",
        )

        self.assertTrue(credenciais_oauth_configuradas())

    def test_carrega_credenciais_oauth_para_upload(self):
        self.app.config.update(
            GOOGLE_OAUTH_CLIENT_ID="client-id",
            GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
            GOOGLE_OAUTH_REFRESH_TOKEN="refresh-token",
        )

        credenciais = carregar_credenciais_oauth(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)

        self.assertEqual("client-id", credenciais.client_id)
        self.assertEqual("client-secret", credenciais.client_secret)
        self.assertEqual("refresh-token", credenciais.refresh_token)
        self.assertEqual(GOOGLE_OAUTH_TOKEN_URI, credenciais.token_uri)
        self.assertEqual(GOOGLE_DRIVE_UPLOAD_SCOPES, credenciais.scopes)

    def test_aceita_nomes_de_variaveis_configuradas_no_render(self):
        self.app.config.update(
            GOOGLE_CLIENT_ID="client-id-render",
            GOOGLE_CLIENT_SECRET="client-secret-render",
            GOOGLE_REFRESH_TOKEN="refresh-token-render",
        )

        self.assertTrue(credenciais_oauth_configuradas())
        credenciais = carregar_credenciais_oauth(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)

        self.assertEqual("client-id-render", credenciais.client_id)
        self.assertEqual("client-secret-render", credenciais.client_secret)
        self.assertEqual("refresh-token-render", credenciais.refresh_token)

    def test_upload_prefere_oauth_quando_configurado(self):
        self.app.config.update(
            GOOGLE_OAUTH_CLIENT_ID="client-id",
            GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
            GOOGLE_OAUTH_REFRESH_TOKEN="refresh-token",
        )

        with patch("app.services.google_drive_service.criar_google_drive_client_oauth") as oauth, patch(
            "app.services.google_drive_service.criar_google_drive_client"
        ) as service_account:
            oauth.return_value = "oauth-client"

            client = criar_google_drive_client_upload(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)

        self.assertEqual("oauth-client", client)
        oauth.assert_called_once_with(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)
        service_account.assert_not_called()


    def test_mensagem_upload_identifica_pasta_nao_encontrada(self):
        mensagem = mensagem_erro_upload_google_drive(
            Exception("<HttpError 404 File not found: pasta-cupons>"),
            "GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID",
            descricao_arquivo="cupom",
        )

        self.assertIn("nao encontrou a pasta", mensagem)
        self.assertIn("GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID", mensagem)

    def test_mensagem_upload_identifica_falta_de_permissao(self):
        mensagem = mensagem_erro_upload_google_drive(
            Exception("<HttpError 403 insufficientFilePermissions>"),
            "GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID",
            descricao_arquivo="cupom",
        )

        self.assertIn("falta de permissao", mensagem)
        self.assertIn("GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID", mensagem)

    def test_mensagem_upload_identifica_token_expirado_ou_revogado(self):
        mensagem = mensagem_erro_upload_google_drive(
            Exception("invalid_grant: Token has been expired or revoked."),
            "GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID",
            descricao_arquivo="cupom",
        )

        self.assertIn("credencial do Google Drive", mensagem)
        self.assertIn("refresh token", mensagem)
if __name__ == "__main__":
    unittest.main()
