from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.services.permissoes_service import (
    buscar_departamentos_liberados,
    buscar_departamento_por_slug,
    buscar_modulos_liberados,
)


departamentos_bp = Blueprint("departamentos", __name__)


@departamentos_bp.route("/")
@login_required
def listar_departamentos():
    departamentos_liberados = buscar_departamentos_liberados(current_user)

    return render_template(
        "inicio.html",
        departamentos_liberados=departamentos_liberados,
    )


@departamentos_bp.route("/<slug_departamento>")
@login_required
def detalhe_departamento(slug_departamento):
    departamento = buscar_departamento_por_slug(slug_departamento)

    if not departamento:
        flash("Departamento não encontrado.", "warning")
        return redirect(url_for("main.acesso_negado"))

    modulos_liberados = buscar_modulos_liberados(
        current_user,
        slug_departamento,
    )

    if not modulos_liberados:
        flash("Você não possui módulos liberados neste departamento.", "danger")
        return redirect(url_for("main.acesso_negado"))

    if slug_departamento == "financeiro":
        return redirect(url_for("financeiro.index"))

    return render_template(
        "departamentos/detalhe.html",
        departamento=departamento,
        modulos_liberados=modulos_liberados,
    )
