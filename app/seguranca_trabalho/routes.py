from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.logs_service import registrar_log
from app.services.seguranca_trabalho_service import (
    MOTIVOS_ENTREGA_EPI,
    STATUS_ENTREGA_EPI_ATIVA,
    TIPOS_MATERIAL_ENTREGA,
    buscar_colaboradores_ativos,
    buscar_entrega_epi_por_id,
    buscar_entregas_epi,
    buscar_itens_estoque_para_entrega,
    cancelar_entrega_epi,
    editar_entrega_epi,
    registrar_entrega_epi,
)
from app.services.suprimentos_service import formatar_decimal_brasil

seguranca_trabalho_bp = Blueprint("seguranca_trabalho", __name__)


@seguranca_trabalho_bp.route("/")
@login_required
def index():
    return redirect(url_for("departamentos.detalhe_departamento", slug_departamento="seguranca_trabalho"))


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
        status_entrega_ativa=STATUS_ENTREGA_EPI_ATIVA,
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
        entrega=None,
        colaboradores=buscar_colaboradores_ativos(),
        itens=buscar_itens_estoque_para_entrega(),
        tipos_material=TIPOS_MATERIAL_ENTREGA,
        motivos_entrega=MOTIVOS_ENTREGA_EPI,
        hoje=date.today().isoformat(),
        formatar_decimal_brasil=formatar_decimal_brasil,
    )


@seguranca_trabalho_bp.route("/epis/<int:entrega_id>/editar", methods=["GET", "POST"])
@login_required
def editar_entrega_epi_route(entrega_id):
    entrega = buscar_entrega_epi_por_id(entrega_id)

    if not entrega:
        flash("Entrega nao encontrada.", "warning")
        return redirect(url_for("seguranca_trabalho.epis"))

    if request.method == "POST":
        sucesso, mensagem, entrega = editar_entrega_epi(entrega, request.form, current_user)

        if sucesso:
            registrar_log(
                "seguranca_trabalho_entrega_epi_editada",
                f"Entrega de EPI/Uniforme editada. ID: {entrega.id}. Movimentacao estoque ID: {entrega.movimentacao_estoque_id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("seguranca_trabalho.epis"))

        flash(mensagem, "danger")

    return render_template(
        "seguranca_trabalho/epis/form.html",
        entrega=entrega,
        colaboradores=buscar_colaboradores_ativos(),
        itens=buscar_itens_estoque_para_entrega(),
        tipos_material=TIPOS_MATERIAL_ENTREGA,
        motivos_entrega=MOTIVOS_ENTREGA_EPI,
        hoje=date.today().isoformat(),
        formatar_decimal_brasil=formatar_decimal_brasil,
    )


@seguranca_trabalho_bp.route("/epis/<int:entrega_id>/cancelar", methods=["POST"])
@login_required
def cancelar_entrega_epi_route(entrega_id):
    entrega = buscar_entrega_epi_por_id(entrega_id)
    sucesso, mensagem = cancelar_entrega_epi(entrega, current_user, request.form.get("motivo_cancelamento"))

    if sucesso and entrega:
        registrar_log(
            "seguranca_trabalho_entrega_epi_cancelada",
            f"Entrega de EPI/Uniforme cancelada. ID: {entrega.id}. Movimentacao estoque ID: {entrega.movimentacao_estoque_id}.",
        )

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("seguranca_trabalho.epis"))


@seguranca_trabalho_bp.route("/status")
@login_required
def status():
    return "Seguranca do Trabalho online."
