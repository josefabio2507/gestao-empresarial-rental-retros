from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.logs_service import registrar_log
from app.services.seguranca_trabalho_service import (
    MOTIVOS_ENTREGA_EPI,
    TIPOS_MATERIAL_ENTREGA,
    buscar_colaboradores_ativos,
    buscar_entregas_epi,
    buscar_itens_estoque_para_entrega,
    registrar_entrega_epi,
)
from app.services.suprimentos_service import formatar_decimal_brasil

seguranca_trabalho_bp = Blueprint("seguranca_trabalho", __name__)


@seguranca_trabalho_bp.route("/")
@login_required
def index():
    return render_template("seguranca_trabalho/index.html")


@seguranca_trabalho_bp.route("/epis/")
@login_required
def epis():
    return render_template(
        "seguranca_trabalho/epis/listar.html",
        entregas=buscar_entregas_epi(
            request.args.get("colaborador_id"),
            request.args.get("item_id"),
            request.args.get("tipo_material"),
        ),
        colaboradores=buscar_colaboradores_ativos(),
        itens=buscar_itens_estoque_para_entrega(),
        tipos_material=TIPOS_MATERIAL_ENTREGA,
        filtros=request.args,
        formatar_decimal_brasil=formatar_decimal_brasil,
    )


@seguranca_trabalho_bp.route("/epis/nova", methods=["GET", "POST"])
@login_required
def nova_entrega_epi():
    if request.method == "POST":
        sucesso, mensagem, entrega = registrar_entrega_epi(request.form, current_user)

        if sucesso:
            registrar_log(
                "seguranca_trabalho_entrega_epi",
                f"Entrega de EPI/Uniforme registrada. ID: {entrega.id}. Movimentacao estoque ID: {entrega.movimentacao_estoque_id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("seguranca_trabalho.epis"))

        flash(mensagem, "danger")

    return render_template(
        "seguranca_trabalho/epis/form.html",
        colaboradores=buscar_colaboradores_ativos(),
        itens=buscar_itens_estoque_para_entrega(),
        tipos_material=TIPOS_MATERIAL_ENTREGA,
        motivos_entrega=MOTIVOS_ENTREGA_EPI,
        hoje=date.today().isoformat(),
        formatar_decimal_brasil=formatar_decimal_brasil,
    )


@seguranca_trabalho_bp.route("/status")
@login_required
def status():
    return "Segurança do Trabalho online."
