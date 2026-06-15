import unittest

from flask import Flask

from app.extensions import db
from app.models import Cargo
from app.services.cargos_service import (
    alterar_status_cargo,
    atualizar_cargo,
    buscar_cargos,
    buscar_cargos_ativos,
    criar_cargo,
)


class CargosServiceTestCase(unittest.TestCase):
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

    def test_cria_cargo_removendo_espacos_externos(self):
        sucesso, mensagem, cargo = criar_cargo("  Motorista  ")

        self.assertTrue(sucesso)
        self.assertEqual("Cargo criado com sucesso.", mensagem)
        self.assertEqual("Motorista", cargo.nome)
        self.assertTrue(cargo.ativo)

    def test_bloqueia_nome_vazio(self):
        sucesso, mensagem, cargo = criar_cargo("   ")

        self.assertFalse(sucesso)
        self.assertEqual("Nome do cargo é obrigatório.", mensagem)
        self.assertIsNone(cargo)
        self.assertEqual(0, Cargo.query.count())

    def test_bloqueia_nome_duplicado_sem_diferenciar_maiusculas(self):
        criar_cargo("Assistente Administrativo")

        sucesso, mensagem, cargo = criar_cargo(" assistente administrativo ")

        self.assertFalse(sucesso)
        self.assertEqual(
            "Já existe um cargo cadastrado com este nome.",
            mensagem,
        )
        self.assertIsNone(cargo)
        self.assertEqual(1, Cargo.query.count())

    def test_edita_cargo_e_mantem_unicidade(self):
        _, _, cargo = criar_cargo("Auxiliar")
        criar_cargo("Supervisor")

        sucesso, mensagem = atualizar_cargo(cargo, " supervisor ")

        self.assertFalse(sucesso)
        self.assertEqual(
            "Já existe um cargo cadastrado com este nome.",
            mensagem,
        )
        self.assertEqual("Auxiliar", cargo.nome)

    def test_inativa_e_reativa_sem_excluir(self):
        _, _, cargo = criar_cargo("Operador")

        alterar_status_cargo(cargo)
        self.assertFalse(cargo.ativo)
        self.assertEqual([], buscar_cargos_ativos())
        self.assertEqual(1, Cargo.query.count())

        alterar_status_cargo(cargo)
        self.assertTrue(cargo.ativo)
        self.assertEqual([cargo], buscar_cargos_ativos())
        self.assertEqual(1, Cargo.query.count())

    def test_busca_por_nome_ordena_resultados(self):
        criar_cargo("Vendedor")
        criar_cargo("Analista")
        criar_cargo("Coordenador")

        cargos = buscar_cargos("a")

        self.assertEqual(
            ["Analista", "Coordenador"],
            [cargo.nome for cargo in cargos],
        )
