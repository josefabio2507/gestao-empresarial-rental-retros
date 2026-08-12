from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import SuprimentosCotacao, SuprimentosCotacaoProposta
from app.services.logs_service import registrar_log
from app.services.suprimentos_service import (
    STATUS_COTACAO_ABERTA,
    STATUS_COTACAO_APROVADA,
    STATUS_COTACAO_CANCELADA,
    STATUS_COTACAO_EM_APROVACAO,
    STATUS_COTACAO_ENCERRADA,
    STATUS_COTACAO_REPROVADA,
    aprovar_cotacao,
    aprovar_cotacao_por_link_publico,
    buscar_cotacoes,
    buscar_cotacao_por_token_aprovacao_publica,
    buscar_por_id,
    cancelar_cotacao,
    encerrar_cotacao,
    enviar_cotacao_para_aprovacao,
    enviar_email_solicitacao_cotacao_fornecedor,
    formatar_moeda_brl,
    formatar_decimal_brasil,
    fornecedor_disponivel_para_cotacao,
    fornecedores_disponiveis_para_cotacao,
    fornecedores_disponiveis_para_requisicao_item,
    gerar_link_whatsapp_aprovacao_cotacao,
    gerar_link_whatsapp_solicitacao_cotacao_fornecedor,
    montar_mapa_comparativo_cotacao,
    reprovar_cotacao,
    reprovar_cotacao_por_link_publico,
    requisicoes_disponiveis_para_cotacao,
    remover_proposta_cotacao,
    salvar_cotacao,
    salvar_proposta_cotacao,
    selecionar_proposta_vencedora,
    usuario_pode_aprovar_cotacao_alcada,
    valor_total_propostas_selecionadas,
)
from app.suprimentos.cotacoes import suprimentos_cotacoes_bp


