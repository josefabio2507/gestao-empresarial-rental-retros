from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import current_user, login_required
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


from app.decorators import module_permission_required
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.departamento_pessoal.pedido_refeicoes.services import (

    TIPOS_CARDAPIO,
    DIAS_SEMANA_CARDAPIO,
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
    criar_consumos_refeicao_bebida,
    atualizar_consumos_refeicao_bebida,
    buscar_consumos_relacionados,
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
    montar_relatorio_refeicoes,
    status_relatorio_opcoes,
)


pedido_refeicoes_bp = Blueprint("pedido_refeicoes", __name__)

DEPARTAMENTO_PESSOAL_SLUG = "departamento_pessoal"
MODULO_REFEICOES_RESTAURANTES = "pedido-refeicoes-restaurantes"
MODULO_REFEICOES_CARDAPIO = "pedido-refeicoes-cardapio"
MODULO_REFEICOES_PEDIDOS = "pedido-refeicoes-pedidos"
MODULO_REFEICOES_RELATORIOS = "pedido-refeicoes-relatorios"

SUBMODULOS_REFEICOES = [
    MODULO_REFEICOES_RESTAURANTES,
    MODULO_REFEICOES_CARDAPIO,
    MODULO_REFEICOES_PEDIDOS,
    MODULO_REFEICOES_RELATORIOS,
]

STATUS_FILTRO_NOVO_PEDIDO = "novo_pedido"
STATUS_FILTRO_TODOS = "todos"

STATUS_PEDIDOS_FILTRO_OPCOES = [
    {"valor": STATUS_FILTRO_NOVO_PEDIDO, "rotulo": "Novo Pedido"},
    {"valor": STATUS_PEDIDO_ABERTO, "rotulo": STATUS_PEDIDO_ABERTO},
    {"valor": STATUS_PEDIDO_FECHADO, "rotulo": STATUS_PEDIDO_FECHADO},
    {"valor": STATUS_PEDIDO_ENVIADO, "rotulo": STATUS_PEDIDO_ENVIADO},
    {"valor": STATUS_PEDIDO_CANCELADO, "rotulo": STATUS_PEDIDO_CANCELADO},
    {"valor": STATUS_FILTRO_TODOS, "rotulo": "Todos"},
]


def pode_acessar_submodulo_refeicoes(modulo_slug, acao="visualizar"):
    return usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        modulo_slug,
        acao,
    )


def pode_visualizar_algum_submodulo_refeicoes():
    return any(
        pode_acessar_submodulo_refeicoes(modulo_slug, "visualizar")
        for modulo_slug in SUBMODULOS_REFEICOES
    )


def separar_itens_consumo(itens):
    refeicoes = [item for item in itens if item.tipo == "Refeição"]
    bebidas = [item for item in itens if item.tipo == "Bebida"]

    return refeicoes, bebidas


@pedido_refeicoes_bp.route("/")
@login_required
def index():
    if not pode_visualizar_algum_submodulo_refeicoes():
        flash("Você não tem permissão para acessar esta área.", "danger")
        return redirect(url_for("main.acesso_negado"))

    pode_visualizar_restaurantes = pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_RESTAURANTES)
    pode_visualizar_cardapio = pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_CARDAPIO)
    pode_visualizar_pedidos = pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_PEDIDOS)
    pode_visualizar_relatorios = pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_RELATORIOS)

    return render_template(
        "departamento_pessoal/pedido_refeicoes/index.html",
        pode_visualizar_restaurantes=pode_visualizar_restaurantes,
        pode_visualizar_cardapio=pode_visualizar_cardapio,
        pode_visualizar_pedidos=pode_visualizar_pedidos,
        pode_visualizar_relatorios=pode_visualizar_relatorios,
    )
    

@pedido_refeicoes_bp.route("/restaurantes")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_RESTAURANTES, "visualizar")
def restaurantes():
    restaurantes_lista = buscar_restaurantes()

    pode_criar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_RESTAURANTES,
        "criar",
    )

    pode_editar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_RESTAURANTES,
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_RESTAURANTES,
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
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_RESTAURANTES, "criar")
def novo_restaurante():
    if request.method == "POST":
        sucesso, mensagem = criar_restaurante(
            nome=request.form.get("nome", ""),
            telefone=request.form.get("telefone", ""),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            registrar_log(
                "restaurante_criado",
                "Restaurante criado.",
            )
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
        pode_editar=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_RESTAURANTES, "editar"),
        pode_excluir=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_RESTAURANTES, "excluir"),
    )


