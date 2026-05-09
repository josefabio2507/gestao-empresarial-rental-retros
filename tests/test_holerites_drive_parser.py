import unittest
from unittest.mock import patch

from app.services.holerites_drive_service import (
    analisar_nome_arquivo_holerite,
    buscar_colaborador_por_matricula,
    extrair_matricula_pasta,
    holerite_ja_importado,
    matriculas_equivalentes,
)


class QueryFake:
    def __init__(self, resultados):
        self.resultados = iter(resultados)

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return next(self.resultados)


class HoleriteModelFake:
    query = None


class ColaboradorQueryFake:
    def filter_by(self, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []


class ColaboradorModelFake:
    query = ColaboradorQueryFake()


class ParserHoleritesDriveTest(unittest.TestCase):
    def assertArquivoValido(self, nome_arquivo, tipo, competencia, matricula=None):
        resultado = analisar_nome_arquivo_holerite(nome_arquivo)

        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["tipo"], tipo)
        self.assertEqual(resultado["competencia"], competencia)

        if matricula is not None:
            self.assertEqual(resultado["matricula"], matricula)

    def test_arquivo_com_hifen_sem_espaco_e_reconhecido(self):
        self.assertArquivoValido(
            "79 -Holerite Salário 08.2025 - William Lino.pdf",
            "Holerite Mensal",
            "08/2025",
            "79",
        )

    def test_arquivo_com_underscore_e_reconhecido(self):
        self.assertArquivoValido(
            "44-Holerite_Adiantamento 02 2024 85.pdf",
            "Adiantamento Salarial",
            "02/2024",
            "44",
        )

    def test_competencia_ano_mes_e_reconhecida(self):
        self.assertArquivoValido(
            "04-Holerites Salário 2024-01 - WILLIAN.pdf",
            "Holerite Mensal",
            "01/2024",
            "04",
        )

    def test_competencia_mes_ano_com_espaco_e_reconhecida(self):
        self.assertArquivoValido(
            "44-Holerite Adiantamento 02 2024 85.pdf",
            "Adiantamento Salarial",
            "02/2024",
            "44",
        )

    def test_matricula_com_zero_a_esquerda_e_equivalente(self):
        self.assertEqual(extrair_matricula_pasta("000079 - William Lino"), "000079")
        self.assertTrue(matriculas_equivalentes("79", "000079"))

    def test_numero_inicial_do_pdf_nao_define_colaborador(self):
        resultado = analisar_nome_arquivo_holerite(
            "79 -Holerite Salário 08.2025 - João da Silva.pdf"
        )

        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["matricula"], "79")
        self.assertEqual(resultado["tipo"], "Holerite Mensal")
        self.assertEqual(resultado["competencia"], "08/2025")

    def test_tipos_de_holerite_sao_normalizados(self):
        self.assertArquivoValido(
            "10-Holerite Salário 08.2025 - Fulano.pdf",
            "Holerite Mensal",
            "08/2025",
        )
        self.assertArquivoValido(
            "10-Holerites Salário 08.2025 - Fulano.pdf",
            "Holerite Mensal",
            "08/2025",
        )

    def test_adiantamento_e_normalizado(self):
        self.assertArquivoValido(
            "10-Adiantamento 08.2025 - Fulano.pdf",
            "Adiantamento Salarial",
            "08/2025",
        )

    def test_cartoes_de_ponto_sao_ignorados_por_tipo(self):
        resultado = analisar_nome_arquivo_holerite(
            "07-Cartões de ponto 26.12.2022 á 25.01.2023 WILLIAN.pdf"
        )

        self.assertFalse(resultado["valido"])
        self.assertEqual(resultado["motivo"], "tipo_nao_aceito")

    def test_competencia_nao_identificada(self):
        resultado = analisar_nome_arquivo_holerite(
            "10-Holerite Salário sem competencia - Fulano.pdf"
        )

        self.assertFalse(resultado["valido"])
        self.assertEqual(resultado["motivo"], "competencia_nao_identificada")

    def test_execucao_repetida_nao_duplica_por_google_drive_file_id(self):
        HoleriteModelFake.query = QueryFake([object()])

        with patch(
            "app.services.holerites_drive_service.HoleriteColaborador",
            HoleriteModelFake,
        ):
            existe = holerite_ja_importado(
                1,
                {
                    "competencia": "08/2025",
                    "tipo": "Holerite Mensal",
                },
                {
                    "id": "drive-file-id",
                    "name": "10-Holerite Salário 08.2025 - Fulano.pdf",
                },
            )

        self.assertTrue(existe)

    def test_colaborador_nao_cadastrado_retorna_none_sem_excecao(self):
        with patch(
            "app.services.holerites_drive_service.Colaborador",
            ColaboradorModelFake,
        ):
            colaborador = buscar_colaborador_por_matricula("999999")

        self.assertIsNone(colaborador)


if __name__ == "__main__":
    unittest.main()
