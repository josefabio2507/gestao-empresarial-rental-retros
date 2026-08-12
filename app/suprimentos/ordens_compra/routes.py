from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import SuprimentosCotacao, SuprimentosOrdemCompra, SuprimentosOrdemCompraItem
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.services.suprimentos_service import (
    STATUS_ORDEM_COMPRA_CANCELADA,
    STATUS_ORDEM_COMPRA_GERADA,
    STATUS_ORDEM_COMPRA_PARCIAL,
    STATUS_ORDEM_COMPRA_RECEBIDA,
    STATUS_FINANCEIRO_CANCELADO,
    STATUS_FINANCEIRO_PENDENTE,
    STATUS_FINANCEIRO_PREPARADO,
    STATUS_FINANCEIRO_PROVISIONADO,
    buscar_fornecedores_ativos,
    buscar_cotacoes_aprovadas_sem_ordem_compra,
    buscar_ordens_aguardando_financeiro,
    buscar_ordens_compra,
    buscar_por_id,
    cancelar_ordem_compra,
    enviar_email_ordem_compra_fornecedor,
    formatar_decimal_brasil,
    formatar_moeda_brl,
    gerar_link_whatsapp_ordem_compra_fornecedor,
    gerar_ordens_compra_cotacao,
    preparar_financeiro_ordem_compra,
    provisionar_financeiro_ordem_compra,
    registrar_recebimento_ordem_compra,
    salvar_evidencia_item_ordem_compra,
    status_evidencia_item_oc,
    totalizar_evidencias_ordem_compra,
    valor_total_propostas_selecionadas,
)
from app.suprimentos.ordens_compra import suprimentos_ordens_compra_bp


STATUS_ORDENS_COMPRA = [
    STATUS_ORDEM_COMPRA_GERADA,
    STATUS_ORDEM_COMPRA_PARCIAL,
    STATUS_ORDEM_COMPRA_RECEBIDA,
    STATUS_ORDEM_COMPRA_CANCELADA,
]

STATUS_FINANCEIROS_OC = [
    STATUS_FINANCEIRO_PENDENTE,
    STATUS_FINANCEIRO_PREPARADO,
    STATUS_FINANCEIRO_PROVISIONADO,
    STATUS_FINANCEIRO_CANCELADO,
]


@suprimentos_ordens_compra_bp.route("/")
@login_required
@module_permission_required("suprimentos", "ordens_compra", "visualizar")
def listar():
    return render_template(
        "suprimentos/ordens_compra/listar.html",
        ordens=buscar_ordens_compra(
            request.args.get("numero"),
            request.args.get("status"),
            request.args.get("fornecedor_id"),
            request.args.get("status_financeiro"),
        ),
        cotacoes_aprovadas_sem_oc=buscar_cotacoes_aprovadas_sem_ordem_compra(request.args.get("numero")),
        fornecedores=buscar_fornecedores_ativos(),
        status_ordens=STATUS_ORDENS_COMPRA,
        status_financeiros=STATUS_FINANCEIROS_OC,
        filtros=request.args,
        formatar_moeda_brl=formatar_moeda_brl,
        valor_total_propostas_selecionadas=valor_total_propostas_selecionadas,
        pode_editar_ordem=usuario_tem_permissao(
            current_user,
            "suprimentos",
            "ordens_compra",
            "editar",
        ),
    )


@suprimentos_ordens_compra_bp.route("/aguardando-financeiro")
@login_required
@module_permission_required("suprimentos", "ordens_compra", "visualizar")
def aguardando_financeiro():
    return render_template(
        "suprimentos/ordens_compra/aguardando_financeiro.html",
        ordens=buscar_ordens_aguardando_financeiro(),
        formatar_moeda_brl=formatar_moeda_brl,
    )