@pedido_refeicoes_bp.route("/restaurantes/<int:restaurante_id>/editar", methods=["GET", "POST"])
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_RESTAURANTES, "editar")
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
            registrar_log(
                "restaurante_atualizado",
                f"Restaurante atualizado. ID: {restaurante.id}.",
            )
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
        pode_criar=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_RESTAURANTES, "criar"),
        pode_editar=True,
        pode_excluir=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_RESTAURANTES, "excluir"),
    )


@pedido_refeicoes_bp.route("/restaurantes/<int:restaurante_id>/status")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_RESTAURANTES, "excluir")
def alterar_status_restaurante_rota(restaurante_id):
    restaurante = buscar_restaurante_por_id(restaurante_id)

    if not restaurante:
        flash("Restaurante não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.restaurantes"))

    sucesso, mensagem = alterar_status_restaurante(restaurante)

    if sucesso:
        registrar_log(
            "restaurante_status_alterado",
            f"Restaurante {'ativado' if restaurante.ativo else 'inativado'}. ID: {restaurante.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.restaurantes"))


@pedido_refeicoes_bp.route("/cardapio")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_CARDAPIO, "visualizar")
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
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_CARDAPIO,
        "criar",
    )

    pode_editar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_CARDAPIO,
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_CARDAPIO,
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
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_CARDAPIO, "criar")
def novo_item_cardapio():
    restaurantes_ativos = buscar_restaurantes_ativos()

    if request.method == "POST":
        sucesso, mensagem = criar_item_cardapio(
            restaurante_id=request.form.get("restaurante_id"),
            tipo=request.form.get("tipo", ""),
            nome=request.form.get("nome", ""),
            preco=request.form.get("preco", ""),
            dia_semana=request.form.get("dia_semana", ""),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            registrar_log(
                "item_cardapio_criado",
                "Item de cardapio criado.",
            )
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
        dias_semana=DIAS_SEMANA_CARDAPIO,
        modo="novo",
        restaurante_id_selecionado="",
        tipo_selecionado="",
        formatar_moeda=formatar_moeda,
        pode_criar=True,
        pode_editar=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_CARDAPIO, "editar"),
        pode_excluir=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_CARDAPIO, "excluir"),
    )


@pedido_refeicoes_bp.route("/cardapio/<int:item_id>/editar", methods=["GET", "POST"])
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_CARDAPIO, "editar")
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
            dia_semana=request.form.get("dia_semana", ""),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            registrar_log(
                "item_cardapio_atualizado",
                f"Item de cardapio atualizado. ID: {item.id}.",
            )
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
        dias_semana=DIAS_SEMANA_CARDAPIO,
        modo="editar",
        restaurante_id_selecionado="",
        tipo_selecionado="",
        formatar_moeda=formatar_moeda,
        pode_criar=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_CARDAPIO, "criar"),
        pode_editar=True,
        pode_excluir=pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_CARDAPIO, "excluir"),
    )


@pedido_refeicoes_bp.route("/cardapio/<int:item_id>/status")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_CARDAPIO, "excluir")
def alterar_status_item_cardapio_rota(item_id):
    item = buscar_item_cardapio_por_id(item_id)

    if not item:
        flash("Item de cardápio não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.cardapio"))

    sucesso, mensagem = alterar_status_item_cardapio(item)

    if sucesso:
        registrar_log(
            "item_cardapio_status_alterado",
            f"Item de cardapio {'ativado' if item.ativo else 'inativado'}. ID: {item.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.cardapio"))

