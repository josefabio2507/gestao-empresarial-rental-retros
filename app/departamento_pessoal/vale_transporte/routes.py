from io import BytesIO
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import zipfile

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
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
    buscar_historico_vale_transporte_colaborador,
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
    listar_colaboradores_ativos_para_historico,
    listar_colaboradores_para_vinculo,
    listar_linhas_ativas,
    montar_previa_pedido_vale_transporte,
    pedido_vale_transporte_pode_ser_cancelado,
    resolver_colaborador_ativo_para_historico,
    salvar_linha_onibus,
    salvar_vinculo_colaborador_linha,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_arquivo import (
    gerar_arquivo_br_mobilidade,
    nome_arquivo_br_mobilidade,
    validar_pedido_br_mobilidade,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_integracao import (
    STATUS_ATIVOS,
    STATUS_MANUAIS,
    preparar_integracao_br_mobilidade,
    registrar_criacao_manual_br_mobilidade,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_conferencia import (
    ResumoPedidoPortal,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_finalizacao import (
    autorizar_finalizacao,
    iniciar_finalizacao,
    preparar_conferencia_finalizacao,
    registrar_falha_finalizacao,
    registrar_finalizacao_sucesso,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_portal import (
    BRMobilidadeFinalizacaoIncerta,
    BRMobilidadePortalErro,
    executar_pedido_manual_br_mobilidade_com_config,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_documentos import (
    capturar_documentos_para_download,
)


vale_transporte_bp = Blueprint("vale_transporte", __name__)


def _pode(acao):
    return usuario_tem_permissao(
        current_user,
        "departamento_pessoal",
        "vale_transporte",
        acao,
    )


def _erros_integracao_br(integracao):
    try:
        return json.loads(integracao.erros_portal or "[]")
    except (TypeError, ValueError):
        return []


@vale_transporte_bp.route("/")
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def index():
    return render_template("departamento_pessoal/vale_transporte/index.html")


@vale_transporte_bp.route("/historico-colaborador")
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def historico_colaborador():
    colaborador_texto = request.args.get("colaborador", "").strip()
    colaborador_id = request.args.get("colaborador_id", "").strip()
    colaborador = None
    lancamentos = []

    if colaborador_texto or colaborador_id:
        try:
            colaborador = resolver_colaborador_ativo_para_historico(
                colaborador_texto=colaborador_texto,
                colaborador_id=colaborador_id,
            )
            lancamentos = buscar_historico_vale_transporte_colaborador(colaborador.id)
        except ValueError as erro:
            flash(str(erro), "warning")

    return render_template(
        "departamento_pessoal/vale_transporte/historico_colaborador.html",
        colaboradores=listar_colaboradores_ativos_para_historico(),
        colaborador=colaborador,
        colaborador_texto=colaborador_texto,
        lancamentos=lancamentos,
        tipos_pagamento=TIPOS_PAGAMENTO,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brl=formatar_data_brl,
    )


def _filtros_pedido_form():
    return {
        "competencia": request.values.get("competencia", "").strip(),
        "data_inicial": request.values.get("data_inicial", "").strip(),
        "data_final": request.values.get("data_final", "").strip(),
        "quantidade_dias": request.values.get("quantidade_dias", "").strip(),
        "equipe_id": request.values.get("equipe_id", "").strip(),
        "colaborador": request.values.get("colaborador", "").strip(),
        "colaboradores_manuais_ids": [
            valor.strip()
            for valor in request.values.getlist("colaboradores_manuais_ids")
            if valor.strip()
        ],
        "forma_pagamento": request.values.get("forma_pagamento", "todos").strip() or "todos",
        "empresa_transporte": (
            request.values.get("empresa_transporte", "todos").strip() or "todos"
        ),
        "prazo_pagamento": request.values.get("prazo_pagamento", "").strip(),
    }


def _colaboradores_manuais_para_exibicao(colaboradores_ids):
    colaboradores = []
    vistos = set()

    for colaborador_id in colaboradores_ids:
        if colaborador_id in vistos:
            continue
        vistos.add(colaborador_id)

        colaborador = buscar_colaborador_por_id(colaborador_id)
        if colaborador:
            colaboradores.append(colaborador)

    return colaboradores


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
            colaboradores_manuais_ids=filtros["colaboradores_manuais_ids"],
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
                colaboradores_manuais_ids=filtros["colaboradores_manuais_ids"],
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
        colaboradores_manuais=_colaboradores_manuais_para_exibicao(
            filtros["colaboradores_manuais_ids"]
        ),
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

    validacao_br_mobilidade = validar_pedido_br_mobilidade(pedido)

    return render_template(
        "departamento_pessoal/vale_transporte/pedido_detalhes.html",
        pedido=pedido,
        tipos_pagamento=TIPOS_PAGAMENTO,
        periodicidades_pagamento=PERIODICIDADES_PAGAMENTO,
        formatar_moeda_brl=formatar_moeda_brl,
        formatar_data_brl=formatar_data_brl,
        pode_excluir=_pode("excluir"),
        pedido_pode_cancelar=pedido_vale_transporte_pode_ser_cancelado,
        validacao_br_mobilidade=validacao_br_mobilidade,
        pode_exportar=_pode("exportar"),
        pode_preparar_br_mobilidade=(
            _pode("criar") and current_app.config.get("BR_MOBILIDADE_INTEGRACAO_ATIVA")
            and not any(
                integracao.status_interno in STATUS_ATIVOS | STATUS_MANUAIS | {"IMPORTADO"}
                for integracao in pedido.integracoes_br_mobilidade
            )
        ),
        ambiente_br_mobilidade=current_app.config.get("BR_MOBILIDADE_AMBIENTE", "local"),
        automacao_br_mobilidade_disponivel=bool(
            current_app.config.get("BR_MOBILIDADE_LOGIN")
            and current_app.config.get("BR_MOBILIDADE_SENHA")
        ),
        erros_integracao_br=_erros_integracao_br,
    )


@vale_transporte_bp.route("/pedidos/<int:pedido_id>/br-mobilidade/validar", methods=["POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "visualizar")
def validar_arquivo_br_mobilidade_rota(pedido_id):
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)
    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    resultado = validar_pedido_br_mobilidade(pedido)
    if resultado.valido:
        flash(
            f"Arquivo BR Mobilidade válido: {resultado.quantidade_colaboradores} "
            f"colaborador(es), total de {formatar_moeda_brl(resultado.valor_total_creditos)}.",
            "success",
        )
    else:
        for erro in resultado.erros:
            flash(erro, "danger")

    return redirect(
        url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
    )


@vale_transporte_bp.route("/pedidos/<int:pedido_id>/br-mobilidade/arquivo")
@module_permission_required("departamento_pessoal", "vale_transporte", "exportar")
def baixar_arquivo_br_mobilidade(pedido_id):
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)
    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    try:
        conteudo, resultado = gerar_arquivo_br_mobilidade(
            pedido,
            encoding=current_app.config["BR_MOBILIDADE_ARQUIVO_ENCODING"],
        )
    except ValueError as erro:
        for mensagem in str(erro).splitlines():
            flash(mensagem, "danger")
        return redirect(
            url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
        )

    registrar_log(
        "vale_transporte_br_mobilidade_arquivo_gerado",
        f"Arquivo 0200 gerado. Pedido: {pedido.id}. Registros: "
        f"{resultado.quantidade_colaboradores}.",
    )
    return send_file(
        BytesIO(conteudo),
        mimetype="text/plain",
        as_attachment=True,
        download_name=nome_arquivo_br_mobilidade(pedido),
    )


@vale_transporte_bp.route("/pedidos/<int:pedido_id>/br-mobilidade/preparar-manual", methods=["POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "criar")
def preparar_pedido_br_mobilidade_manual(pedido_id):
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)
    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    try:
        data_liberacao = datetime.strptime(
            request.form.get("data_liberacao", "").strip(), "%Y-%m-%d"
        ).date()
        integracao = preparar_integracao_br_mobilidade(
            pedido,
            data_liberacao=data_liberacao,
            criado_por_id=current_user.id if current_user.is_authenticated else None,
            modo_manual=True,
        )
        registrar_log(
            "vale_transporte_br_mobilidade_manual_preparado",
            f"Criação manual BR Mobilidade preparada. Pedido: {pedido.id}. Execução: {integracao.id}.",
        )
        flash(
            "Pedido preparado para criação manual. Nenhum arquivo foi enviado. No Portal, use Pedidos > Incluir, informe os valores e confirme a data de liberação antes de criar o pedido.",
            "warning",
        )
    except ValueError as erro:
        flash(str(erro), "danger")

    return redirect(
        url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
    )


def _decimal_br(campo, rotulo):
    valor = request.form.get(campo, "").strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(valor)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Informe um valor válido para {rotulo}.")


@vale_transporte_bp.route(
    "/pedidos/<int:pedido_id>/br-mobilidade/confirmar-manual", methods=["POST"]
)
@module_permission_required("departamento_pessoal", "vale_transporte", "criar")
def confirmar_pedido_br_mobilidade_manual(pedido_id):
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)
    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    try:
        integracao_id = int(request.form.get("integracao_id", ""))
        integracao = next(
            (item for item in pedido.integracoes_br_mobilidade if item.id == integracao_id),
            None,
        )
        if not integracao:
            raise ValueError("Integração BR Mobilidade não encontrada para este pedido.")

        resumo = ResumoPedidoPortal(
            numero=request.form.get("numero_pedido_portal", "").strip(),
            data_pedido=datetime.strptime(
                request.form.get("data_pedido", "").strip(), "%Y-%m-%d"
            ).date(),
            data_liberacao=datetime.strptime(
                request.form.get("data_liberacao_portal", "").strip(), "%Y-%m-%d"
            ).date(),
            status=request.form.get("status_portal", "").strip() or "Novo",
            valor_creditos=_decimal_br("valor_creditos", "os créditos"),
            taxa_administrativa=_decimal_br(
                "taxa_administrativa", "a taxa administrativa"
            ),
            valor_cartoes=_decimal_br("valor_cartoes", "os cartões"),
            valor_total=_decimal_br("valor_total", "o total"),
            quantidade_usuarios=int(request.form.get("quantidade_usuarios", "")),
        )
        integracao, _ = registrar_criacao_manual_br_mobilidade(integracao.id, resumo)
        registrar_log(
            "vale_transporte_br_mobilidade_manual_confirmado",
            f"Criação manual BR Mobilidade confirmada. Pedido: {pedido.id}. "
            f"Pedido portal: {integracao.numero_pedido_portal}.",
        )
        flash(
            f"Pedido {integracao.numero_pedido_portal} criado e conferido no Portal BR Mobilidade.",
            "success",
        )
    except (ValueError, TypeError) as erro:
        flash(str(erro), "danger")

    return redirect(
        url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
    )


def _integracao_do_pedido(pedido, integracao_id):
    try:
        identificador = int(integracao_id)
    except (TypeError, ValueError) as erro:
        raise ValueError("Integração BR Mobilidade inválida.") from erro
    integracao = next(
        (item for item in pedido.integracoes_br_mobilidade if item.id == identificador),
        None,
    )
    if not integracao:
        raise ValueError("Integração BR Mobilidade não encontrada para este pedido.")
    return integracao


@vale_transporte_bp.route(
    "/pedidos/<int:pedido_id>/br-mobilidade/conferir-finalizacao", methods=["POST"]
)
@module_permission_required("departamento_pessoal", "vale_transporte", "criar")
def conferir_finalizacao_br_mobilidade(pedido_id):
    """Chega ao Passo 4, confere os valores e fecha sem finalizar o pedido."""
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)
    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    try:
        integracao = _integracao_do_pedido(pedido, request.form.get("integracao_id"))
        validacao = validar_pedido_br_mobilidade(pedido)
        if not validacao.valido:
            raise ValueError(" ".join(validacao.erros))
        resumo = executar_pedido_manual_br_mobilidade_com_config(
            validacao.registros,
            integracao.data_liberacao,
            current_app.config,
            autorizar_finalizacao=False,
        )
        integracao, _ = preparar_conferencia_finalizacao(integracao.id, resumo)
        registrar_log(
            "vale_transporte_br_mobilidade_finalizacao_conferida",
            f"Fase 7 conferida sem finalizar. Pedido: {pedido.id}. Execução: {integracao.id}.",
        )
        flash(
            "Conferência aprovada. O pedido ainda não foi finalizado; revise os valores e autorize explicitamente o próximo passo.",
            "success",
        )
    except (ValueError, BRMobilidadePortalErro) as erro:
        flash(str(erro), "danger")

    return redirect(
        url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
    )


@vale_transporte_bp.route(
    "/pedidos/<int:pedido_id>/br-mobilidade/finalizar", methods=["POST"]
)
@module_permission_required("departamento_pessoal", "vale_transporte", "criar")
def finalizar_pedido_br_mobilidade(pedido_id):
    """Finaliza uma única vez, somente após uma autorização humana registrada."""
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)
    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))

    integracao = None
    try:
        if request.form.get("confirmacao") != "FINALIZAR":
            raise ValueError("A confirmação explícita da finalização não foi recebida.")
        integracao = _integracao_do_pedido(pedido, request.form.get("integracao_id"))
        resumo_autorizado = ResumoPedidoPortal(
            numero="",
            data_pedido=integracao.data_pedido_portal,
            data_liberacao=integracao.data_liberacao,
            status=integracao.status_portal or "Novo",
            valor_creditos=Decimal(integracao.valor_creditos),
            taxa_administrativa=Decimal(integracao.taxa_administrativa or 0),
            valor_cartoes=Decimal(integracao.valor_cartoes or 0),
            valor_total=Decimal(integracao.valor_total_portal or 0),
            quantidade_usuarios=integracao.quantidade_colaboradores,
        )
        autorizar_finalizacao(integracao.id, current_user.id)
        iniciar_finalizacao(integracao.id)

        validacao = validar_pedido_br_mobilidade(pedido)
        if not validacao.valido:
            raise ValueError(" ".join(validacao.erros))
        resultado = executar_pedido_manual_br_mobilidade_com_config(
            validacao.registros,
            integracao.data_liberacao,
            current_app.config,
            autorizar_finalizacao=True,
            resumo_autorizado=resumo_autorizado,
        )
        integracao = registrar_finalizacao_sucesso(
            integracao.id,
            numero_pedido_portal=resultado.numero_pedido,
            status_portal=resultado.status,
            finalizado_em=resultado.finalizado_em,
        )
        registrar_log(
            "vale_transporte_br_mobilidade_pedido_finalizado",
            f"Pedido finalizado no Portal BR Mobilidade. Pedido local: {pedido.id}. "
            f"Pedido portal: {integracao.numero_pedido_portal}.",
        )
        flash(
            f"Pedido {integracao.numero_pedido_portal} finalizado no Portal BR Mobilidade.",
            "success",
        )
    except BRMobilidadeFinalizacaoIncerta as erro:
        if integracao:
            registrar_falha_finalizacao(integracao.id, str(erro), resultado_incerto=True)
        flash(str(erro), "danger")
    except (ValueError, BRMobilidadePortalErro) as erro:
        if integracao and integracao.status_interno in {
            "AUTORIZADO_FINALIZACAO",
            "FINALIZANDO_PORTAL",
        }:
            registrar_falha_finalizacao(integracao.id, str(erro), resultado_incerto=False)
        flash(str(erro), "danger")

    return redirect(
        url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
    )


@vale_transporte_bp.route(
    "/pedidos/<int:pedido_id>/br-mobilidade/capturar-documentos", methods=["POST"]
)
@module_permission_required("departamento_pessoal", "vale_transporte", "exportar")
def capturar_documentos_pedido_br_mobilidade(pedido_id):
    pedido = buscar_pedido_vale_transporte_por_id(pedido_id)
    if not pedido:
        flash("Pedido de Vale Transporte não encontrado.", "warning")
        return redirect(url_for("vale_transporte.listar_pedidos_vale_transporte"))
    try:
        integracao = _integracao_do_pedido(pedido, request.form.get("integracao_id"))
        integracao, documentos = capturar_documentos_para_download(
            integracao.id, current_app.config
        )
        pacote = BytesIO()
        with zipfile.ZipFile(pacote, "w", compression=zipfile.ZIP_DEFLATED) as arquivo_zip:
            arquivo_zip.writestr(
                f"BOLETO_BR_MOBILIDADE_{integracao.numero_pedido_portal}.pdf",
                documentos.boleto_pdf,
            )
            arquivo_zip.writestr(
                f"RELATORIO_BR_MOBILIDADE_{integracao.numero_pedido_portal}.pdf",
                documentos.relatorio_pdf,
            )
        pacote.seek(0)
        registrar_log(
            "vale_transporte_br_mobilidade_documentos_baixados",
            f"Boleto e relatório preparados para download. Pedido local: {pedido.id}. "
            f"Pedido portal: {integracao.numero_pedido_portal}.",
        )
        return send_file(
            pacote,
            mimetype="application/zip",
            as_attachment=True,
            download_name=(
                f"DOCUMENTOS_BR_MOBILIDADE_{integracao.numero_pedido_portal}.zip"
            ),
        )
    except (ValueError, BRMobilidadePortalErro) as erro:
        flash(str(erro), "danger")
    return redirect(
        url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido.id)
    )


@vale_transporte_bp.route("/pedidos/<int:pedido_id>/br-mobilidade/enviar", methods=["POST"])
@module_permission_required("departamento_pessoal", "vale_transporte", "criar")
def enviar_pedido_br_mobilidade(pedido_id):
    """Impede que links/formulários antigos importem pedidos sem a data escolhida."""
    flash(
        "Envio automático pelo arquivo 0200 bloqueado: esse formato não transmite a data de liberação. Prepare o pedido para criação manual no Portal BR Mobilidade.",
        "danger",
    )
    return redirect(
        url_for("vale_transporte.detalhes_pedido_vale_transporte", pedido_id=pedido_id)
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
