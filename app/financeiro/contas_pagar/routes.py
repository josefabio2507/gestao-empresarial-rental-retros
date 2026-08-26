from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.services.financeiro_contas_pagar_service import (
    FORMAS_PAGAMENTO,
    ORIGENS_LANCAMENTO,
    STATUS_TITULO,
    TIPOS_PAGAMENTO,
    buscar_opcoes_formulario,
    buscar_titulo_por_id,
    cancelar_titulo,
    indicadores_dashboard,
    listar_titulos,
    salvar_titulo,
)
from app.services.logs_service import registrar_log
from app.financeiro.contas_pagar import financeiro_contas_pagar_bp


@financeiro_contas_pagar_bp.route("/")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def dashboard():
    return render_template(
        "financeiro/contas_pagar/dashboard.html",
        indicadores=indicadores_dashboard(),
    )


@financeiro_contas_pagar_bp.route("/titulos")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def titulos():
    opcoes = buscar_opcoes_formulario()
    return render_template(
        "financeiro/contas_pagar/titulos.html",
        titulos=listar_titulos(request.args),
        filtros=request.args,
        opcoes=opcoes,
        origens=ORIGENS_LANCAMENTO,
        tipos_pagamento=TIPOS_PAGAMENTO,
        formas_pagamento=FORMAS_PAGAMENTO,
        status_titulo=STATUS_TITULO,
    )


@financeiro_contas_pagar_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, titulo = salvar_titulo(request.form, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_contas_pagar_criado", f"Titulo a pagar criado. ID: {titulo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.detalhes", titulo_id=titulo.id))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/form.html",
        titulo=None,
        modo="novo",
        opcoes=buscar_opcoes_formulario(),
    )


@financeiro_contas_pagar_bp.route("/<int:titulo_id>")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def detalhes(titulo_id):
    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Titulo nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))

    return render_template("financeiro/contas_pagar/detalhes.html", titulo=titulo)


@financeiro_contas_pagar_bp.route("/<int:titulo_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def editar(titulo_id):
    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Titulo nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))

    status_anterior = titulo.status
    if request.method == "POST":
        sucesso, mensagem, titulo = salvar_titulo(request.form, titulo=titulo, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_contas_pagar_atualizado", f"Titulo a pagar atualizado. ID: {titulo.id}.")
            if status_anterior != titulo.status:
                registrar_log(
                    "financeiro_contas_pagar_status_alterado",
                    f"Status do titulo a pagar alterado. ID: {titulo.id}. {status_anterior} -> {titulo.status}.",
                )
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.detalhes", titulo_id=titulo.id))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/form.html",
        titulo=titulo,
        modo="editar",
        opcoes=buscar_opcoes_formulario(),
    )


@financeiro_contas_pagar_bp.route("/<int:titulo_id>/cancelar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "excluir")
def cancelar(titulo_id):
    titulo = buscar_titulo_por_id(titulo_id)
    sucesso, mensagem = cancelar_titulo(titulo, usuario=current_user)
    if sucesso:
        registrar_log("financeiro_contas_pagar_cancelado", f"Titulo a pagar cancelado. ID: {titulo.id}.")
        registrar_log("financeiro_contas_pagar_status_alterado", f"Status do titulo a pagar alterado. ID: {titulo.id}. Cancelado.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.titulos"))
