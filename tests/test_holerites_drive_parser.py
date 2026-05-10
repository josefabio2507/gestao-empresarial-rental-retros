import unittest
from unittest.mock import patch

from app.departamento_pessoal.documentos.services import chave_ordenacao_competencia
from app.services.holerites_drive_service import (
    analisar_nome_arquivo_holerite,
    buscar_colaborador_por_matricula,
    extrair_matricula_pasta,
    holerite_ja_importado,
    matriculas_equivalentes,
    normalizar_competencia_informada,
    sincronizar_holerites_google_drive,
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


class ColaboradorFake:
    id = 123
    matricula = "000123"
    ativo = True


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

    def test_competencia_mes_ano_com_hifen_e_reconhecida(self):
        self.assertArquivoValido(
            "15-Holerite Salário 02-2023 - Fulano.pdf",
            "Holerite Mensal",
            "02/2023",
            "15",
        )

    def test_competencia_informada_e_normalizada(self):
        self.assertEqual(normalizar_competencia_informada("03/2025"), "03/2025")
        self.assertEqual(normalizar_competencia_informada("03.2025"), "03/2025")
        self.assertIsNone(normalizar_competencia_informada("2025"))

    def test_chave_de_ordenacao_de_competencia_e_numerica(self):
        competencias = ["12/2024", "01/2025", "11/2024"]

        ordenadas = sorted(
            competencias,
            key=chave_ordenacao_competencia,
            reverse=True,
        )

        self.assertEqual(ordenadas, ["01/2025", "12/2024", "11/2024"])

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

    def test_informe_de_rendimentos_e_ignorado_por_tipo(self):
        resultado = analisar_nome_arquivo_holerite(
            "18-Informe de Rendimentos 2024 - Fulano.pdf"
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

    def test_sincronizacao_em_lote_retorna_cursor_de_continuacao(self):
        arquivo = {
            "id": "drive-1",
            "name": "79 -Holerite Salário 08.2025 - João da Silva.pdf",
            "mimeType": "application/pdf",
            "webViewLink": "https://drive.example/drive-1",
        }

        with patch(
            "app.services.holerites_drive_service._listar_proxima_pasta",
            return_value=(
                {"id": "folder-1", "name": "000123 - João da Silva"},
                None,
            ),
        ), patch(
            "app.services.holerites_drive_service.listar_itens_da_pasta_pagina",
            return_value=([arquivo], "next-file-page"),
        ), patch(
            "app.services.holerites_drive_service.buscar_colaborador_por_matricula",
            return_value=ColaboradorFake(),
        ), patch(
            "app.services.holerites_drive_service.carregar_cache_holerites_colaborador",
            return_value={"google_drive_file_ids": set(), "chaves_fallback": set()},
        ), patch(
            "app.services.holerites_drive_service.criar_holerite",
        ) as criar_holerite, patch(
            "app.services.holerites_drive_service.db.session.commit",
        ):
            resumo = sincronizar_holerites_google_drive(
                drive_service=object(),
                folder_id="root",
                limite_arquivos=1,
            )

        self.assertEqual(resumo["arquivos_processados_lote"], 1)
        self.assertEqual(resumo["importados"], 1)
        self.assertFalse(resumo["concluido"])
        self.assertEqual(
            resumo["proximo_estado"]["file_page_token"],
            "next-file-page",
        )
        criar_holerite.assert_called_once()

    def test_sincronizacao_filtra_competencia_parametrizada(self):
        arquivos = [
            {
                "id": "drive-1",
                "name": "79 -Holerite Salário 02.2025 - João da Silva.pdf",
                "mimeType": "application/pdf",
                "webViewLink": "https://drive.example/drive-1",
            },
            {
                "id": "drive-2",
                "name": "79 -Holerite Salário 03.2025 - João da Silva.pdf",
                "mimeType": "application/pdf",
                "webViewLink": "https://drive.example/drive-2",
            },
        ]

        with patch(
            "app.services.holerites_drive_service._listar_proxima_pasta",
            return_value=(
                {"id": "folder-1", "name": "000123 - João da Silva"},
                None,
            ),
        ), patch(
            "app.services.holerites_drive_service.listar_itens_da_pasta_pagina",
            return_value=(arquivos, None),
        ), patch(
            "app.services.holerites_drive_service.buscar_colaborador_por_matricula",
            return_value=ColaboradorFake(),
        ), patch(
            "app.services.holerites_drive_service.carregar_cache_holerites_colaborador",
            return_value={"google_drive_file_ids": set(), "chaves_fallback": set()},
        ), patch(
            "app.services.holerites_drive_service.criar_holerite",
        ) as criar_holerite, patch(
            "app.services.holerites_drive_service.db.session.commit",
        ):
            resumo = sincronizar_holerites_google_drive(
                drive_service=object(),
                folder_id="root",
                limite_arquivos=10,
                competencia_filtro="03.2025",
            )

        self.assertEqual(resumo["competencia_processada"], "03/2025")
        self.assertEqual(resumo["arquivos_processados_lote"], 2)
        self.assertEqual(resumo["importados"], 1)
        criar_holerite.assert_called_once()


if __name__ == "__main__":
    unittest.main()
