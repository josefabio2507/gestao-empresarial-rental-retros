from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import SuprimentosFornecedorItem
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    alterar_status,
    buscar_fornecedores,
    buscar_itens_ativos,
    buscar_por_id,
    buscar_vinculos_fornecedor_item,
    salvar_vinculo_fornecedor_item,
)
from app.suprimentos.fornecedor_itens import suprimentos_fornecedor_itens_bp


def opcoes_formulario():
    return {
        "fornecedores": buscar_fornecedores(status="ativos"),
        "itens": buscar_itens_ativos(),
    }


@suprimentos_fornecedor_itens_bp.route("/")
@login_required
@module_permission_required("suprimentos", "fornecedor_itens", "visualizar")
def listar():
    return render_template(
        "suprimentos/fornecedor_itens/listar.html",
        vinculos=buscar_vinculos_fornecedor_item(
            request.args.get("fornecedor_id", type=int),
            request.args.get("item_id", type=int),
            request.args.get("status"),
        ),
        fornecedores=buscar_fornecedores(status="ativos"),
        itens=buscar_itens_ativos(),
        filtros=request.args,
    )


@suprimentos_fornecedor_itens_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "fornecedor_itens", "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, vinculo = salvar_vinculo_fornecedor_item(request.form)

        if sucesso:
            registrar_log("suprimentos_fornecedor_item_criado", f"Vinculo fornecedor x item criado. ID: {vinculo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_fornecedor_itens.listar"))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/fornecedor_itens/form.html",
        vinculo=None,
        modo="novo",
        **opcoes_formulario(),
    )


@suprimentos_fornecedor_itens_bp.route("/<int:vinculo_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "fornecedor_itens", "editar")
def editar(vinculo_id):
    vinculo = buscar_por_id(SuprimentosFornecedorItem, vinculo_id)

    if not vinculo:
        flash("Vinculo fornecedor x item nao encontrado.", "warning")
        return redirect(url_for("suprimentos_fornecedor_itens.listar"))

    if request.method == "POST":
        sucesso, mensagem, vinculo = salvar_vinculo_fornecedor_item(request.form, vinculo)

        if sucesso:
            registrar_log("suprimentos_fornecedor_item_atualizado", f"Vinculo fornecedor x item atualizado. ID: {vinculo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_fornecedor_itens.listar"))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/fornecedor_itens/form.html",
        vinculo=vinculo,
        modo="editar",
        **opcoes_formulario(),
    )


@suprimentos_fornecedor_itens_bp.route("/<int:vinculo_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "fornecedor_itens", "excluir")
def status(vinculo_id):
    vinculo = buscar_por_id(SuprimentosFornecedorItem, vinculo_id)

    if not vinculo:
        flash("Vinculo fornecedor x item nao encontrado.", "warning")
        return redirect(url_for("suprimentos_fornecedor_itens.listar"))

    sucesso, mensagem = alterar_status(vinculo)
    registrar_log("suprimentos_fornecedor_item_status", f"Status de vinculo fornecedor x item alterado. ID: {vinculo.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_fornecedor_itens.listar"))
