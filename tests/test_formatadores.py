import unittest

from app.utils.formatadores import formatar_leitura_horimetro


class FormatadoresTestCase(unittest.TestCase):
    def test_horimetro_exibe_apenas_quatro_digitos_inteiros(self):
        self.assertEqual("3626,00", formatar_leitura_horimetro("3626100.00"))
        self.assertEqual("3620,00", formatar_leitura_horimetro("362000.00"))
        self.assertEqual("3591,00", formatar_leitura_horimetro("359100.00"))

    def test_preserva_leituras_com_quatro_ou_menos_digitos(self):
        self.assertEqual("3591,00", formatar_leitura_horimetro("3591.00"))
        self.assertEqual("0,00", formatar_leitura_horimetro("0.00"))


if __name__ == "__main__":
    unittest.main()