STATUS_COTACOES = [
    STATUS_COTACAO_ABERTA,
    STATUS_COTACAO_EM_APROVACAO,
    STATUS_COTACAO_APROVADA,
    STATUS_COTACAO_REPROVADA,
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


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/selecionar-vencedor", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def selecionar_vencedor(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem, proposta = selecionar_proposta_vencedora(request.form, cotacao, current_user)

    if sucesso:
        registrar_log(
            "suprimentos_cotacao_vencedor_selecionado",
            f"Proposta vencedora selecionada. Cotacao ID: {cotacao.id}. Proposta ID: {proposta.id}.",
        )

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.mapa_comparativo", cotacao_id=cotacao.id))


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/enviar-aprovacao", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def enviar_aprovacao(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem = enviar_cotacao_para_aprovacao(cotacao, current_user)

    if sucesso:
        registrar_log("suprimentos_cotacao_enviada_aprovacao", f"Cotacao enviada para aprovacao. ID: {cotacao.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.mapa_comparativo", cotacao_id=cotacao.id))


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/aprovar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "aprovar")
def aprovar(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem = aprovar_cotacao(cotacao, current_user, request.form)

    if sucesso:
        registrar_log("suprimentos_cotacao_aprovada", f"Cotacao aprovada. ID: {cotacao.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.mapa_comparativo", cotacao_id=cotacao.id))


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/reprovar", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "aprovar")
def reprovar(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    sucesso, mensagem = reprovar_cotacao(cotacao, current_user, request.form)

    if sucesso:
        registrar_log("suprimentos_cotacao_reprovada", f"Cotacao reprovada. ID: {cotacao.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("suprimentos_cotacoes.mapa_comparativo", cotacao_id=cotacao.id))


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/whatsapp-aprovacao", methods=["GET", "POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def enviar_whatsapp_aprovacao(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    if request.method == "POST" and cotacao.pode_editar:
        sucesso_envio, mensagem_envio = enviar_cotacao_para_aprovacao(cotacao, current_user)

        if not sucesso_envio:
            flash(mensagem_envio, "danger")
            return redirect(url_for("suprimentos_cotacoes.mapa_comparativo", cotacao_id=cotacao.id))

        registrar_log(
            "suprimentos_cotacao_enviada_aprovacao",
            f"Cotacao enviada para aprovacao antes do WhatsApp. ID: {cotacao.id}.",
        )

    sucesso, mensagem, link = gerar_link_whatsapp_aprovacao_cotacao(cotacao)

    if not sucesso:
        flash(mensagem, "danger")
        return redirect(url_for("suprimentos_cotacoes.mapa_comparativo", cotacao_id=cotacao.id))

    registrar_log(
        "suprimentos_cotacao_whatsapp_aprovacao",
        f"WhatsApp de aprovacao gerado. Cotacao ID: {cotacao.id}.",
    )
    flash(mensagem, "success")
    return redirect(link)


@suprimentos_cotacoes_bp.route("/aprovacao/<token>", methods=["GET", "POST"])
def aprovacao_publica(token):
    cotacao, erro = buscar_cotacao_por_token_aprovacao_publica(token)

    if erro:
        return render_template(
            "suprimentos/cotacoes/aprovacao_publica.html",
            cotacao=None,
            erro=erro,
            token=token,
            mapa=None,
            formatar_moeda_brl=formatar_moeda_brl,
            formatar_decimal_brasil=formatar_decimal_brasil,
            valor_total_selecionado=None,
        )

    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "aprovar":
            sucesso, mensagem = aprovar_cotacao_por_link_publico(cotacao, request.form)
            acao_log = "suprimentos_cotacao_aprovada_link_publico"
        elif acao == "reprovar":
            sucesso, mensagem = reprovar_cotacao_por_link_publico(cotacao, request.form)
            acao_log = "suprimentos_cotacao_reprovada_link_publico"
        else:
            sucesso, mensagem = False, "Acao de aprovacao invalida."
            acao_log = None

        if sucesso and acao_log:
            registrar_log(
                acao_log,
                f"Cotacao decidida por link publico. ID: {cotacao.id}.",
                usuario=cotacao.aprovador,
            )

        flash(mensagem, "success" if sucesso else "danger")
        return render_template(
            "suprimentos/cotacoes/aprovacao_publica.html",
            cotacao=cotacao,
            erro=None if sucesso else mensagem,
            token=token,
            mapa=montar_mapa_comparativo_cotacao(cotacao),
            formatar_moeda_brl=formatar_moeda_brl,
            formatar_decimal_brasil=formatar_decimal_brasil,
            valor_total_selecionado=valor_total_propostas_selecionadas(cotacao),
            decisao_concluida=sucesso,
        )

    return render_template(
        "suprimentos/cotacoes/aprovacao_publica.html",
        cotacao=cotacao,
        erro=None,
        token=token,
        mapa=montar_mapa_comparativo_cotacao(cotacao),
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_decimal_brasil=formatar_decimal_brasil,
        valor_total_selecionado=valor_total_propostas_selecionadas(cotacao),
        decisao_concluida=False,
    )


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/fornecedor/whatsapp", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def enviar_whatsapp_fornecedor(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    fornecedor = fornecedor_disponivel_para_cotacao(cotacao, request.form.get("fornecedor_id"))
    sucesso, mensagem, link = gerar_link_whatsapp_solicitacao_cotacao_fornecedor(cotacao, fornecedor)

    if not sucesso:
        flash(mensagem, "danger")
        return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))

    registrar_log(
        "suprimentos_cotacao_whatsapp_fornecedor",
        f"WhatsApp de solicitacao de cotacao gerado. Cotacao ID: {cotacao.id}. Fornecedor ID: {fornecedor.id}.",
    )
    flash(mensagem, "success")
    return redirect(link)


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/fornecedor/email", methods=["POST"])
@login_required
@module_permission_required("suprimentos", "cotacoes", "editar")
def enviar_email_fornecedor(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    fornecedor = fornecedor_disponivel_para_cotacao(cotacao, request.form.get("fornecedor_id"))
    sucesso, mensagem, link_email = enviar_email_solicitacao_cotacao_fornecedor(cotacao, fornecedor)

    if sucesso:
        registrar_log(
            "suprimentos_cotacao_email_fornecedor",
            f"E-mail de solicitacao de cotacao gerado. Cotacao ID: {cotacao.id}. Fornecedor ID: {fornecedor.id}.",
        )
        if link_email:
            return render_template(
                "suprimentos/cotacoes/abrir_email.html",
                cotacao=cotacao,
                fornecedor=fornecedor,
                link_email=link_email,
                mensagem=mensagem,
            )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("suprimentos_cotacoes.detalhes", cotacao_id=cotacao.id))


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
        fornecedores_cotacao=fornecedores_disponiveis_para_cotacao(cotacao),
        formatar_moeda_brl=formatar_moeda_brl,
    )


@suprimentos_cotacoes_bp.route("/<int:cotacao_id>/mapa-comparativo")
@login_required
@module_permission_required("suprimentos", "cotacoes", "visualizar")
def mapa_comparativo(cotacao_id):
    cotacao = buscar_por_id(SuprimentosCotacao, cotacao_id)

    if not cotacao:
        flash("Cotacao nao encontrada.", "warning")
        return redirect(url_for("suprimentos_cotacoes.listar"))

    return render_template(
        "suprimentos/cotacoes/mapa_comparativo.html",
        cotacao=cotacao,
        mapa=montar_mapa_comparativo_cotacao(cotacao),
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_decimal_brasil=formatar_decimal_brasil,
        valor_total_selecionado=valor_total_propostas_selecionadas(cotacao),
        usuario_pode_aprovar=usuario_pode_aprovar_cotacao_alcada(cotacao, current_user),
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
