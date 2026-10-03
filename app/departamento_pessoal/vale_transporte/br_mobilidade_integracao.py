import hashlib
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ValeTransporteIntegracaoBRMobilidade, ValeTransportePedido
from app.departamento_pessoal.vale_transporte.br_mobilidade_arquivo import (
    gerar_arquivo_br_mobilidade,
    nome_arquivo_br_mobilidade,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_conferencia import (
    conferir_resumo_pedido,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_portal import (
    BRMobilidadePortalErro,
    consultar_status_arquivo_br_mobilidade_com_config,
    enviar_arquivo_br_mobilidade_com_config,
)


STATUS_ATIVOS = {"AGUARDANDO_ENVIO", "ENVIANDO", "AGUARDANDO_STATUS"}
STATUS_MANUAIS = {
    "AGUARDANDO_CRIACAO_MANUAL",
    "CRIADO_MANUAL_SEM_CONFERENCIA",
    "AGUARDANDO_AUTORIZACAO_FINALIZACAO",
    "AUTORIZADO_FINALIZACAO",
    "FINALIZANDO_PORTAL",
    "FINALIZADO_PORTAL",
    "ERRO_FINALIZACAO",
    "FINALIZACAO_INCERTA",
}


def registrar_criacao_manual_br_mobilidade(integracao_id, resumo):
    """Confere e registra no sistema um pedido criado manualmente no portal."""
    integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
    if not integracao:
        raise ValueError("Integração BR Mobilidade não encontrada.")
    if integracao.status_interno != "AGUARDANDO_CRIACAO_MANUAL":
        raise ValueError("Esta integração não está aguardando criação manual.")

    numero = (resumo.numero or "").strip()
    if not numero or not numero.isdigit():
        raise ValueError("Informe um número de pedido válido do Portal BR Mobilidade.")

    integracao.numero_pedido_portal = numero
    conferencia = conferir_resumo_pedido(integracao, resumo)
    if not conferencia.aprovado:
        db.session.rollback()
        raise ValueError(" ".join(conferencia.divergencias))

    integracao.status_portal = resumo.status
    integracao.status_interno = "FINALIZADO_PORTAL"
    integracao.consultado_em = datetime.now()
    integracao.finalizado_portal_em = datetime.now()
    integracao.taxa_administrativa = resumo.taxa_administrativa
    integracao.valor_cartoes = resumo.valor_cartoes
    integracao.valor_total_portal = resumo.valor_total
    integracao.data_pedido_portal = resumo.data_pedido
    integracao.comentario_portal = (
        "Criação manual conferida: "
        f"créditos R$ {resumo.valor_creditos:.2f}; "
        f"taxa administrativa R$ {resumo.taxa_administrativa:.2f}; "
        f"cartões R$ {resumo.valor_cartoes:.2f}; "
        f"total R$ {resumo.valor_total:.2f}; "
        f"liberação {resumo.data_liberacao.strftime('%d/%m/%Y')}."
    )
    integracao.erro_etapa = None
    integracao.erro_mensagem = None
    integracao.erros_portal = "[]"
    try:
        db.session.commit()
    except IntegrityError as erro:
        db.session.rollback()
        raise ValueError("Este número de pedido do portal já foi registrado.") from erro
    return integracao, conferencia


def preparar_integracao_br_mobilidade(
    pedido,
    *,
    data_liberacao,
    criado_por_id=None,
    config=None,
    modo_manual=False,
):
    config = config or current_app.config
    if not config.get("BR_MOBILIDADE_INTEGRACAO_ATIVA"):
        raise ValueError("A integração BR Mobilidade não está ativa neste ambiente.")
    pedido = (
        ValeTransportePedido.query
        .filter_by(id=pedido.id)
        .with_for_update()
        .first()
    )
    if not pedido:
        raise ValueError("Pedido de Vale Transporte não encontrado.")
    if pedido.status == "Cancelado":
        raise ValueError("Pedido cancelado não pode ser enviado à BR Mobilidade.")
    if any(
        i.status_interno in STATUS_ATIVOS | STATUS_MANUAIS
        for i in pedido.integracoes_br_mobilidade
    ):
        raise ValueError("Já existe uma integração em andamento para este pedido.")
    if any(
        i.status_interno in {"IMPORTADO", "FINALIZADO_PORTAL"}
        for i in pedido.integracoes_br_mobilidade
    ):
        raise ValueError("Este pedido já foi importado no Portal BR Mobilidade.")

    conteudo, validacao = gerar_arquivo_br_mobilidade(
        pedido,
        encoding=config.get("BR_MOBILIDADE_ARQUIVO_ENCODING", "cp1252"),
    )
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    chave = hashlib.sha256(f"{pedido.id}:{hash_arquivo}".encode()).hexdigest()
    base = Path(nome_arquivo_br_mobilidade(pedido))
    nome = f"{base.stem}_P{pedido.id}_{hash_arquivo[:8].upper()}{base.suffix}"

    integracao = ValeTransporteIntegracaoBRMobilidade(
        pedido_id=pedido.id,
        chave_idempotencia=chave,
        ambiente=config.get("BR_MOBILIDADE_AMBIENTE", "local"),
        data_liberacao=data_liberacao,
        quantidade_colaboradores=validacao.quantidade_colaboradores,
        valor_creditos=validacao.valor_total_creditos,
        nome_arquivo=nome,
        hash_arquivo=hash_arquivo,
        arquivo_conteudo=conteudo,
        status_interno=(
            "AGUARDANDO_CRIACAO_MANUAL" if modo_manual else "AGUARDANDO_ENVIO"
        ),
        criado_por_id=criado_por_id,
    )
    db.session.add(integracao)
    try:
        db.session.commit()
    except IntegrityError as erro:
        db.session.rollback()
        raise ValueError("Este conteúdo já foi preparado ou enviado anteriormente.") from erro
    return integracao


def _registrar_status_portal(integracao, resultado):
    integracao.status_portal = resultado.status
    integracao.comentario_portal = resultado.comentario
    integracao.consultado_em = datetime.now()
    integracao.erros_portal = json.dumps(
        [{"linha": erro.linha, "mensagem": erro.mensagem} for erro in resultado.erros],
        ensure_ascii=False,
    )
    if resultado.processado_com_sucesso:
        integracao.status_interno = "IMPORTADO"
    elif resultado.possui_erro:
        integracao.status_interno = "ERRO_IMPORTACAO"
    else:
        integracao.status_interno = "AGUARDANDO_STATUS"


def processar_integracao_br_mobilidade(integracao_id, config=None):
    config = config or current_app.config
    integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
    if not integracao:
        raise ValueError("Integração BR Mobilidade não encontrada.")
    if integracao.status_interno not in STATUS_ATIVOS:
        return integracao

    try:
        if integracao.status_interno == "AGUARDANDO_ENVIO":
            reivindicada = (
                ValeTransporteIntegracaoBRMobilidade.query
                .filter_by(id=integracao.id, status_interno="AGUARDANDO_ENVIO")
                .update(
                    {
                        "status_interno": "ENVIANDO",
                        "erro_etapa": None,
                        "erro_mensagem": None,
                    },
                    synchronize_session=False,
                )
            )
            db.session.commit()
            if not reivindicada:
                return db.session.get(
                    ValeTransporteIntegracaoBRMobilidade, integracao_id
                )
            integracao = db.session.get(
                ValeTransporteIntegracaoBRMobilidade, integracao_id
            )
            with TemporaryDirectory(prefix="vt_br_") as pasta:
                caminho = Path(pasta) / integracao.nome_arquivo
                caminho.write_bytes(integracao.arquivo_conteudo)
                envio = enviar_arquivo_br_mobilidade_com_config(caminho, config)
            integracao.enviado_em = envio.enviado_em
            integracao.status_interno = "AGUARDANDO_STATUS"
            db.session.commit()

        try:
            resultado = consultar_status_arquivo_br_mobilidade_com_config(
                integracao.nome_arquivo,
                config,
            )
        except BRMobilidadePortalErro as erro:
            integracao.erro_etapa = "CONSULTA_STATUS"
            integracao.erro_mensagem = str(erro)
            db.session.commit()
            return integracao

        _registrar_status_portal(integracao, resultado)
        db.session.commit()
        return integracao
    except Exception as erro:
        db.session.rollback()
        integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
        integracao.status_interno = "ERRO_ENVIO"
        integracao.erro_etapa = "ENVIO"
        integracao.erro_mensagem = (
            str(erro) if isinstance(erro, (ValueError, BRMobilidadePortalErro))
            else "Falha inesperada durante o envio ao Portal BR Mobilidade."
        )
        db.session.commit()
        return integracao


def buscar_integracoes_pendentes(limite=10):
    return (
        ValeTransporteIntegracaoBRMobilidade.query
        .filter(ValeTransporteIntegracaoBRMobilidade.status_interno.in_(STATUS_ATIVOS))
        .order_by(ValeTransporteIntegracaoBRMobilidade.criado_em.asc())
        .limit(limite)
        .all()
    )