@suprimentos_ordens_compra_bp.route("/evidencias")
@login_required
@module_permission_required("suprimentos", "ordens_compra", "visualizar")
def evidencias():
    ordens = buscar_ordens_compra(
        request.args.get("numero"),
        request.args.get("status"),
        request.args.get("fornecedor_id"),
        request.args.get("status_financeiro"),
    )
    return render_template(
        "suprimentos/ordens_compra/evidencias.html",
        ordens=ordens,
        fornecedores=buscar_fornecedores_ativos(),
        status_ordens=STATUS_ORDENS_COMPRA,
        filtros=request.args,
        totalizar_evidencias_ordem_compra=totalizar_evidencias_ordem_compra,
    )


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>")
@login_required
@module_permission_required("suprimentos", "ordens_compra", "visualizar")
def detalhes(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    return render_template(
        "suprimentos/ordens_compra/detalhes.html",
        ordem=ordem,
        movimentacoes_estoque=[
            recebimento_item.movimentacao_estoque
            for recebimento in ordem.recebimentos
            for recebimento_item in recebimento.itens
            if recebimento_item.movimentacao_estoque
        ],
        formatar_decimal_brasil=formatar_decimal_brasil,
        formatar_moeda_brl=formatar_moeda_brl,
        status_evidencia_item_oc=status_evidencia_item_oc,
        pode_editar_ordem=usuario_tem_permissao(
            current_user,
            "suprimentos",
            "ordens_compra",
            "editar",
        ),
    )


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/fornecedor/whatsapp", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def enviar_whatsapp_fornecedor(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    sucesso, mensagem, link = gerar_link_whatsapp_ordem_compra_fornecedor(ordem)

    if sucesso:
        registrar_log(
            "suprimentos_oc_whatsapp_fornecedor",
            f"WhatsApp da ordem de compra gerado. Ordem ID: {ordem.id}. Fornecedor ID: {ordem.fornecedor_id}.",
        )
        flash(mensagem, "success")
        return redirect(link)

    flash(mensagem, "danger")
    return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/fornecedor/email", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def enviar_email_fornecedor(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    sucesso, mensagem, link_email = enviar_email_ordem_compra_fornecedor(ordem)

    if sucesso:
        registrar_log(
            "suprimentos_oc_email_fornecedor",
            f"E-mail da ordem de compra enviado/gerado. Ordem ID: {ordem.id}. Fornecedor ID: {ordem.fornecedor_id}.",
        )
        if link_email:
            return render_template(
                "suprimentos/ordens_compra/abrir_email.html",
                ordem=ordem,
                mensagem=mensagem,
                link_email=link_email,
            )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/evidencias")
@login_required
@module_permission_required("suprimentos", "ordens_compra", "visualizar")
def evidencias_ordem(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.evidencias"))

    return render_template(
        "suprimentos/ordens_compra/evidencias_ordem.html",
        ordem=ordem,
        formatar_decimal_brasil=formatar_decimal_brasil,
        status_evidencia_item_oc=status_evidencia_item_oc,
        totalizar_evidencias_ordem_compra=totalizar_evidencias_ordem_compra,
        pode_editar_ordem=usuario_tem_permissao(
            current_user,
            "suprimentos",
            "ordens_compra",
            "editar",
        ),
    )


@suprimentos_ordens_compra_bp.route(
    "/<int:ordem_id>/itens/<int:item_id>/evidencia",
    methods=["GET", "POST"],
)
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def evidencia_item(ordem_id, item_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)
    item = buscar_por_id(SuprimentosOrdemCompraItem, item_id)

    if not ordem or not item or item.ordem_compra_id != ordem.id:
        flash("Item da ordem de compra nao encontrado.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.evidencias"))

    if request.method == "POST":
        sucesso, mensagem, evidencia = salvar_evidencia_item_ordem_compra(
            ordem,
            item,
            request.form,
            request.files,
            current_user,
        )

        if sucesso:
            registrar_log(
                "suprimentos_oc_item_evidencia_salva",
                f"Evidencia salva. Ordem ID: {ordem.id}. Item ID: {item.id}. Evidencia ID: {evidencia.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_ordens_compra.evidencias_ordem", ordem_id=ordem.id))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/ordens_compra/evidencia_item.html",
        ordem=ordem,
        item=item,
        evidencia=item.evidencia,
        formatar_decimal_brasil=formatar_decimal_brasil,
        hoje=date.today().isoformat(),
    )


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/preparar-financeiro", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def preparar_financeiro(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    sucesso, mensagem = preparar_financeiro_ordem_compra(ordem, request.form)

    if sucesso:
        registrar_log("suprimentos_oc_financeiro_preparado", f"Financeiro preparado. Ordem ID: {ordem.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/provisionar-financeiro", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def provisionar_financeiro(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    sucesso, mensagem = provisionar_financeiro_ordem_compra(ordem)

    if sucesso:
        registrar_log("suprimentos_oc_financeiro_provisionado", f"Financeiro provisionado. Ordem ID: {ordem.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/receber", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def receber(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    if request.method == "POST":
        sucesso, mensagem, recebimento = registrar_recebimento_ordem_compra(
            request.form,
            ordem,
            current_user,
        )

        if sucesso:
            registrar_log(
                "suprimentos_recebimento_compra_registrado",
                f"Recebimento registrado. ID: {recebimento.id}. Ordem ID: {ordem.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/ordens_compra/receber.html",
        ordem=ordem,
        formatar_decimal_brasil=formatar_decimal_brasil,
    )


@suprimentos_ordens_compra_bp.route("/gerar/cotacao/<int:cotacao_id>", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "criar")
def gerar_por_cotacao(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    sucesso, mensagem, ordens = gerar_ordens_compra_cotacao(cotacao, current_user, request.form)

    if sucesso:
        ids = ", ".join(str(ordem.id) for ordem in ordens)
        registrar_log("suprimentos_ordem_compra_gerada", f"Ordens de compra geradas. IDs: {ids}.")
        flash(mensagem, "success")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    flash(mensagem, "danger")

    if ordens:
        return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordens[0].id))

    return redirect(url_for("suprimentos_cotacoes.mapa_comparativo", cotacao_id=cotacao.id))


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/cancelar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "excluir")
def cancelar(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    sucesso, mensagem = cancelar_ordem_compra(ordem, request.form.get("motivo_cancelamento"))

    if sucesso:
        registrar_log("suprimentos_ordem_compra_cancelada", f"Ordem de compra cancelada. ID: {ordem.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))
