from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from app.decorators import module_permission_required
from app.services.permissoes_service import usuario_tem_permissao
from app.services.importacao_colaboradores_service import importar_colaboradores_csv
from app.services.logs_service import registrar_log
from app.utils.mascaras_lgpd import (
    exibir_cpf,
    exibir_email,
    exibir_telefone,
    pode_ver_dados_sensiveis,
)
from app.departamento_pessoal.colaboradores.services import (
    buscar_colaboradores,
    buscar_colaborador_por_id,
    buscar_cargos_ativos,
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

    pode_importar = pode_criar or pode_editar
    pode_ver_sensiveis = pode_ver_dados_sensiveis(current_user)

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
        pode_importar=pode_importar,
        pode_ver_dados_sensiveis=pode_ver_sensiveis,
        exibir_cpf=exibir_cpf,
        exibir_telefone=exibir_telefone,
    )


@colaboradores_bp.route("/importar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "colaboradores", "visualizar")
def importar_colaboradores():
    pode_importar = (
        usuario_tem_permissao(
            current_user,
            "departamento_pessoal",
            "colaboradores",
            "criar",
        )
        or usuario_tem_permissao(
            current_user,
            "departamento_pessoal",
            "colaboradores",
            "editar",
        )
    )

    if not pode_importar:
        flash("Você não tem permissão para importar colaboradores.", "danger")
        return redirect(url_for("main.acesso_negado"))

    resumo = None

    if request.method == "POST":
        arquivo_csv = request.files.get("arquivo_csv")

        if not arquivo_csv or not arquivo_csv.filename:
            flash("Selecione um arquivo CSV para importar.", "danger")
            return redirect(url_for("colaboradores.importar_colaboradores"))

        if not arquivo_csv.filename.lower().endswith(".csv"):
            flash("O arquivo deve estar no formato CSV.", "danger")
            return redirect(url_for("colaboradores.importar_colaboradores"))

        resumo = importar_colaboradores_csv(arquivo_csv)
        registrar_log(
            "colaboradores_importacao_csv",
            (
                "Importacao CSV de colaboradores concluida. "
                f"Total: {resumo['total_linhas']}, criados: {resumo['criados']}, "
                f"atualizados: {resumo['atualizados']}, rejeitados: {resumo['rejeitados']}."
            ),
        )
        flash("Importação concluída.", "success")

    return render_template(
        "departamento_pessoal/colaboradores/importar.html",
        resumo=resumo,
    )


@colaboradores_bp.route("/novo", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "colaboradores", "criar")
def novo_colaborador():
    equipes = buscar_equipes_ativas()
    cargos = buscar_cargos_ativos()

    if request.method == "POST":
        sucesso, mensagem = criar_colaborador(
            matricula=request.form.get("matricula", ""),
            nome=request.form.get("nome", ""),
            cpf=request.form.get("cpf", ""),
            email=request.form.get("email", ""),
            telefone=request.form.get("telefone", ""),
            cargo=request.form.get("cargo", ""),
            equipe_id=request.form.get("equipe_id"),
            vale_transporte_optante=(
                request.form.get("vale_transporte_optante") == "optante"
            ),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            registrar_log(
                "colaborador_criado",
                f"Colaborador criado. Matricula: {request.form.get('matricula', '').strip()}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("colaboradores.listar_colaboradores"))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/colaboradores/form.html",
        colaborador=None,
        cargos=cargos,
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

    pode_editar = usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "colaboradores",
        "editar",
    )
    pode_ver_sensiveis = pode_ver_dados_sensiveis(current_user)

    return render_template(
        "departamento_pessoal/colaboradores/detalhes.html",
        colaborador=colaborador,
        formatar_cpf=formatar_cpf,
        formatar_telefone=formatar_telefone,
        pode_editar=pode_editar,
        pode_ver_dados_sensiveis=pode_ver_sensiveis,
        exibir_cpf=exibir_cpf,
        exibir_email=exibir_email,
        exibir_telefone=exibir_telefone,
    )


@colaboradores_bp.route("/<int:colaborador_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "colaboradores", "editar")
def editar_colaborador(colaborador_id):
    colaborador = buscar_colaborador_por_id(colaborador_id)

    if not colaborador:
        flash("Colaborador não encontrado.", "warning")
        return redirect(url_for("colaboradores.listar_colaboradores"))

    equipes = buscar_equipes_ativas()
    cargos = buscar_cargos_ativos()

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
            vale_transporte_optante=(
                request.form.get("vale_transporte_optante") == "optante"
            ),
            ativo=request.form.get("ativo") == "on",
        )

        if sucesso:
            registrar_log(
                "colaborador_atualizado",
                f"Colaborador atualizado. Matricula: {colaborador.matricula}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("colaboradores.listar_colaboradores"))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/colaboradores/form.html",
        colaborador=colaborador,
        cargos=cargos,
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
        acao = "colaborador_ativado" if colaborador.ativo else "colaborador_inativado"
        descricao = (
            f"Colaborador {'ativado' if colaborador.ativo else 'inativado'}. "
            f"Matricula: {colaborador.matricula}."
        )
        registrar_log(acao, descricao)
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("colaboradores.listar_colaboradores"))
