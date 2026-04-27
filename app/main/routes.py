from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def inicio():
    return render_template("inicio.html")


@main_bp.route("/status")
def status():
    return "Sistema Gestão Empresarial Rental Retros online."


@main_bp.route("/acesso-negado")
def acesso_negado():
    return render_template("acesso_negado.html")