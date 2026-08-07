from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import SuprimentosFornecedor
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    alterar_status,
    buscar_fornecedores,
    buscar_por_id,
    consultar_cnpj_publico,
    salvar_fornecedor,
)
from app.suprimentos.fornecedores import suprimentos_fornecedores_bp


@suprimentos_fornecedores_bp.route("/")
@login_required
@module_permission_required("suprimentos", "fornecedores", "visualizar")
def listar():
    return render_template(
        "suprimentos/fornecedores/listar.html",
        fornecedores=buscar_fornecedores(
            request.args.get("nome"),
            request.args.get("documento"),
            request.args.get("status"),
        ),
        filtros=request.args,
    )


@suprimentos_fornecedores_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "fornecedores", "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, fornecedor = salvar_fornecedor(request.form)

        if sucesso:
            registrar_log("suprimentos_fornecedor_criado", f"Fornecedor criado. ID: {fornecedor.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_fornecedores.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/fornecedores/form.html", fornecedor=None, modo="novo")


@suprimentos_fornecedores_bp.route("/consultar-cnpj")
@login_required
@module_permission_required("suprimentos", "fornecedores", "visualizar")
def consultar_cnpj():
    sucesso, mensagem, dados = consultar_cnpj_publico(request.args.get("cnpj", ""))

    return jsonify(
        {
            "sucesso": sucesso,
            "mensagem": mensagem,
            "dados": dados or {},
        }
    ), 200 if sucesso else 400


@suprimentos_fornecedores_bp.route("/<int:fornecedor_id>")
@login_required
@module_permission_required("suprimentos", "fornecedores", "visualizar")
def detalhes(fornecedor_id):
    fornecedor = buscar_por_id(SuprimentosFornecedor, fornecedor_id)

    if not fornecedor:
        flash("Fornecedor nao encontrado.", "warning")
        return redirect(url_for("suprimentos_fornecedores.listar"))

    return render_template("suprimentos/fornecedores/detalhes.html", fornecedor=fornecedor)


@suprimentos_fornecedores_bp.route("/<int:fornecedor_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "fornecedores", "editar")
def editar(fornecedor_id):
    fornecedor = buscar_por_id(SuprimentosFornecedor, fornecedor_id)

    if not fornecedor:
        flash("Fornecedor nao encontrado.", "warning")
        return redirect(url_for("suprimentos_fornecedores.listar"))

    if request.method == "POST":
        sucesso, mensagem, fornecedor = salvar_fornecedor(request.form, fornecedor)

        if sucesso:
            registrar_log("suprimentos_fornecedor_atualizado", f"Fornecedor atualizado. ID: {fornecedor.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_fornecedores.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/fornecedores/form.html", fornecedor=fornecedor, modo="editar")


@suprimentos_fornecedores_bp.route("/<int:fornecedor_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "fornecedores", "excluir")
def status(fornecedor_id):
    fornecedor = buscar_por_id(SuprimentosFornecedor, fornecedor_id)

    if not fornecedor:
        flash("Fornecedor nao encontrado.", "warning")
        return redirect(url_for("suprimentos_fornecedores.listar"))

    sucesso, mensagem = alterar_status(fornecedor)
    registrar_log("suprimentos_fornecedor_status", f"Status de fornecedor alterado. ID: {fornecedor.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_fornecedores.listar"))
