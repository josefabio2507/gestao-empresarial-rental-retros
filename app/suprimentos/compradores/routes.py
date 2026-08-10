from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import SuprimentosComprador
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    alterar_status_comprador_suprimentos,
    buscar_compradores_suprimentos,
    buscar_centros_custo,
    buscar_por_id,
    buscar_usuarios_ativos,
    salvar_comprador_suprimentos,
)
from app.suprimentos.compradores import suprimentos_compradores_bp


def _opcoes_formulario():
    return {
        "usuarios": buscar_usuarios_ativos(),
        "centros_custo": buscar_centros_custo(status="ativos"),
    }


@suprimentos_compradores_bp.route("/")
@login_required
@module_permission_required("suprimentos", "compradores", "visualizar")
def listar():
    return render_template(
        "suprimentos/compradores/listar.html",
        compradores=buscar_compradores_suprimentos(),
    )


@suprimentos_compradores_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "compradores", "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, comprador = salvar_comprador_suprimentos(request.form)

        if sucesso:
            registrar_log("suprimentos_comprador_criado", f"Comprador criado. ID: {comprador.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_compradores.listar"))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/compradores/form.html",
        comprador=None,
        modo="novo",
        **_opcoes_formulario(),
    )


@suprimentos_compradores_bp.route("/<int:comprador_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "compradores", "editar")
def editar(comprador_id):
    comprador = buscar_por_id(SuprimentosComprador, comprador_id)

    if not comprador:
        flash("Comprador nao encontrado.", "warning")
        return redirect(url_for("suprimentos_compradores.listar"))

    if request.method == "POST":
        sucesso, mensagem, comprador = salvar_comprador_suprimentos(request.form, comprador)

        if sucesso:
            registrar_log("suprimentos_comprador_atualizado", f"Comprador atualizado. ID: {comprador.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_compradores.listar"))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/compradores/form.html",
        comprador=comprador,
        modo="editar",
        **_opcoes_formulario(),
    )


@suprimentos_compradores_bp.route("/<int:comprador_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "compradores", "editar")
def status(comprador_id):
    comprador = buscar_por_id(SuprimentosComprador, comprador_id)

    if not comprador:
        flash("Comprador nao encontrado.", "warning")
        return redirect(url_for("suprimentos_compradores.listar"))

    sucesso, mensagem = alterar_status_comprador_suprimentos(comprador)

    if sucesso:
        registrar_log("suprimentos_comprador_status", f"Status do comprador alterado. ID: {comprador.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_compradores.listar"))