@pedido_refeicoes_bp.route("/pedidos")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "visualizar")
def pedidos():
    status_filtro = request.args.get("status", STATUS_FILTRO_NOVO_PEDIDO).strip()
    status_opcoes_validas = {opcao["valor"] for opcao in STATUS_PEDIDOS_FILTRO_OPCOES}

    if status_filtro not in status_opcoes_validas:
        status_filtro = STATUS_FILTRO_NOVO_PEDIDO

    if status_filtro == STATUS_FILTRO_NOVO_PEDIDO:
        pedidos_lista = []
    elif status_filtro == STATUS_FILTRO_TODOS:
        pedidos_lista = buscar_pedidos()
    else:
        pedidos_lista = buscar_pedidos(status=status_filtro)

    pode_criar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
        "criar",
    )

    pode_editar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
        "excluir",
    )

    pode_aprovar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
        "aprovar",
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
        pode_enviar_whatsapp=pode_aprovar,
        pedido_pode_ser_fechado=pedido_pode_ser_fechado,
        pedido_pode_enviar_whatsapp=pedido_pode_enviar_whatsapp,
        status_whatsapp_pedido=status_whatsapp_pedido,
        pedido_enviado_com_correcao_permitida=pedido_enviado_com_correcao_permitida,
        pedido_pode_ser_cancelado=pedido_pode_ser_cancelado,
        status_filtro=status_filtro,
        status_opcoes=STATUS_PEDIDOS_FILTRO_OPCOES,
        status_filtro_novo_pedido=STATUS_FILTRO_NOVO_PEDIDO,
    )


@pedido_refeicoes_bp.route("/pedidos/novo", methods=["GET", "POST"])
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "criar")
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
            registrar_log(
                "pedido_refeicao_criado",
                f"Pedido de refeicao criado. Pedido ID: {pedido.id}.",
            )
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
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "visualizar")
def detalhes_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    pode_editar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
        "excluir",
    )

    pode_aprovar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
        "aprovar",
    )

    consumos = buscar_consumos_do_pedido(pedido)
    resumo_pedido, total_geral = calcular_resumo_pedido(pedido)

    pode_criar = usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_PESSOAL_SLUG,
        MODULO_REFEICOES_PEDIDOS,
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
        pode_enviar_whatsapp=pode_aprovar,
        pedido_pode_ser_fechado=pedido_pode_ser_fechado,
        pedido_pode_enviar_whatsapp=pedido_pode_enviar_whatsapp,
        pedido_enviado_com_correcao_permitida=pedido_enviado_com_correcao_permitida,
        pedido_pode_ser_cancelado=pedido_pode_ser_cancelado,
    )

@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/editar", methods=["GET", "POST"])
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "editar")
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
            registrar_log(
                "pedido_refeicao_atualizado",
                f"Pedido de refeicao atualizado. Pedido ID: {pedido.id}.",
            )
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
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "excluir")
def cancelar_pedido(pedido_id):
    pedido = buscar_pedido_por_id(pedido_id)

    if not pedido:
        flash("Pedido não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    sucesso, mensagem = cancelar_pedido_refeicao(pedido)

    if sucesso:
        registrar_log(
            "pedido_refeicao_cancelado",
            f"Pedido de refeicao cancelado. Pedido ID: {pedido.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/consumos/novo", methods=["GET", "POST"])
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "criar")
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
    refeicoes, bebidas = separar_itens_consumo(itens)

    if request.method == "POST":
        sucesso, mensagem = criar_consumos_refeicao_bebida(
            pedido=pedido,
            colaborador_id=request.form.get("colaborador_id"),
            refeicao_id=request.form.get("refeicao_id"),
            bebida_id=request.form.get("bebida_id"),
            quantidade_refeicao=request.form.get("quantidade_refeicao"),
            quantidade_bebida=request.form.get("quantidade_bebida"),
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
        refeicoes=refeicoes,
        bebidas=bebidas,
        modo="novo",
        formatar_moeda=formatar_moeda,
    )


