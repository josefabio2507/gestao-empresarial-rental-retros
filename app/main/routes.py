from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.services.permissoes_service import buscar_departamentos_liberados


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def inicio():
    departamentos_liberados = buscar_departamentos_liberados(current_user)

    return render_template(
        "inicio.html",
        departamentos_liberados=departamentos_liberados,
    )


@main_bp.route("/status")
def status():
    return "Sistema Gestão Empresarial Rental Retros online."


@main_bp.route("/acesso-negado")
@login_required
def acesso_negado():
    return render_template("acesso_negado.html")