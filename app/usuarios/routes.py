from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.decorators import admin_required
from app.models import Usuario
from app.services.logs_service import registrar_log
from app.services.usuarios_service import (
    buscar_usuarios_por_nome,
    buscar_usuario_por_id,
    buscar_niveis_ativos,
    buscar_colaboradores_ativos_para_vinculo,
    criar_usuario,
    atualizar_usuario,
    alterar_status_usuario,
)


usuarios_bp = Blueprint("usuarios", __name__)


def incluir_colaborador_atual(colaboradores, usuario):
    if not usuario or not usuario.colaborador:
        return colaboradores

    if any(colaborador.id == usuario.colaborador.id for colaborador in colaboradores):
        return colaboradores

    return [usuario.colaborador] + colaboradores


@usuarios_bp.route("/")
@login_required
@admin_required
def listar_usuarios():
    filtro_nome = request.args.get("nome", "").strip()
    filtro_aplicado = bool(filtro_nome)
    usuarios = []

    if filtro_aplicado:
        usuarios = buscar_usuarios_por_nome(filtro_nome)

    return render_template(
        "usuarios/listar.html",
        usuarios=usuarios,
        filtro_nome=filtro_nome,
        filtro_aplicado=filtro_aplicado,
    )


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo_usuario():
    niveis = buscar_niveis_ativos()
    colaboradores = buscar_colaboradores_ativos_para_vinculo()

    if request.method == "POST":
        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        senha = request.form.get("senha", "")
        nivel_acesso_id = request.form.get("nivel_acesso_id")
        colaborador_id = request.form.get("colaborador_id")
        ativo = request.form.get("ativo") == "on"

        sucesso, mensagem = criar_usuario(
            nome=nome,
            email=email,
            senha=senha,
            nivel_acesso_id=nivel_acesso_id,
            colaborador_id=colaborador_id,
            ativo=ativo,
        )

        if sucesso:
            usuario_criado = Usuario.query.filter_by(email=email.strip().lower()).first()
            descricao = "Usuario criado."

            if usuario_criado:
                descricao = f"Usuario criado. ID: {usuario_criado.id}."

            registrar_log("usuario_criado", descricao)

            if usuario_criado and usuario_criado.colaborador_id:
                registrar_log(
                    "usuario_colaborador_vinculado",
                    (
                        f"Usuario ID {usuario_criado.id} vinculado ao "
                        f"colaborador ID {usuario_criado.colaborador_id}."
                    ),
                )

            flash(mensagem, "success")
            return redirect(url_for("usuarios.listar_usuarios"))

        flash(mensagem, "danger")

    return render_template(
        "usuarios/form.html",
        usuario=None,
        niveis=niveis,
        colaboradores=colaboradores,
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
    colaboradores = incluir_colaborador_atual(
        buscar_colaboradores_ativos_para_vinculo(),
        usuario,
    )

    if request.method == "POST":
        colaborador_id_anterior = usuario.colaborador_id
        nome = request.form.get("nome", "")
        email = request.form.get("email", "")
        nivel_acesso_id = request.form.get("nivel_acesso_id")
        colaborador_id = request.form.get("colaborador_id")
        ativo = request.form.get("ativo") == "on"
        nova_senha = request.form.get("nova_senha", "").strip()

        sucesso, mensagem = atualizar_usuario(
            usuario=usuario,
            nome=nome,
            email=email,
            nivel_acesso_id=nivel_acesso_id,
            colaborador_id=colaborador_id,
            ativo=ativo,
            nova_senha=nova_senha,
        )

        if sucesso:
            descricao = f"Usuario atualizado. ID: {usuario.id}."

            if nova_senha:
                descricao += " Senha redefinida pelo administrador."

            registrar_log("usuario_atualizado", descricao)

            if colaborador_id_anterior != usuario.colaborador_id:
                if colaborador_id_anterior and usuario.colaborador_id:
                    registrar_log(
                        "usuario_colaborador_alterado",
                        f"Vinculo de colaborador alterado no usuario ID {usuario.id}.",
                    )
                elif usuario.colaborador_id:
                    registrar_log(
                        "usuario_colaborador_vinculado",
                        (
                            f"Usuario ID {usuario.id} vinculado ao "
                            f"colaborador ID {usuario.colaborador_id}."
                        ),
                    )
                else:
                    registrar_log(
                        "usuario_colaborador_removido",
                        f"Vinculo de colaborador removido do usuario ID {usuario.id}.",
                    )

            flash(mensagem, "success")
            return redirect(url_for("usuarios.listar_usuarios"))

        flash(mensagem, "danger")

    return render_template(
        "usuarios/form.html",
        usuario=usuario,
        niveis=niveis,
        colaboradores=colaboradores,
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
