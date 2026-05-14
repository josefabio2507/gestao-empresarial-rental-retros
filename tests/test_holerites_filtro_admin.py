import unittest

from app.departamento_pessoal.documentos.services import termos_filtro_holerites


class HoleritesFiltroAdminTestCase(unittest.TestCase):
    def test_filtro_remove_espacos_extras(self):
        self.assertEqual(termos_filtro_holerites("  Maria Silva  "), ["Maria Silva"])

    def test_filtro_competencia_com_ponto_tambem_busca_com_barra(self):
        termos = termos_filtro_holerites("03.2025")

        self.assertIn("03.2025", termos)
        self.assertIn("03/2025", termos)

    def test_filtro_competencia_com_barra_tambem_busca_com_ponto(self):
        termos = termos_filtro_holerites("03/2025")

        self.assertIn("03/2025", termos)
        self.assertIn("03.2025", termos)


if __name__ == "__main__":
    unittest.main()
