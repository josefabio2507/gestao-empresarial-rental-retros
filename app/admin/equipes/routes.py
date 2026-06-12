from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.admin.equipes import equipes_bp
from app.decorators import admin_required
from app.services.equipes_service import (
    alterar_status_equipe,
    atualizar_equipe,
    buscar_equipe_por_id,
    buscar_equipes,
    criar_equipe,
)
from app.services.logs_service import registrar_log


@equipes_bp.route("/")
@login_required
@admin_required
def listar_equipes():
    filtro_nome = request.args.get("nome", "").strip()

    return render_template(
        "admin/equipes/listar.html",
        equipes=buscar_equipes(filtro_nome),
        filtro_nome=filtro_nome,
    )


@equipes_bp.route("/nova", methods=["GET", "POST"])
@login_required
@admin_required
def nova_equipe():
    nome_informado = ""

    if request.method == "POST":
        nome_informado = request.form.get("nome", "")
        sucesso, mensagem, equipe = criar_equipe(nome_informado)

        if sucesso:
            registrar_log(
                "equipe_criada",
                f"Equipe criada. ID: {equipe.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("equipes.listar_equipes"))

        flash(mensagem, "danger")

    return render_template(
        "admin/equipes/form.html",
        equipe=None,
        nome_informado=nome_informado,
        modo="nova",
    )


@equipes_bp.route("/<int:equipe_id>")
@login_required
@admin_required
def detalhes_equipe(equipe_id):
    equipe = buscar_equipe_por_id(equipe_id)

    if not equipe:
        flash("Equipe não encontrada.", "warning")
        return redirect(url_for("equipes.listar_equipes"))

    return render_template("admin/equipes/detalhes.html", equipe=equipe)


@equipes_bp.route("/<int:equipe_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_equipe(equipe_id):
    equipe = buscar_equipe_por_id(equipe_id)

    if not equipe:
        flash("Equipe não encontrada.", "warning")
        return redirect(url_for("equipes.listar_equipes"))

    nome_informado = equipe.nome

    if request.method == "POST":
        nome_informado = request.form.get("nome", "")
        sucesso, mensagem = atualizar_equipe(equipe, nome_informado)

        if sucesso:
            registrar_log(
                "equipe_atualizada",
                f"Equipe atualizada. ID: {equipe.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("equipes.listar_equipes"))

        flash(mensagem, "danger")

    return render_template(
        "admin/equipes/form.html",
        equipe=equipe,
        nome_informado=nome_informado,
        modo="editar",
    )


@equipes_bp.route("/<int:equipe_id>/status", methods=["POST"])
@login_required
@admin_required
def alterar_status(equipe_id):
    equipe = buscar_equipe_por_id(equipe_id)

    if not equipe:
        flash("Equipe não encontrada.", "warning")
        return redirect(url_for("equipes.listar_equipes"))

    sucesso, mensagem = alterar_status_equipe(equipe)
    acao = "equipe_reativada" if equipe.ativo else "equipe_inativada"
    registrar_log(
        acao,
        (
            f"Equipe {'reativada' if equipe.ativo else 'inativada'}. "
            f"ID: {equipe.id}."
        ),
    )
    flash(mensagem, "success" if sucesso else "danger")

    return redirect(url_for("equipes.listar_equipes"))
