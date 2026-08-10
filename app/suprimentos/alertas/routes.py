from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import SuprimentosAlerta
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    buscar_alertas_usuario,
    buscar_por_id,
    marcar_alerta_como_lido,
)
from app.suprimentos.alertas import suprimentos_alertas_bp


@suprimentos_alertas_bp.route("/")
@login_required
def listar():
    return render_template(
        "suprimentos/alertas/listar.html",
        alertas=buscar_alertas_usuario(current_user, request.args.get("status")),
        filtros=request.args,
    )


@suprimentos_alertas_bp.route("/<int:alerta_id>/ler", methods=["POST"])
@login_required
def ler(alerta_id):
    alerta = buscar_por_id(SuprimentosAlerta, alerta_id)

    sucesso, mensagem = marcar_alerta_como_lido(alerta, current_user)

    if sucesso:
        registrar_log("suprimentos_alerta_lido", f"Alerta marcado como lido. ID: {alerta.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(alerta.link_destino if sucesso and alerta.link_destino else url_for("suprimentos_alertas.listar"))
