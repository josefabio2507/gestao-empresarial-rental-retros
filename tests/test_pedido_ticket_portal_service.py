import tempfile
import unittest
from pathlib import Path

from app.departamento_pessoal.pedido_tiquete.portal_service import (
    PortalTicketError,
    enviar_planilha_para_portal,
)

class _LocalizadorFalso:
    def __init__(self, pagina, seletor):
        self.pagina = pagina
        self.seletor = seletor

    def count(self):
        if self.pagina.desafio and "captcha" in self.seletor:
            return 1
        if self.seletor == "#send-ticket-file-button":
            return 1
        if self.seletor == "#sheetFileInput" and self.pagina.upload:
            return 1
        return 0

    def click(self):
        self.pagina.upload = True

    def set_input_files(self, caminho):
        self.pagina.arquivo = caminho


class _PaginaFalsa:
    def __init__(self, desafio=False):
        self.desafio = desafio
        self.upload = False
        self.arquivo = None

    def set_default_timeout(self, _timeout):
        pass

    def goto(self, *_args, **_kwargs):
        pass

    def locator(self, seletor):
        return _LocalizadorFalso(self, seletor)

    def wait_for_function(self, *_args, **_kwargs):
        pass

    def wait_for_timeout(self, _timeout):
        pass


class PortalTicketServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.temp.name) / "pedido.xlsx"
        self.arquivo.write_bytes(b"arquivo-de-teste")
        self.config = {
            "PEDIDO_TICKET_UPLOAD_ENABLED": True,
            "PEDIDO_TICKET_SIMULATION": True,
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_simulacao_nao_acessa_portal(self):
        resultado = enviar_planilha_para_portal(
            self.arquivo,
            operador_id="teste",
            confirmado=True,
            settings=self.config,
            playwright_factory=lambda: self.fail("simulação não deve abrir navegador"),
        )
        self.assertEqual(resultado.status, "simulado")
        self.assertIn("Nenhum arquivo foi enviado", resultado.mensagem)

    def test_envio_desabilitado_falha_fechado(self):
        self.config["PEDIDO_TICKET_UPLOAD_ENABLED"] = False
        with self.assertRaises(PortalTicketError):
            enviar_planilha_para_portal(
                self.arquivo,
                    operador_id="teste",
                confirmado=True,
                settings=self.config,
            )

    def test_exige_confirmacao_explicitamente(self):
        with self.assertRaises(PortalTicketError):
            enviar_planilha_para_portal(
                self.arquivo,
                    operador_id="teste",
                confirmado=False,
                settings=self.config,
            )

    def test_fluxo_real_simulado_com_navegador_falso(self):
        self.config["PEDIDO_TICKET_SIMULATION"] = False
        self.config.update({
            "PEDIDO_TICKET_PORTAL_LOGIN": "usuario-teste",
            "PEDIDO_TICKET_PORTAL_PASSWORD": "senha-teste",
            "PEDIDO_TICKET_PORTAL_URL": "https://beneficios.ticket.com.br/",
        })
        pagina = _PaginaFalsa()

        class Navegador:
            def new_page(self):
                return pagina

            def close(self):
                self.fechado = True

        class Chromium:
            def launch(self, headless):
                self.assert_headless = headless
                return navegador

        class Gerenciador:
            def __enter__(self):
                self.chromium = Chromium()
                return self

            def __exit__(self, *_args):
                return False

        navegador = Navegador()
        resultado = enviar_planilha_para_portal(
            self.arquivo,
            operador_id="teste",
            confirmado=True,
            settings=self.config,
            playwright_factory=Gerenciador,
        )
        self.assertEqual(resultado.status, "upload_iniciado")
        self.assertEqual(pagina.arquivo, str(self.arquivo))
        self.assertTrue(navegador.fechado)

    def test_mfa_ou_captcha_exige_intervencao_humana(self):
        self.config["PEDIDO_TICKET_SIMULATION"] = False
        self.config.update({
            "PEDIDO_TICKET_PORTAL_LOGIN": "usuario-teste",
            "PEDIDO_TICKET_PORTAL_PASSWORD": "senha-teste",
            "PEDIDO_TICKET_PORTAL_URL": "https://beneficios.ticket.com.br/",
        })
        pagina = _PaginaFalsa(desafio=True)

        class Navegador:
            def new_page(self):
                return pagina

            def close(self):
                pass

        class Chromium:
            def launch(self, headless):
                return Navegador()

        class Gerenciador:
            def __enter__(self):
                self.chromium = Chromium()
                return self

            def __exit__(self, *_args):
                return False

        with self.assertRaisesRegex(PortalTicketError, "validação humana"):
            enviar_planilha_para_portal(
                self.arquivo,
                operador_id="teste",
                confirmado=True,
                settings=self.config,
                playwright_factory=Gerenciador,
            )
        self.assertIsNone(pagina.arquivo)


if __name__ == "__main__":
    unittest.main()
