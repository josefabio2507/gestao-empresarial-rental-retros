from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import SuprimentosUnidadeMedida
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    alterar_status,
    buscar_por_id,
    buscar_unidades,
    salvar_unidade,
)
from app.suprimentos.unidades_medida import suprimentos_unidades_medida_bp


@suprimentos_unidades_medida_bp.route("/")
@login_required
@module_permission_required("suprimentos", "unidades_medida", "visualizar")
def listar():
    return render_template(
        "suprimentos/unidades_medida/listar.html",
        unidades=buscar_unidades(request.args.get("nome"), request.args.get("status")),
        filtros=request.args,
    )


@suprimentos_unidades_medida_bp.route("/nova", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "unidades_medida", "criar")
def nova():
    if request.method == "POST":
        sucesso, mensagem, unidade = salvar_unidade(request.form)

        if sucesso:
            registrar_log("suprimentos_unidade_criada", f"Unidade criada. ID: {unidade.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_unidades_medida.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/unidades_medida/form.html", unidade=None, modo="nova")


@suprimentos_unidades_medida_bp.route("/<int:unidade_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "unidades_medida", "editar")
def editar(unidade_id):
    unidade = buscar_por_id(SuprimentosUnidadeMedida, unidade_id)

    if not unidade:
        flash("Unidade nao encontrada.", "warning")
        return redirect(url_for("suprimentos_unidades_medida.listar"))

    if request.method == "POST":
        sucesso, mensagem, unidade = salvar_unidade(request.form, unidade)

        if sucesso:
            registrar_log("suprimentos_unidade_atualizada", f"Unidade atualizada. ID: {unidade.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_unidades_medida.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/unidades_medida/form.html", unidade=unidade, modo="editar")


@suprimentos_unidades_medida_bp.route("/<int:unidade_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "unidades_medida", "excluir")
def status(unidade_id):
    unidade = buscar_por_id(SuprimentosUnidadeMedida, unidade_id)

    if not unidade:
        flash("Unidade nao encontrada.", "warning")
        return redirect(url_for("suprimentos_unidades_medida.listar"))

    sucesso, mensagem = alterar_status(unidade)
    registrar_log("suprimentos_unidade_status", f"Status de unidade alterado. ID: {unidade.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_unidades_medida.listar"))
