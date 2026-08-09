from flask import redirect, url_for
from flask_login import login_required

from app.suprimentos import suprimentos_bp


@suprimentos_bp.route("/")
@login_required
def index():
    return redirect(
        url_for("departamentos.detalhe_departamento", slug_departamento="suprimentos")
    )
