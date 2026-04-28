from flask import Blueprint
from flask_login import login_required

departamentos_bp = Blueprint("departamentos", __name__)


@departamentos_bp.route("/")
@login_required
def listar_departamentos():
    return "Módulo de Departamentos em construção."


@departamentos_bp.route("/<slug_departamento>")
@login_required
def detalhe_departamento(slug_departamento):
    return f"Departamento {slug_departamento} em construção."