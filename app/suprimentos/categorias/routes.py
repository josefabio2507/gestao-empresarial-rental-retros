from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import SuprimentosCategoriaItem
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    alterar_status,
    buscar_categorias,
    buscar_por_id,
    salvar_categoria,
)
from app.suprimentos.categorias import suprimentos_categorias_bp


@suprimentos_categorias_bp.route("/")
@login_required
@module_permission_required("suprimentos", "categorias", "visualizar")
def listar():
    return render_template(
        "suprimentos/categorias/listar.html",
        categorias=buscar_categorias(request.args.get("nome"), request.args.get("status")),
        filtros=request.args,
    )


@suprimentos_categorias_bp.route("/nova", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "categorias", "criar")
def nova():
    if request.method == "POST":
        sucesso, mensagem, categoria = salvar_categoria(request.form)

        if sucesso:
            registrar_log("suprimentos_categoria_criada", f"Categoria criada. ID: {categoria.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_categorias.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/categorias/form.html", categoria=None, modo="nova")


@suprimentos_categorias_bp.route("/<int:categoria_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "categorias", "editar")
def editar(categoria_id):
    categoria = buscar_por_id(SuprimentosCategoriaItem, categoria_id)

    if not categoria:
        flash("Categoria nao encontrada.", "warning")
        return redirect(url_for("suprimentos_categorias.listar"))

    if request.method == "POST":
        sucesso, mensagem, categoria = salvar_categoria(request.form, categoria)

        if sucesso:
            registrar_log("suprimentos_categoria_atualizada", f"Categoria atualizada. ID: {categoria.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_categorias.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/categorias/form.html", categoria=categoria, modo="editar")


@suprimentos_categorias_bp.route("/<int:categoria_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "categorias", "excluir")
def status(categoria_id):
    categoria = buscar_por_id(SuprimentosCategoriaItem, categoria_id)

    if not categoria:
        flash("Categoria nao encontrada.", "warning")
        return redirect(url_for("suprimentos_categorias.listar"))

    sucesso, mensagem = alterar_status(categoria)
    registrar_log("suprimentos_categoria_status", f"Status de categoria alterado. ID: {categoria.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_categorias.listar"))
