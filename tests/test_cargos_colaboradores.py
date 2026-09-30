import unittest

from flask import render_template

from app import create_app
from app.extensions import db
from app.models import Cargo, Colaborador, Equipe
from app.services.cargos_service import buscar_cargos_ativos


class CargosColaboradoresTestCase(unittest.TestCase):
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
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_formulario_preserva_cargo_inativo_do_colaborador(self):
        equipe = Equipe(nome="Operação", slug="operacao", ativo=True)
        cargo = Cargo(nome="Cargo Antigo", ativo=False)
        colaborador = Colaborador(
            matricula="1",
            nome="Colaborador",
            cpf="12345678901",
            cargo=cargo.nome,
            equipe=equipe,
            ativo=True,
        )
        db.session.add_all([equipe, cargo, colaborador])
        db.session.commit()

        with self.app.test_request_context():
            html = render_template(
                "departamento_pessoal/colaboradores/form.html",
                colaborador=colaborador,
                cargos=buscar_cargos_ativos(),
                equipes=[equipe],
                modo="editar",
            )

        self.assertIn("Cargo Antigo (inativo)", html)
        self.assertIn('value="Cargo Antigo" selected', html)

    def test_listagem_exibe_dez_linhas_em_area_rolavel(self):
        with self.app.test_request_context():
            html = render_template(
                "departamento_pessoal/colaboradores/listar.html",
                colaboradores=[],
                equipes=[],
                filtro_texto="",
                equipe_id_selecionada="",
                pode_criar=False,
                pode_editar=False,
                pode_excluir=False,
                pode_importar=False,
                pode_ver_dados_sensiveis=False,
                exibir_cpf=lambda valor, permitido: valor,
                exibir_telefone=lambda valor, permitido: valor,
            )

        self.assertIn("table-card table-responsive listbox-10-linhas", html)
        self.assertIn('role="region"', html)
        self.assertIn('aria-label="Lista de colaboradores"', html)
        self.assertIn('tabindex="0"', html)
