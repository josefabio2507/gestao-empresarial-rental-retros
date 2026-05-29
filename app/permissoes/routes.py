from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.decorators import admin_required
from app.services.logs_service import registrar_log
from app.services.permissoes_service import (
    buscar_usuario_com_permissoes,
    buscar_departamentos_com_modulos,
    garantir_modulo_historico_refeicoes_colaborador,
    buscar_permissoes_usuario,
    salvar_permissoes_usuario,
    permissoes_por_departamento,
    listar_acoes_liberadas,
)
from app.services.usuarios_service import buscar_usuarios_por_nome


permissoes_bp = Blueprint("permissoes", __name__)


@permissoes_bp.route("/")
@login_required
@admin_required
def listar_permissoes():
    filtro_nome = request.args.get("nome", "").strip()
    filtro_aplicado = bool(filtro_nome)
    usuarios = buscar_usuarios_por_nome(filtro_nome) if filtro_aplicado else []

    return render_template(
        "permissoes/listar.html",
        usuarios=usuarios,
        filtro_nome=filtro_nome,
        filtro_aplicado=filtro_aplicado,
    )


@permissoes_bp.route("/usuario/<int:usuario_id>")
@login_required
@admin_required
def visualizar_permissoes(usuario_id):
    usuario = buscar_usuario_com_permissoes(usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("usuarios.listar_usuarios"))

    permissoes_departamentos = permissoes_por_departamento(usuario.id)

    return render_template(
        "permissoes/visualizar.html",
        usuario=usuario,
        permissoes_departamentos=permissoes_departamentos,
        listar_acoes_liberadas=listar_acoes_liberadas,
    )


@permissoes_bp.route("/usuario/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_permissoes(usuario_id):
    usuario = buscar_usuario_com_permissoes(usuario_id)

    if not usuario:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("usuarios.listar_usuarios"))

    if request.method == "POST":
        sucesso, mensagem = salvar_permissoes_usuario(usuario.id, request.form)

        if sucesso:
            registrar_log(
                "permissoes_atualizadas",
                f"Permissoes atualizadas para usuario ID {usuario.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("permissoes.visualizar_permissoes", usuario_id=usuario.id))

        flash(mensagem, "danger")

    garantir_modulo_historico_refeicoes_colaborador()
    departamentos = buscar_departamentos_com_modulos()
    permissoes = buscar_permissoes_usuario(usuario.id)

    return render_template(
        "permissoes/editar.html",
        usuario=usuario,
        departamentos=departamentos,
        permissoes=permissoes,
    )
