from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.services.financeiro_contas_receber_service import (
    FORMAS_RECEBIMENTO,
    ORIGENS_LANCAMENTO,
    STATUS_TITULOS_RECEBER,
    buscar_baixa_recebimento_por_id,
    buscar_lote_recebimento_por_id,
    buscar_centros_custo_ativos,
    buscar_equipes_ativas,
    buscar_titulo_por_id,
    cancelar_lote_recebimento,
    cancelar_recebimento_titulo,
    cancelar_titulo_receber,
    caminho_comprovante_lote_recebimento,
    caminho_comprovante_recebimento,
    formatar_data_brasil,
    formatar_moeda_brl,
    gerar_dashboard,
    listar_lotes_recebimento,
    listar_titulos_receber,
    preparar_baixa_em_massa,
    recalcular_recebimento_titulo,
    registrar_recebimento_em_massa,
    registrar_recebimento_titulo,
    salvar_titulo_receber,
    titulo_elegivel_recebimento,
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
        pode_registrar_recebimento=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "editar"),
        pode_baixa_em_massa=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "editar"),
        titulo_elegivel_recebimento=titulo_elegivel_recebimento,
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
        pode_registrar_recebimento=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "editar"),
        pode_baixa_em_massa=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "editar"),
        titulo_elegivel_recebimento=titulo_elegivel_recebimento,
        pode_ver_recebimentos=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "visualizar"),
        pode_baixar_comprovante=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "visualizar"),
        pode_estornar_recebimento=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "excluir"),
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




@financeiro_contas_receber_bp.route("/baixa-em-massa", methods=["GET", "POST"])
@login_required
def baixa_em_massa():
    if not _permitido("editar"):
        flash("Você não possui permissão para registrar recebimento em massa.", "danger")
        return redirect(url_for("main.acesso_negado"))

    if request.method == "POST" and request.form.get("confirmar") == "1":
        arquivo = request.files.get("comprovante")
        sucesso, mensagem, lote = registrar_recebimento_em_massa(request.form, arquivo=arquivo, usuario=current_user)
        flash(mensagem, "success" if sucesso else "danger")
        if sucesso:
            registrar_log("financeiro_contas_receber_baixa_em_massa_confirmada", f"Baixa em massa registrada. Lote: {lote.id}.")
            return redirect(url_for("financeiro_contas_receber.lote_detalhe", lote_id=lote.id))

    ids = request.form.getlist("titulos_ids") if request.method == "POST" else request.args.getlist("titulos_ids")
    if not ids and request.args.get("ids"):
        ids = [item for item in request.args.get("ids", "").split(",") if item]

    titulos, total = preparar_baixa_em_massa(ids)
    if not titulos:
        flash("Nenhum título selecionado.", "warning")
        return redirect(url_for("financeiro_contas_receber.titulos"))

    return render_template(
        "financeiro/contas_receber/baixa_massa.html",
        titulos=titulos,
        total=total,
        formas_recebimento=FORMAS_RECEBIMENTO,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
    )


@financeiro_contas_receber_bp.route("/lotes")
@login_required
def lotes():
    if not _permitido("visualizar"):
        return redirect(url_for("main.acesso_negado"))
    return render_template(
        "financeiro/contas_receber/lotes.html",
        lotes=listar_lotes_recebimento(),
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
    )


@financeiro_contas_receber_bp.route("/lotes/<int:lote_id>")
@login_required
def lote_detalhe(lote_id):
    if not _permitido("visualizar"):
        return redirect(url_for("main.acesso_negado"))
    lote = buscar_lote_recebimento_por_id(lote_id)
    if not lote:
        flash("Lote de recebimento não encontrado.", "warning")
        return redirect(url_for("financeiro_contas_receber.lotes"))
    return render_template(
        "financeiro/contas_receber/lote_detalhe.html",
        lote=lote,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
        pode_estornar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "excluir"),
        pode_baixar_comprovante=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CONTAS_RECEBER, "visualizar"),
    )


