import unittest

from flask import Flask

from app.extensions import db
from app.models import Equipe
from app.services.equipes_service import (
    alterar_status_equipe,
    atualizar_equipe,
    buscar_equipes,
    criar_equipe,
)


class EquipesServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_cria_equipe_removendo_espacos_externos(self):
        sucesso, mensagem, equipe = criar_equipe("  Equipe Norte  ")

        self.assertTrue(sucesso)
        self.assertEqual("Equipe criada com sucesso.", mensagem)
        self.assertEqual("Equipe Norte", equipe.nome)
        self.assertEqual("equipe-norte", equipe.slug)
        self.assertTrue(equipe.ativo)

    def test_bloqueia_nome_vazio(self):
        sucesso, mensagem, equipe = criar_equipe("   ")

        self.assertFalse(sucesso)
        self.assertEqual("Nome da equipe é obrigatório.", mensagem)
        self.assertIsNone(equipe)
        self.assertEqual(0, Equipe.query.count())

    def test_bloqueia_nome_duplicado_sem_diferenciar_maiusculas(self):
        criar_equipe("Equipe Operacional")

        sucesso, mensagem, equipe = criar_equipe(" equipe operacional ")

        self.assertFalse(sucesso)
        self.assertEqual(
            "Já existe uma equipe cadastrada com este nome.",
            mensagem,
        )
        self.assertIsNone(equipe)
        self.assertEqual(1, Equipe.query.count())

    def test_edita_equipe_e_mantem_unicidade(self):
        _, _, equipe = criar_equipe("Equipe A")
        criar_equipe("Equipe B")

        sucesso, mensagem = atualizar_equipe(equipe, " equipe b ")

        self.assertFalse(sucesso)
        self.assertEqual(
            "Já existe uma equipe cadastrada com este nome.",
            mensagem,
        )
        self.assertEqual("Equipe A", equipe.nome)

    def test_inativa_e_reativa_sem_excluir(self):
        _, _, equipe = criar_equipe("Equipe Campo")

        alterar_status_equipe(equipe)
        self.assertFalse(equipe.ativo)
        self.assertEqual(1, Equipe.query.count())

        alterar_status_equipe(equipe)
        self.assertTrue(equipe.ativo)
        self.assertEqual(1, Equipe.query.count())

    def test_busca_por_nome_ordena_resultados(self):
        criar_equipe("Zulu")
        criar_equipe("Alfa")
        criar_equipe("Beta")

        equipes = buscar_equipes("a")

        self.assertEqual(["Alfa", "Beta"], [equipe.nome for equipe in equipes])
