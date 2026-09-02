from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.financeiro.clientes import financeiro_clientes_bp
from app.services.financeiro_clientes_service import (
    alterar_status_cliente,
    buscar_clientes,
    buscar_vinculos_cliente,
    cliente_para_json,
    cliente_por_id,
    clientes_ativos,
    consultar_cnpj_publico,
    documento_cliente_ja_existe,
    salvar_cliente,
)
from app.services.financeiro_contas_receber_service import formatar_data_brasil, formatar_moeda_brl
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.services.suprimentos_service import somente_digitos

DEPARTAMENTO_FINANCEIRO = "financeiro"
MODULO_CLIENTES = "clientes"


def _pode(acao="visualizar"):
    if usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CLIENTES, acao):
        return True
    registrar_log("financeiro_clientes_permissao_bloqueada", f"Tentativa bloqueada em Clientes. Acao: {acao}.")
    flash("Você não possui permissão para acessar o Cadastro de Clientes.", "danger")
    return False


@financeiro_clientes_bp.route("/")
@login_required
@module_permission_required("financeiro", "clientes", "visualizar")
def listar():
    return render_template(
        "financeiro/clientes/listar.html",
        clientes=buscar_clientes(request.args),
        filtros=request.args,
        pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CLIENTES, "criar"),
        pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CLIENTES, "editar"),
        pode_inativar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CLIENTES, "excluir"),
        pode_consultar_cnpj=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CLIENTES, "visualizar"),
    )


@financeiro_clientes_bp.route("/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "clientes", "criar")
def novo():
    cliente = None
    if request.method == "POST":
        sucesso, mensagem, cliente = salvar_cliente(request.form, usuario=current_user)
        flash(mensagem, "success" if sucesso else "danger")
        if sucesso:
            registrar_log("financeiro_cliente_criado", f"Cliente criado. ID: {cliente.id}.")
            return redirect(url_for("financeiro_clientes.detalhes", cliente_id=cliente.id))
    return render_template("financeiro/clientes/form.html", cliente=cliente, modo="novo")


@financeiro_clientes_bp.route("/consultar-cnpj")
@login_required
@module_permission_required("financeiro", "clientes", "visualizar")
def consultar_cnpj():
    cnpj = request.args.get("cnpj", "")
    if documento_cliente_ja_existe(cnpj):
        return jsonify({"sucesso": False, "mensagem": "CNPJ já cadastrado.", "dados": {}}), 400
    sucesso, mensagem, dados = consultar_cnpj_publico(cnpj)
    registrar_log("financeiro_cliente_consulta_cnpj", f"Consulta de CNPJ para cliente. CNPJ: {somente_digitos(cnpj)}. Sucesso: {sucesso}.")
    return jsonify({"sucesso": sucesso, "mensagem": "Cliente localizado com sucesso." if sucesso else mensagem, "dados": dados or {}}), 200 if sucesso else 400


@financeiro_clientes_bp.route("/buscar")
@login_required
@module_permission_required("financeiro", "clientes", "visualizar")
def buscar_json():
    termo = request.args.get("q", "")
    clientes = buscar_clientes({"razao_social": termo, "status": "ativos"}) if termo else clientes_ativos()
    if termo and not clientes:
        clientes = buscar_clientes({"nome_fantasia": termo, "status": "ativos"})
    if termo and not clientes:
        clientes = buscar_clientes({"cnpj_cpf": termo, "status": "ativos"})
    return jsonify([cliente_para_json(cliente) for cliente in clientes[:20]])


@financeiro_clientes_bp.route("/<int:cliente_id>/json")
@login_required
@module_permission_required("financeiro", "clientes", "visualizar")
def detalhe_json(cliente_id):
    cliente = cliente_por_id(cliente_id)
    if not cliente:
        return jsonify({"sucesso": False, "mensagem": "Cliente não encontrado."}), 404
    return jsonify({"sucesso": True, "dados": cliente_para_json(cliente)})


@financeiro_clientes_bp.route("/<int:cliente_id>")
@login_required
@module_permission_required("financeiro", "clientes", "visualizar")
def detalhes(cliente_id):
    cliente = cliente_por_id(cliente_id)
    if not cliente:
        flash("Cliente não encontrado.", "warning")
        return redirect(url_for("financeiro_clientes.listar"))
    return render_template(
        "financeiro/clientes/detalhes.html",
        cliente=cliente,
        vinculos=buscar_vinculos_cliente(cliente),
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brasil=formatar_data_brasil,
        pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CLIENTES, "editar"),
        pode_inativar=usuario_tem_permissao(current_user, DEPARTAMENTO_FINANCEIRO, MODULO_CLIENTES, "excluir"),
    )


@financeiro_clientes_bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "clientes", "editar")
def editar(cliente_id):
    cliente = cliente_por_id(cliente_id)
    if not cliente:
        flash("Cliente não encontrado.", "warning")
        return redirect(url_for("financeiro_clientes.listar"))
    if request.method == "POST":
        sucesso, mensagem, cliente = salvar_cliente(request.form, cliente=cliente, usuario=current_user)
        flash(mensagem, "success" if sucesso else "danger")
        if sucesso:
            registrar_log("financeiro_cliente_atualizado", f"Cliente atualizado. ID: {cliente.id}.")
            return redirect(url_for("financeiro_clientes.detalhes", cliente_id=cliente.id))
    return render_template("financeiro/clientes/form.html", cliente=cliente, modo="editar")


@financeiro_clientes_bp.route("/<int:cliente_id>/status", methods=["POST"])
@login_required
@module_permission_required("financeiro", "clientes", "excluir")
def status(cliente_id):
    cliente = cliente_por_id(cliente_id)
    if not cliente:
        flash("Cliente não encontrado.", "warning")
        return redirect(url_for("financeiro_clientes.listar"))
    sucesso, mensagem = alterar_status_cliente(cliente, request.form.get("motivo_inativacao"), usuario=current_user)
    registrar_log("financeiro_cliente_status_alterado", f"Status de cliente alterado. ID: {cliente.id}. Ativo: {cliente.ativo}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("financeiro_clientes.detalhes", cliente_id=cliente.id))
