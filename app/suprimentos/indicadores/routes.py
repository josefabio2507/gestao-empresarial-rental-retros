from flask import render_template, request
from flask_login import login_required

from app.decorators import module_permission_required
from app.services.suprimentos_service import (
    buscar_categorias_ativas,
    buscar_centros_custo,
    buscar_fornecedores_ativos,
    formatar_decimal_brasil,
    formatar_moeda_brl,
    indicadores_suprimentos,
)
from app.suprimentos.indicadores import suprimentos_indicadores_bp


@suprimentos_indicadores_bp.route("/")
@login_required
@module_permission_required("suprimentos", "indicadores", "visualizar")
def painel():
    return render_template(
        "suprimentos/indicadores/painel.html",
        indicadores=indicadores_suprimentos(
            request.args.get("data_inicio"),
            request.args.get("data_fim"),
            request.args.get("fornecedor_id"),
            request.args.get("centro_custo_id"),
            request.args.get("categoria_id"),
        ),
        fornecedores=buscar_fornecedores_ativos(),
        centros_custo=buscar_centros_custo(status="ativos"),
        categorias=buscar_categorias_ativas(),
        filtros=request.args,
        formatar_decimal_brasil=formatar_decimal_brasil,
        formatar_moeda_brl=formatar_moeda_brl,
    )
