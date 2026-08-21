import os
import tempfile
import unittest
from types import SimpleNamespace

from app import create_app
from app.fiscal_drive_storage import sincronizar_documento_fiscal_drive


class FakeDriveCreateRequest:
    def __init__(self, resposta):
        self.resposta = resposta

    def execute(self):
        return self.resposta


class FakeDriveFiles:
    def __init__(self):
        self.uploads = []

    def create(self, body, media_body, fields, supportsAllDrives):
        self.uploads.append(
            {
                "body": body,
                "media_body": media_body,
                "fields": fields,
                "supportsAllDrives": supportsAllDrives,
            }
        )
        indice = len(self.uploads)
        return FakeDriveCreateRequest(
            {
                "id": f"drive-fiscal-{indice}",
                "name": body["name"],
                "webViewLink": f"https://drive.google.com/file/{indice}",
            }
        )


class FakeDriveService:
    def __init__(self):
        self._files = FakeDriveFiles()

    def files(self):
        return self._files


class FiscalDriveStorageTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app()
        self.contexto = self.app.app_context()
        self.contexto.push()

        self.xml_path = os.path.join(self.tmp.name, "35260000000000000000550010000000011000000010.xml")
        self.pdf_path = os.path.join(self.tmp.name, "35260000000000000000550010000000011000000010.pdf")
        with open(self.xml_path, "wb") as destino:
            destino.write(b"<xml />")
        with open(self.pdf_path, "wb") as destino:
            destino.write(b"%PDF-1.4")

        self.documento = SimpleNamespace(
            xml_path=self.xml_path,
            danfe_path=self.pdf_path,
        )

    def tearDown(self):
        self.contexto.pop()
        self.tmp.cleanup()

    def test_envia_xml_e_danfe_para_pastas_drive_configuradas(self):
        self.app.config.update(
            FISCAL_XML_DIR="pastaXmlDrive123",
            FISCAL_DANFE_DIR="pastaDanfeDrive456",
        )
        drive = FakeDriveService()

        sucesso, mensagem = sincronizar_documento_fiscal_drive(
            self.documento,
            drive_service=drive,
        )

        self.assertTrue(sucesso)
        self.assertEqual("", mensagem)
        self.assertEqual(2, len(drive.files().uploads))
        self.assertEqual("pastaXmlDrive123", drive.files().uploads[0]["body"]["parents"][0])
        self.assertEqual("pastaDanfeDrive456", drive.files().uploads[1]["body"]["parents"][0])
        self.assertTrue(drive.files().uploads[0]["body"]["name"].endswith(".xml"))
        self.assertTrue(drive.files().uploads[1]["body"]["name"].endswith(".pdf"))

    def test_nao_envia_para_drive_quando_configuracao_e_caminho_local(self):
        self.app.config.update(
            FISCAL_XML_DIR=os.path.join(self.tmp.name, "xmls"),
            FISCAL_DANFE_DIR=os.path.join(self.tmp.name, "danfes"),
        )
        drive = FakeDriveService()

        sucesso, mensagem = sincronizar_documento_fiscal_drive(
            self.documento,
            drive_service=drive,
        )

        self.assertTrue(sucesso)
        self.assertEqual("", mensagem)
        self.assertEqual([], drive.files().uploads)


if __name__ == "__main__":
    unittest.main()
