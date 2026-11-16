from datetime import date, timedelta
from decimal import Decimal

import pytest
from flask import Blueprint, Flask
from flask_login import LoginManager, UserMixin

from app.departamento_pessoal.pedido_tiquete.routes import pedido_tiquete_bp
from app.extensions import db
from app.models import (
    Colaborador,
    Equipe,
    NivelAcesso,
    Usuario,
    PedidoTicketBeneficiario,
    PedidoTicketEmpresa,
    PedidoTicketPedido,
    PedidoTicketUnidadeEntrega,
)
from app.services import permissoes_service


class _UsuarioTeste(UserMixin):
    id = "1"


def _data_credito():
    dia = date.today()
    uteis = 0
    while uteis < 12:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            uteis += 1
    return dia


@pytest.fixture
def cliente_pedidos_ticket(monkeypatch):
    monkeypatch.setattr(permissoes_service, "usuario_tem_permissao", lambda *_args: True)
    app = Flask(__name__)
    app.secret_key = "teste"
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PEDIDO_TICKET_ENABLED=True,
        WTF_CSRF_ENABLED=False,
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
        NivelAcesso.__table__,
        Usuario.__table__,
        Equipe.__table__,
        Colaborador.__table__,
        PedidoTicketPedido.__table__,
        PedidoTicketEmpresa.__table__,
        PedidoTicketUnidadeEntrega.__table__,
        PedidoTicketBeneficiario.__table__,
    ]
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=tabelas)
        db.session.add(NivelAcesso(id=1, nome="Teste", slug="teste"))
        db.session.flush()
        db.session.add(Usuario(id=1, nome="Teste", email="teste@example.com", senha_hash="x", nivel_acesso_id=1))
        equipe = Equipe(nome="OBRAS", slug="obras", ativo=True)
        db.session.add(equipe)
        db.session.flush()
        colaboradores = [
            Colaborador(matricula="0001", cpf="12345678901", nome="COLABORADOR UM", equipe_id=equipe.id, ativo=True),
            Colaborador(matricula="0002", cpf="98765432100", nome="COLABORADOR DOIS", equipe_id=equipe.id, ativo=True),
            Colaborador(matricula="0003", cpf="11122233344", nome="INATIVO", equipe_id=equipe.id, ativo=False),
        ]
        db.session.add_all(colaboradores)
        db.session.add(
            PedidoTicketEmpresa(
                numero_pedido="42",
                cnpj="12345678000190",
                nome_empresa="EMPRESA TESTE",
                numero_contrato="1234",
                produto="TAE",
                data_credito=_data_credito(),
                ativo=True,
            )
        )
        db.session.add(
            PedidoTicketUnidadeEntrega(
                cnpj="12345678000190",
                codigo_unidade="001",
                nome_unidade="MATRIZ",
                tipo_logradouro="RUA",
                logradouro="DAS FLORES",
                numero="10",
                bairro="CENTRO",
                estado="SP",
                cidade="SAO PAULO",
                cep="01001000",
                interlocutor="CONTATO TESTE",
                ativo=True,
            )
        )
        db.session.commit()
        ids = [item.id for item in colaboradores]
    client = app.test_client()
    with client.session_transaction() as sessao:
        sessao["_user_id"] = "1"
        sessao["_fresh"] = True
    yield app, client, ids
    with app.app_context():
        db.session.remove()
        db.metadata.drop_all(bind=db.engine, tables=tabelas)


def _pedido_form(colaborador_id, **overrides):
    dados = {
        "empresa_id": "1",
        "unidade_id": "1",
        "colaborador_ids": [str(colaborador_id)],
        f"data_nascimento_{colaborador_id}": "1990-01-01",
        f"valor_mensal_{colaborador_id}": "125.50",
        f"numero_parcelas_{colaborador_id}": "2",
    }
    dados.update(overrides)
    return dados


def test_pedido_usa_colaborador_existente_e_salva_resumo(cliente_pedidos_ticket):
    app, client, ids = cliente_pedidos_ticket
    response = client.post("/pedido-tiquete/pedidos", data={
        "empresa_id": "1",
        "unidade_id": "1",
        "colaborador_ids": [str(ids[0]), str(ids[1])],
        f"data_nascimento_{ids[0]}": "1990-01-01",
        f"valor_mensal_{ids[0]}": "125.50",
        f"numero_parcelas_{ids[0]}": "2",
        f"data_nascimento_{ids[1]}": "1992-04-12",
        f"valor_mensal_{ids[1]}": "75.25",
        f"numero_parcelas_{ids[1]}": "",
    })
    assert response.status_code == 302
    with app.app_context():
        pedido = PedidoTicketPedido.query.one()
        itens = PedidoTicketBeneficiario.query.filter_by(pedido_id=pedido.id).order_by(PedidoTicketBeneficiario.matricula).all()
        assert pedido.numero_pedido == "42"
        assert pedido.status == "rascunho"
        assert pedido.quantidade_beneficiarios == 2
        assert pedido.valor_total == Decimal("200.75")
        assert [(item.colaborador_id, item.nome, item.cpf, item.matricula) for item in itens] == [
            (ids[0], "COLABORADOR UM", "12345678901", "0001"),
            (ids[1], "COLABORADOR DOIS", "98765432100", "0002"),
        ]


def test_continua_rascunho_sem_repetir_colaborador(cliente_pedidos_ticket):
    app, client, ids = cliente_pedidos_ticket
    client.post("/pedido-tiquete/pedidos", data=_pedido_form(ids[0]))
    with app.app_context():
        pedido_id = PedidoTicketPedido.query.one().id
    response = client.post("/pedido-tiquete/pedidos", data=_pedido_form(
        ids[1], pedido_id=str(pedido_id)
    ))
    assert response.status_code == 302
    with app.app_context():
        pedido = db.session.get(PedidoTicketPedido, pedido_id)
        assert pedido.quantidade_beneficiarios == 2
        assert pedido.valor_total == Decimal("251.00")
        assert PedidoTicketBeneficiario.query.filter_by(pedido_id=pedido_id).count() == 2
    client.post("/pedido-tiquete/pedidos", data=_pedido_form(
        ids[0], pedido_id=str(pedido_id)
    ))
    with app.app_context():
        assert PedidoTicketPedido.query.count() == 1
        assert PedidoTicketBeneficiario.query.filter_by(pedido_id=pedido_id).count() == 2


def test_nao_cria_pedido_para_colaborador_inativo_ou_unidade_de_outra_empresa(cliente_pedidos_ticket):
    app, client, ids = cliente_pedidos_ticket
    client.post("/pedido-tiquete/pedidos", data=_pedido_form(ids[2]))
    with app.app_context():
        assert PedidoTicketPedido.query.count() == 0
        assert PedidoTicketBeneficiario.query.count() == 0
    client.post("/pedido-tiquete/pedidos", data=_pedido_form(ids[0], unidade_id="999"))
    with app.app_context():
        assert PedidoTicketPedido.query.count() == 0
        assert PedidoTicketBeneficiario.query.count() == 0


def test_tela_de_novo_pedido_lista_colaboradores_ativos(cliente_pedidos_ticket):
    _app, client, _ids = cliente_pedidos_ticket
    response = client.get("/pedido-tiquete/?aba=novo_pedido")
    assert response.status_code == 200
    assert b"COLABORADOR UM" in response.data
    assert b"COLABORADOR DOIS" in response.data
    assert b"INATIVO" not in response.data
    assert b"data_nascimento_" in response.data
