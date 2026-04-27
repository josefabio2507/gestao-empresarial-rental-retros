from flask import Blueprint, render_template

departamento_pessoal_bp = Blueprint("departamento_pessoal", __name__)


@departamento_pessoal_bp.route("/")
def index():
    return render_template("departamento_pessoal/index.html")


@departamento_pessoal_bp.route("/status")
def status():
    return "Departamento Pessoal online."