from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from app.decorators import module_permission_required
from app.services.permissoes_service import usuario_tem_permissao
from app.departamento_pessoal.pedido_refeicoes.services import (
    TIPOS_CARDAPIO,
    buscar_restaurantes,
    buscar_restaurantes_ativos,
    buscar_restaurante_por_id,
    criar_restaurante,
    atualizar_restaurante,
    alterar_status_restaurante,
    buscar_itens_cardapio,
    buscar_item_cardapio_por_id,
    criar_item_cardapio,
    atualizar_item_cardapio,
    alterar_status_item_cardapio,
    formatar_telefone,
    formatar_moeda,
    buscar_equipes_ativas,
    buscar_pedidos,
    buscar_pedido_por_id,
    criar_pedido_refeicao,
    atualizar_pedido_refeicao,
    cancelar_pedido_refeicao,
    pedido_pode_ser_editado,
    formatar_data,
    formatar_status_pedido,
    STATUS_PEDIDO_ABERTO,
    buscar_colaboradores_do_pedido,
    buscar_itens_do_pedido,
    buscar_consumos_do_pedido,
    buscar_consumo_por_id,
    criar_consumo_refeicao,
    atualizar_consumo_refeicao,
    remover_consumo_refeicao,
    calcular_resumo_pedido,
    fechar_pedido_refeicao,
    gerar_link_whatsapp,
    registrar_envio_whatsapp,
    pedido_pode_ser_fechado,
    pedido_pode_enviar_whatsapp,
    status_whatsapp_pedido,
    STATUS_PEDIDO_FECHADO,
    STATUS_PEDIDO_ENVIADO,
    STATUS_PEDIDO_CANCELADO,
    pedido_enviado_com_correcao_permitida,
    pedido_pode_ser_cancelado,
)


pedido_refeicoes_bp = Blueprint("pedido_refeicoes", __name__)


@pedido_refeicoes_bp.route("/")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "visualizar")
def index():
    pode_criar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "criar",
    )

    return render_template(
        "departamento_pessoal/pedido_refeicoes/index.html",
        pode_criar=pode_criar,
    )


@pedido_refeicoes_bp.route("/restaurantes")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "visualizar")
def restaurantes():
    restaurantes_lista = buscar_restaurantes()

    pode_criar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "criar",
    )

    pode_editar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "excluir",
    )

    return render_template(
        "departamento_pessoal/pedido_refeicoes/restaurantes.html",
        restaurantes=restaurantes_lista,
        restaurante=None,
        modo="listar",
        formatar_telefone=formatar_telefone,
        pode_criar=pode_criar,
        pode_editar=pode_editar,
        pode_excluir=pode_excluir,
    )


@pedido_refeicoes_bp.route("/restaurantes/novo", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "criar")
def novo_restaurante():
    if request.method == "POST":
        sucesso, mensagem = criar_restaurante(
            nome=request.form.get("nome", ""),
            telefone=request.form.get("telefone", ""),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.restaurantes"))

        flash(mensagem, "danger")

    restaurantes_lista = buscar_restaurantes()

    return render_template(
        "departamento_pessoal/pedido_refeicoes/restaurantes.html",
        restaurantes=restaurantes_lista,
        restaurante=None,
        modo="novo",
        formatar_telefone=formatar_telefone,
        pode_criar=True,
        pode_editar=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "editar"),
        pode_excluir=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "excluir"),
    )


@pedido_refeicoes_bp.route("/restaurantes/<int:restaurante_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "editar")
def editar_restaurante(restaurante_id):
    restaurante = buscar_restaurante_por_id(restaurante_id)

    if not restaurante:
        flash("Restaurante não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.restaurantes"))

    if request.method == "POST":
        sucesso, mensagem = atualizar_restaurante(
            restaurante=restaurante,
            nome=request.form.get("nome", ""),
            telefone=request.form.get("telefone", ""),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.restaurantes"))

        flash(mensagem, "danger")

    restaurantes_lista = buscar_restaurantes()

    return render_template(
        "departamento_pessoal/pedido_refeicoes/restaurantes.html",
        restaurantes=restaurantes_lista,
        restaurante=restaurante,
        modo="editar",
        formatar_telefone=formatar_telefone,
        pode_criar=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "criar"),
        pode_editar=True,
        pode_excluir=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "excluir"),
    )


@pedido_refeicoes_bp.route("/restaurantes/<int:restaurante_id>/status")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "excluir")
def alterar_status_restaurante_rota(restaurante_id):
    restaurante = buscar_restaurante_por_id(restaurante_id)

    if not restaurante:
        flash("Restaurante não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.restaurantes"))

    sucesso, mensagem = alterar_status_restaurante(restaurante)

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.restaurantes"))


