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
    dias_uteis = 0
    while dias_uteis < 12:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            dias_uteis += 1
    return dia.isoformat()


@pytest.fixture
def cliente_ticket(monkeypatch):
    monkeypatch.setattr(permissoes_service, "usuario_tem_permissao", lambda *_args: True)
    app = Flask(__name__)
    app.secret_key = "teste"
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PEDIDO_TICKET_ENABLED=True,
    )
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

    tabelas = [
        PedidoTicketEmpresa.__table__,
        PedidoTicketUnidadeEntrega.__table__,
        PedidoTicketBeneficiario.__table__,
    ]
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=tabelas)
    client = app.test_client()
    with client.session_transaction() as sessao:
        sessao["_user_id"] = "1"
        sessao["_fresh"] = True
    yield app, client
    with app.app_context():
        db.session.remove()
        db.metadata.drop_all(bind=db.engine, tables=tabelas)


def _empresa_form(**overrides):
    dados = {
        "numero_pedido": "42",
        "cnpj": "12345678000190",
        "nome_empresa": "EMPRESA TESTE",
        "numero_contrato": "1234",
        "produto": "TAE",
        "data_credito": _data_credito_futura(),
    }
    dados.update(overrides)
    return dados


def test_cadastra_empresa_e_rejeita_contrato_duplicado(cliente_ticket):
    app, client = cliente_ticket
    resposta = client.post("/pedido-tiquete/empresas", data=_empresa_form())
    assert resposta.status_code == 302
    with app.app_context():
        empresa = PedidoTicketEmpresa.query.one()
        assert empresa.nome_empresa == "EMPRESA TESTE"
        assert empresa.ativo is True
        empresa_id = empresa.id

    resposta = client.post("/pedido-tiquete/empresas", data=_empresa_form(nome_empresa="OUTRA EMPRESA"))
    assert resposta.status_code == 302
    with app.app_context():
        assert PedidoTicketEmpresa.query.count() == 1
        assert db.session.get(PedidoTicketEmpresa, empresa_id).nome_empresa == "EMPRESA TESTE"


def test_edita_e_desativa_sem_apagar_o_registro(cliente_ticket):
    app, client = cliente_ticket
    client.post("/pedido-tiquete/empresas", data=_empresa_form())
    with app.app_context():
        empresa_id = PedidoTicketEmpresa.query.one().id

    resposta = client.post(
        f"/pedido-tiquete/empresas/{empresa_id}/editar",
        data=_empresa_form(nome_empresa="EMPRESA EDITADA", ativo="on"),
    )
    assert resposta.status_code == 302
    client.post(f"/pedido-tiquete/empresas/{empresa_id}/status")
    with app.app_context():
        empresa = db.session.get(PedidoTicketEmpresa, empresa_id)
        assert empresa.nome_empresa == "EMPRESA EDITADA"
        assert empresa.ativo is False
        assert PedidoTicketEmpresa.query.count() == 1


def test_impede_mudar_chave_de_contrato_com_beneficiario_vinculado(cliente_ticket):
    app, client = cliente_ticket
    client.post("/pedido-tiquete/empresas", data=_empresa_form())
    with app.app_context():
        empresa = PedidoTicketEmpresa.query.one()
        db.session.add(
            PedidoTicketBeneficiario(
                numero_pedido="42",
                matricula="1",
                cpf="12345678901",
                nome="COLABORADOR SINTETICO",
                data_nascimento=date(1990, 1, 1),
                departamento="TESTE",
                unidade_entrega="001 - UNIDADE TESTE",
                valor_mensal=1,
                contrato_produto="1234 - TAE",
            )
        )
        db.session.commit()
        empresa_id = empresa.id

    client.post(
        f"/pedido-tiquete/empresas/{empresa_id}/editar",
        data=_empresa_form(numero_contrato="5678", ativo="on"),
    )
    with app.app_context():
        assert db.session.get(PedidoTicketEmpresa, empresa_id).numero_contrato == "1234"
