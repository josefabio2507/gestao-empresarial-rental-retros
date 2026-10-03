"""Conferência de um pedido já existente no portal, sem alterar seu estado."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ResumoPedidoPortal:
    numero: str
    data_pedido: date
    data_liberacao: date
    status: str
    valor_creditos: Decimal
    taxa_administrativa: Decimal
    valor_cartoes: Decimal
    valor_total: Decimal
    quantidade_usuarios: int
    valor_historico: Decimal | None = None
    acrescimo_historico_confirmado: bool = False


@dataclass(frozen=True)
class ResultadoConferenciaPedido:
    numero: str
    quantidade_sistema: int
    quantidade_portal: int
    valor_sistema: Decimal
    valor_portal: Decimal
    acrescimo_historico: Decimal | None
    divergencias: tuple[str, ...]

    @property
    def aprovado(self):
        return not self.divergencias


def conferir_resumo_pedido(integracao, resumo: ResumoPedidoPortal):
    """Compara créditos, usuários e liberação com o registro enviado."""
    divergencias = []
    if (
        integracao.numero_pedido_portal
        and resumo.numero
        and integracao.numero_pedido_portal != resumo.numero
    ):
        divergencias.append("Número do pedido no portal diferente do registrado.")
    if integracao.quantidade_colaboradores != resumo.quantidade_usuarios:
        divergencias.append("Quantidade de colaboradores divergente.")
    if Decimal(integracao.valor_creditos) != resumo.valor_creditos:
        divergencias.append("Valor dos créditos divergente.")
    if integracao.data_liberacao != resumo.data_liberacao:
        divergencias.append("Data de liberação divergente.")
    if (
        resumo.valor_creditos
        + resumo.taxa_administrativa
        + resumo.valor_cartoes
        != resumo.valor_total
    ):
        divergencias.append("Composição do valor total divergente no portal.")
    acrescimo_historico = None
    if resumo.valor_historico is not None:
        acrescimo_historico = resumo.valor_historico - resumo.valor_total
        if acrescimo_historico < 0:
            divergencias.append("Valor do histórico é inferior ao total no detalhamento do portal.")
        elif acrescimo_historico > 0 and not resumo.acrescimo_historico_confirmado:
            divergencias.append("Acréscimo do histórico requer confirmação da taxa da empresa.")
    return ResultadoConferenciaPedido(
        numero=resumo.numero,
        quantidade_sistema=integracao.quantidade_colaboradores,
        quantidade_portal=resumo.quantidade_usuarios,
        valor_sistema=Decimal(integracao.valor_creditos),
        valor_portal=resumo.valor_creditos,
        acrescimo_historico=acrescimo_historico,
        divergencias=tuple(divergencias),
    )
