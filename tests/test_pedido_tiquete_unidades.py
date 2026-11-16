from datetime import date, timedelta

import pytest
from flask import Blueprint, Flask
from flask_login import LoginManager, UserMixin

from app.departamento_pessoal.pedido_tiquete.routes import pedido_tiquete_bp
from app.extensions import db
from app.models import PedidoTicketBeneficiario, PedidoTicketEmpresa, PedidoTicketUnidadeEntrega
from app.services import permissoes_service


class _UsuarioTeste(UserMixin):
    id = "1"


def _data_credito_futura():
    dia = date.today()
    uteis = 0
    while uteis < 12:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            uteis += 1
    return dia.isoformat()


@pytest.fixture
def cliente_ticket_unidades(monkeypatch):
    monkeypatch.setattr(permissoes_service, "usuario_tem_permissao", lambda *_args: True)
    app = Flask(__name__)
    app.secret_key = "teste"
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, PEDIDO_TICKET_ENABLED=True)
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def carregar_usuario(_user_id):
        return _UsuarioTeste()

    auth_bp = Blueprint("auth", __name__)
    auth_bp.add_url_rule("/login", endpoint="login", view_func=lambda: "login")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.add_url_rule("/acesso-negado", endpoint="main.acesso_negado", view_func=lambda: "negado")
    app.register_blueprint(pedido_tiquete_bp, url_prefix="/pedido-tiquete")
    tabelas = [PedidoTicketEmpresa.__table__, PedidoTicketUnidadeEntrega.__table__, PedidoTicketBeneficiario.__table__]
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=tabelas)
        db.session.add_all([
            PedidoTicketEmpresa(numero_pedido="42", cnpj="12345678000190", nome_empresa="EMPRESA TESTE", numero_contrato="1234", produto="TAE", data_credito=date.fromisoformat(_data_credito_futura()), ativo=True),
            PedidoTicketEmpresa(numero_pedido="43", cnpj="98765432000190", nome_empresa="OUTRA EMPRESA", numero_contrato="5678", produto="TRE", data_credito=date.fromisoformat(_data_credito_futura()), ativo=True),
        ])
        db.session.commit()
    client = app.test_client()
    with client.session_transaction() as sessao:
        sessao["_user_id"] = "1"
        sessao["_fresh"] = True
    yield app, client
    with app.app_context():
        db.session.remove()
        db.metadata.drop_all(bind=db.engine, tables=tabelas)


def _unidade_form(**overrides):
    dados = {
        "empresa_id": "1", "codigo_unidade": "001", "nome_unidade": "MATRIZ", "tipo_logradouro": "RUA",
        "logradouro": "DAS FLORES", "numero": "10", "complemento": "", "bairro": "CENTRO",
        "estado": "SP", "cidade": "SAO PAULO", "cep": "01001000", "interlocutor": "CONTATO TESTE",
        "cpf_interlocutor": "", "rg_interlocutor": "", "ddd": "", "telefone": "", "ramal": "",
    }
    dados.update(overrides)
    return dados


def test_cria_unidade_vinculada_e_rejeita_codigo_duplicado(cliente_ticket_unidades):
    app, client = cliente_ticket_unidades
    assert client.post("/pedido-tiquete/unidades", data=_unidade_form()).status_code == 302
    with app.app_context():
        unidade = PedidoTicketUnidadeEntrega.query.one()
        assert unidade.cnpj == "12345678000190"
        assert unidade.ativo is True
    client.post("/pedido-tiquete/unidades", data=_unidade_form(nome_unidade="DUPLICADA"))
    with app.app_context():
        assert PedidoTicketUnidadeEntrega.query.count() == 1


def test_mesmo_codigo_pode_existir_em_empresa_diferente(cliente_ticket_unidades):
    app, client = cliente_ticket_unidades
    client.post("/pedido-tiquete/unidades", data=_unidade_form())
    client.post("/pedido-tiquete/unidades", data=_unidade_form(empresa_id="2"))
    with app.app_context():
        assert PedidoTicketUnidadeEntrega.query.count() == 2
        assert {u.cnpj for u in PedidoTicketUnidadeEntrega.query.all()} == {"12345678000190", "98765432000190"}


def test_edita_unidade_e_impede_mudar_empresa_apos_vinculo(cliente_ticket_unidades):
    app, client = cliente_ticket_unidades
    client.post("/pedido-tiquete/unidades", data=_unidade_form())
    with app.app_context():
        unidade_id = PedidoTicketUnidadeEntrega.query.one().id
        db.session.add(PedidoTicketBeneficiario(numero_pedido="42", matricula="1", cpf="12345678901", nome="COLABORADOR", data_nascimento=date(1990, 1, 1), departamento="TESTE", unidade_entrega="001 - MATRIZ", valor_mensal=1, contrato_produto="1234 - TAE"))
        db.session.commit()
    client.post(f"/pedido-tiquete/unidades/{unidade_id}/editar", data=_unidade_form(empresa_id="2", nome_unidade="NOVA MATRIZ"))
    with app.app_context():
        unidade = db.session.get(PedidoTicketUnidadeEntrega, unidade_id)
        assert unidade.cnpj == "12345678000190"
        assert unidade.nome_unidade == "MATRIZ"


def test_bloqueia_desativacao_de_unidade_com_beneficiario(cliente_ticket_unidades):
    app, client = cliente_ticket_unidades
    client.post("/pedido-tiquete/unidades", data=_unidade_form())
    with app.app_context():
        unidade = PedidoTicketUnidadeEntrega.query.one()
        db.session.add(PedidoTicketBeneficiario(numero_pedido="42", matricula="1", cpf="12345678901", nome="COLABORADOR", data_nascimento=date(1990, 1, 1), departamento="TESTE", unidade_entrega="001 - MATRIZ", valor_mensal=1, contrato_produto="1234 - TAE"))
        db.session.commit()
        unidade_id = unidade.id
    client.post(f"/pedido-tiquete/unidades/{unidade_id}/status")
    with app.app_context():
        assert db.session.get(PedidoTicketUnidadeEntrega, unidade_id).ativo is True


def test_desativa_unidade_sem_excluir_registro(cliente_ticket_unidades):
    app, client = cliente_ticket_unidades
    client.post("/pedido-tiquete/unidades", data=_unidade_form())
    with app.app_context():
        unidade_id = PedidoTicketUnidadeEntrega.query.one().id
    client.post(f"/pedido-tiquete/unidades/{unidade_id}/status")
    with app.app_context():
        unidade = db.session.get(PedidoTicketUnidadeEntrega, unidade_id)
        assert unidade.ativo is False
        assert PedidoTicketUnidadeEntrega.query.count() == 1
