from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import (
    SuprimentosRequisicaoCompra,
    SuprimentosRequisicaoCompraItem,
)
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    STATUS_REQUISICAO_APROVADA,
    STATUS_REQUISICAO_CANCELADA,
    STATUS_REQUISICAO_ENVIADA,
    STATUS_REQUISICAO_RASCUNHO,
    adicionar_item_requisicao,
    buscar_centros_custo_ativos,
    buscar_equipes_ativas,
    buscar_itens_ativos,
    buscar_por_id,
    buscar_requisicoes_compra,
    cancelar_requisicao_compra,
    editar_item_requisicao,
    enviar_requisicao_compra,
    enviar_email_requisicao_compra,
    gerar_link_whatsapp_requisicao_compra,
    requisicao_compra_pode_editar,
    remover_item_requisicao,
    salvar_requisicao_compra,
)
from app.suprimentos.requisicoes import suprimentos_requisicoes_bp


STATUS_REQUISICOES = [
    STATUS_REQUISICAO_RASCUNHO,
    STATUS_REQUISICAO_ENVIADA,
    STATUS_REQUISICAO_APROVADA,
    STATUS_REQUISICAO_CANCELADA,
]


def opcoes_formulario():
    return {
        "centros": buscar_centros_custo_ativos(),
        "equipes": buscar_equipes_ativas(),
        "itens_disponiveis": buscar_itens_ativos(),
    }


@suprimentos_requisicoes_bp.route("/")
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "visualizar")
def listar():
    return render_template(
        "suprimentos/requisicoes/listar.html",
        requisicoes=buscar_requisicoes_compra(
            request.args.get("numero"),
            request.args.get("status"),
        ),
        status_requisicoes=STATUS_REQUISICOES,
        filtros=request.args,
        requisicao_compra_pode_editar=requisicao_compra_pode_editar,
    )


@suprimentos_requisicoes_bp.route("/nova", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "criar")
def nova():
    if request.method == "POST":
        sucesso, mensagem, requisicao = salvar_requisicao_compra(request.form, current_user)

        if sucesso:
            registrar_log("suprimentos_requisicao_criada", f"Requisicao criada. ID: {requisicao.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/requisicoes/form.html",
        requisicao=None,
        modo="nova",
        **opcoes_formulario(),
    )


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>")
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "visualizar")
def detalhes(requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)
    item_em_edicao = None

    if not requisicao:
        flash("Requisicao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    if requisicao_compra_pode_editar(requisicao):
        item_em_edicao_id = request.args.get("editar_item_id", type=int)
        if item_em_edicao_id:
            item_em_edicao = buscar_por_id(SuprimentosRequisicaoCompraItem, item_em_edicao_id)
            if not item_em_edicao or item_em_edicao.requisicao_id != requisicao.id:
                flash("Item da requisicao nao encontrado.", "warning")
                item_em_edicao = None

    return render_template(
        "suprimentos/requisicoes/detalhes.html",
        requisicao=requisicao,
        item_em_edicao=item_em_edicao,
        pode_editar_requisicao=requisicao_compra_pode_editar(requisicao),
        **opcoes_formulario(),
    )


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "editar")
def editar(requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)

    if not requisicao:
        flash("Requisicao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    if not requisicao_compra_pode_editar(requisicao):
        flash("Requisicao com cotacao vinculada, aprovada ou cancelada nao pode ser editada.", "warning")
        return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))

    if request.method == "POST":
        sucesso, mensagem, requisicao = salvar_requisicao_compra(request.form, current_user, requisicao)

        if sucesso:
            registrar_log("suprimentos_requisicao_atualizada", f"Requisicao atualizada. ID: {requisicao.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/requisicoes/form.html",
        requisicao=requisicao,
        modo="editar",
        **opcoes_formulario(),
    )


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>/itens", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "editar")
def adicionar_item(requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)

    if not requisicao:
        flash("Requisicao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    sucesso, mensagem, requisicao_item = adicionar_item_requisicao(request.form, requisicao)

    if sucesso:
        registrar_log("suprimentos_requisicao_item_adicionado", f"Item adicionado. ID: {requisicao_item.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>/itens/<int:item_requisicao_id>/editar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "editar")
def editar_item(requisicao_id, item_requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)
    requisicao_item = buscar_por_id(SuprimentosRequisicaoCompraItem, item_requisicao_id)

    if not requisicao or not requisicao_item:
        flash("Item da requisicao nao encontrado.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    sucesso, mensagem = editar_item_requisicao(request.form, requisicao, requisicao_item)
    if sucesso:
        registrar_log("suprimentos_requisicao_item_atualizado", f"Item atualizado. ID: {requisicao_item.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>/itens/<int:item_requisicao_id>/remover", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "editar")
def remover_item(requisicao_id, item_requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)
    requisicao_item = buscar_por_id(SuprimentosRequisicaoCompraItem, item_requisicao_id)

    if not requisicao or not requisicao_item:
        flash("Item da requisicao nao encontrado.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    sucesso, mensagem = remover_item_requisicao(requisicao, requisicao_item)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>/enviar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "editar")
def enviar(requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)

    if not requisicao:
        flash("Requisicao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    sucesso, mensagem = enviar_requisicao_compra(requisicao)

    if sucesso:
        registrar_log("suprimentos_requisicao_enviada", f"Requisicao enviada. ID: {requisicao.id}.")
        sucesso_whatsapp, mensagem_whatsapp, link_whatsapp = gerar_link_whatsapp_requisicao_compra(requisicao)
        if sucesso_whatsapp:
            flash(mensagem, "success")
            return redirect(link_whatsapp)
        flash(mensagem_whatsapp, "warning")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>/enviar-email", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "editar")
def enviar_email(requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)

    if not requisicao:
        flash("Requisicao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    if requisicao_compra_pode_editar(requisicao):
        sucesso, mensagem = enviar_requisicao_compra(requisicao)
        if not sucesso:
            flash(mensagem, "danger")
            return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))
        registrar_log("suprimentos_requisicao_enviada", f"Requisicao enviada por e-mail. ID: {requisicao.id}.")
    else:
        flash("Somente requisicoes sem cotacao vinculada podem ser enviadas por e-mail.", "danger")
        return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))

    sucesso_email, mensagem_email, link_email = enviar_email_requisicao_compra(requisicao)

    if sucesso_email:
        if link_email:
            return render_template(
                "suprimentos/requisicoes/abrir_email.html",
                requisicao=requisicao,
                link_email=link_email,
                mensagem=mensagem_email,
            )
        flash(mensagem, "success")
        flash(mensagem_email, "success")
    else:
        flash(mensagem_email, "warning")

    return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))


@suprimentos_requisicoes_bp.route("/<int:requisicao_id>/cancelar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "requisicoes_compra", "excluir")
def cancelar(requisicao_id):
    requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)

    if not requisicao:
        flash("Requisicao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_requisicoes.listar"))

    sucesso, mensagem = cancelar_requisicao_compra(
        requisicao,
        request.form.get("motivo_cancelamento"),
    )

    if sucesso:
        registrar_log("suprimentos_requisicao_cancelada", f"Requisicao cancelada. ID: {requisicao.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_requisicoes.detalhes", requisicao_id=requisicao.id))