@pedido_refeicoes_bp.route("/cardapio")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "visualizar")
def cardapio():
    restaurante_id = request.args.get("restaurante_id", "").strip()
    tipo = request.args.get("tipo", "").strip()

    itens = buscar_itens_cardapio(
        restaurante_id=restaurante_id if restaurante_id else None,
        tipo=tipo if tipo else None,
    )

    restaurantes_ativos = buscar_restaurantes_ativos()

    pode_criar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "criar",
    )

    pode_editar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "excluir",
    )

    return render_template(
        "departamento_pessoal/pedido_refeicoes/cardapios.html",
        itens=itens,
        item=None,
        restaurantes=restaurantes_ativos,
        tipos=TIPOS_CARDAPIO,
        modo="listar",
        restaurante_id_selecionado=restaurante_id,
        tipo_selecionado=tipo,
        formatar_moeda=formatar_moeda,
        pode_criar=pode_criar,
        pode_editar=pode_editar,
        pode_excluir=pode_excluir,
    )


@pedido_refeicoes_bp.route("/cardapio/novo", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "criar")
def novo_item_cardapio():
    restaurantes_ativos = buscar_restaurantes_ativos()

    if request.method == "POST":
        sucesso, mensagem = criar_item_cardapio(
            restaurante_id=request.form.get("restaurante_id"),
            tipo=request.form.get("tipo", ""),
            nome=request.form.get("nome", ""),
            preco=request.form.get("preco", ""),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.cardapio"))

        flash(mensagem, "danger")

    itens = buscar_itens_cardapio()

    return render_template(
        "departamento_pessoal/pedido_refeicoes/cardapios.html",
        itens=itens,
        item=None,
        restaurantes=restaurantes_ativos,
        tipos=TIPOS_CARDAPIO,
        modo="novo",
        restaurante_id_selecionado="",
        tipo_selecionado="",
        formatar_moeda=formatar_moeda,
        pode_criar=True,
        pode_editar=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "editar"),
        pode_excluir=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "excluir"),
    )


@pedido_refeicoes_bp.route("/cardapio/<int:item_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "editar")
def editar_item_cardapio(item_id):
    item = buscar_item_cardapio_por_id(item_id)

    if not item:
        flash("Item de cardápio não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.cardapio"))

    restaurantes_ativos = buscar_restaurantes_ativos()

    if request.method == "POST":
        sucesso, mensagem = atualizar_item_cardapio(
            item=item,
            restaurante_id=request.form.get("restaurante_id"),
            tipo=request.form.get("tipo", ""),
            nome=request.form.get("nome", ""),
            preco=request.form.get("preco", ""),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.cardapio"))

        flash(mensagem, "danger")

    itens = buscar_itens_cardapio()

    return render_template(
        "departamento_pessoal/pedido_refeicoes/cardapios.html",
        itens=itens,
        item=item,
        restaurantes=restaurantes_ativos,
        tipos=TIPOS_CARDAPIO,
        modo="editar",
        restaurante_id_selecionado="",
        tipo_selecionado="",
        formatar_moeda=formatar_moeda,
        pode_criar=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "criar"),
        pode_editar=True,
        pode_excluir=usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_refeicoes", "excluir"),
    )


@pedido_refeicoes_bp.route("/cardapio/<int:item_id>/status")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "excluir")
def alterar_status_item_cardapio_rota(item_id):
    item = buscar_item_cardapio_por_id(item_id)

    if not item:
        flash("Item de cardápio não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.cardapio"))

    sucesso, mensagem = alterar_status_item_cardapio(item)

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.cardapio"))

@pedido_refeicoes_bp.route("/pedidos")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "visualizar")
def pedidos():
    pedidos_lista = buscar_pedidos()

    pode_criar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "criar",
    )

    pode_editar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "excluir",
    )

    pode_aprovar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "aprovar",
    )

    pode_exportar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "exportar",
    )

    return render_template(
        "departamento_pessoal/pedido_refeicoes/pedidos.html",
        pedidos=pedidos_lista,
        pode_criar=pode_criar,
        pode_editar=pode_editar,
        pode_excluir=pode_excluir,
        pedido_pode_ser_editado=pedido_pode_ser_editado,
        formatar_data=formatar_data,
        pode_aprovar=pode_aprovar,
        pode_exportar=pode_exportar,
        pedido_pode_ser_fechado=pedido_pode_ser_fechado,
        pedido_pode_enviar_whatsapp=pedido_pode_enviar_whatsapp,
        status_whatsapp_pedido=status_whatsapp_pedido,
        pedido_enviado_com_correcao_permitida=pedido_enviado_com_correcao_permitida,
        pedido_pode_ser_cancelado=pedido_pode_ser_cancelado,
    )


@pedido_refeicoes_bp.route("/pedidos/novo", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "criar")
def novo_pedido():
    equipes = buscar_equipes_ativas()
    restaurantes = buscar_restaurantes_ativos()

    if request.method == "POST":
        sucesso, mensagem, pedido = criar_pedido_refeicao(
            equipe_id=request.form.get("equipe_id"),
            restaurante_id=request.form.get("restaurante_id"),
            data_pedido=request.form.get("data_pedido"),
            observacao=request.form.get("observacao", ""),
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/pedido_refeicoes/pedido_form.html",
        pedido=None,
        equipes=equipes,
        restaurantes=restaurantes,
        modo="novo",
    )


