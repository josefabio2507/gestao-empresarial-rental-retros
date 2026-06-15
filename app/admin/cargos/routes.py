from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.admin.cargos import cargos_bp
from app.decorators import admin_required
from app.services.cargos_service import (
    alterar_status_cargo,
    atualizar_cargo,
    buscar_cargo_por_id,
    buscar_cargos,
    criar_cargo,
)
from app.services.logs_service import registrar_log


@cargos_bp.route("/")
@login_required
@admin_required
def listar_cargos():
    filtro_nome = request.args.get("nome", "").strip()

    return render_template(
        "admin/cargos/listar.html",
        cargos=buscar_cargos(filtro_nome),
        filtro_nome=filtro_nome,
    )


@cargos_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo_cargo():
    nome_informado = ""

    if request.method == "POST":
        nome_informado = request.form.get("nome", "")
        sucesso, mensagem, cargo = criar_cargo(nome_informado)

        if sucesso:
            registrar_log("cargo_criado", f"Cargo criado. ID: {cargo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("cargos.listar_cargos"))

        flash(mensagem, "danger")

    return render_template(
        "admin/cargos/form.html",
        cargo=None,
        nome_informado=nome_informado,
        modo="novo",
    )


@cargos_bp.route("/<int:cargo_id>")
@login_required
@admin_required
def detalhes_cargo(cargo_id):
    cargo = buscar_cargo_por_id(cargo_id)

    if not cargo:
        flash("Cargo não encontrado.", "warning")
        return redirect(url_for("cargos.listar_cargos"))

    return render_template("admin/cargos/detalhes.html", cargo=cargo)


@cargos_bp.route("/<int:cargo_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_cargo(cargo_id):
    cargo = buscar_cargo_por_id(cargo_id)

    if not cargo:
        flash("Cargo não encontrado.", "warning")
        return redirect(url_for("cargos.listar_cargos"))

    nome_informado = cargo.nome

    if request.method == "POST":
        nome_informado = request.form.get("nome", "")
        sucesso, mensagem = atualizar_cargo(cargo, nome_informado)

        if sucesso:
            registrar_log(
                "cargo_atualizado",
                f"Cargo atualizado. ID: {cargo.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("cargos.listar_cargos"))

        flash(mensagem, "danger")

    return render_template(
        "admin/cargos/form.html",
        cargo=cargo,
        nome_informado=nome_informado,
        modo="editar",
    )


@cargos_bp.route("/<int:cargo_id>/status", methods=["POST"])
@login_required
@admin_required
def alterar_status(cargo_id):
    cargo = buscar_cargo_por_id(cargo_id)

    if not cargo:
        flash("Cargo não encontrado.", "warning")
        return redirect(url_for("cargos.listar_cargos"))

    sucesso, mensagem = alterar_status_cargo(cargo)
    acao = "cargo_reativado" if cargo.ativo else "cargo_inativado"
    registrar_log(
        acao,
        (
            f"Cargo {'reativado' if cargo.ativo else 'inativado'}. "
            f"ID: {cargo.id}."
        ),
    )
    flash(mensagem, "success" if sucesso else "danger")

    return redirect(url_for("cargos.listar_cargos"))
