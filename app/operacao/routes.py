from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import module_permission_required
from app.services.logs_service import registrar_log
from app.services.operacao_veiculos_service import (
    SITUACOES_AQUISICAO,
    TIPOS_VEICULO_EQUIPAMENTO,
    alterar_status,
    buscar_por_id,
    buscar_veiculos_equipamentos,
    salvar_veiculo_equipamento,
)

operacao_bp = Blueprint("operacao", __name__)


@operacao_bp.route("/")
@login_required
def index():
    return redirect(
        url_for("departamentos.detalhe_departamento", slug_departamento="operacao")
    )


@operacao_bp.route("/status")
@login_required
def status():
    return "Operação online."


@operacao_bp.route("/gestao-veiculos-epgs/veiculos-equipamentos")
@login_required
@module_permission_required("operacao", "gestao_veiculos_epgs", "visualizar")
def listar_veiculos_equipamentos():
    filtro_aplicado = any(
        request.args.get(campo, "").strip()
        for campo in [
            "identificacao",
            "placa",
            "descricao",
            "chassi",
            "centro_custo",
            "situacao_aquisicao",
            "tipo",
            "status",
        ]
    )

    veiculos = buscar_veiculos_equipamentos(request.args) if filtro_aplicado else []

    return render_template(
        "operacao/veiculos_equipamentos/listar.html",
        veiculos=veiculos,
        filtros=request.args,
        filtro_aplicado=filtro_aplicado,
        situacoes=SITUACOES_AQUISICAO,
        tipos=TIPOS_VEICULO_EQUIPAMENTO,
    )


@operacao_bp.route("/gestao-veiculos-epgs/veiculos-equipamentos/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", "gestao_veiculos_epgs", "criar")
def novo_veiculo_equipamento():
    if request.method == "POST":
        sucesso, mensagem, veiculo = salvar_veiculo_equipamento(request.form)

        if sucesso:
            registrar_log(
                "operacao_veiculo_equipamento_criado",
                f"Veiculo/equipamento criado. ID: {veiculo.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("operacao.listar_veiculos_equipamentos"))

        flash(mensagem, "danger")

    return render_template(
        "operacao/veiculos_equipamentos/form.html",
        veiculo=None,
        modo="novo",
        situacoes=SITUACOES_AQUISICAO,
        tipos=TIPOS_VEICULO_EQUIPAMENTO,
    )


@operacao_bp.route("/gestao-veiculos-epgs/veiculos-equipamentos/<int:veiculo_id>")
@login_required
@module_permission_required("operacao", "gestao_veiculos_epgs", "visualizar")
def visualizar_veiculo_equipamento(veiculo_id):
    veiculo = buscar_por_id(veiculo_id)

    if not veiculo:
        flash("Veículo/equipamento não encontrado.", "warning")
        return redirect(url_for("operacao.listar_veiculos_equipamentos"))

    return render_template(
        "operacao/veiculos_equipamentos/detalhes.html",
        veiculo=veiculo,
    )


@operacao_bp.route("/gestao-veiculos-epgs/veiculos-equipamentos/<int:veiculo_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", "gestao_veiculos_epgs", "editar")
def editar_veiculo_equipamento(veiculo_id):
    veiculo = buscar_por_id(veiculo_id)

    if not veiculo:
        flash("Veículo/equipamento não encontrado.", "warning")
        return redirect(url_for("operacao.listar_veiculos_equipamentos"))

    if request.method == "POST":
        sucesso, mensagem, veiculo = salvar_veiculo_equipamento(request.form, veiculo)

        if sucesso:
            registrar_log(
                "operacao_veiculo_equipamento_atualizado",
                f"Veiculo/equipamento atualizado. ID: {veiculo.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("operacao.visualizar_veiculo_equipamento", veiculo_id=veiculo.id))

        flash(mensagem, "danger")

    return render_template(
        "operacao/veiculos_equipamentos/form.html",
        veiculo=veiculo,
        modo="editar",
        situacoes=SITUACOES_AQUISICAO,
        tipos=TIPOS_VEICULO_EQUIPAMENTO,
    )


@operacao_bp.route("/gestao-veiculos-epgs/veiculos-equipamentos/<int:veiculo_id>/status", methods=["POST"])
@login_required
@module_permission_required("operacao", "gestao_veiculos_epgs", "excluir")
def status_veiculo_equipamento(veiculo_id):
    veiculo = buscar_por_id(veiculo_id)

    if not veiculo:
        flash("Veículo/equipamento não encontrado.", "warning")
        return redirect(url_for("operacao.listar_veiculos_equipamentos"))

    sucesso, mensagem = alterar_status(veiculo)
    registrar_log(
        "operacao_veiculo_equipamento_status",
        f"Status de veiculo/equipamento alterado. ID: {veiculo.id}.",
    )
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("operacao.listar_veiculos_equipamentos"))
