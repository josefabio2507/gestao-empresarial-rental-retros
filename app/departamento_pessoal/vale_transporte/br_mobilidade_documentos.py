"""Captura do boleto e relatório da BR Mobilidade para download imediato."""
from decimal import Decimal

from flask import current_app

from app.extensions import db
from app.models import ValeTransporteIntegracaoBRMobilidade
from app.departamento_pessoal.vale_transporte.br_mobilidade_portal import (
    BRMobilidadePortalErro,
    capturar_documentos_br_mobilidade_com_config,
)


def capturar_documentos_para_download(integracao_id, config=None):
    config = config or current_app.config
    integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
    if not integracao:
        raise ValueError("Integração BR Mobilidade não encontrada.")
    if integracao.status_interno != "FINALIZADO_PORTAL":
        raise ValueError("O pedido ainda não está pronto para capturar documentos.")
    if not integracao.numero_pedido_portal:
        raise ValueError("O pedido não possui número confirmado no Portal.")

    try:
        resultado = capturar_documentos_br_mobilidade_com_config(
            integracao.numero_pedido_portal,
            config,
        )
        integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
        creditos = Decimal(integracao.valor_creditos or 0)
        cartoes = Decimal(integracao.valor_cartoes or 0)
        taxa = resultado.valor_historico - creditos - cartoes
        if taxa < 0:
            raise BRMobilidadePortalErro(
                "O valor do histórico é inferior aos créditos do pedido."
            )

        integracao.status_portal = resultado.status
        integracao.taxa_administrativa = taxa
        integracao.valor_total_portal = resultado.valor_historico
        integracao.comentario_portal = (
            f"Boleto e relatório do pedido {integracao.numero_pedido_portal} "
            "preparados para download."
        )
        integracao.erro_etapa = None
        integracao.erro_mensagem = None
        db.session.commit()
        return integracao, resultado
    except Exception as erro:
        db.session.rollback()
        integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
        integracao.erro_etapa = "CAPTURA_DOCUMENTOS"
        integracao.erro_mensagem = (
            str(erro)
            if isinstance(erro, (ValueError, BRMobilidadePortalErro))
            else "Falha inesperada ao capturar os documentos do Portal."
        )
        db.session.commit()
        raise
