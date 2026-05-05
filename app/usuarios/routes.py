from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.decorators import admin_required
from app.models import Usuario
from app.services.logs_service import registrar_log
from app.services.usuarios_service import (
    buscar_usuarios,
    buscar_usuario_por_id,
    buscar_niveis_ativos,
    criar_usuario,
    atualizar_usuario,
    alterar_status_usuario,
)


usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.route("/")
@login_required
@admin_required
def listar_usuarios():
    usuarios = buscar_usuarios()
    return render_template("usuarios/listar.html", usuarios=usuarios)


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo_usuario():
    niveis = buscar_niveis_ativos()

    if request.method == "POST":
        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        senha = request.form.get("senha", "")
        nivel_acesso_id = request.form.get("nivel_acesso_id")
        ativo = request.form.get("ativo") == "on"

        sucesso, mensagem = criar_usuario(
            nome=nome,
            email=email,
            senha=senha,
            nivel_acesso_id=nivel_acesso_id,
            ativo=ativo,
        )

        if sucesso:
            usuario_criado = Usuario.query.filter_by(email=email.strip().lower()).first()
            descricao = "Usuario criado."

            if usuario_criado:
                descricao = f"Usuario criado. ID: {usuario_criado.id}."

            registrar_log("usuario_criado", descricao)
            flash(mensagem, "success")
            return redirect(url_for("usuarios.listar_usuarios"))

        flash(mensagem, "danger")

    return render_template(
        "usuarios/form.html",
        usuario=None,
        niveis=niveis,
        modo="novo",
    )


@usuarios_bp.route("/<int:usuario_id>")
@login_required
@admin_required
def detalhes_usuario(usuario_id):
    usuario = buscar_usuario_por_id(usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("usuarios.listar_usuarios"))

    return render_template("usuarios/detalhes.html", usuario=usuario)


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_usuario(usuario_id):
    usuario = buscar_usuario_por_id(usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("usuarios.listar_usuarios"))

    niveis = buscar_niveis_ativos()

    if request.method == "POST":
        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        nivel_acesso_id = request.form.get("nivel_acesso_id")
        ativo = request.form.get("ativo") == "on"
        nova_senha = request.form.get("nova_senha", "").strip()

        sucesso, mensagem = atualizar_usuario(
            usuario=usuario,
            nome=nome,
            email=email,
            nivel_acesso_id=nivel_acesso_id,
            ativo=ativo,
            nova_senha=nova_senha,
        )

        if sucesso:
            descricao = f"Usuario atualizado. ID: {usuario.id}."

            if nova_senha:
                descricao += " Senha redefinida pelo administrador."

            registrar_log("usuario_atualizado", descricao)
            flash(mensagem, "success")
            return redirect(url_for("usuarios.listar_usuarios"))

        flash(mensagem, "danger")

    return render_template(
        "usuarios/form.html",
        usuario=usuario,
        niveis=niveis,
        modo="editar",
    )


@usuarios_bp.route("/<int:usuario_id>/status")
@login_required
@admin_required
def alterar_status(usuario_id):
    usuario = buscar_usuario_por_id(usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("usuarios.listar_usuarios"))

    sucesso, mensagem = alterar_status_usuario(usuario, current_user)

    if sucesso:
        acao = "usuario_ativado" if usuario.ativo else "usuario_inativado"
        registrar_log(
            acao,
            f"Usuario {'ativado' if usuario.ativo else 'inativado'}. ID: {usuario.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("usuarios.listar_usuarios"))
