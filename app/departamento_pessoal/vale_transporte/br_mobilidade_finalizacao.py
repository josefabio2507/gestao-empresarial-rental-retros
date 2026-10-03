"""Estados e travas da finalização de pedidos no Portal BR Mobilidade."""

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ValeTransporteIntegracaoBRMobilidade
from app.departamento_pessoal.vale_transporte.br_mobilidade_conferencia import (
    conferir_resumo_pedido,
)


STATUS_AGUARDANDO_AUTORIZACAO = "AGUARDANDO_AUTORIZACAO_FINALIZACAO"
STATUS_AUTORIZADO = "AUTORIZADO_FINALIZACAO"
STATUS_FINALIZANDO = "FINALIZANDO_PORTAL"
STATUS_FINALIZADO = "FINALIZADO_PORTAL"
STATUS_ERRO = "ERRO_FINALIZACAO"
STATUS_INCERTO = "FINALIZACAO_INCERTA"


def preparar_conferencia_finalizacao(integracao_id, resumo):
    """Persiste a conferência do Passo 4 sem autorizar o clique final."""
    integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
    if not integracao:
        raise ValueError("Integração BR Mobilidade não encontrada.")
    if integracao.status_interno != "AGUARDANDO_CRIACAO_MANUAL":
        raise ValueError("A integração não está pronta para conferência final.")

    conferencia = conferir_resumo_pedido(integracao, resumo)
    if not conferencia.aprovado:
        raise ValueError(" ".join(conferencia.divergencias))

    integracao.taxa_administrativa = resumo.taxa_administrativa
    integracao.valor_cartoes = resumo.valor_cartoes
    integracao.valor_total_portal = resumo.valor_total
    integracao.data_pedido_portal = resumo.data_pedido
    integracao.status_portal = resumo.status
    integracao.consultado_em = datetime.now()
    integracao.status_interno = STATUS_AGUARDANDO_AUTORIZACAO
    integracao.comentario_portal = (
        "Conferência aprovada; aguardando autorização explícita para finalizar."
    )
    integracao.erro_etapa = None
    integracao.erro_mensagem = None
    db.session.commit()
    return integracao, conferencia


def autorizar_finalizacao(integracao_id, usuario_id):
    """Registra uma autorização humana; não acessa o portal nem finaliza."""
    if not usuario_id:
        raise ValueError("A autorização deve estar vinculada a um usuário autenticado.")

    atualizados = (
        ValeTransporteIntegracaoBRMobilidade.query
        .filter_by(
            id=integracao_id,
            status_interno=STATUS_AGUARDANDO_AUTORIZACAO,
        )
        .update(
            {
                "status_interno": STATUS_AUTORIZADO,
                "autorizado_finalizacao_em": datetime.now(),
                "autorizado_finalizacao_por_id": usuario_id,
                "erro_etapa": None,
                "erro_mensagem": None,
            },
            synchronize_session=False,
        )
    )
    db.session.commit()
    if not atualizados:
        raise ValueError(
            "A finalização não está aguardando autorização ou já foi autorizada."
        )
    return db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)


def iniciar_finalizacao(integracao_id):
    """Reserva a execução uma única vez, impedindo concorrência e duplo clique."""
    atualizados = (
        ValeTransporteIntegracaoBRMobilidade.query
        .filter_by(id=integracao_id, status_interno=STATUS_AUTORIZADO)
        .update(
            {"status_interno": STATUS_FINALIZANDO},
            synchronize_session=False,
        )
    )
    db.session.commit()
    if not atualizados:
        raise ValueError("A finalização não está autorizada ou já foi iniciada.")
    return db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)


def registrar_finalizacao_sucesso(
    integracao_id,
    *,
    numero_pedido_portal,
    status_portal,
    finalizado_em=None,
):
    integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
    if not integracao or integracao.status_interno != STATUS_FINALIZANDO:
        raise ValueError("Não existe finalização em andamento para registrar.")

    numero = str(numero_pedido_portal or "").strip()
    if not numero.isdigit():
        raise ValueError("O Portal não retornou um número de pedido válido.")

    integracao.numero_pedido_portal = numero
    integracao.status_portal = str(status_portal or "").strip() or "Novo"
    integracao.status_interno = STATUS_FINALIZADO
    integracao.finalizado_portal_em = finalizado_em or datetime.now()
    integracao.comentario_portal = "Pedido finalizado e identificado no Portal BR Mobilidade."
    integracao.erro_etapa = None
    integracao.erro_mensagem = None
    try:
        db.session.commit()
    except IntegrityError as erro:
        db.session.rollback()
        raise ValueError("Este número de pedido do portal já foi registrado.") from erro
    return integracao


def registrar_falha_finalizacao(integracao_id, mensagem, *, resultado_incerto=True):
    integracao = db.session.get(ValeTransporteIntegracaoBRMobilidade, integracao_id)
    if not integracao:
        raise ValueError("Integração BR Mobilidade não encontrada.")
    integracao.status_interno = STATUS_INCERTO if resultado_incerto else STATUS_ERRO
    integracao.erro_etapa = "FINALIZACAO_PORTAL"
    integracao.erro_mensagem = str(mensagem or "Falha ao finalizar pedido no portal.")
    db.session.commit()
    return integracao
