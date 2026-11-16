from flask import Blueprint, Flask
from flask_login import LoginManager, UserMixin

from app.departamento_pessoal.pedido_tiquete.routes import pedido_tiquete_bp
from app.services import permissoes_service


class _UsuarioTeste(UserMixin):
    id = "1"


def _criar_app():
    app = Flask(__name__)
    app.secret_key = "teste"
    app.config["PEDIDO_TICKET_ENABLED"] = False

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
    return app


def test_rotas_exigem_login(monkeypatch):
    monkeypatch.setattr(permissoes_service, "usuario_tem_permissao", lambda *_args: True)
    resposta = _criar_app().test_client().get("/pedido-tiquete/")

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("/auth/login")


def test_feature_flag_desabilita_consulta_cadastro_e_download(monkeypatch):
    monkeypatch.setattr(permissoes_service, "usuario_tem_permissao", lambda *_args: True)
    app = _criar_app()
    client = app.test_client()
    with client.session_transaction() as sessao:
        sessao["_user_id"] = "1"
        sessao["_fresh"] = True

    assert client.get("/pedido-tiquete/").status_code == 404
    assert client.post("/pedido-tiquete/empresas").status_code == 404
