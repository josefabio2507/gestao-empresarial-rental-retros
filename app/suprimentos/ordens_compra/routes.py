from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import SuprimentosCotacao, SuprimentosOrdemCompra
from app.services.logs_service import registrar_log
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
    buscar_ordens_aguardando_financeiro,
    buscar_ordens_compra,
    buscar_por_id,
    cancelar_ordem_compra,
    formatar_decimal_brasil,
    formatar_moeda_brl,
    gerar_ordens_compra_cotacao,
    preparar_financeiro_ordem_compra,
    provisionar_financeiro_ordem_compra,
    registrar_recebimento_ordem_compra,
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
        fornecedores=buscar_fornecedores_ativos(),
        status_ordens=STATUS_ORDENS_COMPRA,
        status_financeiros=STATUS_FINANCEIROS_OC,
        filtros=request.args,
        formatar_moeda_brl=formatar_moeda_brl,
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
