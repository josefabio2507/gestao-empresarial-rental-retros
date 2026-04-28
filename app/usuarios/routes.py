from flask import Blueprint
from flask_login import login_required

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/")
@login_required
def listar_usuarios():
    return "Módulo de Usuários em construção."


@usuarios_bp.route("/novo")
@login_required
def novo_usuario():
    return "Cadastro de usuário será implementado futuramente."