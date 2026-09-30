import unittest
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.extensions import db
from app.departamento_pessoal.colaboradores.services import (
    criar_colaborador,
    normalizar_equipe_id,
    validar_dados_colaborador,
)
from app.models import Equipe


class ColaboradoresValidacaoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            AUTO_MIGRATE_ON_START=False,
            AUTO_SEED_MODULES_ON_START=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()
        self.equipe = Equipe(nome="Equipe Teste", slug="equipe-teste", ativo=True)
        db.session.add(self.equipe)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_rejeita_campos_maiores_que_as_colunas_do_banco(self):
        casos = (
            ({"matricula": "1" * 41}, "Matrícula deve conter no máximo 40 caracteres."),
            ({"nome": "A" * 151}, "Nome deve conter no máximo 150 caracteres."),
            (
                {"email": ("a" * 141) + "@exemplo.com"},
                "E-mail deve conter no máximo 150 caracteres.",
            ),
        )

        dados_base = {
            "matricula": "123",
            "nome": "Colaborador Teste",
            "cpf": "12345678901",
            "equipe_id": str(self.equipe.id),
            "telefone": "",
            "email": "",
        }

        for alteracao, mensagem_esperada in casos:
            with self.subTest(alteracao=alteracao):
                dados = {**dados_base, **alteracao}
                valido, mensagem = validar_dados_colaborador(**dados)
                self.assertFalse(valido)
                self.assertEqual(mensagem_esperada, mensagem)

    def test_normaliza_id_da_equipe_recebido_pelo_formulario(self):
        self.assertEqual(11, normalizar_equipe_id("11"))
        self.assertEqual(11, normalizar_equipe_id(11))
        self.assertIsNone(normalizar_equipe_id("equipe-invalida"))
        self.assertIsNone(normalizar_equipe_id(""))

    def test_falha_de_commit_retorna_mensagem_sem_erro_500(self):
        with patch.object(
            db.session,
            "commit",
            side_effect=SQLAlchemyError("falha simulada"),
        ):
            sucesso, mensagem = criar_colaborador(
                matricula="123",
                nome="Colaborador Teste",
                cpf="12345678901",
                email="",
                telefone="",
                cargo="",
                equipe_id=str(self.equipe.id),
            )

        self.assertFalse(sucesso)
        self.assertEqual(
            "Não foi possível salvar o colaborador. Revise os dados e tente novamente.",
            mensagem,
        )


if __name__ == "__main__":
    unittest.main()
