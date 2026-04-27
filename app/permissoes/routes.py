from flask import Blueprint

permissoes_bp = Blueprint("permissoes", __name__)


@permissoes_bp.route("/")
def listar_permissoes():
    return "Módulo de Permissões em construção."


@permissoes_bp.route("/usuario/<int:usuario_id>")
def permissoes_usuario(usuario_id):
    return f"Permissões do usuário {usuario_id} serão implementadas futuramente."