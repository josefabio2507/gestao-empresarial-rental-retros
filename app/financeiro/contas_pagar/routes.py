from flask import abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import SuprimentosOrdemCompra
from app.services.financeiro_contas_pagar_service import (
    FORMAS_PAGAMENTO,
    ORIGENS_LANCAMENTO,
    STATUS_FATURA,
    STATUS_TITULO,
    STATUS_XML_FINANCEIRO,
    TIPOS_PAGAMENTO,
    buscar_baixa_por_id,
    calcular_saldo_titulo,
    cancelar_baixa_titulo,
    caminho_comprovante_baixa,
    caminho_comprovante_lote,
    alterar_status_cartao,
    atualizar_status_fatura,
    buscar_cartao_por_id,
    buscar_documento_fiscal_por_id,
    buscar_lote_baixa_por_id,
    buscar_fatura_por_id,
    buscar_opcoes_formulario,
    buscar_titulo_por_id,
    cancelar_titulo,
    dados_padrao_conferencia_xml,
    gerar_contas_pagar_xml,
    ignorar_xml_financeiro,
    indicadores_dashboard,
    listar_agendamentos_xml_contas_pagar,
    listar_cartoes,
    listar_faturas,
    listar_titulos,
    opcoes_conferencia_xml,
    reativar_xml_financeiro,
    registrar_baixa_em_massa,
    registrar_baixa_titulo,
    estornar_lote_baixa,
    salvar_cartao,
    titulos_para_baixa_em_massa,
    titulo_elegivel_baixa,
    salvar_titulo,
    status_financeiro_xml,
    titulos_ativos_documento_fiscal,
)
from app.services.financeiro_relatorios_service import (
    dashboard_avancado,
    filtros_padrao,
    filtros_para_template,
    opcoes_relatorios,
    periodo_valido,
    valor_coluna,
)
from app.services.suprimentos_service import (
    buscar_agendamentos_oc_contas_pagar,
    buscar_por_id,
    formatar_moeda_brl,
    gerar_contas_pagar_ordem_compra,
    status_financeiro_calculado_ordem,
    titulos_ativos_ordem_compra,
)
from app.services.logs_service import registrar_log
from app.financeiro.contas_pagar import financeiro_contas_pagar_bp


@financeiro_contas_pagar_bp.route("/")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def dashboard():
    filtros = filtros_padrao(request.args)
    if not periodo_valido(filtros):
        flash("A data inicial nao pode ser maior que a data final.", "warning")
        filtros = filtros_padrao({})
    return render_template(
        "financeiro/contas_pagar/dashboard.html",
        indicadores=indicadores_dashboard(),
        dashboard_avancado=dashboard_avancado(filtros),
        filtros=filtros_para_template(filtros),
        opcoes_relatorios=opcoes_relatorios(),
        valor_coluna=valor_coluna,
    )


@financeiro_contas_pagar_bp.route("/relatorios")
@login_required
def relatorios():
    return redirect(url_for("financeiro.relatorios", **request.args))


@financeiro_contas_pagar_bp.route("/relatorios/exportar")
@login_required
def exportar_relatorio():
    return redirect(url_for("financeiro.exportar_relatorio", **request.args))

