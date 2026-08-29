from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.financeiro_contas_receber_service import (
    ORIGENS_LANCAMENTO,
    STATUS_TITULOS_RECEBER,
    buscar_centros_custo_ativos,
    buscar_equipes_ativas,
    buscar_titulo_por_id,
    cancelar_titulo_receber,
    formatar_data_brasil,
    formatar_moeda_brl,
    gerar_dashboard,
    listar_titulos_receber,
    salvar_titulo_receber,
)
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.financeiro.contas_receber import financeiro_contas_receber_bp

DEPARTAMENTO_FINANCEIRO = "financeiro"
MODULO_CONTAS_RECEBER = "contas_a_receber"


def _permitido(acao="visualizar"):
    if usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, acao):
        return True

    registrar_log(
        "financeiro_contas_receber_permissao_bloqueada",
        f"Tentativa bloqueada em Contas a Receber. Acao: {acao}.",
    )
    flash("Você não possui permissão para acessar o Contas a Receber.", "danger")
    return False


def _contexto_formulario():
    return {
        "status_titulos": STATUS_TITULOS_RECEBER,
        "origens_lancamento": ORIGENS_LANCAMENTO,
        "centros_custo": buscar_centros_custo_ativos(),
        "equipes": buscar_equipes_ativas(),
    }


@financeiro_contas_receber_bp.route("/")
@login_required
def index():
    return redirect(url_for("financeiro_contas_receber.dashboard"))


@financeiro_contas_receber_bp.route("/dashboard")
@login_required
def dashboard():
    if not _permitido("visualizar"):
        return redirect(url_for("main.acesso_negado"))

    dados = gerar_dashboard(request.args)
    return render_template(
        "financeiro/contas_receber/dashboard.html",
        dados=dados,
        filtros=request.args,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
        pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "criar"),
    )


@financeiro_contas_receber_bp.route("/titulos")
@login_required
def titulos():
    if not _permitido("visualizar"):
        return redirect(url_for("main.acesso_negado"))

    return render_template(
        "financeiro/contas_receber/titulos.html",
        titulos=listar_titulos_receber(request.args),
        filtros=request.args,
        status_titulos=STATUS_TITULOS_RECEBER,
        origens_lancamento=ORIGENS_LANCAMENTO,
        centros_custo=buscar_centros_custo_ativos(),
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
        pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "criar"),
        pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "editar"),
        pode_cancelar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "excluir"),
    )


@financeiro_contas_receber_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if not _permitido("criar"):
        return redirect(url_for("main.acesso_negado"))

    titulo = None
    if request.method == "POST":
        sucesso, mensagem, titulo, status_alterado = salvar_titulo_receber(
            request.form,
            usuario=current_user,
        )

        if sucesso:
            registrar_log("financeiro_contas_receber_titulo_criado", f"Título a receber criado. ID: {titulo.id}.")
            if status_alterado:
                registrar_log("financeiro_contas_receber_status_alterado", f"Status alterado. Título ID: {titulo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_receber.detalhe", titulo_id=titulo.id))

        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_receber/form.html",
        titulo=titulo,
        modo="novo",
        **_contexto_formulario(),
    )


@financeiro_contas_receber_bp.route("/<int:titulo_id>")
@login_required
def detalhe(titulo_id):
    if not _permitido("visualizar"):
        return redirect(url_for("main.acesso_negado"))

    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Título a receber não encontrado.", "warning")
        return redirect(url_for("financeiro_contas_receber.titulos"))

    return render_template(
        "financeiro/contas_receber/detalhe.html",
        titulo=titulo,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
        pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "editar"),
        pode_cancelar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "excluir"),
    )


@financeiro_contas_receber_bp.route("/<int:titulo_id>/editar", methods=["GET", "POST"])
@login_required
def editar(titulo_id):
    if not _permitido("editar"):
        return redirect(url_for("main.acesso_negado"))

    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Título a receber não encontrado.", "warning")
        return redirect(url_for("financeiro_contas_receber.titulos"))

    if request.method == "POST":
        sucesso, mensagem, titulo, status_alterado = salvar_titulo_receber(
            request.form,
            titulo=titulo,
            usuario=current_user,
        )

        if sucesso:
            registrar_log("financeiro_contas_receber_titulo_atualizado", f"Título a receber atualizado. ID: {titulo.id}.")
            if status_alterado:
                registrar_log("financeiro_contas_receber_status_alterado", f"Status alterado. Título ID: {titulo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_receber.detalhe", titulo_id=titulo.id))

        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_receber/form.html",
        titulo=titulo,
        modo="editar",
        **_contexto_formulario(),
    )


@financeiro_contas_receber_bp.route("/<int:titulo_id>/cancelar", methods=["POST"])
@login_required
def cancelar(titulo_id):
    if not _permitido("excluir"):
        return redirect(url_for("main.acesso_negado"))

    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Título a receber não encontrado.", "warning")
        return redirect(url_for("financeiro_contas_receber.titulos"))

    sucesso, mensagem = cancelar_titulo_receber(
        titulo,
        motivo=request.form.get("motivo_cancelamento"),
        usuario=current_user,
    )
    if sucesso:
        registrar_log("financeiro_contas_receber_titulo_cancelado", f"Título a receber cancelado. ID: {titulo.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_receber.detalhe", titulo_id=titulo.id))
