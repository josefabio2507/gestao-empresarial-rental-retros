from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import OperacaoVeiculoEquipamento, OperacaoVeiculoResponsavel
from app.services.logs_service import registrar_log
from app.services.operacao_abastecimento_service import (
    TIPOS_COMBUSTIVEL,
    buscar_abastecimento_usuario,
    colaborador_do_usuario,
    data_padrao_form,
    listar_abastecimentos_usuario,
    listar_veiculos_abastecimento_usuario,
    salvar_abastecimento,
    vinculo_ativo_usuario_veiculo,
)
from app.services.operacao_pool_service import (
    STATUS_DISPONIVEL,
    STATUS_EM_USO,
    STATUS_INDISPONIVEL,
    TIPOS_LEITURA,
    TIPOS_VEICULO,
    alterar_indisponibilidade_veiculo,
    buscar_centros_custo_ativos,
    buscar_colaboradores_ativos,
    buscar_equipes_ativas,
    buscar_por_id,
    buscar_veiculos_pool,
    corrigir_vinculo,
    leitura_final_anterior_sugerida,
    encerrar_vinculo,
    salvar_veiculo_equipamento,
    vincular_responsavel,
)
from app.services.permissoes_service import usuario_tem_permissao

operacao_bp = Blueprint("operacao", __name__)
MODULO_POOL = "gestao_veiculos_epgs"
STATUS_POOL = [STATUS_DISPONIVEL, STATUS_EM_USO, STATUS_INDISPONIVEL]


@operacao_bp.route("/")
@login_required
def index():
    pode_acessar_gestao_veiculos = usuario_tem_permissao(
        current_user,
        "operacao",
        "gestao_veiculos_epgs",
        "visualizar",
    )

    return render_template(
        "operacao/index.html",
        pode_acessar_gestao_veiculos=pode_acessar_gestao_veiculos,
    )


@operacao_bp.route("/status")
@login_required
def status():
    return "Operação online."


@operacao_bp.route("/abastecimentos")
@login_required
@module_permission_required("operacao", MODULO_POOL, "visualizar")
def abastecimentos():
    colaborador = colaborador_do_usuario(current_user)
    if not colaborador:
        flash("Usuario logado precisa estar vinculado a um colaborador ativo para registrar abastecimentos.", "danger")
        return redirect(url_for("operacao.pool"))

    return render_template(
        "operacao/abastecimentos.html",
        colaborador=colaborador,
        veiculos=listar_veiculos_abastecimento_usuario(current_user),
        abastecimentos=listar_abastecimentos_usuario(current_user),
    )


@operacao_bp.route("/abastecimentos/veiculos/<int:veiculo_id>/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "editar")
def novo_abastecimento(veiculo_id):
    veiculo = buscar_por_id(OperacaoVeiculoEquipamento, veiculo_id)
    vinculo = vinculo_ativo_usuario_veiculo(current_user, veiculo_id)
    if not veiculo or not vinculo:
        flash("Veiculo/equipamento nao esta vinculado ao usuario logado.", "danger")
        return redirect(url_for("operacao.abastecimentos"))

    if request.method == "POST":
        sucesso, mensagem, abastecimento = salvar_abastecimento(request.form, request.files, current_user, veiculo=veiculo)
        if sucesso:
            registrar_log("operacao_abastecimento_criado", f"Abastecimento registrado. ID: {abastecimento.id}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.abastecimentos"))
        flash(mensagem, "danger")

    return render_template(
        "operacao/abastecimento_form.html",
        abastecimento=None,
        veiculo=veiculo,
        vinculo=vinculo,
        colaborador=vinculo.colaborador,
        equipe=vinculo.equipe or vinculo.colaborador.equipe,
        tipos_combustivel=TIPOS_COMBUSTIVEL,
        data_padrao=data_padrao_form(),
        modo="novo",
    )


