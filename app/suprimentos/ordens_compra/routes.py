from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import (
    CentroCusto,
    FinanceiroCartaoCredito,
    SuprimentosCotacao,
    SuprimentosFornecedor,
    SuprimentosOrdemCompra,
    SuprimentosOrdemCompraItem,
    SuprimentosRecebimentoCompra,
)
from app.services.fiscal_service import (
    buscar_documentos_para_ordem_compra,
    vincular_documento_ordem_compra,
)
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.services.suprimentos_service import (
    CLASSE_CENTRO_CUSTO,
    CLASSE_CENTRO_CUSTO_EQUIPES,
    CLASSE_CENTRO_EPG_VEICULOS,
    STATUS_ORDEM_COMPRA_CANCELADA,
    STATUS_ORDEM_COMPRA_GERADA,
    STATUS_ORDEM_COMPRA_PARCIAL,
    STATUS_ORDEM_COMPRA_RECEBIDA,
    STATUS_FINANCEIRO_CANCELADO,
    STATUS_FINANCEIRO_CONFERENCIA,
    STATUS_FINANCEIRO_INTEGRADO,
    CONDICOES_PAGAMENTO_FINANCEIRO_OC,
    FORMAS_PAGAMENTO_FINANCEIRO_OC,
    TIPOS_PAGAMENTO_FINANCEIRO_OC,
    STATUS_FINANCEIRO_PENDENTE,
    STATUS_FINANCEIRO_PREPARADO,
    STATUS_FINANCEIRO_PROVISIONADO,
    buscar_centros_custo_ativos,
    buscar_fornecedores_ativos,
    buscar_cotacoes_aprovadas_sem_ordem_compra,
    buscar_ordens_aguardando_financeiro,
    buscar_ordens_compra,
    buscar_por_id,
    cancelar_ordem_compra,
    editar_recebimento_ordem_compra,
    enviar_email_ordem_compra_fornecedor,
    formatar_decimal_brasil,
    formatar_moeda_brl,
    gerar_link_whatsapp_ordem_compra_fornecedor,
    gerar_ordens_compra_cotacao,
    nome_subcentro_equipe_requisicao,
    nome_subcentro_veiculo_requisicao,
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
    STATUS_FINANCEIRO_CONFERENCIA,
    STATUS_FINANCEIRO_INTEGRADO,
]


