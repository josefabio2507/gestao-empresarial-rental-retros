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