@financeiro_contas_pagar_bp.route("/titulos/baixa-em-massa", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def baixa_em_massa():
    if request.method == "POST":
        arquivo = request.files.get("comprovante")
        sucesso, mensagem, lote = registrar_baixa_em_massa(request.form, arquivo=arquivo, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_lote_baixa_confirmado", f"Baixa em massa confirmada. Lote: {lote.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.detalhes_lote_baixa", lote_id=lote.id))
        flash(mensagem, "danger")

    ids = request.args.getlist("titulos_ids") or request.form.getlist("titulos_ids")
    titulos = [titulo for titulo in titulos_para_baixa_em_massa(ids) if titulo_elegivel_baixa(titulo)]
    if not titulos:
        flash("Nenhum titulo selecionado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))
    total_saldo = sum((calcular_saldo_titulo(titulo) for titulo in titulos), start=0)
    return render_template(
        "financeiro/contas_pagar/baixa_em_massa.html",
        titulos=titulos,
        total_saldo=total_saldo,
        formas_pagamento=FORMAS_PAGAMENTO,
        calcular_saldo_titulo=calcular_saldo_titulo,
    )


@financeiro_contas_pagar_bp.route("/lotes-baixa/<int:lote_id>")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def detalhes_lote_baixa(lote_id):
    lote = buscar_lote_baixa_por_id(lote_id)
    if not lote:
        flash("Lote de baixa nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))
    return render_template("financeiro/contas_pagar/lote_baixa_detalhes.html", lote=lote)


@financeiro_contas_pagar_bp.route("/lotes-baixa/<int:lote_id>/estornar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "excluir")
def estornar_lote(lote_id):
    lote = buscar_lote_baixa_por_id(lote_id)
    sucesso, mensagem = estornar_lote_baixa(lote, request.form.get("motivo_cancelamento"), usuario=current_user)
    if sucesso:
        registrar_log("financeiro_lote_baixa_estornado", f"Lote de baixa estornado. ID: {lote.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.detalhes_lote_baixa", lote_id=lote_id))


@financeiro_contas_pagar_bp.route("/lotes-baixa/<int:lote_id>/comprovante")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def baixar_comprovante_lote(lote_id):
    lote = buscar_lote_baixa_por_id(lote_id)
    caminho = caminho_comprovante_lote(lote)
    if not caminho:
        abort(404)
    registrar_log("financeiro_lote_baixa_comprovante_download", f"Download de comprovante do lote. Lote: {lote.id}.")
    return send_file(
        caminho,
        as_attachment=True,
        download_name=lote.comprovante_nome_original or lote.comprovante_nome_armazenado,
    )

@financeiro_contas_pagar_bp.route("/titulos")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def titulos():
    opcoes = buscar_opcoes_formulario()
    return render_template(
        "financeiro/contas_pagar/titulos.html",
        titulos=listar_titulos(request.args),
        filtros=request.args,
        opcoes=opcoes,
        origens=ORIGENS_LANCAMENTO,
        tipos_pagamento=TIPOS_PAGAMENTO,
        formas_pagamento=FORMAS_PAGAMENTO,
        status_titulo=STATUS_TITULO,
        titulo_elegivel_baixa=titulo_elegivel_baixa,
        calcular_saldo_titulo=calcular_saldo_titulo,
    )


@financeiro_contas_pagar_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, titulo = salvar_titulo(request.form, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_contas_pagar_criado", f"Titulo a pagar criado. ID: {titulo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.detalhes", titulo_id=titulo.id))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/form.html",
        titulo=None,
        modo="novo",
        opcoes=buscar_opcoes_formulario(),
    )


@financeiro_contas_pagar_bp.route("/agendamentos-oc")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def agendamentos_oc():
    return render_template(
        "financeiro/contas_pagar/agendamentos_oc.html",
        ordens=buscar_agendamentos_oc_contas_pagar(),
        formatar_moeda_brl=formatar_moeda_brl,
        status_financeiro_calculado_ordem=status_financeiro_calculado_ordem,
        titulos_ativos_ordem_compra=titulos_ativos_ordem_compra,
    )


@financeiro_contas_pagar_bp.route("/agendamentos-oc/<int:ordem_id>/gerar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def gerar_agendamento_oc(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)
    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("financeiro_contas_pagar.agendamentos_oc"))

    sucesso, mensagem, titulos = gerar_contas_pagar_ordem_compra(ordem, usuario=current_user)
    if sucesso:
        registrar_log("financeiro_contas_pagar_oc_gerado", f"Contas a pagar gerado por O.C. ID: {ordem.id}. Titulos: {len(titulos)}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.agendamentos_oc"))


@financeiro_contas_pagar_bp.route("/agendamentos-xml")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def agendamentos_xml():
    return render_template(
        "financeiro/contas_pagar/agendamentos_xml.html",
        documentos=listar_agendamentos_xml_contas_pagar(request.args),
        filtros=request.args,
        status_xml=STATUS_XML_FINANCEIRO,
        status_financeiro_xml=status_financeiro_xml,
        titulos_ativos_documento_fiscal=titulos_ativos_documento_fiscal,
        formatar_moeda_brl=formatar_moeda_brl,
    )


@financeiro_contas_pagar_bp.route("/agendamentos-xml/<int:documento_id>/conferir", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def conferir_xml(documento_id):
    documento = buscar_documento_fiscal_por_id(documento_id)
    if not documento:
        flash("Documento fiscal nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.agendamentos_xml"))

    if request.method == "POST":
        sucesso, mensagem, titulos = gerar_contas_pagar_xml(documento, request.form, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_xml_contas_pagar_gerado", f"Contas a pagar gerado por XML. Documento fiscal ID: {documento.id}. Titulos: {len(titulos)}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.titulos", numero_nfe=documento.numero))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/conferir_xml.html",
        documento=documento,
        padrao=dados_padrao_conferencia_xml(documento),
        opcoes=opcoes_conferencia_xml(documento),
        status_financeiro=status_financeiro_xml(documento),
        titulos=titulos_ativos_documento_fiscal(documento),
        formatar_moeda_brl=formatar_moeda_brl,
    )


@financeiro_contas_pagar_bp.route("/agendamentos-xml/<int:documento_id>/ignorar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "excluir")
def ignorar_agendamento_xml(documento_id):
    documento = buscar_documento_fiscal_por_id(documento_id)
    sucesso, mensagem = ignorar_xml_financeiro(documento, usuario=current_user, observacoes=request.form.get("observacoes"))
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.agendamentos_xml"))


@financeiro_contas_pagar_bp.route("/agendamentos-xml/<int:documento_id>/reativar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def reativar_agendamento_xml(documento_id):
    documento = buscar_documento_fiscal_por_id(documento_id)
    sucesso, mensagem = reativar_xml_financeiro(documento, usuario=current_user)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.agendamentos_xml"))


@financeiro_contas_pagar_bp.route("/cartoes")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def cartoes():
    return render_template(
        "financeiro/contas_pagar/cartoes.html",
        cartoes=listar_cartoes(request.args),
        filtros=request.args,
    )


@financeiro_contas_pagar_bp.route("/cartoes/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def novo_cartao():
    if request.method == "POST":
        sucesso, mensagem, cartao = salvar_cartao(request.form, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_cartao_credito_criado", f"Cartao de credito criado. ID: {cartao.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.cartoes"))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/cartao_form.html",
        cartao=None,
        modo="novo",
        opcoes=buscar_opcoes_formulario(),
    )


@financeiro_contas_pagar_bp.route("/cartoes/<int:cartao_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def editar_cartao(cartao_id):
    cartao = buscar_cartao_por_id(cartao_id)
    if not cartao:
        flash("Cartao nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.cartoes"))

    if request.method == "POST":
        sucesso, mensagem, cartao = salvar_cartao(request.form, cartao=cartao, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_cartao_credito_atualizado", f"Cartao de credito atualizado. ID: {cartao.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.cartoes"))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/cartao_form.html",
        cartao=cartao,
        modo="editar",
        opcoes=buscar_opcoes_formulario(),
    )


@financeiro_contas_pagar_bp.route("/cartoes/<int:cartao_id>/status", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "excluir")
def status_cartao(cartao_id):
    cartao = buscar_cartao_por_id(cartao_id)
    ativar = request.form.get("ativo") == "1"
    sucesso, mensagem = alterar_status_cartao(cartao, ativar, usuario=current_user)
    if sucesso:
        registrar_log(
            "financeiro_cartao_credito_status_alterado",
            f"Cartao de credito {'reativado' if ativar else 'inativado'}. ID: {cartao.id}.",
        )
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.cartoes"))


@financeiro_contas_pagar_bp.route("/faturas")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def faturas():
    return render_template(
        "financeiro/contas_pagar/faturas.html",
        faturas=listar_faturas(request.args),
        filtros=request.args,
        opcoes=buscar_opcoes_formulario(),
        cartoes_filtro=listar_cartoes({}),
        status_fatura=STATUS_FATURA,
    )


@financeiro_contas_pagar_bp.route("/faturas/<int:fatura_id>")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def detalhes_fatura(fatura_id):
    fatura = buscar_fatura_por_id(fatura_id)
    if not fatura:
        flash("Fatura nao encontrada.", "warning")
        return redirect(url_for("financeiro_contas_pagar.faturas"))
    return render_template("financeiro/contas_pagar/fatura_detalhes.html", fatura=fatura, calcular_saldo_titulo=calcular_saldo_titulo)


@financeiro_contas_pagar_bp.route("/faturas/<int:fatura_id>/fechar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def fechar_fatura(fatura_id):
    fatura = buscar_fatura_por_id(fatura_id)
    sucesso, mensagem = atualizar_status_fatura(fatura, "Fechada", usuario=current_user)
    if sucesso:
        registrar_log("financeiro_cartao_fatura_fechada", f"Fatura fechada. ID: {fatura.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.detalhes_fatura", fatura_id=fatura_id))


@financeiro_contas_pagar_bp.route("/faturas/<int:fatura_id>/reabrir", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def reabrir_fatura(fatura_id):
    fatura = buscar_fatura_por_id(fatura_id)
    sucesso, mensagem = atualizar_status_fatura(fatura, "Aberta", usuario=current_user)
    if sucesso:
        registrar_log("financeiro_cartao_fatura_reaberta", f"Fatura reaberta. ID: {fatura.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.detalhes_fatura", fatura_id=fatura_id))


@financeiro_contas_pagar_bp.route("/faturas/<int:fatura_id>/cancelar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "excluir")
def cancelar_fatura(fatura_id):
    fatura = buscar_fatura_por_id(fatura_id)
    sucesso, mensagem = atualizar_status_fatura(fatura, "Cancelada", usuario=current_user)
    if sucesso:
        registrar_log("financeiro_cartao_fatura_cancelada", f"Fatura cancelada. ID: {fatura.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.detalhes_fatura", fatura_id=fatura_id))


@financeiro_contas_pagar_bp.route("/<int:titulo_id>")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def detalhes(titulo_id):
    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Titulo nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))

    return render_template("financeiro/contas_pagar/detalhes.html", titulo=titulo, saldo=calcular_saldo_titulo(titulo))



@financeiro_contas_pagar_bp.route("/<int:titulo_id>/pagamentos/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def registrar_pagamento(titulo_id):
    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Titulo nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))

    if request.method == "POST":
        arquivo = request.files.get("comprovante")
        sucesso, mensagem, baixa = registrar_baixa_titulo(titulo, request.form, arquivo=arquivo, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_baixa_registrada", f"Pagamento registrado. Titulo: {titulo.id}. Baixa: {baixa.id}.")
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.detalhes", titulo_id=titulo.id))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/pagamento_form.html",
        titulo=titulo,
        saldo=calcular_saldo_titulo(titulo),
        formas_pagamento=FORMAS_PAGAMENTO,
    )


@financeiro_contas_pagar_bp.route("/<int:titulo_id>/pagamentos/<int:baixa_id>/estornar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "excluir")
def estornar_pagamento(titulo_id, baixa_id):
    titulo = buscar_titulo_por_id(titulo_id)
    baixa = buscar_baixa_por_id(baixa_id)
    if not titulo or not baixa or baixa.titulo_id != titulo.id:
        flash("Baixa nao encontrada.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))
    sucesso, mensagem = cancelar_baixa_titulo(baixa, request.form.get("motivo_cancelamento"), usuario=current_user)
    if sucesso:
        registrar_log("financeiro_baixa_estornada", f"Baixa estornada. Titulo: {titulo.id}. Baixa: {baixa.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.detalhes", titulo_id=titulo.id))


@financeiro_contas_pagar_bp.route("/baixas/<int:baixa_id>/comprovante")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "visualizar")
def baixar_comprovante(baixa_id):
    baixa = buscar_baixa_por_id(baixa_id)
    caminho = caminho_comprovante_baixa(baixa)
    if not caminho:
        abort(404)
    registrar_log("financeiro_comprovante_download", f"Download de comprovante. Baixa: {baixa.id}. Titulo: {baixa.titulo_id}.")
    return send_file(
        caminho,
        as_attachment=True,
        download_name=baixa.comprovante_nome_original or baixa.comprovante_nome_armazenado,
    )

@financeiro_contas_pagar_bp.route("/<int:titulo_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "editar")
def editar(titulo_id):
    titulo = buscar_titulo_por_id(titulo_id)
    if not titulo:
        flash("Titulo nao encontrado.", "warning")
        return redirect(url_for("financeiro_contas_pagar.titulos"))

    status_anterior = titulo.status
    if request.method == "POST":
        sucesso, mensagem, titulo = salvar_titulo(request.form, titulo=titulo, usuario=current_user)
        if sucesso:
            registrar_log("financeiro_contas_pagar_atualizado", f"Titulo a pagar atualizado. ID: {titulo.id}.")
            if status_anterior != titulo.status:
                registrar_log(
                    "financeiro_contas_pagar_status_alterado",
                    f"Status do titulo a pagar alterado. ID: {titulo.id}. {status_anterior} -> {titulo.status}.",
                )
            flash(mensagem, "success")
            return redirect(url_for("financeiro_contas_pagar.detalhes", titulo_id=titulo.id))
        flash(mensagem, "danger")

    return render_template(
        "financeiro/contas_pagar/form.html",
        titulo=titulo,
        modo="editar",
        opcoes=buscar_opcoes_formulario(titulo=titulo),
    )


@financeiro_contas_pagar_bp.route("/<int:titulo_id>/cancelar", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "excluir")
def cancelar(titulo_id):
    titulo = buscar_titulo_por_id(titulo_id)
    sucesso, mensagem = cancelar_titulo(titulo, usuario=current_user)
    if sucesso:
        registrar_log("financeiro_contas_pagar_cancelado", f"Titulo a pagar cancelado. ID: {titulo.id}.")
        registrar_log("financeiro_contas_pagar_status_alterado", f"Status do titulo a pagar alterado. ID: {titulo.id}. Cancelado.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_contas_pagar.titulos"))
