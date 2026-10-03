from pathlib import Path
from tempfile import TemporaryDirectory
from decimal import Decimal
import unittest

from app.departamento_pessoal.vale_transporte.br_mobilidade_portal import (
    BRMobilidadePortalErro,
    ErroImportacaoBRMobilidade,
    StatusImportacaoBRMobilidade,
    _validar_arquivo_para_upload,
    _cpf_normalizado,
    _numero_pedido_da_celula,
    _resumo_revisao_por_texto,
    enviar_arquivo_br_mobilidade,
    executar_pedido_manual_br_mobilidade,
    capturar_documentos_br_mobilidade,
)


class PortalBRMobilidadeTestCase(unittest.TestCase):
    def test_recusa_arquivo_sem_cabecalho_0200(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "pedido.txt"
            caminho.write_bytes(b"0100\r\n")

            with self.assertRaisesRegex(BRMobilidadePortalErro, "cabeçalho 0200"):
                _validar_arquivo_para_upload(caminho)

    def test_recusa_extensao_diferente_de_txt(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "pedido.csv"
            caminho.write_bytes(b"0200\r\n")

            with self.assertRaisesRegex(BRMobilidadePortalErro, "extensão .txt"):
                _validar_arquivo_para_upload(caminho)

    def test_exige_credenciais_antes_de_abrir_playwright(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "pedido.txt"
            caminho.write_bytes(b"0200\r\n")

            with self.assertRaisesRegex(BRMobilidadePortalErro, "Credenciais"):
                enviar_arquivo_br_mobilidade(
                    caminho,
                    login="",
                    senha="",
                    playwright_factory=lambda: self.fail("não deveria abrir o navegador"),
                )

    def test_aceita_arquivo_0200_valido(self):
        with TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "pedido.txt"
            caminho.write_bytes(b"0200\r\n52998224725|1|1|TESTE\r\n")

            self.assertEqual(caminho.resolve(), _validar_arquivo_para_upload(caminho))

    def test_status_interpreta_sucesso_e_erro(self):
        sucesso = StatusImportacaoBRMobilidade(
            nome_arquivo="PEDIDO.TXT",
            processado_em=__import__("datetime").datetime(2026, 10, 1, 10, 0),
            status="Processado com sucesso",
            comentario="",
        )
        falha = StatusImportacaoBRMobilidade(
            nome_arquivo="PEDIDO.TXT",
            processado_em=__import__("datetime").datetime(2026, 10, 1, 10, 0),
            status="Erro no arquivo",
            comentario="Arquivo recusado",
            erros=(ErroImportacaoBRMobilidade(2, "CPF inválido"),),
        )

        self.assertTrue(sucesso.processado_com_sucesso)
        self.assertFalse(sucesso.possui_erro)
        self.assertTrue(falha.possui_erro)
        self.assertFalse(falha.processado_com_sucesso)
        self.assertEqual(2, falha.erros[0].linha)

    def test_interpreta_resumo_do_passo_4(self):
        resumo = _resumo_revisao_por_texto(
            """Data do Pedido: 02/10/2026
Data de Liberação: 06/10/2026
Status do Pedido: Novo
Valor do Pedido: R$ 27,40
Taxa Administrativa: R$ 0,82
Valor de Impressão de Cartões: R$ 0,00
Valor Total: R$ 28,22""",
            1,
        )

        self.assertEqual(Decimal("27.40"), resumo.valor_creditos)
        self.assertEqual(Decimal("0.82"), resumo.taxa_administrativa)
        self.assertEqual(Decimal("28.22"), resumo.valor_total)
        self.assertEqual(1, resumo.quantidade_usuarios)

    def test_normaliza_cpf_para_pesquisa_no_portal(self):
        self.assertEqual("27189241876", _cpf_normalizado("271.892.418-76"))
        self.assertEqual("27189241876", _cpf_normalizado("27189241876"))

    def test_numero_do_pedido_exige_celula_isolada(self):
        self.assertEqual("2972189", _numero_pedido_da_celula(" 2972189 "))
        self.assertIsNone(
            _numero_pedido_da_celula(
                "402102026071020264110123000423371049209416714110111"
            )
        )
        self.assertIsNone(_numero_pedido_da_celula("Pedido 2972189"))

    def test_fluxo_manual_exige_credenciais_antes_do_navegador(self):
        registro = type(
            "Registro",
            (),
            {
                "cpf": "52998224725",
                "nome": "USUARIO TESTE",
                "valor_total": Decimal("27.40"),
            },
        )()
        with self.assertRaisesRegex(BRMobilidadePortalErro, "Credenciais"):
            executar_pedido_manual_br_mobilidade(
                [registro],
                __import__("datetime").date(2026, 10, 6),
                login="",
                senha="",
                playwright_factory=lambda: self.fail("não deveria abrir o navegador"),
            )

    def test_captura_documentos_exige_credenciais_antes_do_navegador(self):
        with self.assertRaisesRegex(BRMobilidadePortalErro, "Credenciais"):
            capturar_documentos_br_mobilidade(
                "2972189",
                login="",
                senha="",
                playwright_factory=lambda: self.fail("não deveria abrir o navegador"),
            )


if __name__ == "__main__":
    unittest.main()
