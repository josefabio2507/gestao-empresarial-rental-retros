from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.services.financeiro_contas_receber_relatorios_service import (
    filtros_padrao_cr,
    filtros_para_template_cr,
    gerar_csv_relatorio_cr,
    montar_relatorio_cr,
    nome_arquivo_relatorio_cr,
    opcoes_relatorios_cr,
    periodo_valido_cr,
    valor_coluna_cr,
)
from app.services.financeiro_relatorios_service import (
    filtros_padrao,
    filtros_para_template,
    gerar_csv_relatorio,
    montar_relatorio,
    nome_arquivo_relatorio,
    opcoes_relatorios,
    periodo_valido,
    valor_coluna,
)
from app.services.financeiro_fluxo_caixa_service import (
    dashboard_fluxo_caixa,
    filtros_padrao_fluxo,
    filtros_para_template_fluxo,
    gerar_csv_movimentos,
    movimentos_fluxo_caixa,
    nome_arquivo_fluxo,
    opcoes_fluxo_caixa,
    periodo_valido_fluxo,
    valor_coluna_fluxo,
    visao_fluxo_caixa,
)
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao

financeiro_bp = Blueprint("financeiro", __name__)


@financeiro_bp.route("/")
@login_required
def index():
    return render_template(
        "financeiro/index.html",
        pode_ver_contas_pagar=usuario_tem_permissao(current_user, "financeiro", "contas_a_pagar", "visualizar"),
        pode_ver_contas_receber=usuario_tem_permissao(current_user, "financeiro", "contas_a_receber", "visualizar"),
        pode_ver_fluxo_caixa=usuario_tem_permissao(current_user, "financeiro", "fluxo_de_caixa", "visualizar"),
        pode_ver_relatorios=usuario_tem_permissao(current_user, "financeiro", "relatorios", "visualizar"),
    )


@financeiro_bp.route("/relatorios")
@login_required
@module_permission_required("financeiro", "relatorios", "visualizar")
def relatorios():
    escopo = request.args.get("escopo") or "contas_pagar"
    if escopo == "contas_receber":
        filtros = filtros_padrao_cr(request.args)
        if not periodo_valido_cr(filtros):
            flash("A data inicial nao pode ser maior que a data final.", "warning")
            filtros = filtros_padrao_cr({})
        relatorio = montar_relatorio_cr(filtros["tipo_relatorio"], filtros)
        registrar_log("financeiro_relatorio_visualizado", "Relatorio financeiro de Contas a Receber visualizado: {}.".format(relatorio["tipo"]))
        return render_template(
            "financeiro/relatorios.html",
            relatorio=relatorio,
            filtros=filtros_para_template_cr(filtros),
            opcoes_relatorios=opcoes_relatorios_cr(),
            valor_coluna=valor_coluna_cr,
            escopo="contas_receber",
        )

    filtros = filtros_padrao(request.args)
    if not periodo_valido(filtros):
        flash("A data inicial nao pode ser maior que a data final.", "warning")
        filtros = filtros_padrao({})
    relatorio = montar_relatorio(filtros["tipo_relatorio"], filtros)
    registrar_log("financeiro_relatorio_visualizado", "Relatorio financeiro visualizado: {}.".format(relatorio["tipo"]))
    return render_template(
        "financeiro/relatorios.html",
        relatorio=relatorio,
        filtros=filtros_para_template(filtros),
        opcoes_relatorios=opcoes_relatorios(),
        valor_coluna=valor_coluna,
        escopo="contas_pagar",
    )


@financeiro_bp.route("/relatorios/exportar")
@login_required
@module_permission_required("financeiro", "relatorios", "exportar")
def exportar_relatorio():
    escopo = request.args.get("escopo") or "contas_pagar"
    if escopo == "contas_receber":
        filtros = filtros_padrao_cr(request.args)
        if not periodo_valido_cr(filtros):
            flash("Informe um periodo valido.", "warning")
            return redirect(url_for("financeiro.relatorios", escopo="contas_receber"))
        relatorio = montar_relatorio_cr(filtros["tipo_relatorio"], filtros)
        conteudo = gerar_csv_relatorio_cr(relatorio)
        registrar_log("financeiro_relatorio_exportado", "Relatorio financeiro de Contas a Receber exportado: {}.".format(relatorio["tipo"]))
        return Response(
            conteudo,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename={}".format(nome_arquivo_relatorio_cr(relatorio["tipo"]))},
        )

    filtros = filtros_padrao(request.args)
    if not periodo_valido(filtros):
        flash("Informe um periodo valido.", "warning")
        return redirect(url_for("financeiro.relatorios"))
    relatorio = montar_relatorio(filtros["tipo_relatorio"], filtros)
    conteudo = gerar_csv_relatorio(relatorio)
    registrar_log("financeiro_relatorio_exportado", "Relatorio financeiro exportado: {}.".format(relatorio["tipo"]))
    return Response(
        conteudo,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename={}".format(nome_arquivo_relatorio(relatorio["tipo"]))},
    )



