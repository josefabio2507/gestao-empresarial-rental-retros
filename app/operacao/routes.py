from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.models import OperacaoAbastecimento, OperacaoMultaTransito, OperacaoVeiculoEquipamento, OperacaoVeiculoResponsavel
from app.services.logs_service import registrar_log
from app.services.operacao_central_custos_service import (
    STATUS_CENTRAL_CUSTOS,
    buscar_veiculos_central_custos,
    central_custos_veiculo as central_custos_veiculo_service,
    periodo_filtros,
)
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
from app.services.operacao_impostos_taxas_service import (
    PARCELAS_IMPOSTO_TAXA,
    TIPOS_IMPOSTO_TAXA,
    buscar_imposto_taxa,
    listar_impostos_taxas,
    salvar_impostos_taxas,
    veiculos_para_impostos_taxas,
)
from app.services.operacao_multas_transito_service import (
    CIDADES_MULTA,
    GRAVIDADES_MULTA,
    buscar_multa,
    colaboradores_para_indicacao,
    data_form,
    hora_form,
    listar_multas_transito,
    listar_motoristas_vinculados_multas,
    motorista_vinculado_na_data,
    salvar_multa_transito,
    veiculos_para_multas,
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
from app.services.operacao_permissoes_service import (
    MODULO_ABASTECIMENTO,
    MODULO_CENTRAL_CUSTOS,
    MODULO_IMPOSTOS_TAXAS,
    MODULO_MULTAS_TRANSITO,
    MODULO_POOL_VEICULOS,
    MODULO_VEICULOS_EQUIPAMENTOS,
    permissoes_cards_gestao,
    usuario_tem_algum_submodulo_gestao,
)
from app.services.suprimentos_service import formatar_moeda_brl

operacao_bp = Blueprint("operacao", __name__)
STATUS_POOL = [STATUS_DISPONIVEL, STATUS_EM_USO, STATUS_INDISPONIVEL]


@operacao_bp.route("/")
@login_required
def index():
    pode_acessar_gestao_veiculos = usuario_tem_algum_submodulo_gestao(current_user)

    return render_template(
        "operacao/index.html",
        pode_acessar_gestao_veiculos=pode_acessar_gestao_veiculos,
    )


@operacao_bp.route("/status")
@login_required
def status():
    return "Operação online."


@operacao_bp.route("/impostos-taxas")
@login_required
@module_permission_required("operacao", MODULO_IMPOSTOS_TAXAS, "visualizar")
def impostos_taxas():
    return render_template(
        "operacao/impostos_taxas.html",
        lancamentos=listar_impostos_taxas(),
        parcelas=dict(PARCELAS_IMPOSTO_TAXA),
        formatar_moeda_brl=formatar_moeda_brl,
    )


@operacao_bp.route("/impostos-taxas/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_IMPOSTOS_TAXAS, "criar")
def novo_imposto_taxa():
    if request.method == "POST":
        sucesso, mensagem, lancamentos = salvar_impostos_taxas(request.form, current_user)
        if sucesso:
            registrar_log("operacao_impostos_taxas_criados", f"Impostos e taxas criados. Quantidade: {len(lancamentos)}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.impostos_taxas"))
        flash(mensagem, "danger")

    return render_template(
        "operacao/imposto_taxa_form.html",
        veiculos=veiculos_para_impostos_taxas(),
        tipos_custo=TIPOS_IMPOSTO_TAXA,
        parcelas=PARCELAS_IMPOSTO_TAXA,
        dados=request.form,
    )


@operacao_bp.route("/impostos-taxas/<int:lancamento_id>/ver")
@login_required
@module_permission_required("operacao", MODULO_IMPOSTOS_TAXAS, "visualizar")
def ver_imposto_taxa(lancamento_id):
    lancamento = buscar_imposto_taxa(lancamento_id)
    if not lancamento:
        flash("Imposto ou taxa nao encontrado.", "warning")
        return redirect(url_for("operacao.impostos_taxas"))

    return render_template(
        "operacao/imposto_taxa_detalhes.html",
        lancamento=lancamento,
        parcelas=dict(PARCELAS_IMPOSTO_TAXA),
        formatar_moeda_brl=formatar_moeda_brl,
    )

@operacao_bp.route("/central-custos")
@login_required
@module_permission_required("operacao", MODULO_CENTRAL_CUSTOS, "visualizar")
def central_custos():
    veiculos, status_filtro = buscar_veiculos_central_custos(request.args)
    return render_template(
        "operacao/central_custos.html",
        veiculos=veiculos,
        filtros=request.args,
        status_filtro=status_filtro,
        status_opcoes=STATUS_CENTRAL_CUSTOS,
    )


@operacao_bp.route("/central-custos/veiculos/<int:veiculo_id>")
@login_required
@module_permission_required("operacao", MODULO_CENTRAL_CUSTOS, "visualizar")
def central_custos_veiculo(veiculo_id):
    veiculo = buscar_por_id(OperacaoVeiculoEquipamento, veiculo_id)
    if not veiculo:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("operacao.central_custos"))

    data_inicio, data_fim = periodo_filtros(request.args)
    grupos, total_geral = central_custos_veiculo_service(veiculo, data_inicio, data_fim)
    return render_template(
        "operacao/central_custos_veiculo.html",
        veiculo=veiculo,
        grupos=grupos,
        total_geral=total_geral,
        filtros=request.args,
        data_inicio=data_inicio,
        data_fim=data_fim,
        formatar_moeda_brl=formatar_moeda_brl,
    )

