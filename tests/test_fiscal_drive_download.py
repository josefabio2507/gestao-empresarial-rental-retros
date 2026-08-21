import unittest

from app import create_app
from app.fiscal_drive_storage import MIME_XML, baixar_arquivo_fiscal_drive


class FakeDriveRequest:
    def __init__(self, resposta):
        self.resposta = resposta

    def execute(self):
        return self.resposta


class FakeDriveFiles:
    def __init__(self):
        self.list_calls = []
        self.media_calls = []

    def list(self, q, fields, pageSize, supportsAllDrives, includeItemsFromAllDrives):
        self.list_calls.append(
            {
                "q": q,
                "fields": fields,
                "pageSize": pageSize,
                "supportsAllDrives": supportsAllDrives,
                "includeItemsFromAllDrives": includeItemsFromAllDrives,
            }
        )
        return FakeDriveRequest(
            {
                "files": [
                    {
                        "id": "drive-xml-1",
                        "name": "35260000000000000000550010000000011000000010.xml",
                        "createdTime": "2026-08-21T10:00:00Z",
                    }
                ]
            }
        )

    def get_media(self, fileId):
        self.media_calls.append(fileId)
        return FakeDriveRequest(b"<xml>ok</xml>")


class FakeDriveService:
    def __init__(self):
        self._files = FakeDriveFiles()

    def files(self):
        return self._files


class FiscalDriveDownloadTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.contexto = self.app.app_context()
        self.contexto.push()

    def tearDown(self):
        self.contexto.pop()

    def test_baixa_arquivo_fiscal_por_nome_na_pasta_drive_configurada(self):
        self.app.config["FISCAL_XML_DIR"] = "pastaXmlDrive123"
        drive = FakeDriveService()

        arquivo = baixar_arquivo_fiscal_drive(
            "35260000000000000000550010000000011000000010.xml",
            "FISCAL_XML_DIR",
            MIME_XML,
            drive_service=drive,
        )

        self.assertIsNotNone(arquivo)
        self.assertEqual(b"<xml>ok</xml>", arquivo.read())
        self.assertIn("pastaXmlDrive123", drive.files().list_calls[0]["q"])
        self.assertIn("35260000000000000000550010000000011000000010.xml", drive.files().list_calls[0]["q"])
        self.assertEqual(["drive-xml-1"], drive.files().media_calls)


if __name__ == "__main__":
    unittest.main()
