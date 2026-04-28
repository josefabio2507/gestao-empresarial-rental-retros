from flask import Blueprint, render_template
from flask_login import login_required

seguranca_trabalho_bp = Blueprint("seguranca_trabalho", __name__)


@seguranca_trabalho_bp.route("/")
@login_required
def index():
    return render_template("seguranca_trabalho/index.html")


@seguranca_trabalho_bp.route("/status")
@login_required
def status():
    return "Segurança do Trabalho online."