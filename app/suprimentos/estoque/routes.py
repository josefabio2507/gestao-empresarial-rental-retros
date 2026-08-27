from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    CLASSE_CENTRO_CUSTO_EQUIPES,
    buscar_categorias_ativas,
    buscar_centros_custo_ativos,
    buscar_fornecedores_ativos,
    buscar_itens_ativos,
    buscar_movimentacoes_estoque,
    buscar_saldos_estoque,
    formatar_decimal_brasil,
    formatar_moeda_brl,
    registrar_movimentacao_manual_estoque,
)
from app.suprimentos.estoque import suprimentos_estoque_bp


@suprimentos_estoque_bp.route("/")
@login_required
@module_permission_required("suprimentos", "estoque", "visualizar")
def listar():
    return render_template(
        "suprimentos/estoque/listar.html",
        itens=buscar_saldos_estoque(
            request.args.get("descricao"),
            request.args.get("categoria_id"),
            request.args.get("abaixo_minimo"),
        ),
        categorias=buscar_categorias_ativas(),
        filtros=request.args,
        formatar_decimal_brasil=formatar_decimal_brasil,
    )


@suprimentos_estoque_bp.route("/movimentacoes")
@login_required
@module_permission_required("suprimentos", "estoque", "visualizar")
def movimentacoes():
    itens = buscar_itens_ativos()
    item_fixado = next(
        (
            item
            for item in itens
            if str(item.id) == str(request.args.get("item_id", ""))
        ),
        None,
    )

    return render_template(
        "suprimentos/estoque/movimentacoes.html",
        movimentacoes=buscar_movimentacoes_estoque(
            request.args.get("item_id"),
            request.args.get("fornecedor_id"),
            request.args.get("documento"),
            request.args.get("data_inicio"),
            request.args.get("data_fim"),
        ),
        itens=itens,
        item_fixado=item_fixado,
        fornecedores=buscar_fornecedores_ativos(),
        filtros=request.args,
        formatar_decimal_brasil=formatar_decimal_brasil,
        formatar_moeda_brl=formatar_moeda_brl,
    )


@suprimentos_estoque_bp.route("/movimentacoes/nova", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "estoque", "editar")
def nova_movimentacao():
    if request.method == "POST":
        sucesso, mensagem, movimentacao = registrar_movimentacao_manual_estoque(
            request.form,
            current_user,
        )

        if sucesso:
            registrar_log(
                "suprimentos_estoque_movimentacao_manual",
                f"Movimentacao manual de estoque registrada. ID: {movimentacao.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_estoque.movimentacoes", item_id=movimentacao.item_id))

        flash(mensagem, "danger")

    itens = buscar_saldos_estoque()
    item_fixado = next(
        (
            item
            for item in itens
            if str(item.id) == str(request.args.get("item_id", ""))
        ),
        None,
    )

    return render_template(
        "suprimentos/estoque/form_movimentacao.html",
        itens=itens,
        item_fixado=item_fixado,
        centros_custo_equipes=buscar_centros_custo_ativos(CLASSE_CENTRO_CUSTO_EQUIPES),
        hoje=date.today().isoformat(),
        filtros=request.args,
        formatar_decimal_brasil=formatar_decimal_brasil,
    )

