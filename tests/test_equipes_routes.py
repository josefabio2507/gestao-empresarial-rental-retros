import unittest

from app import create_app
from app.extensions import db
from app.models import NivelAcesso, Usuario


class EquipesRoutesTestCase(unittest.TestCase):
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

    def test_administrador_acessa_listagem(self):
        self._autenticar(self.admin)

        resposta = self.client.get("/admin/equipes/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"+ Nova Equipe", resposta.data)

    def test_usuario_comum_nao_acessa_rota_direta(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/admin/equipes/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_menu_de_equipes_aparece_somente_para_administrador(self):
        self._autenticar(self.admin)
        resposta_admin = self.client.get("/admin/")
        self.assertIn(b"Acessar equipes", resposta_admin.data)

        self.client.get("/auth/logout")
        self._autenticar(self.usuario)
        resposta_usuario = self.client.get("/admin/")
        self.assertNotIn(b"Acessar equipes", resposta_usuario.data)
