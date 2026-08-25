from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.operacao.veiculos_equipamentos import veiculos_equipamentos_bp
from app.operacao.veiculos_equipamentos.services import (
    SITUACOES_AQUISICAO,
    TIPOS_VEICULO_EQUIPAMENTO,
    alterar_status,
    buscar_por_id,
    buscar_veiculos_equipamentos,
    centro_custo_calculado,
    salvar_veiculo_equipamento,
)
from app.services.logs_service import registrar_log
from app.services.operacao_permissoes_service import (
    MODULO_VEICULOS_EQUIPAMENTOS,
    permissoes_cards_gestao,
    usuario_tem_algum_submodulo_gestao,
)


@veiculos_equipamentos_bp.route("/")
@login_required
def index():
    if not usuario_tem_algum_submodulo_gestao(current_user):
        flash("Você não tem permissão para acessar esta área.", "danger")
        return redirect(url_for("main.acesso_negado"))
    return render_template(
        "operacao/gestao_veiculos_epgs/index.html",
        permissoes_cards=permissoes_cards_gestao(current_user),
    )


@veiculos_equipamentos_bp.route("/veiculos-equipamentos")
@login_required
@module_permission_required("operacao", MODULO_VEICULOS_EQUIPAMENTOS, "visualizar")
def listar():
    return render_template(
        "operacao/gestao_veiculos_epgs/veiculos_equipamentos/listar.html",
        registros=buscar_veiculos_equipamentos(request.args),
        filtros=request.args,
        situacoes=SITUACOES_AQUISICAO,
        tipos=TIPOS_VEICULO_EQUIPAMENTO,
    )


@veiculos_equipamentos_bp.route("/veiculos-equipamentos/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_VEICULOS_EQUIPAMENTOS, "criar")
def novo():
    if request.method == "POST":
        sucesso, mensagem, registro = salvar_veiculo_equipamento(request.form)

        if sucesso:
            registrar_log("operacao_veiculo_equipamento_criado", f"Veiculo/equipamento criado. ID: {registro.id}.")
            flash(mensagem, "success")
            return redirect(url_for("veiculos_equipamentos.listar"))

        flash(mensagem, "danger")

    return render_template(
        "operacao/gestao_veiculos_epgs/veiculos_equipamentos/form.html",
        registro=None,
        modo="novo",
        situacoes=SITUACOES_AQUISICAO,
        tipos=TIPOS_VEICULO_EQUIPAMENTO,
        centro_custo_previsto="",
    )


@veiculos_equipamentos_bp.route("/veiculos-equipamentos/<int:registro_id>")
@login_required
@module_permission_required("operacao", MODULO_VEICULOS_EQUIPAMENTOS, "visualizar")
def detalhes(registro_id):
    registro = buscar_por_id(registro_id)

    if not registro:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("veiculos_equipamentos.listar"))

    return render_template(
        "operacao/gestao_veiculos_epgs/veiculos_equipamentos/detalhes.html",
        registro=registro,
    )


@veiculos_equipamentos_bp.route("/veiculos-equipamentos/<int:registro_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_VEICULOS_EQUIPAMENTOS, "editar")
def editar(registro_id):
    registro = buscar_por_id(registro_id)

    if not registro:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("veiculos_equipamentos.listar"))

    if request.method == "POST":
        sucesso, mensagem, registro = salvar_veiculo_equipamento(request.form, registro)

        if sucesso:
            registrar_log("operacao_veiculo_equipamento_atualizado", f"Veiculo/equipamento atualizado. ID: {registro.id}.")
            flash(mensagem, "success")
            return redirect(url_for("veiculos_equipamentos.detalhes", registro_id=registro.id))

        flash(mensagem, "danger")

    return render_template(
        "operacao/gestao_veiculos_epgs/veiculos_equipamentos/form.html",
        registro=registro,
        modo="editar",
        situacoes=SITUACOES_AQUISICAO,
        tipos=TIPOS_VEICULO_EQUIPAMENTO,
        centro_custo_previsto=centro_custo_calculado(registro.identificacao, registro.descricao),
    )


@veiculos_equipamentos_bp.route("/veiculos-equipamentos/<int:registro_id>/status", methods=["POST"])
@login_required
@module_permission_required("operacao", MODULO_VEICULOS_EQUIPAMENTOS, "excluir")
def status(registro_id):
    registro = buscar_por_id(registro_id)

    if not registro:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("veiculos_equipamentos.listar"))

    sucesso, mensagem = alterar_status(registro)
    registrar_log("operacao_veiculo_equipamento_status", f"Status alterado. ID: {registro.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("veiculos_equipamentos.listar"))
