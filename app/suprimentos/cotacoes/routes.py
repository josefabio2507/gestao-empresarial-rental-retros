from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import SuprimentosCotacao, SuprimentosCotacaoProposta
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    STATUS_COTACAO_ABERTA,
    STATUS_COTACAO_CANCELADA,
    STATUS_COTACAO_ENCERRADA,
    buscar_cotacoes,
    buscar_por_id,
    cancelar_cotacao,
    encerrar_cotacao,
    formatar_moeda_brl,
    fornecedores_disponiveis_para_requisicao_item,
    requisicoes_disponiveis_para_cotacao,
    remover_proposta_cotacao,
    salvar_cotacao,
    salvar_proposta_cotacao,
)
from app.suprimentos.cotacoes import suprimentos_cotacoes_bp


STATUS_COTACOES = [
    STATUS_COTACAO_ABERTA,
    STATUS_COTACAO_ENCERRADA,
    STATUS_COTACAO_CANCELADA,
]


@suprimentos_cotacoes_bp.route("/")
@login_required
@module_permission_required("suprimentos", "cotacoes", "visualizar")
def listar():
    return render_template(
        "suprimentos/cotacoes/listar.html",
        cotacoes=buscar_cotacoes(request.args.get("numero"), request.args.get("status")),
        status_cotacoes=STATUS_COTACOES,
        filtros=request.args,
    )


@suprimentos_cotacoes_bp.route("/nova", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "criar")
def nova():
    if request.method == "POST":
        sucesso, mensagem, cotacao = salvar_cotacao(request.form, current_user)

        if sucesso:
            registrar_log("suprimentos_cotacao_criada", f"Cotacao criada. ID: {cotacao.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/cotacoes/form.html",
        cotacao=None,
        requisicoes=requisicoes_disponiveis_para_cotacao(),
        modo="nova",
    )


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>")
@login_required
@module_permission_required("suprimentos", "cotacoes", "visualizar")
def detalhes(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    fornecedores_por_item = {
        item.id: fornecedores_disponiveis_para_requisicao_item(item)
        for item in cotacao.requisicao.itens
    }

    return render_template(
        "suprimentos/cotacoes/detalhes.html",
        cotacao=cotacao,
        fornecedores_por_item=fornecedores_por_item,
        formatar_moeda_brl=formatar_moeda_brl,
    )


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def editar(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    if request.method == "POST":
        sucesso, mensagem, cotacao = salvar_cotacao(request.form, current_user, cotacao)

        if sucesso:
            registrar_log("suprimentos_cotacao_atualizada", f"Cotacao atualizada. ID: {cotacao.id}.")
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/cotacoes/form.html",
        cotacao=cotacao,
        requisicoes=[],
        modo="editar",
    )


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/propostas", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def adicionar_proposta(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem, proposta = salvar_proposta_cotacao(request.form, cotacao)

    if sucesso:
        registrar_log("suprimentos_cotacao_proposta_criada", f"Proposta registrada. ID: {proposta.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/propostas/<int:proposta_id>/remover", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def remover_proposta(cotacao_id, proposta_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)
    proposta = buscar_por_id(SuprimentosCotacaoProposta, proposta_id)

    if not cotacao or not proposta:
        flash("Proposta nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem = remover_proposta_cotacao(cotacao, proposta)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/encerrar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def encerrar(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem = encerrar_cotacao(cotacao)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/cancelar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "excluir")
def cancelar(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem = cancelar_cotacao(cotacao)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))
