from flask import Blueprint, render_template
from flask_login import login_required

operacao_bp = Blueprint("operacao", __name__)


@operacao_bp.route("/")
@login_required
def index():
    return render_template("operacao/index.html")


@operacao_bp.route("/status")
@login_required
def status():
    return "Operação online."