import tempfile
import unittest
from pathlib import Path

from app.seed_usuarios_csv import (
    carregar_linhas_csv,
    interpretar_booleano,
    normalizar_email,
)


class SeedUsuariosCsvTestCase(unittest.TestCase):
    def test_normalizar_email_remove_espacos_e_converte_minusculas(self):
        self.assertEqual(
            normalizar_email("  TESTE@EMAIL.COM  "),
            "teste@email.com",
        )

    def test_interpretar_booleano_aceita_sim_e_nao(self):
        self.assertTrue(interpretar_booleano("sim"))
        self.assertFalse(interpretar_booleano("não"))

    def test_carregar_csv_com_ponto_e_virgula(self):
        conteudo = (
            "nome;email;nivel_acesso_id;ativo;precisa_trocar_senha;colaborador_id\n"
            "Teste;teste@email.com;1;sim;sim;\n"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            caminho = Path(temp_dir) / "usuarios.csv"
            caminho.write_text(conteudo, encoding="utf-8")
            linhas = carregar_linhas_csv(caminho)

        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["email"], "teste@email.com")


if __name__ == "__main__":
    unittest.main()
