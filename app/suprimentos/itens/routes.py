from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.models import SuprimentosItem
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    TIPOS_ITEM,
    alterar_status,
    buscar_categorias_ativas,
    buscar_centros_custo_ativos,
    buscar_itens,
    buscar_por_id,
    buscar_unidades_ativas,
    gerar_proximo_codigo_item,
    salvar_item,
)
from app.suprimentos.itens import suprimentos_itens_bp


def opcoes_formulario():
    return {
        "categorias": buscar_categorias_ativas(),
        "unidades": buscar_unidades_ativas(),
        "centros": buscar_centros_custo_ativos(),
        "tipos_item": sorted(TIPOS_ITEM),
        "proximo_codigo_item": gerar_proximo_codigo_item(),
    }


@suprimentos_itens_bp.route("/")
@login_required
@module_permission_required("suprimentos", "itens", "visualizar")
def listar():
    return render_template(
        "suprimentos/itens/listar.html",
        itens=buscar_itens(
            request.args.get("descricao"),
            request.args.get("categoria_id", type=int),
            request.args.get("tipo"),
            request.args.get("estocavel"),
            request.args.get("status"),
        ),
        categorias=buscar_categorias_ativas(),
        tipos_item=sorted(TIPOS_ITEM),
        filtros=request.args,
    )


@suprimentos_itens_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "itens", "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, item = salvar_item(request.form)

        if sucesso:
            registrar_log("suprimentos_item_criado", f"Item criado. ID: {item.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_itens.listar"))

        flash(mensagem, "danger")

    return render_template("suprimentos/itens/form.html", item=None, modo="novo", **opcoes_formulario())


@suprimentos_itens_bp.route("/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "itens", "editar")
def editar(item_id):
    item = buscar_por_id(SuprimentosItem, item_id)

    if not item:
        flash("Item nao encontrado.", "warning")
        return redirect(url_for("suprimentos_itens.listar"))

    if request.method == "POST":
        sucesso, mensagem, item = salvar_item(request.form, item)

        if sucesso:
            registrar_log("suprimentos_item_atualizado", f"Item atualizado. ID: {item.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_itens.listar"))

        flash(mensagem, "danger")

    opcoes = opcoes_formulario()
    opcoes["proximo_codigo_item"] = gerar_proximo_codigo_item(item.id)
    return render_template("suprimentos/itens/form.html", item=item, modo="editar", **opcoes)


@suprimentos_itens_bp.route("/<int:item_id>/status", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "itens", "excluir")
def status(item_id):
    item = buscar_por_id(SuprimentosItem, item_id)

    if not item:
        flash("Item nao encontrado.", "warning")
        return redirect(url_for("suprimentos_itens.listar"))

    sucesso, mensagem = alterar_status(item)
    registrar_log("suprimentos_item_status", f"Status de item alterado. ID: {item.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_itens.listar"))
