from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.decorators import module_permission_required
from app.models import LinhaOnibus
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.departamento_pessoal.vale_transporte.services import (
    PERIODICIDADES_PAGAMENTO,
    STATUS_PEDIDOS,
    TIPOS_PAGAMENTO,
    alternar_status_linha,
    alternar_status_vinculo,
    atualizar_pagamento_vinculo,
    buscar_colaborador_por_id,
    buscar_linha_por_id,
    buscar_linhas_onibus,
    buscar_pedido_vale_transporte_por_id,
    buscar_pedidos_vale_transporte,
    buscar_vinculo_por_id,
    buscar_vinculos_colaborador,
    cancelar_pedido_vale_transporte,
    criar_pedido_vale_transporte,
    formatar_data_brl,
    formatar_moeda_brl,
    listar_empresas_transporte_ativas,
    listar_equipes_ativas,
    listar_colaboradores_para_filtro_pedido,
    listar_colaboradores_para_vinculo,
    listar_linhas_ativas,
    montar_previa_pedido_vale_transporte,
    pedido_vale_transporte_pode_ser_cancelado,
    salvar_linha_onibus,
    salvar_vinculo_colaborador_linha,
)


vale_transporte_bp = Blueprint("vale_transporte", __name__)


def _pode(acao):
    return usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "vale_transporte",
        acao,
    )


@vale_transporte_bp.route("/")
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def index():
    return render_template("departamento_pessoal/vale_transporte/index.html")


def _filtros_pedido_form():
    return {
        "competencia": request.values.get("competencia", "").strip(),
        "data_inicial": request.values.get("data_inicial", "").strip(),
        "data_final": request.values.get("data_final", "").strip(),
        "quantidade_dias": request.values.get("quantidade_dias", "").strip(),
        "equipe_id": request.values.get("equipe_id", "").strip(),
        "colaborador": request.values.get("colaborador", "").strip(),
        "forma_pagamento": request.values.get("forma_pagamento", "todos").strip() or "todos",
        "empresa_transporte": (
            request.values.get("empresa_transporte", "todos").strip() or "todos"
        ),
        "prazo_pagamento": request.values.get("prazo_pagamento", "").strip(),
    }


def _ajustes_itens_form():
    ajustes = {}

    for chave, valor in request.form.items():
        for prefixo, campo in (
            ("quantidade_dias_", "quantidade_dias"),
            ("valor_acrescimo_", "valor_acrescimo"),
            ("valor_desconto_", "valor_desconto"),
            ("observacao_", "observacao"),
        ):
            if chave.startswith(prefixo):
                vinculo_id = chave.replace(prefixo, "", 1)
                ajustes.setdefault(vinculo_id, {})[campo] = valor

    return ajustes


@vale_transporte_bp.route("/pedidos", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def pedidos():
    filtros = _filtros_pedido_form()
    previa = None
    acao = request.values.get("acao", "").strip()

    if request.method == "POST" and acao == "criar":
        if not _pode("criar"):
            flash("Você não tem permissão para criar pedidos de Vale Transporte.", "danger")
            return redirect(url_for("main.acesso_negado"))

        sucesso, mensagem, pedido = criar_pedido_vale_transporte(
            competencia=filtros["competencia"],
            data_inicial=filtros["data_inicial"],
            data_final=filtros["data_final"],
            quantidade_dias=filtros["quantidade_dias"],
            equipe_id=filtros["equipe_id"],
            colaborador=filtros["colaborador"],
            forma_pagamento=filtros["forma_pagamento"],
            empresa_transporte=filtros["empresa_transporte"],
            prazo_pagamento=filtros["prazo_pagamento"],
            ajustes_itens=_ajustes_itens_form(),
            criado_por_id=current_user.id if current_user.is_authenticated else None,
        )

        if sucesso:
            registrar_log(
                "vale_transporte_pedido_criado",
                f"Pedido de Vale Transporte criado. ID: {pedido.id}.",
            )
            flash(mensagem, "success")
            return redirect(
                url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
            )

        flash(mensagem, "danger")

    if request.values and (request.method == "GET" or acao in {"consultar", "criar"}):
        try:
            previa = montar_previa_pedido_vale_transporte(
                competencia=filtros["competencia"],
                data_inicial=filtros["data_inicial"],
                data_final=filtros["data_final"],
                quantidade_dias=filtros["quantidade_dias"],
                equipe_id=filtros["equipe_id"],
                colaborador=filtros["colaborador"],
                forma_pagamento=filtros["forma_pagamento"],
                empresa_transporte=filtros["empresa_transporte"],
                prazo_pagamento=filtros["prazo_pagamento"],
            )
            if not previa["itens"]:
                flash("Nenhum colaborador encontrado para os filtros informados.", "warning")
        except ValueError as erro:
            if acao:
                flash(str(erro), "danger")

    return render_template(
        "departamento_pessoal/vale_transporte/pedidos.html",
        filtros=filtros,
        previa=previa,
        equipes=listar_equipes_ativas(),
        colaboradores=listar_colaboradores_para_filtro_pedido(),
        empresas_transporte=listar_empresas_transporte_ativas(),
        tipos_pagamento=TIPOS_PAGAMENTO,
        periodicidades_pagamento=PERIODICIDADES_PAGAMENTO,
        formatar_moeda_brl=formatar_moeda_brl,
        pode_criar=_pode("criar"),
    )


@vale_transporte_bp.route("/pedidos/listar")
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def listar_pedidos_vale_transporte():
    status = request.args.get("status", "todos").strip() or "todos"

    return render_template(
        "departamento_pessoal/vale_transporte/pedidos_listar.html",
        pedidos=buscar_pedidos_vale_transporte(status=status),
        status=status,
        status_pedidos=STATUS_PEDIDOS,
        tipos_pagamento=TIPOS_PAGAMENTO,
        periodicidades_pagamento=PERIODICIDADES_PAGAMENTO,
        formatar_data_brl=formatar_data_brl,
        pode_criar=_pode("criar"),
        pode_excluir=_pode("excluir"),
        pedido_pode_cancelar=pedido_vale_transporte_pode_ser_cancelado,
    )


@vale_transporte_bp.route("/pedidos/<int:pedido_id>")
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def detalhes_pedido_vale_transporte(pedido_id):
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)

    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    return render_template(
        "departamento_pessoal/vale_transporte/pedido_detalhes.html",
        pedido=pedido,
        tipos_pagamento=TIPOS_PAGAMENTO,
        periodicidades_pagamento=PERIODICIDADES_PAGAMENTO,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brl=formatar_data_brl,
        pode_excluir=_pode("excluir"),
        pedido_pode_cancelar=pedido_vale_transporte_pode_ser_cancelado,
    )