@operacao_bp.route("/abastecimentos/<int:abastecimento_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "editar")
def editar_abastecimento(abastecimento_id):
    abastecimento = buscar_abastecimento_usuario(abastecimento_id, current_user)
    if not abastecimento:
        flash("Abastecimento nao encontrado para o usuario logado.", "warning")
        return redirect(url_for("operacao.abastecimentos"))

    vinculo = vinculo_ativo_usuario_veiculo(current_user, abastecimento.veiculo_id)
    if not vinculo:
        flash("Veiculo/equipamento nao esta mais vinculado ao usuario logado.", "danger")
        return redirect(url_for("operacao.abastecimentos"))

    if request.method == "POST":
        sucesso, mensagem, abastecimento = salvar_abastecimento(
            request.form,
            request.files,
            current_user,
            abastecimento=abastecimento,
        )
        if sucesso:
            registrar_log("operacao_abastecimento_atualizado", f"Abastecimento atualizado. ID: {abastecimento.id}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.abastecimentos"))
        flash(mensagem, "danger")

    return render_template(
        "operacao/abastecimento_form.html",
        abastecimento=abastecimento,
        veiculo=abastecimento.veiculo,
        vinculo=vinculo,
        colaborador=abastecimento.colaborador,
        equipe=abastecimento.equipe,
        tipos_combustivel=TIPOS_COMBUSTIVEL,
        data_padrao=abastecimento.data_abastecimento.isoformat(),
        modo="editar",
    )

@operacao_bp.route("/pool-veiculos")
@login_required
@module_permission_required("operacao", MODULO_POOL, "visualizar")
def pool():
    return render_template(
        "operacao/pool.html",
        veiculos=buscar_veiculos_pool(
            request.args.get("termo"),
            request.args.get("status"),
            request.args.get("tipo"),
        ),
        filtros=request.args,
        status_pool=STATUS_POOL,
        tipos_veiculo=TIPOS_VEICULO,
    )


@operacao_bp.route("/pool-veiculos/ativos/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "criar")
def novo_veiculo():
    if request.method == "POST":
        sucesso, mensagem, veiculo = salvar_veiculo_equipamento(request.form)
        if sucesso:
            registrar_log("operacao_veiculo_criado", f"Veiculo/equipamento criado. ID: {veiculo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.pool"))
        flash(mensagem, "danger")

    return render_template(
        "operacao/veiculo_form.html",
        veiculo=None,
        modo="novo",
        tipos_veiculo=TIPOS_VEICULO,
        centros_custo=buscar_centros_custo_ativos(),
    )


@operacao_bp.route("/pool-veiculos/ativos/<int:veiculo_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "editar")
def editar_veiculo(veiculo_id):
    veiculo = buscar_por_id(OperacaoVeiculoEquipamento, veiculo_id)
    if not veiculo:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("operacao.pool"))

    if request.method == "POST":
        sucesso, mensagem, veiculo = salvar_veiculo_equipamento(request.form, veiculo)
        if sucesso:
            registrar_log("operacao_veiculo_atualizado", f"Veiculo/equipamento atualizado. ID: {veiculo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.pool"))
        flash(mensagem, "danger")

    return render_template(
        "operacao/veiculo_form.html",
        veiculo=veiculo,
        modo="editar",
        tipos_veiculo=TIPOS_VEICULO,
        centros_custo=buscar_centros_custo_ativos(),
    )


