from flask import Blueprint

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/")
def listar_usuarios():
    return "Módulo de Usuários em construção."


@usuarios_bp.route("/novo")
def novo_usuario():
    return "Cadastro de usuário será implementado futuramente."