@suprimentos_ordens_compra_bp.route("/")
@login_required
@module_permission_required("suprimentos", "ordens_compra", "visualizar")
def listar():
    fornecedor_id = request.args.get("fornecedor_id", type=int)
    centro_custo_id = request.args.get("centro_custo_id", type=int)
    sub_centro_custo_equipe_id = request.args.get("sub_centro_custo_equipe_id", type=int)
    sub_centro_custo_veiculo_id = request.args.get("sub_centro_custo_veiculo_id", type=int)

    return render_template(
        "suprimentos/ordens_compra/listar.html",
        ordens=buscar_ordens_compra(
            request.args.get("numero"),
            request.args.get("status"),
            fornecedor_id,
            request.args.get("status_financeiro"),
            centro_custo_id,
            sub_centro_custo_equipe_id,
            sub_centro_custo_veiculo_id,
        ),
        cotacoes_aprovadas_sem_oc=buscar_cotacoes_aprovadas_sem_ordem_compra(request.args.get("numero")),
        fornecedores=buscar_fornecedores_ativos(),
        centros_custo=buscar_centros_custo_ativos(CLASSE_CENTRO_CUSTO),
        subcentros_equipe=buscar_centros_custo_ativos(CLASSE_CENTRO_CUSTO_EQUIPES),
        subcentros_veiculo=buscar_centros_custo_ativos(CLASSE_CENTRO_EPG_VEICULOS),
        fornecedor_filtro=buscar_por_id(SuprimentosFornecedor, fornecedor_id) if fornecedor_id else None,
        centro_custo_filtro=buscar_por_id(CentroCusto, centro_custo_id) if centro_custo_id else None,
        subcentro_equipe_filtro=buscar_por_id(CentroCusto, sub_centro_custo_equipe_id) if sub_centro_custo_equipe_id else None,
        subcentro_veiculo_filtro=buscar_por_id(CentroCusto, sub_centro_custo_veiculo_id) if sub_centro_custo_veiculo_id else None,
        status_ordens=STATUS_ORDENS_COMPRA,
        status_financeiros=STATUS_FINANCEIROS_OC,
        filtros=request.args,
        formatar_moeda_brl=formatar_moeda_brl,
        nome_subcentro_equipe_requisicao=nome_subcentro_equipe_requisicao,
        nome_subcentro_veiculo_requisicao=nome_subcentro_veiculo_requisicao,
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
        cartoes_credito=FinanceiroCartaoCredito.query.filter_by(ativo=True).order_by(FinanceiroCartaoCredito.nome.asc()).all(),
        tipos_pagamento_financeiro=TIPOS_PAGAMENTO_FINANCEIRO_OC,
        formas_pagamento_financeiro=FORMAS_PAGAMENTO_FINANCEIRO_OC,
        condicoes_pagamento_financeiro=CONDICOES_PAGAMENTO_FINANCEIRO_OC,
        pode_visualizar_fiscal=usuario_tem_permissao(
            current_user,
            "fiscal",
            "documentos_fiscais",
            "visualizar",
        ),
    )


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/documentos-fiscais")
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def documentos_fiscais(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    if not usuario_tem_permissao(current_user, "fiscal", "documentos_fiscais", "visualizar"):
        flash("Voce nao tem permissao para visualizar documentos fiscais.", "danger")
        return redirect(url_for("main.acesso_negado"))

    return render_template(
        "suprimentos/ordens_compra/documentos_fiscais.html",
        ordem=ordem,
        documentos=buscar_documentos_para_ordem_compra(ordem),
    )


@suprimentos_ordens_compra_bp.route("/<int:ordem_id>/documentos-fiscais/vincular", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def vincular_documento_fiscal(ordem_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    if not usuario_tem_permissao(current_user, "fiscal", "documentos_fiscais", "visualizar"):
        flash("Voce nao tem permissao para visualizar documentos fiscais.", "danger")
        return redirect(url_for("main.acesso_negado"))

    sucesso, mensagem, documento = vincular_documento_ordem_compra(
        request.form.get("documento_id"),
        ordem,
        current_user,
    )

    if sucesso and documento:
        registrar_log(
            "suprimentos_oc_documento_fiscal_vinculado",
            f"Documento fiscal vinculado. Ordem ID: {ordem.id}. Documento ID: {documento.id}.",
        )

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))


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

    sucesso, mensagem = provisionar_financeiro_ordem_compra(ordem, usuario=current_user)

    if sucesso:
        registrar_log("suprimentos_oc_financeiro_gerado", f"Contas a pagar gerado. Ordem ID: {ordem.id}.")

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


@suprimentos_ordens_compra_bp.route(
    "/<int:ordem_id>/recebimentos/<int:recebimento_id>/editar",
    methods=["GET", "POST"],
)
@login_required
@module_permission_required("suprimentos", "ordens_compra", "editar")
def editar_recebimento(ordem_id, recebimento_id):
    ordem = buscar_por_id(SuprimentosOrdemCompra, ordem_id)
    recebimento = buscar_por_id(SuprimentosRecebimentoCompra, recebimento_id)

    if not ordem:
        flash("Ordem de compra nao encontrada.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.listar"))

    if not recebimento or recebimento.ordem_compra_id != ordem.id:
        flash("Recebimento nao encontrado para esta ordem.", "warning")
        return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))

    if request.method == "POST":
        sucesso, mensagem = editar_recebimento_ordem_compra(request.form, recebimento)

        if sucesso:
            registrar_log(
                "suprimentos_recebimento_compra_atualizado",
                f"Recebimento atualizado. ID: {recebimento.id}. Ordem ID: {ordem.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("suprimentos_ordens_compra.detalhes", ordem_id=ordem.id))

        flash(mensagem, "danger")

    return render_template(
        "suprimentos/ordens_compra/editar_recebimento.html",
        ordem=ordem,
        recebimento=recebimento,
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
