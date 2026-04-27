from flask import Blueprint, render_template

operacao_bp = Blueprint("operacao", __name__)


@operacao_bp.route("/")
def index():
    return render_template("operacao/index.html")


@operacao_bp.route("/status")
def status():
    return "Operação online."