@pedido_refeicoes_bp.route("/consumos/<int:consumo_id>/editar", methods=["GET", "POST"])
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "editar")
def editar_consumo(consumo_id):
    consumo = buscar_consumo_por_id(consumo_id)

    if not consumo:
        flash("Consumo não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    pedido = consumo.pedido

    if not pedido_pode_ser_editado(pedido):
        flash("Este pedido não permite mais alterações de consumo.", "danger")
        return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido.id))

    colaboradores = buscar_colaboradores_do_pedido(pedido)
    consumo_refeicao, consumo_bebida = buscar_consumos_relacionados(consumo)
    itens_incluir = []

    if consumo_refeicao:
        itens_incluir.append(consumo_refeicao.item_cardapio_id)

    if consumo_bebida:
        itens_incluir.append(consumo_bebida.item_cardapio_id)

    itens = buscar_itens_do_pedido(pedido, incluir_item_ids=itens_incluir)
    refeicoes, bebidas = separar_itens_consumo(itens)

    if request.method == "POST":
        sucesso, mensagem = atualizar_consumos_refeicao_bebida(
            consumo_referencia=consumo,
            colaborador_id=request.form.get("colaborador_id"),
            refeicao_id=request.form.get("refeicao_id"),
            bebida_id=request.form.get("bebida_id"),
            quantidade_refeicao=request.form.get("quantidade_refeicao"),
            quantidade_bebida=request.form.get("quantidade_bebida"),
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
        consumo_refeicao=consumo_refeicao,
        consumo_bebida=consumo_bebida,
        colaboradores=colaboradores,
        itens=itens,
        refeicoes=refeicoes,
        bebidas=bebidas,
        modo="editar",
        formatar_moeda=formatar_moeda,
    )


@pedido_refeicoes_bp.route("/consumos/<int:consumo_id>/remover")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "excluir")
def remover_consumo(consumo_id):
    consumo = buscar_consumo_por_id(consumo_id)

    if not consumo:
        flash("Consumo não encontrado.", "warning")
        return redirect(url_for("pedido_refeicoes.pedidos"))

    pedido_id = consumo.pedido_id

    sucesso, mensagem = remover_consumo_refeicao(consumo)

    if sucesso:
        registrar_log(
            "pedido_refeicao_fechado",
            f"Pedido de refeicao fechado. Pedido ID: {pedido.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("pedido_refeicoes.detalhes_pedido", pedido_id=pedido_id))

@pedido_refeicoes_bp.route("/pedidos/<int:pedido_id>/fechar")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "aprovar")
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
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_PEDIDOS, "aprovar")
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
    acao = (
        "pedido_refeicao_reenviado_whatsapp"
        if (pedido.quantidade_envios or 0) > 1
        else "pedido_refeicao_enviado_whatsapp"
    )
    registrar_log(
        acao,
        f"Pedido de refeicao enviado via WhatsApp. Pedido: {pedido.numero_pedido or pedido.id}.",
    )
    return redirect(link)

def gerar_pdf_relatorio_refeicoes(relatorio, filtros):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()
    elementos = []

    titulo = Paragraph("<b>Relatório de Pedido de Refeições</b>", styles["Title"])
    elementos.append(titulo)
    elementos.append(Spacer(1, 10))

    cabecalho = [
        f"Empresa: Rental Retros",
        f"Período: {filtros.get('data_inicial')} a {filtros.get('data_final')}",
        f"Agrupamento: {relatorio['agrupamento_label']}",
        f"Status: {filtros.get('status')}",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
    ]

    for linha in cabecalho:
        elementos.append(Paragraph(linha, styles["Normal"]))

    elementos.append(Spacer(1, 16))

    for grupo in relatorio["grupos"]:
        elementos.append(Paragraph(f"<b>{grupo['tipo']}: {grupo['titulo']}</b>", styles["Heading2"]))
        elementos.append(Spacer(1, 8))

        tabela_pedidos = [
            ["Número", "Data", "Equipe", "Restaurante", "Status", "Envios", "Total"]
        ]

        for pedido in grupo["pedidos"]:
            tabela_pedidos.append([
                pedido["numero"],
                formatar_data(pedido["data"]),
                pedido["equipe"],
                pedido["restaurante"],
                pedido["status"],
                str(pedido["quantidade_envios"]),
                formatar_moeda(pedido["total"]),
            ])

        tabela = Table(tabela_pedidos, repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elementos.append(tabela)
        elementos.append(Spacer(1, 10))

        elementos.append(Paragraph("<b>Resumo por item</b>", styles["Heading3"]))

        tabela_resumo = [
            ["Tipo", "Item", "Quantidade", "Total"]
        ]

        for item in grupo["resumo_itens"]:
            tabela_resumo.append([
                item["tipo"],
                item["nome"],
                str(item["quantidade"]),
                formatar_moeda(item["total"]),
            ])

        tabela2 = Table(tabela_resumo, repeatRows=1)
        tabela2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        elementos.append(tabela2)
        elementos.append(Spacer(1, 8))

        elementos.append(Paragraph(
            f"<b>Total do grupo:</b> {formatar_moeda(grupo['total_grupo'])}",
            styles["Normal"],
        ))
        elementos.append(Spacer(1, 18))

    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph(
        f"<b>Total geral:</b> {formatar_moeda(relatorio['total_geral'])}",
        styles["Heading2"],
    ))

    doc.build(elementos)

    buffer.seek(0)
    return buffer

