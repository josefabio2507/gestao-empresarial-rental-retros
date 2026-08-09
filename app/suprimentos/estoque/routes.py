from flask import render_template, request
from flask_login import login_required

from app.decorators import module_permission_required
from app.services.suprimentos_service import (
    buscar_categorias_ativas,
    buscar_fornecedores_ativos,
    buscar_itens_ativos,
    buscar_movimentacoes_estoque,
    buscar_saldos_estoque,
    formatar_decimal_brasil,
    formatar_moeda_brl,
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
    return render_template(
        "suprimentos/estoque/movimentacoes.html",
        movimentacoes=buscar_movimentacoes_estoque(
            request.args.get("item_id"),
            request.args.get("fornecedor_id"),
            request.args.get("documento"),
            request.args.get("data_inicio"),
            request.args.get("data_fim"),
        ),
        itens=buscar_itens_ativos(),
        fornecedores=buscar_fornecedores_ativos(),
        filtros=request.args,
        formatar_decimal_brasil=formatar_decimal_brasil,
        formatar_moeda_brl=formatar_moeda_brl,
    )