@financeiro_contas_receber_bp.route("/lotes/<int:lote_id>/estornar", methods=["POST"])
@login_required
def lote_estornar(lote_id):
    if not _permitido("excluir"):
        return redirect(url_for("main.acesso_negado"))
    lote = buscar_lote_recebimento_por_id(lote_id)
    sucesso, mensagem = cancelar_lote_recebimento(lote, request.form.get("motivo_cancelamento"), usuario=current_user)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_receber.lote_detalhe", lote_id=lote_id) if lote else url_for("financeiro_contas_receber.lotes"))


@financeiro_contas_receber_bp.route("/lotes/<int:lote_id>/comprovante")
@login_required
def lote_comprovante(lote_id):
    if not _permitido("visualizar"):
        return redirect(url_for("main.acesso_negado"))
    lote = buscar_lote_recebimento_por_id(lote_id)
    caminho = caminho_comprovante_lote_recebimento(lote)
    if not caminho:
        abort(404)
    registrar_log("financeiro_contas_receber_lote_comprovante_download", f"Download de comprovante do lote. Lote: {lote.id}.")
    return send_file(
        caminho,
        as_attachment=True,
        download_name=lote.comprovante_nome_original or lote.comprovante_nome_armazenado,
    )
@financeiro_contas_receber_bp.route("/<int:titulo_id>/recebimentos/novo", methods=["GET", "POST"])
@login_required
def registrar_recebimento(titulo_id):
    if not _permitido("editar"):
        flash("Você não possui permissão para registrar recebimentos.", "danger")
        return redirect(url_for("main.acesso_negado"))

    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Título a receber não encontrado.", "warning")
        return redirect(url_for("financeiro_contas_receber.titulos"))

    recalcular_recebimento_titulo(titulo, usuario=current_user)
    if request.method == "POST":
        arquivo = request.files.get("comprovante")
        sucesso, mensagem, baixa = registrar_recebimento_titulo(
            titulo,
            request.form,
            arquivo=arquivo,
            usuario=current_user,
        )
        if sucesso:
            registrar_log("financeiro_contas_receber_recebimento_registrado", f"Recebimento registrado. Titulo: {titulo.id}. Baixa: {baixa.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_receber.detalhe", titulo_id=titulo.id))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_receber/recebimento_form.html",
        titulo=titulo,
        formas_recebimento=FORMAS_RECEBIMENTO,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
    )


@financeiro_contas_receber_bp.route("/<int:titulo_id>/recebimentos/<int:baixa_id>/estornar", methods=["POST"])
@login_required
def estornar_recebimento(titulo_id, baixa_id):
    if not _permitido("excluir"):
        return redirect(url_for("main.acesso_negado"))

    titulo = buscar_titulo_por_id(titulo_id)
    baixa = buscar_baixa_recebimento_por_id(baixa_id)
    if not titulo or not baixa or baixa.titulo_id != titulo.id:
        flash("Recebimento não encontrado.", "warning")
        return redirect(url_for("financeiro_contas_receber.titulos"))

    sucesso, mensagem = cancelar_recebimento_titulo(
        baixa,
        request.form.get("motivo_cancelamento"),
        usuario=current_user,
    )
    if sucesso:
        registrar_log("financeiro_contas_receber_recebimento_estornado", f"Recebimento estornado. Titulo: {titulo.id}. Baixa: {baixa.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_receber.detalhe", titulo_id=titulo.id))


@financeiro_contas_receber_bp.route("/baixas/<int:baixa_id>/comprovante")
@login_required
def baixar_comprovante(baixa_id):
    if not _permitido("visualizar"):
        return redirect(url_for("main.acesso_negado"))

    baixa = buscar_baixa_recebimento_por_id(baixa_id)
    caminho = caminho_comprovante_recebimento(baixa)
    if not caminho:
        abort(404)

    registrar_log("financeiro_contas_receber_comprovante_download", f"Download de comprovante. Baixa: {baixa.id}. Titulo: {baixa.titulo_id}.")
    return send_file(
        caminho,
        as_attachment=True,
        download_name=baixa.comprovante_nome_original or baixa.comprovante_nome_armazenado or (baixa.lote_baixa.comprovante_nome_original if baixa.lote_baixa else None) or (baixa.lote_baixa.comprovante_nome_armazenado if baixa.lote_baixa else None),
    )