@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "visualizar")
def detalhes_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    pode_editar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "excluir",
    )

    pode_aprovar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "aprovar",
    )

    pode_exportar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "exportar",
    )

    consumos = buscar_consumos_do_pedido(pedido)
    resumo_pedido, total_geral = calcular_resumo_pedido(pedido)

    pode_criar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "pedido_refeicoes",
        "criar",
    )

    return render_template(
        "departamento_pessoal/pedido_refeicoes/pedido_detalhes.html",
        pedido=pedido,
        pode_editar=pode_editar,
        pode_excluir=pode_excluir,
        pedido_pode_ser_editado=pedido_pode_ser_editado,
        formatar_data=formatar_data,
        formatar_telefone=formatar_telefone,
        consumos=consumos,
        resumo_pedido=resumo_pedido,
        total_geral=total_geral,
        pode_criar=pode_criar,
        formatar_moeda=formatar_moeda,
        pode_aprovar=pode_aprovar,
        pode_exportar=pode_exportar,
        pedido_pode_ser_fechado=pedido_pode_ser_fechado,
        pedido_pode_enviar_whatsapp=pedido_pode_enviar_whatsapp,
        pedido_enviado_com_correcao_permitida=pedido_enviado_com_correcao_permitida,
        pedido_pode_ser_cancelado=pedido_pode_ser_cancelado,
    )

@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "editar")
def editar_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    if not pedido_pode_ser_editado(pedido):
        flash("Este pedido não permite mais alterações.", "danger")
        return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

    equipes = buscar_equipes_ativas()
    restaurantes = buscar_restaurantes_ativos()

    if request.method == "POST":
        sucesso, mensagem = atualizar_pedido_refeicao(
            pedido=pedido,
            equipe_id=request.form.get("equipe_id"),
            restaurante_id=request.form.get("restaurante_id"),
            data_pedido=request.form.get("data_pedido"),
            observacao=request.form.get("observacao", ""),
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/pedido_refeicoes/pedido_form.html",
        pedido=pedido,
        equipes=equipes,
        restaurantes=restaurantes,
        modo="editar",
    )


@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/cancelar")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "excluir")
def cancelar_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    sucesso, mensagem = cancelar_pedido_refeicao(pedido)

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/consumos/novo", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "criar")
def novo_consumo(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    if not pedido_pode_ser_editado(pedido):
        flash("Este pedido não permite mais alterações de consumo.", "danger")
        return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

    colaboradores = buscar_colaboradores_do_pedido(pedido)
    itens = buscar_itens_do_pedido(pedido)

    if request.method == "POST":
        sucesso, mensagem = criar_consumo_refeicao(
            pedido=pedido,
            colaborador_id=request.form.get("colaborador_id"),
            item_cardapio_id=request.form.get("item_cardapio_id"),
            quantidade=request.form.get("quantidade"),
            observacao=request.form.get("observacao", ""),
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/pedido_refeicoes/consumo_form.html",
        pedido=pedido,
        consumo=None,
        colaboradores=colaboradores,
        itens=itens,
        modo="novo",
        formatar_moeda=formatar_moeda,
    )


@pedido_refeicoes_bp.route("/consumos/<int:consumo_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "editar")
def editar_consumo(consumo_id):
    consumo = buscar_consumo_por_id(consumo_id)

    if not consumo:
        flash("Consumo não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    pedido = consumo.pedido

    if not pedido_pode_ser_editado(pedido):
        flash("Somente pedidos em aberto podem ter consumo alterado.", "danger")
        return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

    colaboradores = buscar_colaboradores_do_pedido(pedido)
    itens = buscar_itens_do_pedido(pedido)

    if request.method == "POST":
        sucesso, mensagem = atualizar_consumo_refeicao(
            consumo=consumo,
            colaborador_id=request.form.get("colaborador_id"),
            item_cardapio_id=request.form.get("item_cardapio_id"),
            quantidade=request.form.get("quantidade"),
            observacao=request.form.get("observacao", ""),
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/pedido_refeicoes/consumo_form.html",
        pedido=pedido,
        consumo=consumo,
        colaboradores=colaboradores,
        itens=itens,
        modo="editar",
        formatar_moeda=formatar_moeda,
    )


@pedido_refeicoes_bp.route("/consumos/<int:consumo_id>/remover")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "excluir")
def remover_consumo(consumo_id):
    consumo = buscar_consumo_por_id(consumo_id)

    if not consumo:
        flash("Consumo não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    pedido_id = consumo.pedido_id

    sucesso, mensagem = remover_consumo_refeicao(consumo)

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido_id))

@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/fechar")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "aprovar")
def fechar_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    sucesso, mensagem = fechar_pedido_refeicao(pedido)

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))


@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/whatsapp")
@module_permission_required("departamento_pessoal", "pedido_refeicoes", "exportar")
def enviar_whatsapp(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    sucesso, mensagem, link = gerar_link_whatsapp(pedido)

    if not sucesso:
        flash(mensagem, "danger")
        return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

    sucesso_registro, mensagem_registro = registrar_envio_whatsapp(pedido)

    if not sucesso_registro:
        flash(mensagem_registro, "danger")
        return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

    flash(mensagem_registro, "success")
    return redirect(link)