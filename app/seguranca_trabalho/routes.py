from flask import Blueprint, render_template

seguranca_trabalho_bp = Blueprint("seguranca_trabalho", __name__)


@seguranca_trabalho_bp.route("/")
def index():
    return render_template("seguranca_trabalho/index.html")


@seguranca_trabalho_bp.route("/status")
def status():
    return "Segurança do Trabalho online."