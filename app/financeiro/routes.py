from flask import Blueprint, render_template

financeiro_bp = Blueprint("financeiro", __name__)


@financeiro_bp.route("/")
def index():
    return render_template("financeiro/index.html")


@financeiro_bp.route("/status")
def status():
    return "Financeiro online."