@pedido_refeicoes_bp.route("/relatorios")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_RELATORIOS, "visualizar")
def relatorios():
    data_inicial = request.args.get("data_inicial", "").strip()
    data_final = request.args.get("data_final", "").strip()
    equipe_id = request.args.get("equipe_id", "").strip()
    restaurante_id = request.args.get("restaurante_id", "").strip()
    status = request.args.get("status", "Enviado").strip() or "Enviado"
    agrupamento = request.args.get("agrupamento", "restaurante").strip() or "restaurante"

    equipes = buscar_equipes_ativas()
    restaurantes = buscar_restaurantes_ativos()
    status_opcoes = status_relatorio_opcoes()
    pode_exportar = pode_acessar_submodulo_refeicoes(MODULO_REFEICOES_RELATORIOS, "exportar")

    relatorio = None
    filtros_aplicados = bool(request.args)

    if filtros_aplicados:
        if not data_inicial or not data_final:
            flash("Informar data inicial e data final.", "danger")
        else:
            relatorio = montar_relatorio_refeicoes(
                data_inicial=data_inicial,
                data_final=data_final,
                equipe_id=equipe_id if equipe_id else None,
                restaurante_id=restaurante_id if restaurante_id else None,
                status=status,
                agrupamento=agrupamento,
            )

    return render_template(
        "departamento_pessoal/pedido_refeicoes/relatorios.html",
        relatorio=relatorio,
        equipes=equipes,
        restaurantes=restaurantes,
        status_opcoes=status_opcoes,
        filtros={
            "data_inicial": data_inicial,
            "data_final": data_final,
            "equipe_id": equipe_id,
            "restaurante_id": restaurante_id,
            "status": status,
            "agrupamento": agrupamento,
        },
        formatar_data=formatar_data,
        formatar_moeda=formatar_moeda,
        pode_exportar=pode_exportar,
    )

@pedido_refeicoes_bp.route("/relatorios/pdf")
@module_permission_required(DEPARTAMENTO_PESSOAL_SLUG, MODULO_REFEICOES_RELATORIOS, "exportar")
def relatorios_pdf():
    data_inicial = request.args.get("data_inicial", "").strip()
    data_final = request.args.get("data_final", "").strip()
    equipe_id = request.args.get("equipe_id", "").strip()
    restaurante_id = request.args.get("restaurante_id", "").strip()
    status = request.args.get("status", "Enviado").strip() or "Enviado"
    agrupamento = request.args.get("agrupamento", "restaurante").strip() or "restaurante"

    if not data_inicial or not data_final:
        flash("Informar data inicial e data final.", "danger")
        return redirect(url_for("pedido_refeicoes.relatorios"))

    relatorio = montar_relatorio_refeicoes(
        data_inicial=data_inicial,
        data_final=data_final,
        equipe_id=equipe_id if equipe_id else None,
        restaurante_id=restaurante_id if restaurante_id else None,
        status=status,
        agrupamento=agrupamento,
    )

    pdf_buffer = gerar_pdf_relatorio_refeicoes(
        relatorio=relatorio,
        filtros={
            "data_inicial": data_inicial,
            "data_final": data_final,
            "status": status,
            "agrupamento": agrupamento,
        },
    )

    nome_arquivo = f"relatorio_pedidos_refeicoes_{data_inicial}_a_{data_final}.pdf"
    registrar_log(
        "relatorio_refeicoes_pdf_exportado",
        "Relatorio de refeicoes exportado em PDF.",
    )

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=nome_arquivo,
        mimetype="application/pdf",
    )