@operacao_bp.route("/pool-veiculos/ativos/<int:veiculo_id>/vincular", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "editar")
def vincular_veiculo(veiculo_id):
    veiculo = buscar_por_id(OperacaoVeiculoEquipamento, veiculo_id)
    if not veiculo:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("operacao.pool"))

    colaborador_logado = getattr(current_user, "colaborador", None)
    if not colaborador_logado or not colaborador_logado.ativo:
        flash("Usuario logado precisa estar vinculado a um colaborador ativo para assumir o ativo.", "danger")
        return redirect(url_for("operacao.pool"))

    leitura_final_anterior = leitura_final_anterior_sugerida(veiculo)
    leitura_final_anterior_form = (
        format(leitura_final_anterior, "f").replace(".", ",")
        if leitura_final_anterior is not None
        else ""
    )

    if request.method == "POST":
        dados_vinculo = request.form.to_dict()
        dados_vinculo["colaborador_id"] = str(colaborador_logado.id)
        dados_vinculo["equipe_id"] = str(colaborador_logado.equipe_id)
        if leitura_final_anterior is not None:
            dados_vinculo["leitura_final_anterior"] = leitura_final_anterior_form

        sucesso, mensagem, vinculo = vincular_responsavel(dados_vinculo, usuario=current_user, veiculo=veiculo)
        if sucesso:
            registrar_log("operacao_vinculo_criado", f"Vinculo operacional criado. ID: {vinculo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.historico_veiculo", veiculo_id=veiculo.id))
        flash(mensagem, "danger")

    return render_template(
        "operacao/vinculo_form.html",
        veiculo=veiculo,
        colaborador=colaborador_logado,
        equipe=colaborador_logado.equipe,
        leitura_final_anterior=leitura_final_anterior_form,
        tipos_leitura=TIPOS_LEITURA,
    )


@operacao_bp.route("/pool-veiculos/vinculos/<int:vinculo_id>/encerrar", methods=["POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "editar")
def encerrar_vinculo_rota(vinculo_id):
    vinculo = buscar_por_id(OperacaoVeiculoResponsavel, vinculo_id)
    sucesso, mensagem = encerrar_vinculo(vinculo, request.form, usuario=current_user)
    if sucesso:
        registrar_log("operacao_vinculo_encerrado", f"Vinculo operacional encerrado. ID: {vinculo.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("operacao.historico_veiculo", veiculo_id=vinculo.veiculo_id if vinculo else 0))


@operacao_bp.route("/pool-veiculos/vinculos/<int:vinculo_id>/corrigir", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "excluir")
def corrigir_vinculo_rota(vinculo_id):
    vinculo = buscar_por_id(OperacaoVeiculoResponsavel, vinculo_id)
    if not vinculo:
        flash("Vinculo nao encontrado.", "warning")
        return redirect(url_for("operacao.pool"))

    if request.method == "POST":
        sucesso, mensagem, _ = corrigir_vinculo(vinculo, request.form, usuario=current_user)
        if sucesso:
            registrar_log("operacao_vinculo_corrigido", f"Vinculo operacional corrigido. ID: {vinculo.id}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.historico_veiculo", veiculo_id=vinculo.veiculo_id))
        flash(mensagem, "danger")

    return render_template(
        "operacao/correcao_vinculo.html",
        vinculo=vinculo,
        colaboradores=buscar_colaboradores_ativos(),
        equipes=buscar_equipes_ativas(),
        tipos_leitura=TIPOS_LEITURA,
    )


@operacao_bp.route("/pool-veiculos/ativos/<int:veiculo_id>/indisponibilidade", methods=["POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL, "excluir")
def indisponibilidade_veiculo(veiculo_id):
    veiculo = buscar_por_id(OperacaoVeiculoEquipamento, veiculo_id)
    indisponivel = request.form.get("acao") != "disponibilizar"
    sucesso, mensagem = alterar_indisponibilidade_veiculo(
        veiculo,
        indisponivel=indisponivel,
        motivo=request.form.get("motivo_indisponibilidade"),
    )
    if sucesso:
        registrar_log("operacao_veiculo_indisponibilidade", f"Status operacional alterado. ID: {veiculo.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("operacao.pool"))


@operacao_bp.route("/pool-veiculos/ativos/<int:veiculo_id>/historico")
@login_required
@module_permission_required("operacao", MODULO_POOL, "visualizar")
def historico_veiculo(veiculo_id):
    veiculo = buscar_por_id(OperacaoVeiculoEquipamento, veiculo_id)
    if not veiculo:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("operacao.pool"))

    return render_template("operacao/historico.html", veiculo=veiculo)
