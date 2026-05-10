import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.seed_usuarios_csv import (
    atualizar_vinculo_usuario_existente,
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

    def test_usuario_existente_sem_colaborador_passa_a_ser_vinculado_por_email(self):
        usuario = SimpleNamespace(
            id=10,
            email="usuario@email.com",
            colaborador_id=None,
            senha_hash="hash-original",
            nivel_acesso_id=2,
        )
        colaborador = SimpleNamespace(id=99, email="usuario@email.com", ativo=True)

        with patch("app.seed_usuarios_csv.colaborador_ja_vinculado", return_value=False):
            resultado = atualizar_vinculo_usuario_existente(
                usuario,
                "usuario@email.com",
                {"usuario@email.com": [colaborador]},
            )

        self.assertFalse(resultado["criado"])
        self.assertTrue(resultado["existente"])
        self.assertEqual(resultado["status_vinculo"], "usuario_existente_vinculado")
        self.assertEqual(usuario.colaborador_id, 99)

    def test_usuario_existente_com_colaborador_preserva_vinculo(self):
        usuario = SimpleNamespace(
            id=10,
            email="usuario@email.com",
            colaborador_id=77,
            senha_hash="hash-original",
            nivel_acesso_id=2,
        )

        resultado = atualizar_vinculo_usuario_existente(
            usuario,
            "usuario@email.com",
            {},
        )

        self.assertEqual(resultado["status_vinculo"], "vinculo_preservado")
        self.assertEqual(usuario.colaborador_id, 77)

    def test_usuario_existente_sem_colaborador_correspondente_permanece_sem_vinculo(self):
        usuario = SimpleNamespace(
            id=10,
            email="usuario@email.com",
            colaborador_id=None,
            senha_hash="hash-original",
            nivel_acesso_id=2,
        )

        resultado = atualizar_vinculo_usuario_existente(
            usuario,
            "usuario@email.com",
            {},
        )

        self.assertEqual(resultado["status_vinculo"], "sem_colaborador")
        self.assertIsNone(usuario.colaborador_id)

    def test_usuario_existente_nao_tem_senha_sobrescrita(self):
        usuario = SimpleNamespace(
            id=10,
            email="usuario@email.com",
            colaborador_id=None,
            senha_hash="hash-original",
            nivel_acesso_id=2,
        )
        colaborador = SimpleNamespace(id=99, email="usuario@email.com", ativo=True)

        with patch("app.seed_usuarios_csv.colaborador_ja_vinculado", return_value=False):
            atualizar_vinculo_usuario_existente(
                usuario,
                "usuario@email.com",
                {"usuario@email.com": [colaborador]},
            )

        self.assertEqual(usuario.senha_hash, "hash-original")

    def test_usuario_existente_nao_tem_nivel_acesso_alterado(self):
        usuario = SimpleNamespace(
            id=10,
            email="usuario@email.com",
            colaborador_id=None,
            senha_hash="hash-original",
            nivel_acesso_id=2,
        )
        colaborador = SimpleNamespace(id=99, email="usuario@email.com", ativo=True)

        with patch("app.seed_usuarios_csv.colaborador_ja_vinculado", return_value=False):
            atualizar_vinculo_usuario_existente(
                usuario,
                "usuario@email.com",
                {"usuario@email.com": [colaborador]},
            )

        self.assertEqual(usuario.nivel_acesso_id, 2)


if __name__ == "__main__":
    unittest.main()
