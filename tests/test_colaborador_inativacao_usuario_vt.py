import unittest

from app import create_app
from app.extensions import db
from app.models import Colaborador, Equipe, NivelAcesso, Usuario
from app.departamento_pessoal.colaboradores.services import (
    alterar_status_colaborador,
    atualizar_colaborador,
)
from app.departamento_pessoal.vale_transporte.services import (
    listar_colaboradores_para_vinculo,
)


class ColaboradorInativacaoUsuarioValeTransporteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            WTF_CSRF_ENABLED=False,
            AUTO_MIGRATE_ON_START=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

        self.nivel = NivelAcesso(
            nome="Usuario",
            slug="usuario",
            ativo=True,
        )
        self.equipe = Equipe(
            nome="Operacao",
            slug="operacao",
            ativo=True,
        )
        db.session.add_all([self.nivel, self.equipe])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _criar_colaborador_com_usuario(self):
        colaborador = Colaborador(
            matricula="001",
            nome="Colaborador Teste",
            cpf="12345678901",
            email="colaborador@teste.com",
            telefone="11999999999",
            cargo="Operador",
            equipe=self.equipe,
            vale_transporte_optante=True,
            ativo=True,
        )
        usuario = Usuario(
            nome="Usuario Teste",
            email="usuario@teste.com",
            nivel_acesso=self.nivel,
            colaborador=colaborador,
            ativo=True,
            precisa_trocar_senha=False,
        )
        usuario.definir_senha("teste")
        db.session.add_all([colaborador, usuario])
        db.session.commit()

        return colaborador, usuario

    def test_inativar_colaborador_inativa_usuario_vinculado(self):
        colaborador, usuario = self._criar_colaborador_com_usuario()

        sucesso, mensagem = alterar_status_colaborador(colaborador)

        self.assertTrue(sucesso)
        self.assertFalse(colaborador.ativo)
        self.assertFalse(usuario.ativo)
        self.assertIn("usuário(s) vinculado(s)", mensagem)

    def test_editar_colaborador_para_inativo_inativa_usuario_vinculado(self):
        colaborador, usuario = self._criar_colaborador_com_usuario()

        sucesso, mensagem = atualizar_colaborador(
            colaborador=colaborador,
            matricula=colaborador.matricula,
            nome=colaborador.nome,
            cpf=colaborador.cpf,
            email=colaborador.email,
            telefone=colaborador.telefone,
            cargo=colaborador.cargo,
            equipe_id=self.equipe.id,
            vale_transporte_optante=colaborador.vale_transporte_optante,
            ativo=False,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertFalse(colaborador.ativo)
        self.assertFalse(usuario.ativo)

    def test_colaborador_inativo_nao_aparece_nos_optantes_vale_transporte(self):
        colaborador, _ = self._criar_colaborador_com_usuario()
        colaborador.ativo = False
        db.session.commit()

        colaboradores = listar_colaboradores_para_vinculo()

        self.assertNotIn(colaborador, colaboradores)


if __name__ == "__main__":
    unittest.main()