@operacao_bp.route("/abastecimentos")
@login_required
@module_permission_required("operacao", MODULO_ABASTECIMENTO, "visualizar")
def abastecimentos():
    colaborador = colaborador_do_usuario(current_user)
    if not colaborador and not current_user.is_admin:
        flash("Usuario logado precisa estar vinculado a um colaborador ativo para registrar abastecimentos.", "danger")
        return redirect(url_for("operacao.pool"))

    return render_template(
        "operacao/abastecimentos.html",
        colaborador=colaborador,
        veiculos=listar_veiculos_abastecimento_usuario(current_user),
        abastecimentos=listar_abastecimentos_usuario(current_user),
        eh_admin=current_user.is_admin,
    )


@operacao_bp.route("/abastecimentos/veiculos/<int:veiculo_id>/novo", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_ABASTECIMENTO, "criar")
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


@operacao_bp.route("/abastecimentos/<int:abastecimento_id>/ver")
@login_required
@module_permission_required("operacao", MODULO_ABASTECIMENTO, "visualizar")
def ver_abastecimento(abastecimento_id):
    abastecimento = buscar_por_id(OperacaoAbastecimento, abastecimento_id)
    if not abastecimento:
        flash("Abastecimento nao encontrado.", "warning")
        return redirect(url_for("operacao.central_custos"))

    return render_template(
        "operacao/abastecimento_detalhes.html",
        abastecimento=abastecimento,
        formatar_moeda_brl=formatar_moeda_brl,
    )

@operacao_bp.route("/abastecimentos/<int:abastecimento_id>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_ABASTECIMENTO, "editar")
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

@operacao_bp.route("/multas-transito")
@login_required
@module_permission_required("operacao", MODULO_MULTAS_TRANSITO, "visualizar")
def multas_transito():
    return render_template(
        "operacao/multas_transito.html",
        multas=listar_multas_transito(request.args),
        filtros=request.args,
        motoristas_vinculados=listar_motoristas_vinculados_multas(),
        formatar_moeda_brl=formatar_moeda_brl,
    )


@operacao_bp.route("/multas-transito/nova", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_MULTAS_TRANSITO, "criar")
def nova_multa_transito():
    if request.method == "POST":
        sucesso, mensagem, multa = salvar_multa_transito(request.form, current_user)
        if sucesso:
            registrar_log("operacao_multa_transito_criada", f"Multa de transito criada. ID: {multa.id}.")
            flash(mensagem, "success")
            return redirect(url_for("operacao.multas_transito"))
        flash(mensagem, "danger")

    return render_template(
        "operacao/multa_transito_form.html",
        multa=None,
        veiculos=veiculos_para_multas(),
        colaboradores=colaboradores_para_indicacao(),
        cidades=CIDADES_MULTA,
        gravidades=GRAVIDADES_MULTA,
        dados=request.form,
    )


@operacao_bp.route("/multas-transito/<int:multa_id>/ver")
@login_required
@module_permission_required("operacao", MODULO_MULTAS_TRANSITO, "visualizar")
def ver_multa_transito(multa_id):
    multa = buscar_multa(multa_id)
    if not multa:
        flash("Multa de transito nao encontrada.", "warning")
        return redirect(url_for("operacao.multas_transito"))

    return render_template(
        "operacao/multa_transito_detalhes.html",
        multa=multa,
        cidades=dict(CIDADES_MULTA),
        gravidades=dict(GRAVIDADES_MULTA),
        formatar_moeda_brl=formatar_moeda_brl,
    )


@operacao_bp.route("/multas-transito/motorista-vinculado")
@login_required
@module_permission_required("operacao", MODULO_MULTAS_TRANSITO, "visualizar")
def motorista_vinculado_multa():
    data_infracao = data_form(request.args.get("data_infracao"))
    hora_infracao = hora_form(request.args.get("hora_infracao"))
    veiculo_id = request.args.get("veiculo_id", type=int)
    motorista = motorista_vinculado_na_data(veiculo_id, data_infracao, hora_infracao)
    return jsonify({"nome": motorista.nome if motorista else "Sem motorista vinculado na data"})

@operacao_bp.route("/pool-veiculos")
@login_required
@module_permission_required("operacao", MODULO_POOL_VEICULOS, "visualizar")
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
@module_permission_required("operacao", MODULO_VEICULOS_EQUIPAMENTOS, "criar")
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
@module_permission_required("operacao", MODULO_VEICULOS_EQUIPAMENTOS, "editar")
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
@module_permission_required("operacao", MODULO_POOL_VEICULOS, "editar")
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
@module_permission_required("operacao", MODULO_POOL_VEICULOS, "editar")
def encerrar_vinculo_rota(vinculo_id):
    vinculo = buscar_por_id(OperacaoVeiculoResponsavel, vinculo_id)
    sucesso, mensagem = encerrar_vinculo(vinculo, request.form, usuario=current_user)
    if sucesso:
        registrar_log("operacao_vinculo_encerrado", f"Vinculo operacional encerrado. ID: {vinculo.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("operacao.historico_veiculo", veiculo_id=vinculo.veiculo_id if vinculo else 0))


@operacao_bp.route("/pool-veiculos/vinculos/<int:vinculo_id>/corrigir", methods=["GET", "POST"])
@login_required
@module_permission_required("operacao", MODULO_POOL_VEICULOS, "excluir")
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
@module_permission_required("operacao", MODULO_POOL_VEICULOS, "excluir")
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
@module_permission_required("operacao", MODULO_POOL_VEICULOS, "visualizar")
def historico_veiculo(veiculo_id):
    veiculo = buscar_por_id(OperacaoVeiculoEquipamento, veiculo_id)
    if not veiculo:
        flash("Veiculo/equipamento nao encontrado.", "warning")
        return redirect(url_for("operacao.pool"))

    return render_template("operacao/historico.html", veiculo=veiculo)
