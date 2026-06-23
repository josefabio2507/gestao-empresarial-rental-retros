from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.decorators import module_permission_required
from app.models import LinhaOnibus
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.departamento_pessoal.vale_transporte.services import (
    PERIODICIDADES_PAGAMENTO,
    TIPOS_PAGAMENTO,
    alternar_status_linha,
    alternar_status_vinculo,
    atualizar_pagamento_vinculo,
    buscar_colaborador_por_id,
    buscar_linha_por_id,
    buscar_linhas_onibus,
    buscar_vinculo_por_id,
    buscar_vinculos_colaborador,
    formatar_moeda_brl,
    listar_colaboradores_para_vinculo,
    listar_linhas_ativas,
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
