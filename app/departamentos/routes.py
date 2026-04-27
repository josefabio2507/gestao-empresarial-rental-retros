from flask import Blueprint

departamentos_bp = Blueprint("departamentos", __name__)


@departamentos_bp.route("/")
def listar_departamentos():
    return "Módulo de Departamentos em construção."


@departamentos_bp.route("/<slug_departamento>")
def detalhe_departamento(slug_departamento):
    return f"Departamento {slug_departamento} em construção."