def _contexto_fluxo_caixa():
    filtros = filtros_padrao_fluxo(request.args)
    if not periodo_valido_fluxo(filtros):
        flash("A data inicial nao pode ser maior que a data final.", "warning")
        filtros = filtros_padrao_fluxo({})
    return filtros, filtros_para_template_fluxo(filtros), opcoes_fluxo_caixa(), usuario_tem_permissao(current_user, "financeiro", "fluxo_de_caixa", "exportar")


@financeiro_bp.route("/fluxo-caixa")
@login_required
@module_permission_required("financeiro", "fluxo_de_caixa", "visualizar")
def fluxo_caixa_dashboard():
    filtros, filtros_template, opcoes, pode_exportar = _contexto_fluxo_caixa()
    return render_template(
        "financeiro/fluxo_caixa/dashboard.html",
        dados=dashboard_fluxo_caixa(filtros),
        filtros=filtros_template,
        opcoes=opcoes,
        pode_exportar=pode_exportar,
        valor_coluna=valor_coluna_fluxo,
    )


@financeiro_bp.route("/fluxo-caixa/movimentos")
@login_required
@module_permission_required("financeiro", "fluxo_de_caixa", "visualizar")
def fluxo_caixa_movimentos():
    filtros, filtros_template, opcoes, pode_exportar = _contexto_fluxo_caixa()
    return render_template(
        "financeiro/fluxo_caixa/movimentos.html",
        movimentos=movimentos_fluxo_caixa(filtros),
        filtros=filtros_template,
        opcoes=opcoes,
        pode_exportar=pode_exportar,
        valor_coluna=valor_coluna_fluxo,
    )


def _renderizar_visao_fluxo(periodo, titulo, aba, primeira_coluna, agrupamento_nome, limpar_endpoint):
    filtros, filtros_template, opcoes, pode_exportar = _contexto_fluxo_caixa()
    return render_template(
        "financeiro/fluxo_caixa/visao.html",
        visao=visao_fluxo_caixa(periodo, filtros),
        filtros=filtros_template,
        opcoes=opcoes,
        pode_exportar=pode_exportar,
        valor_coluna=valor_coluna_fluxo,
        titulo=titulo,
        aba=aba,
        primeira_coluna=primeira_coluna,
        agrupamento_nome=agrupamento_nome,
        limpar_url=url_for(limpar_endpoint),
        exportar_url=url_for("financeiro.exportar_fluxo_caixa", **request.args),
    )


@financeiro_bp.route("/fluxo-caixa/diario")
@login_required
@module_permission_required("financeiro", "fluxo_de_caixa", "visualizar")
def fluxo_caixa_diario():
    return _renderizar_visao_fluxo("dia", "Visão Diária", "diaria", "Data", "dia", "financeiro.fluxo_caixa_diario")


@financeiro_bp.route("/fluxo-caixa/semanal")
@login_required
@module_permission_required("financeiro", "fluxo_de_caixa", "visualizar")
def fluxo_caixa_semanal():
    return _renderizar_visao_fluxo("semana", "Visão Semanal", "semanal", "Semana", "semana", "financeiro.fluxo_caixa_semanal")


@financeiro_bp.route("/fluxo-caixa/mensal")
@login_required
@module_permission_required("financeiro", "fluxo_de_caixa", "visualizar")
def fluxo_caixa_mensal():
    return _renderizar_visao_fluxo("mes", "Visão Mensal", "mensal", "Mês/Ano", "mês", "financeiro.fluxo_caixa_mensal")


@financeiro_bp.route("/fluxo-caixa/exportar")
@login_required
@module_permission_required("financeiro", "fluxo_de_caixa", "exportar")
def exportar_fluxo_caixa():
    filtros = filtros_padrao_fluxo(request.args)
    if not periodo_valido_fluxo(filtros):
        flash("Informe um periodo valido.", "warning")
        return redirect(url_for("financeiro.fluxo_caixa_movimentos"))
    movimentos = movimentos_fluxo_caixa(filtros)
    registrar_log("financeiro_fluxo_caixa_exportado", "Movimentos do Fluxo de Caixa exportados.")
    return Response(
        gerar_csv_movimentos(movimentos),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename={}".format(nome_arquivo_fluxo("movimentos"))},
    )


@financeiro_bp.route("/status")
@login_required
def status():
    return "Financeiro online."
