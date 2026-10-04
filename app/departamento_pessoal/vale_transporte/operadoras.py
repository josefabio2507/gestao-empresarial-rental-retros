"""Identificação da operadora responsável pela integração de um pedido de VT."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import unicodedata


BR_MOBILIDADE = "BR_MOBILIDADE"
CITY_TRANSPORTES = "CITY_TRANSPORTES"
SEM_INTEGRACAO = "SEM_INTEGRACAO"
PEDIDO_MISTO = "PEDIDO_MISTO"


@dataclass(frozen=True)
class ResultadoOperadoraPedido:
    codigo: str
    empresas: tuple[str, ...]

    @property
    def permite_integracao(self):
        return self.codigo in {BR_MOBILIDADE, CITY_TRANSPORTES}


def normalizar_nome_operadora(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    return " ".join(texto.casefold().split())


def codigo_operadora_por_nome(nome):
    normalizado = normalizar_nome_operadora(nome)
    if normalizado == "br mobilidade" or normalizado.startswith("br mobilidade "):
        return BR_MOBILIDADE
    if normalizado in {"city transporte", "city transportes"} or normalizado.startswith(
        ("city transporte ", "city transportes ")
    ):
        return CITY_TRANSPORTES
    return SEM_INTEGRACAO


def resolver_operadora_pedido(pedido):
    if not pedido:
        return ResultadoOperadoraPedido(SEM_INTEGRACAO, ())

    empresas_por_nome = {}
    for item in pedido.itens:
        if not item.ativo:
            continue
        if getattr(item, "forma_pagamento", "cartao_transporte") != "cartao_transporte":
            continue
        try:
            valor_total = Decimal(str(getattr(item, "valor_total", "1") or "0"))
        except (InvalidOperation, TypeError, ValueError):
            valor_total = Decimal("0")
        if valor_total <= 0:
            continue
        nome = str(item.empresa_transporte_snapshot or "").strip()
        normalizado = normalizar_nome_operadora(nome)
        if normalizado:
            empresas_por_nome.setdefault(normalizado, nome)

    empresas = tuple(
        empresas_por_nome[chave] for chave in sorted(empresas_por_nome)
    )
    if len(empresas_por_nome) != 1:
        codigo = PEDIDO_MISTO if empresas_por_nome else SEM_INTEGRACAO
        return ResultadoOperadoraPedido(codigo, empresas)

    codigo = codigo_operadora_por_nome(empresas[0])
    return ResultadoOperadoraPedido(codigo, empresas)
