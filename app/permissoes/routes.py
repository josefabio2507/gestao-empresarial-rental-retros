from flask import Blueprint
from flask_login import login_required

permissoes_bp = Blueprint("permissoes", __name__)


@permissoes_bp.route("/")
@login_required
def listar_permissoes():
    return "Módulo de Permissões em construção."


@permissoes_bp.route("/usuario/<int:usuario_id>")
@login_required
def permissoes_usuario(usuario_id):
    return f"Permissões do usuário {usuario_id} serão implementadas futuramente."