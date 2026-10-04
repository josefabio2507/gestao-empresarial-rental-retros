from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import re
import unicodedata

from app.departamento_pessoal.vale_transporte.operadoras import (
    BR_MOBILIDADE,
    PEDIDO_MISTO,
    resolver_operadora_pedido,
)


VERSAO_LAYOUT = "0200"
LIMITE_REGISTROS = 5000
ENCODING_PADRAO = "cp1252"


@dataclass(frozen=True)
class RegistroBRMobilidade:
    cpf: str
    quantidade_dias: int
    valor_diario_centavos: int
    nome: str

    @property
    def valor_total(self):
        return (
            Decimal(self.valor_diario_centavos) * self.quantidade_dias / Decimal("100")
        ).quantize(Decimal("0.01"))


@dataclass
class ResultadoValidacaoBRMobilidade:
    registros: list[RegistroBRMobilidade] = field(default_factory=list)
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


def somente_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def cpf_valido(cpf):
    cpf = somente_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for tamanho in (9, 10):
        soma = sum(int(cpf[indice]) * (tamanho + 1 - indice) for indice in range(tamanho))
        digito = 11 - (soma % 11)
        digito = 0 if digito >= 10 else digito
        if digito != int(cpf[tamanho]):
            return False

    return True


def _texto_normalizado(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return " ".join(texto.casefold().split())


def _eh_br_mobilidade(empresa):
    empresa = _texto_normalizado(empresa)
    return empresa == "br mobilidade" or empresa.startswith("br mobilidade ")


def _nome_para_arquivo(nome):
    nome = re.sub(r"[|\r\n]+", " ", str(nome or ""))
    return " ".join(nome.split()).upper()


def _centavos(valor):
    decimal = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(decimal * 100)


def validar_pedido_br_mobilidade(pedido):
    resultado = ResultadoValidacaoBRMobilidade()

    if not pedido:
        resultado.erros.append("Pedido de Vale Transporte não encontrado.")
        return resultado

    if pedido.status == "Cancelado":
        resultado.erros.append("Pedido cancelado não pode gerar arquivo BR Mobilidade.")
        return resultado

    operadora = resolver_operadora_pedido(pedido)
    if operadora.codigo != BR_MOBILIDADE:
        if operadora.codigo == PEDIDO_MISTO:
            resultado.erros.append(
                "O pedido possui mais de uma empresa de transporte. "
                "Crie um pedido separado para cada operadora antes de integrar."
            )
        else:
            resultado.erros.append(
                "Este pedido não pertence exclusivamente à BR Mobilidade."
            )
        return resultado

    grupos = {}
    total_itens_elegiveis = Decimal("0.00")

    for item in pedido.itens:
        elegivel = (
            item.ativo
            and item.forma_pagamento == "cartao_transporte"
            and _eh_br_mobilidade(item.empresa_transporte_snapshot)
        )
        if not elegivel:
            resultado.itens_ignorados += 1
            continue

        identificacao = item.nome_colaborador_snapshot or f"item {item.id}"
        valor_item = Decimal(item.valor_total or 0).quantize(Decimal("0.01"))
        if valor_item == 0:
            # Colaboradores sem crédito não podem compor o arquivo 0200 nem o
            # preenchimento manual do Portal BR Mobilidade.
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
            resultado.erros.append(f"{identificacao}: quantidade de dias deve ser maior que zero.")
            continue

        tarifa = Decimal(item.tarifa_diaria or 0).quantize(Decimal("0.01"))
        if tarifa <= 0:
            resultado.erros.append(f"{identificacao}: valor diário deve ser maior que zero.")
            continue

        acrescimo = Decimal(item.valor_acrescimo or 0).quantize(Decimal("0.01"))
        desconto = Decimal(item.valor_desconto or 0).quantize(Decimal("0.01"))
        if acrescimo or desconto:
            resultado.erros.append(
                f"{identificacao}: o layout 0200 não representa acréscimos ou descontos."
            )
            continue

        valor_esperado = (tarifa * item.quantidade_dias).quantize(Decimal("0.01"))
        if valor_item != valor_esperado:
            resultado.erros.append(
                f"{identificacao}: total do item diverge da tarifa multiplicada pelos dias."
            )
            continue

        if cpf in grupos and grupos[cpf]["quantidade_dias"] != item.quantidade_dias:
            resultado.erros.append(
                f"{identificacao}: linhas do mesmo CPF possuem quantidades de dias diferentes."
            )
            continue

        grupo = grupos.setdefault(
            cpf,
            {
                "quantidade_dias": item.quantidade_dias,
                "valor_diario": Decimal("0.00"),
                "nome": _nome_para_arquivo(item.nome_colaborador_snapshot),
            },
        )
        grupo["valor_diario"] += tarifa
        total_itens_elegiveis += valor_item

    if not grupos:
        resultado.erros.append(
            "O pedido não possui colaboradores da BR Mobilidade com valor a receber maior que R$ 0,00."
        )
        return resultado

    if len(grupos) > LIMITE_REGISTROS:
        resultado.erros.append(
            f"O arquivo excede o limite de {LIMITE_REGISTROS} registros."
        )

    for cpf, grupo in grupos.items():
        valor_diario_centavos = _centavos(grupo["valor_diario"])
        if valor_diario_centavos <= 0:
            resultado.erros.append(f"CPF {cpf}: valor diário consolidado deve ser maior que zero.")
            continue
        resultado.registros.append(
            RegistroBRMobilidade(
                cpf=cpf,
                quantidade_dias=grupo["quantidade_dias"],
                valor_diario_centavos=valor_diario_centavos,
                nome=grupo["nome"],
            )
        )

    resultado.registros.sort(key=lambda registro: (registro.nome, registro.cpf))

    if resultado.valor_total_creditos != total_itens_elegiveis.quantize(Decimal("0.01")):
        resultado.erros.append(
            "O valor total consolidado diverge do total dos itens elegíveis do pedido."
        )

    return resultado


def nome_arquivo_br_mobilidade(pedido):
    competencia = str(pedido.competencia or "").strip()
    partes = competencia.split(".")
    if len(partes) == 2 and len(partes[0]) == 2 and len(partes[1]) == 4:
        competencia = f"{partes[1]}_{partes[0]}"
    else:
        competencia = re.sub(r"[^0-9A-Za-z]+", "_", competencia).strip("_") or str(pedido.id)
    return f"PEDIDO_VT_BR_MOBILIDADE_{competencia}.txt"


def gerar_arquivo_br_mobilidade(pedido, encoding=ENCODING_PADRAO):
    resultado = validar_pedido_br_mobilidade(pedido)
    if not resultado.valido:
        raise ValueError("\n".join(resultado.erros))

    linhas = [VERSAO_LAYOUT]
    linhas.extend(
        f"{registro.cpf}|{registro.quantidade_dias}|{registro.valor_diario_centavos}|{registro.nome}"
        for registro in resultado.registros
    )
    conteudo = ("\r\n".join(linhas) + "\r\n")

    try:
        return conteudo.encode(encoding), resultado
    except (LookupError, UnicodeEncodeError) as erro:
        raise ValueError(
            f"Não foi possível gerar o arquivo na codificação configurada ({encoding})."
        ) from erro
