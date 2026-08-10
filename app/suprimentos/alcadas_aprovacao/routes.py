from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import SuprimentosAlcadaAprovacao
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    alterar_status_alcada_aprovacao,
    buscar_alcadas_aprovacao,
    buscar_categorias_ativas,
    buscar_centros_custo,
    buscar_por_id,
    buscar_usuarios_ativos,
    formatar_moeda_brl,
    salvar_alcada_aprovacao,
)
from app.suprimentos.alcadas_aprovacao import suprimentos_alcadas_aprovacao_bp


def _opcoes_formulario():
    return {
        "usuarios": buscar_usuarios_ativos(),
        "centros_custo": buscar_centros_custo(status="ativos"),
        "categorias": buscar_categorias_ativas(),
        "formatar_moeda_brl": formatar_moeda_brl,
    }


@suprimentos_alcadas_aprovacao_bp.route("/")
@login_required
@module_permission_required("suprimentos", "alcadas_aprovacao", "visualizar")
def listar():
    return render_template(
        "suprimentos/alcadas_aprovacao/listar.html",
        alcadas=buscar_alcadas_aprovacao(),
        formatar_moeda_brl=formatar_moeda_brl,
    )


@suprimentos_alcadas_aprovacao_bp.route("/nova", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "alcadas_aprovacao", "criar")
def nova():
    if request.method == "POST":
        sucesso, mensagem, alcada = salvar_alcada_aprovacao(request.form)

        if sucesso:
            registrar_log("suprimentos_alcada_criada", f"Alcada de aprovacao criada. ID: {alcada.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_alcadas_aprovacao.listar"))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/alcadas_aprovacao/form.html",
        alcada=None,
        modo="nova",
        **_opcoes_formulario(),
    )


@suprimentos_alcadas_aprovacao_bp.route("/<int:alcada_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "alcadas_aprovacao", "editar")
def editar(alcada_id):
    alcada = buscar_por_id(SuprimentosAlcadaAprovacao, alcada_id)

    if not alcada:
        flash("Alcada de aprovacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_alcadas_aprovacao.listar"))

    if request.method == "POST":
        sucesso, mensagem, alcada = salvar_alcada_aprovacao(request.form, alcada)

        if sucesso:
            registrar_log("suprimentos_alcada_atualizada", f"Alcada de aprovacao atualizada. ID: {alcada.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_alcadas_aprovacao.listar"))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/alcadas_aprovacao/form.html",
        alcada=alcada,
        modo="editar",
        **_opcoes_formulario(),
    )


@suprimentos_alcadas_aprovacao_bp.route("/<int:alcada_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "alcadas_aprovacao", "editar")
def status(alcada_id):
    alcada = buscar_por_id(SuprimentosAlcadaAprovacao, alcada_id)

    if not alcada:
        flash("Alcada de aprovacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_alcadas_aprovacao.listar"))

    sucesso, mensagem = alterar_status_alcada_aprovacao(alcada)

    if sucesso:
        registrar_log("suprimentos_alcada_status", f"Status da alcada alterado. ID: {alcada.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_alcadas_aprovacao.listar"))
