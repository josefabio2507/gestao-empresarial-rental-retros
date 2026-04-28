from flask import Blueprint, render_template
from flask_login import login_required

financeiro_bp = Blueprint("financeiro", __name__)


@financeiro_bp.route("/")
@login_required
def index():
    return render_template("financeiro/index.html")


@financeiro_bp.route("/status")
@login_required
def status():
    return "Financeiro online."