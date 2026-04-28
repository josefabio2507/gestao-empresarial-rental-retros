from flask import Blueprint, render_template
from flask_login import login_required

departamento_pessoal_bp = Blueprint("departamento_pessoal", __name__)


@departamento_pessoal_bp.route("/")
@login_required
def index():
    return render_template("departamento_pessoal/index.html")


@departamento_pessoal_bp.route("/status")
@login_required
def status():
    return "Departamento Pessoal online."