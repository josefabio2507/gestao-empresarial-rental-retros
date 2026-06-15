import unittest

from app import create_app
from app.extensions import db
from app.models import Cargo, NivelAcesso, Usuario


class CargosRoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )

        self.contexto = self.app.app_context()
        self.contexto.push()
        db.drop_all()
        db.create_all()

        admin = NivelAcesso(
            nome="Administrador",
            slug="administrador",
            ativo=True,
        )
        comum = NivelAcesso(
            nome="Usuário",
            slug="usuario",
            ativo=True,
        )
        db.session.add_all([admin, comum])
        db.session.flush()

        self.admin = Usuario(
            nome="Admin",
            email="admin@teste.com",
            nivel_acesso=admin,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario = Usuario(
            nome="Comum",
            email="comum@teste.com",
            nivel_acesso=comum,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _autenticar(self, usuario):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True

    def test_administrador_acessa_listagem_e_menu(self):
        self._autenticar(self.admin)

        resposta = self.client.get("/admin/cargos/")
        menu = self.client.get("/admin/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"+ Novo Cargo", resposta.data)
        self.assertIn(b"Acessar cargos", menu.data)

    def test_usuario_comum_nao_acessa_rota_direta_nem_ve_menu(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/admin/cargos/")
        menu = self.client.get("/admin/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])
        self.assertNotIn(b"Acessar cargos", menu.data)

    def test_cadastra_edita_inativa_e_reativa_cargo(self):
        self._autenticar(self.admin)

        resposta_criacao = self.client.post(
            "/admin/cargos/novo",
            data={"nome": "  Motorista  "},
            follow_redirects=True,
        )
        cargo = Cargo.query.one()

        self.assertEqual(200, resposta_criacao.status_code)
        self.assertEqual("Motorista", cargo.nome)
        self.assertTrue(cargo.ativo)

        resposta_edicao = self.client.post(
            f"/admin/cargos/{cargo.id}/editar",
            data={"nome": "Motorista Líder"},
            follow_redirects=True,
        )
        db.session.refresh(cargo)

        self.assertEqual(200, resposta_edicao.status_code)
        self.assertEqual("Motorista Líder", cargo.nome)

        self.client.post(
            f"/admin/cargos/{cargo.id}/status",
            follow_redirects=True,
        )
        db.session.refresh(cargo)
        self.assertFalse(cargo.ativo)
        self.assertEqual(1, Cargo.query.count())

        self.client.post(
            f"/admin/cargos/{cargo.id}/status",
            follow_redirects=True,
        )
        db.session.refresh(cargo)
        self.assertTrue(cargo.ativo)
        self.assertEqual(1, Cargo.query.count())

    def test_exibe_mensagem_amigavel_para_nome_duplicado(self):
        self._autenticar(self.admin)
        db.session.add(Cargo(nome="Analista", ativo=True))
        db.session.commit()

        resposta = self.client.post(
            "/admin/cargos/novo",
            data={"nome": " analista "},
            follow_redirects=True,
        )

        self.assertEqual(200, resposta.status_code)
        self.assertIn(
            "Já existe um cargo cadastrado com este nome.".encode(),
            resposta.data,
        )
        self.assertEqual(1, Cargo.query.count())
