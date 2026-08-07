from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import CentroCusto
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    alterar_status,
    buscar_centros_custo,
    buscar_por_id,
    salvar_centro_custo,
)
from app.suprimentos.centros_custo import suprimentos_centros_custo_bp


@suprimentos_centros_custo_bp.route("/")
@login_required
@module_permission_required("suprimentos", "centros_custo", "visualizar")
def listar():
    return render_template(
        "suprimentos/centros_custo/listar.html",
        centros=buscar_centros_custo(request.args.get("nome"), request.args.get("status")),
        filtros=request.args,
    )


@suprimentos_centros_custo_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "centros_custo", "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, centro = salvar_centro_custo(request.form)

        if sucesso:
            registrar_log("suprimentos_centro_custo_criado", f"Centro de custo criado. ID: {centro.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_centros_custo.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/centros_custo/form.html", centro=None, modo="novo")


@suprimentos_centros_custo_bp.route("/<int:centro_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "centros_custo", "editar")
def editar(centro_id):
    centro = buscar_por_id(CentroCusto, centro_id)

    if not centro:
        flash("Centro de custo nao encontrado.", "warning")
        return redirect(url_for("suprimentos_centros_custo.listar"))

    if request.method == "POST":
        sucesso, mensagem, centro = salvar_centro_custo(request.form, centro)

        if sucesso:
            registrar_log("suprimentos_centro_custo_atualizado", f"Centro de custo atualizado. ID: {centro.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_centros_custo.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/centros_custo/form.html", centro=centro, modo="editar")


@suprimentos_centros_custo_bp.route("/<int:centro_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "centros_custo", "excluir")
def status(centro_id):
    centro = buscar_por_id(CentroCusto, centro_id)

    if not centro:
        flash("Centro de custo nao encontrado.", "warning")
        return redirect(url_for("suprimentos_centros_custo.listar"))

    sucesso, mensagem = alterar_status(centro)
    registrar_log("suprimentos_centro_custo_status", f"Status de centro de custo alterado. ID: {centro.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_centros_custo.listar"))
