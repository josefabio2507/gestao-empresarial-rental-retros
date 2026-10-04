from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import re

from app.departamento_pessoal.vale_transporte.br_mobilidade_arquivo import (
    cpf_valido,
    somente_digitos,
)
from app.departamento_pessoal.vale_transporte.operadoras import (
    CITY_TRANSPORTES,
    PEDIDO_MISTO,
    codigo_operadora_por_nome,
    resolver_operadora_pedido,
)


VERSAO_LAYOUT = "0800"
ENCODING_PADRAO = "cp1252"
APLICACOES_VALIDAS = {"400", "410"}


@dataclass(frozen=True)
class RegistroCityTransportes:
    cpf: str
    quantidade_dias: int
    valor_diario_centavos: int
    nome: str
    design_cartao: str
    aplicacao: str

    @property
    def valor_total(self):
        return (
            Decimal(self.valor_diario_centavos) * self.quantidade_dias / Decimal("100")
        ).quantize(Decimal("0.01"))


@dataclass
class ResultadoValidacaoCityTransportes:
    registros: list[RegistroCityTransportes] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    itens_ignorados: int = 0

    @property
    def valido(self):
        return not self.erros and bool(self.registros)

    @property
    def quantidade_colaboradores(self):
        return len(self.registros)

    @property
    def valor_total_creditos(self):
        return sum(
            (registro.valor_total for registro in self.registros),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))


def _nome_para_arquivo(nome):
    nome = re.sub(r"[|\r\n]+", " ", str(nome or ""))
    return " ".join(nome.split()).upper()


def _centavos(valor):
    decimal = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(decimal * 100)


