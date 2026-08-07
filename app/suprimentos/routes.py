from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.services.permissoes_service import buscar_modulos_liberados
from app.suprimentos import suprimentos_bp


@suprimentos_bp.route("/")
@login_required
def index():
    modulos_liberados = buscar_modulos_liberados(current_user, "suprimentos")

    if not modulos_liberados:
        flash("Voce nao possui modulos liberados em Suprimentos.", "danger")
        return redirect(url_for("main.acesso_negado"))

    return render_template(
        "suprimentos/index.html",
        modulos_liberados=modulos_liberados,
    )
