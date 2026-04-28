from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def inicio():
    return render_template("inicio.html")


@main_bp.route("/status")
def status():
    return "Sistema Gestão Empresarial Rental Retros online."


@main_bp.route("/acesso-negado")
@login_required
def acesso_negado():
    return render_template("acesso_negado.html")