def validar_pedido_city_transportes(pedido):
    resultado = ResultadoValidacaoCityTransportes()
    if not pedido:
        resultado.erros.append("Pedido de Vale Transporte não encontrado.")
        return resultado
    if pedido.status == "Cancelado":
        resultado.erros.append("Pedido cancelado não pode gerar arquivo City Transportes.")
        return resultado

    operadora = resolver_operadora_pedido(pedido)
    if operadora.codigo != CITY_TRANSPORTES:
        if operadora.codigo == PEDIDO_MISTO:
            resultado.erros.append(
                "O pedido possui mais de uma empresa de transporte. "
                "Crie um pedido separado para cada operadora antes de integrar."
            )
        else:
            resultado.erros.append(
                "Este pedido não pertence exclusivamente à City Transportes."
            )
        return resultado

    grupos = {}
    total_itens = Decimal("0.00")
    for item in pedido.itens:
        elegivel = (
            item.ativo
            and item.forma_pagamento == "cartao_transporte"
            and codigo_operadora_por_nome(item.empresa_transporte_snapshot)
            == CITY_TRANSPORTES
        )
        if not elegivel:
            resultado.itens_ignorados += 1
            continue

        identificacao = item.nome_colaborador_snapshot or f"item {item.id}"
        valor_item = Decimal(item.valor_total or 0).quantize(Decimal("0.01"))
        if valor_item == 0:
            resultado.itens_ignorados += 1
            continue
        if valor_item < 0:
            resultado.erros.append(
                f"{identificacao}: valor a receber não pode ser negativo."
            )
            continue

        cpf = somente_digitos(getattr(item.colaborador, "cpf", ""))
        if len(cpf) != 11:
            resultado.erros.append(f"{identificacao}: CPF deve conter 11 dígitos.")
            continue
        if not cpf_valido(cpf):
            resultado.erros.append(f"{identificacao}: CPF inválido.")
            continue
        if not item.quantidade_dias or item.quantidade_dias <= 0:
            resultado.erros.append(
                f"{identificacao}: quantidade de dias deve ser maior que zero."
            )
            continue

        tarifa = Decimal(item.tarifa_diaria or 0).quantize(Decimal("0.01"))
        if tarifa <= 0:
            resultado.erros.append(
                f"{identificacao}: valor diário deve ser maior que zero."
            )
            continue
        acrescimo = Decimal(item.valor_acrescimo or 0).quantize(Decimal("0.01"))
        desconto = Decimal(item.valor_desconto or 0).quantize(Decimal("0.01"))
        if acrescimo or desconto:
            resultado.erros.append(
                f"{identificacao}: o layout 0800 não representa acréscimos ou descontos."
            )
            continue
        valor_esperado = (tarifa * item.quantidade_dias).quantize(Decimal("0.01"))
        if valor_item != valor_esperado:
            resultado.erros.append(
                f"{identificacao}: total do item diverge da tarifa multiplicada pelos dias."
            )
            continue

        design = somente_digitos(getattr(item, "city_design_cartao_snapshot", ""))
        aplicacao = str(getattr(item, "city_aplicacao_snapshot", "") or "").strip()
        if len(design) != 2:
            resultado.erros.append(
                f"{identificacao}: informe os 2 dígitos do design do cartão City Transportes."
            )
            continue
        if aplicacao not in APLICACOES_VALIDAS:
            resultado.erros.append(
                f"{identificacao}: aplicação City Transportes deve ser 400 (Guarujá) ou 410 (Bertioga)."
            )
            continue

        chave_operacional = (item.quantidade_dias, design, aplicacao)
        if cpf in grupos and grupos[cpf]["chave_operacional"] != chave_operacional:
            resultado.erros.append(
                f"{identificacao}: o mesmo CPF possui dias, design ou aplicação divergentes."
            )
            continue
        grupo = grupos.setdefault(
            cpf,
            {
                "chave_operacional": chave_operacional,
                "quantidade_dias": item.quantidade_dias,
                "valor_diario": Decimal("0.00"),
                "nome": _nome_para_arquivo(item.nome_colaborador_snapshot),
                "design": design,
                "aplicacao": aplicacao,
            },
        )
        grupo["valor_diario"] += tarifa
        total_itens += valor_item

    if not grupos:
        resultado.erros.append(
            "O pedido não possui colaboradores da City Transportes com valor a receber maior que R$ 0,00."
        )
        return resultado

    for cpf, grupo in grupos.items():
        resultado.registros.append(
            RegistroCityTransportes(
                cpf=cpf,
                quantidade_dias=grupo["quantidade_dias"],
                valor_diario_centavos=_centavos(grupo["valor_diario"]),
                nome=grupo["nome"],
                design_cartao=grupo["design"],
                aplicacao=grupo["aplicacao"],
            )
        )
    resultado.registros.sort(key=lambda registro: (registro.nome, registro.cpf))
    if resultado.valor_total_creditos != total_itens.quantize(Decimal("0.01")):
        resultado.erros.append(
            "O valor total consolidado diverge do total dos itens elegíveis do pedido."
        )
    return resultado


def nome_arquivo_city_transportes(pedido):
    competencia = str(pedido.competencia or "").strip()
    partes = competencia.split(".")
    if len(partes) == 2 and len(partes[0]) == 2 and len(partes[1]) == 4:
        competencia = f"{partes[1]}_{partes[0]}"
    else:
        competencia = re.sub(r"[^0-9A-Za-z]+", "_", competencia).strip("_") or str(pedido.id)
    return f"PEDIDO_VT_CITY_TRANSPORTES_{competencia}.txt"


def gerar_arquivo_city_transportes(pedido, encoding=ENCODING_PADRAO):
    resultado = validar_pedido_city_transportes(pedido)
    if not resultado.valido:
        raise ValueError("\n".join(resultado.erros))
    linhas = [VERSAO_LAYOUT]
    linhas.extend(
        f"{registro.cpf}|{registro.quantidade_dias}|{registro.valor_diario_centavos}|"
        f"{registro.nome}|{registro.design_cartao}|{registro.aplicacao}"
        for registro in resultado.registros
    )
    try:
        return ("\r\n".join(linhas) + "\r\n").encode(encoding), resultado
    except (LookupError, UnicodeEncodeError) as erro:
        raise ValueError(
            f"Não foi possível gerar o arquivo na codificação configurada ({encoding})."
        ) from erro