@vale_transporte_bp.route("/pedidos/<int:pedido_id>/cancelar", methods=["POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "excluir")
def cancelar_pedido_vale_transporte_rota(pedido_id):
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)

    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    sucesso, mensagem = cancelar_pedido_vale_transporte(pedido)

    if sucesso:
        registrar_log(
            "vale_transporte_pedido_cancelado",
            f"Pedido de Vale Transporte cancelado. ID: {pedido.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id))


@vale_transporte_bp.route("/linhas")
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def listar_linhas():
    filtro_texto = request.args.get("q", "").strip()
    linhas = buscar_linhas_onibus(filtro_texto)

    return render_template(
        "departamento_pessoal/vale_transporte/linhas_listar.html",
        linhas=linhas,
        filtro_texto=filtro_texto,
        formatar_moeda_brl=formatar_moeda_brl,
        pode_criar=_pode("criar"),
        pode_editar=_pode("editar"),
        pode_excluir=_pode("excluir"),
    )


@vale_transporte_bp.route("/linhas/nova", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "criar")
def nova_linha():
    if request.method == "POST":
        sucesso, mensagem = salvar_linha_onibus(
            linha=None,
            nome=request.form.get("nome", ""),
            codigo=request.form.get("codigo", ""),
            empresa_transporte=request.form.get("empresa_transporte", ""),
            valor_tarifa_dia=request.form.get("valor_tarifa_dia", ""),
        )

        if sucesso:
            registrar_log("vale_transporte_linha_criada", mensagem)
            flash(mensagem, "success")
            return redirect(url_for("vale_transporte.listar_linhas"))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/vale_transporte/linha_form.html",
        linha=None,
        modo="nova",
        formatar_moeda_brl=formatar_moeda_brl,
    )


@vale_transporte_bp.route("/linhas/<int:linha_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "editar")
def editar_linha(linha_id):
    linha = buscar_linha_por_id(linha_id)

    if not linha:
        flash("Linha de ônibus não encontrada.", "warning")
        return redirect(url_for("vale_transporte.listar_linhas"))

    if request.method == "POST":
        sucesso, mensagem = salvar_linha_onibus(
            linha=linha,
            nome=request.form.get("nome", ""),
            codigo=request.form.get("codigo", ""),
            empresa_transporte=request.form.get("empresa_transporte", ""),
            valor_tarifa_dia=request.form.get("valor_tarifa_dia", ""),
        )

        if sucesso:
            registrar_log(
                "vale_transporte_linha_atualizada",
                f"Linha de ônibus atualizada. ID: {linha.id}.",
            )
            flash(mensagem, "success")
            return redirect(url_for("vale_transporte.listar_linhas"))

        flash(mensagem, "danger")

    return render_template(
        "departamento_pessoal/vale_transporte/linha_form.html",
        linha=linha,
        modo="editar",
        formatar_moeda_brl=formatar_moeda_brl,
    )


@vale_transporte_bp.route("/linhas/<int:linha_id>/status", methods=["POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "excluir")
def alterar_status_linha(linha_id):
    linha = buscar_linha_por_id(linha_id)

    if not linha:
        flash("Linha de ônibus não encontrada.", "warning")
        return redirect(url_for("vale_transporte.listar_linhas"))

    sucesso, mensagem = alternar_status_linha(linha)

    if sucesso:
        registrar_log(
            "vale_transporte_linha_status",
            f"Status da linha de ônibus alterado. ID: {linha.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(url_for("vale_transporte.listar_linhas"))


@vale_transporte_bp.route("/vinculos", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def vinculos():
    colaborador_id = request.values.get("colaborador_id", "").strip()
    colaborador = buscar_colaborador_por_id(colaborador_id) if colaborador_id else None

    if request.method == "POST":
        if not _pode("criar"):
            flash("Você não tem permissão para criar vínculos.", "danger")
            return redirect(url_for("main.acesso_negado"))

        sucesso, mensagem = salvar_vinculo_colaborador_linha(
            colaborador=colaborador,
            linha_onibus_id=request.form.get("linha_onibus_id"),
            tipo_pagamento=request.form.get("tipo_pagamento"),
            periodicidade_pagamento=request.form.get("periodicidade_pagamento"),
        )

        if sucesso:
            registrar_log(
                "vale_transporte_vinculo_criado",
                f"Vínculo de Vale Transporte criado. Colaborador ID: {colaborador.id}.",
            )
            flash(mensagem, "success")
            return redirect(
                url_for(
                    "vale_transporte.vinculos",
                    colaborador_id=colaborador.id,
                )
            )

        flash(mensagem, "danger")

    vinculos_colaborador = (
        buscar_vinculos_colaborador(colaborador.id)
        if colaborador else []
    )

    return render_template(
        "departamento_pessoal/vale_transporte/vinculos.html",
        colaboradores=listar_colaboradores_para_vinculo(),
        linhas_ativas=listar_linhas_ativas(),
        colaborador=colaborador,
        colaborador_id_selecionado=colaborador_id,
        vinculos=vinculos_colaborador,
        tipos_pagamento=TIPOS_PAGAMENTO,
        periodicidades_pagamento=PERIODICIDADES_PAGAMENTO,
        formatar_moeda_brl=formatar_moeda_brl,
        pode_criar=_pode("criar"),
        pode_editar=_pode("editar"),
        pode_excluir=_pode("excluir"),
    )


@vale_transporte_bp.route("/vinculos/<int:vinculo_id>/editar", methods=["POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "editar")
def editar_vinculo(vinculo_id):
    vinculo = buscar_vinculo_por_id(vinculo_id)

    if not vinculo:
        flash("Vínculo não encontrado.", "warning")
        return redirect(url_for("vale_transporte.vinculos"))

    sucesso, mensagem = atualizar_pagamento_vinculo(
        vinculo,
        request.form.get("tipo_pagamento"),
        request.form.get("periodicidade_pagamento"),
    )

    if sucesso:
        registrar_log(
            "vale_transporte_vinculo_atualizado",
            f"Dados de pagamento de vínculo atualizados. ID: {vinculo.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(
        url_for(
            "vale_transporte.vinculos",
            colaborador_id=vinculo.colaborador_id,
        )
    )


@vale_transporte_bp.route("/vinculos/<int:vinculo_id>/status", methods=["POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "excluir")
def alterar_status_vinculo(vinculo_id):
    vinculo = buscar_vinculo_por_id(vinculo_id)

    if not vinculo:
        flash("Vínculo não encontrado.", "warning")
        return redirect(url_for("vale_transporte.vinculos"))

    if not vinculo.ativo and LinhaOnibus.query.get(vinculo.linha_onibus_id):
        ativo_duplicado = any(
            outro.id != vinculo.id
            and outro.ativo
            and outro.linha_onibus_id == vinculo.linha_onibus_id
            for outro in buscar_vinculos_colaborador(vinculo.colaborador_id)
        )

        if ativo_duplicado:
            flash("Esta linha de ônibus já está vinculada a este colaborador.", "danger")
            return redirect(
                url_for(
                    "vale_transporte.vinculos",
                    colaborador_id=vinculo.colaborador_id,
                )
            )

    sucesso, mensagem = alternar_status_vinculo(vinculo)

    if sucesso:
        registrar_log(
            "vale_transporte_vinculo_status",
            f"Status de vínculo de Vale Transporte alterado. ID: {vinculo.id}.",
        )
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")

    return redirect(
        url_for(
            "vale_transporte.vinculos",
            colaborador_id=vinculo.colaborador_id,
        )
    )
