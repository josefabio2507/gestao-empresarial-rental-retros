from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from app.decorators import module_permission_required
from app.services.permissoes_service import usuario_tem_permissao
from app.departamento_pessoal.colaboradores.services import (
    buscar_colaboradores,
    buscar_colaborador_por_id,
    buscar_equipes_ativas,
    criar_colaborador,
    atualizar_colaborador,
    alterar_status_colaborador,
    formatar_cpf,
    formatar_telefone,
)


colaboradores_bp = Blueprint("colaboradores", __name__)


@colaboradores_bp.route("/")
@module_permission_required("departamento_pessoal", "colaboradores", "visualizar")
def listar_colaboradores():
    filtro_texto = request.args.get("q", "").strip()
    equipe_id = request.args.get("equipe_id", "").strip()

    colaboradores = buscar_colaboradores(
        filtro_texto=filtro_texto,
        equipe_id=equipe_id if equipe_id else None,
    )

    equipes = buscar_equipes_ativas()

    pode_criar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "colaboradores",
        "criar",
    )

    pode_editar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "colaboradores",
        "editar",
    )

    pode_excluir = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "colaboradores",
        "excluir",
    )

    return render_template(
        "departamento_pessoal/colaboradores/listar.html",
        colaboradores=colaboradores,
        equipes=equipes,
        filtro_texto=filtro_texto,
        equipe_id_selecionada=equipe_id,
        formatar_cpf=formatar_cpf,
        formatar_telefone=formatar_telefone,
        pode_criar=pode_criar,
        pode_editar=pode_editar,
        pode_excluir=pode_excluir,
    )


@colaboradores_bp.route("/novo", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "colaboradores", "criar")
def novo_colaborador():
    equipes = buscar_equipes_ativas()

    if request.method == "POST":
        sucesso, mensagem = criar_colaborador(
            matricula=request.form.get("matricula", ""),
            nome=request.form.get("nome", ""),
            cpf=request.form.get("cpf", ""),
            email=request.form.get("email", ""),
            telefone=request.form.get("telefone", ""),
            cargo=request.form.get("cargo", ""),
            equipe_id=request.form.get("equipe_id"),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("colaboradores.listar_colaboradores"))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/colaboradores/form.html",
        colaborador=None,
        equipes=equipes,
        modo="novo",
    )


@colaboradores_bp.route("/<int:colaborador_id>")
@module_permission_required("departamento_pessoal", "colaboradores", "visualizar")
def detalhes_colaborador(colaborador_id):
    colaborador = buscar_colaborador_por_id(colaborador_id)

    if not colaborador:
        flash("Colaborador não encontrado.", "warning")
        return redirect(url_for("colaboradores.listar_colaboradores"))

    return render_template(
        "departamento_pessoal/colaboradores/detalhes.html",
        colaborador=colaborador,
        formatar_cpf=formatar_cpf,
        formatar_telefone=formatar_telefone,
    )


@colaboradores_bp.route("/<int:colaborador_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "colaboradores", "editar")
def editar_colaborador(colaborador_id):
    colaborador = buscar_colaborador_por_id(colaborador_id)

    if not colaborador:
        flash("Colaborador não encontrado.", "warning")
        return redirect(url_for("colaboradores.listar_colaboradores"))

    equipes = buscar_equipes_ativas()

    if request.method == "POST":
        sucesso, mensagem = atualizar_colaborador(
            colaborador=colaborador,
            matricula=request.form.get("matricula", ""),
            nome=request.form.get("nome", ""),
            cpf=request.form.get("cpf", ""),
            email=request.form.get("email", ""),
            telefone=request.form.get("telefone", ""),
            cargo=request.form.get("cargo", ""),
            equipe_id=request.form.get("equipe_id"),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for("colaboradores.listar_colaboradores"))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/colaboradores/form.html",
        colaborador=colaborador,
        equipes=equipes,
        modo="editar",
    )


@colaboradores_bp.route("/<int:colaborador_id>/status")
@module_permission_required("departamento_pessoal", "colaboradores", "excluir")
def alterar_status(colaborador_id):
    colaborador = buscar_colaborador_por_id(colaborador_id)

    if not colaborador:
        flash("Colaborador não encontrado.", "warning")
        return redirect(url_for("colaboradores.listar_colaboradores"))

    sucesso, mensagem = alterar_status_colaborador(colaborador)

    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("colaboradores.listar_colaboradores"))