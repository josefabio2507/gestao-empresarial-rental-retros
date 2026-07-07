from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import or_

from app.extensions import db
from app.models import (
    Colaborador,
    Equipe,
    LinhaOnibus,
    ValeTransporteColaboradorLinha,
    ValeTransportePedido,
    ValeTransportePedidoItem,
)


TIPOS_PAGAMENTO = {
    "dinheiro": "Dinheiro",
    "cartao_transporte": "Cartão Transporte",
}

PERIODICIDADES_PAGAMENTO = {
    "mensal": "Mensal",
    "semanal": "Semanal",
}

STATUS_PEDIDO_RASCUNHO = "Rascunho"
STATUS_PEDIDO_GERADO = "Gerado"
STATUS_PEDIDO_CANCELADO = "Cancelado"

STATUS_PEDIDOS = {
    STATUS_PEDIDO_RASCUNHO: STATUS_PEDIDO_RASCUNHO,
    STATUS_PEDIDO_GERADO: STATUS_PEDIDO_GERADO,
    STATUS_PEDIDO_CANCELADO: STATUS_PEDIDO_CANCELADO,
}

FILTRO_TODOS = "todos"


def formatar_moeda_brl(valor):
    if valor is None:
        return "R$ 0,00"

    valor_decimal = Decimal(valor).quantize(Decimal("0.01"))
    texto = f"{valor_decimal:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def parse_decimal_brasileiro(valor):
    texto = (valor or "").strip()

    if not texto:
        raise ValueError("Valor da tarifa por dia é obrigatório.")

    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")

    try:
        valor_decimal = Decimal(texto)
    except (InvalidOperation, ValueError):
        raise ValueError("Informe um valor de tarifa válido.")

    if valor_decimal <= 0:
        raise ValueError("O valor da tarifa deve ser maior que zero.")

    return valor_decimal.quantize(Decimal("0.01"))


def parse_decimal_brasileiro_nao_negativo(valor, nome_campo):
    texto = (valor or "").strip()

    if not texto:
        return Decimal("0.00")

    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", ".")

    try:
        valor_decimal = Decimal(texto)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Informe um valor válido para {nome_campo}.")

    if valor_decimal < 0:
        raise ValueError(f"{nome_campo} não pode ser negativo.")

    return valor_decimal.quantize(Decimal("0.01"))


def formatar_data_brl(data):
    if not data:
        return "-"

    return data.strftime("%d/%m/%Y")


def converter_data_iso(data_texto, nome_campo):
    texto = (data_texto or "").strip()

    if not texto:
        raise ValueError(f"{nome_campo} é obrigatória.")

    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{nome_campo} inválida.")


def validar_competencia(competencia):
    competencia = (competencia or "").strip()

    if not competencia:
        raise ValueError("Competência é obrigatória.")

    if not re.match(r"^(0[1-9]|1[0-2])\.\d{4}$", competencia):
        raise ValueError("Competência deve estar no formato MM.AAAA. Exemplo: 05.2026.")

    return competencia


def converter_quantidade_dias(valor, nome_campo="Quantidade de dias"):
    try:
        quantidade = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nome_campo} deve ser um número inteiro maior que zero.")

    if quantidade <= 0:
        raise ValueError(f"{nome_campo} deve ser maior que zero.")

    return quantidade


def buscar_linhas_onibus(filtro_texto=None):
    query = LinhaOnibus.query

    if filtro_texto:
        filtro = filtro_texto.strip()
        query = query.filter(
            or_(
                LinhaOnibus.nome.ilike(f"%{filtro}%"),
                LinhaOnibus.codigo.ilike(f"%{filtro}%"),
                LinhaOnibus.empresa_transporte.ilike(f"%{filtro}%"),
            )
        )

    return query.order_by(
        LinhaOnibus.nome.asc(),
        LinhaOnibus.empresa_transporte.asc(),
    ).all()


def buscar_linha_por_id(linha_id):
    return LinhaOnibus.query.get(linha_id)


def salvar_linha_onibus(
    linha,
    nome,
    codigo,
    empresa_transporte,
    valor_tarifa_dia,
):
    nome = (nome or "").strip()
    codigo = (codigo or "").strip()
    empresa_transporte = (empresa_transporte or "").strip()

    if not nome:
        return False, "Nome da linha é obrigatório."

    if not empresa_transporte:
        return False, "Empresa de transporte é obrigatória."

    try:
        valor_decimal = parse_decimal_brasileiro(valor_tarifa_dia)
    except ValueError as erro:
        return False, str(erro)

    if not linha:
        linha = LinhaOnibus()
        db.session.add(linha)

    linha.nome = nome
    linha.codigo = codigo
    linha.empresa_transporte = empresa_transporte
    linha.valor_tarifa_dia = valor_decimal

    db.session.commit()

    return True, "Linha de ônibus salva com sucesso."


def alternar_status_linha(linha):
    linha.ativo = not linha.ativo
    db.session.commit()

    if linha.ativo:
        return True, "Linha de ônibus reativada com sucesso."

    return True, "Linha de ônibus inativada com sucesso."


def listar_colaboradores_para_vinculo():
    return (
        Colaborador.query
        .filter(
            Colaborador.ativo.is_(True),
            Colaborador.vale_transporte_optante.is_(True),
        )
        .order_by(Colaborador.nome.asc())
        .all()
    )


def listar_linhas_ativas():
    return (
        LinhaOnibus.query
        .filter_by(ativo=True)
        .order_by(LinhaOnibus.nome.asc(), LinhaOnibus.empresa_transporte.asc())
        .all()
    )


def listar_equipes_ativas():
    return (
        Equipe.query
        .filter_by(ativo=True)
        .order_by(Equipe.nome.asc())
        .all()
    )


def listar_empresas_transporte_ativas():
    linhas = (
        LinhaOnibus.query
        .with_entities(LinhaOnibus.empresa_transporte)
        .filter_by(ativo=True)
        .order_by(LinhaOnibus.empresa_transporte.asc())
        .distinct()
        .all()
    )

    return [linha.empresa_transporte for linha in linhas if linha.empresa_transporte]


def buscar_colaborador_por_id(colaborador_id):
    return Colaborador.query.get(colaborador_id)


def buscar_vinculo_por_id(vinculo_id):
    return ValeTransporteColaboradorLinha.query.get(vinculo_id)


def buscar_vinculos_colaborador(colaborador_id):
    return (
        ValeTransporteColaboradorLinha.query
        .join(LinhaOnibus)
        .filter(ValeTransporteColaboradorLinha.colaborador_id == colaborador_id)
        .order_by(
            ValeTransporteColaboradorLinha.ativo.desc(),
            LinhaOnibus.nome.asc(),
        )
        .all()
    )


def existe_vinculo_ativo(colaborador_id, linha_onibus_id, ignorar_vinculo_id=None):
    query = ValeTransporteColaboradorLinha.query.filter_by(
        colaborador_id=colaborador_id,
        linha_onibus_id=linha_onibus_id,
        ativo=True,
    )

    if ignorar_vinculo_id:
        query = query.filter(ValeTransporteColaboradorLinha.id != ignorar_vinculo_id)

    return query.first() is not None


def salvar_vinculo_colaborador_linha(
    colaborador,
    linha_onibus_id,
    tipo_pagamento,
    periodicidade_pagamento,
):
    if not colaborador:
        return False, "Colaborador não encontrado."

    if not colaborador.vale_transporte_optante:
        return False, "Este colaborador não está marcado como optante de Vale Transporte."

    linha = LinhaOnibus.query.filter_by(
        id=linha_onibus_id,
        ativo=True,
    ).first()

    if not linha:
        return False, "Selecione uma linha de ônibus ativa."

    if tipo_pagamento not in TIPOS_PAGAMENTO:
        return False, "Tipo de pagamento inválido."

    if periodicidade_pagamento not in PERIODICIDADES_PAGAMENTO:
        return False, "Periodicidade do pagamento inválida."

    if existe_vinculo_ativo(colaborador.id, linha.id):
        return False, "Esta linha de ônibus já está vinculada a este colaborador."

    vinculo = ValeTransporteColaboradorLinha(
        colaborador_id=colaborador.id,
        linha_onibus_id=linha.id,
        tipo_pagamento=tipo_pagamento,
        periodicidade_pagamento=periodicidade_pagamento,
        ativo=True,
    )
    db.session.add(vinculo)
    db.session.commit()

    return True, "Linha vinculada ao colaborador com sucesso."


def atualizar_pagamento_vinculo(
    vinculo,
    tipo_pagamento,
    periodicidade_pagamento,
):
    if not vinculo:
        return False, "Vínculo não encontrado."

    if tipo_pagamento not in TIPOS_PAGAMENTO:
        return False, "Tipo de pagamento inválido."

    if periodicidade_pagamento not in PERIODICIDADES_PAGAMENTO:
        return False, "Periodicidade do pagamento inválida."

    vinculo.tipo_pagamento = tipo_pagamento
    vinculo.periodicidade_pagamento = periodicidade_pagamento
    db.session.commit()

    return True, "Dados de pagamento atualizados com sucesso."


def alternar_status_vinculo(vinculo):
    vinculo.ativo = not vinculo.ativo
    db.session.commit()

    if vinculo.ativo:
        return True, "Vínculo reativado com sucesso."

    return True, "Vínculo inativado com sucesso."


def normalizar_filtro_opcional(valor):
    texto = (valor or "").strip()
    return None if not texto or texto == FILTRO_TODOS else texto


def montar_linha_snapshot(linha):
    if not linha:
        return "-"

    codigo = (linha.codigo or "").strip()
    if codigo:
        return f"{linha.nome} - {codigo}"

    return linha.nome


def validar_cabecalho_pedido(
    competencia,
    data_inicial,
    data_final,
    quantidade_dias,
    prazo_pagamento,
):
    competencia_validada = validar_competencia(competencia)
    data_inicio = converter_data_iso(data_inicial, "Data Inicial")
    data_fim = converter_data_iso(data_final, "Data Final")

    if data_inicio > data_fim:
        raise ValueError("Data Inicial não pode ser maior que a Data Final.")

    quantidade = converter_quantidade_dias(quantidade_dias, "Quantidade de dias")

    prazo = (prazo_pagamento or "").strip()
    if prazo not in PERIODICIDADES_PAGAMENTO:
        raise ValueError("Prazo de pagamento é obrigatório.")

    return competencia_validada, data_inicio, data_fim, quantidade, prazo


def buscar_vinculos_para_pedido(
    equipe_id=None,
    forma_pagamento=None,
    empresa_transporte=None,
    prazo_pagamento=None,
):
    equipe_id = normalizar_filtro_opcional(equipe_id)
    forma_pagamento = normalizar_filtro_opcional(forma_pagamento)
    empresa_transporte = normalizar_filtro_opcional(empresa_transporte)
    prazo_pagamento = normalizar_filtro_opcional(prazo_pagamento)

    query = (
        ValeTransporteColaboradorLinha.query
        .join(Colaborador)
        .join(LinhaOnibus)
        .outerjoin(Equipe, Colaborador.equipe_id == Equipe.id)
        .filter(
            ValeTransporteColaboradorLinha.ativo.is_(True),
            Colaborador.ativo.is_(True),
            Colaborador.vale_transporte_optante.is_(True),
            LinhaOnibus.ativo.is_(True),
        )
    )

    if equipe_id:
        query = query.filter(Colaborador.equipe_id == equipe_id)

    if forma_pagamento:
        query = query.filter(ValeTransporteColaboradorLinha.tipo_pagamento == forma_pagamento)

    if empresa_transporte:
        query = query.filter(LinhaOnibus.empresa_transporte == empresa_transporte)

    if prazo_pagamento:
        query = query.filter(
            ValeTransporteColaboradorLinha.periodicidade_pagamento == prazo_pagamento
        )

    return (
        query
        .order_by(
            Equipe.nome.asc(),
            Colaborador.nome.asc(),
            LinhaOnibus.empresa_transporte.asc(),
            LinhaOnibus.nome.asc(),
        )
        .all()
    )


def calcular_valor_base(tarifa_diaria, quantidade_dias):
    return (Decimal(tarifa_diaria) * quantidade_dias).quantize(Decimal("0.01"))


def calcular_totais_item(tarifa_diaria, quantidade_dias, valor_acrescimo, valor_desconto):
    valor_base = calcular_valor_base(tarifa_diaria, quantidade_dias)
    total = (valor_base + valor_acrescimo - valor_desconto).quantize(Decimal("0.01"))

    if total < 0:
        raise ValueError(
            "Valor a descontar não pode ser maior que o valor base somado ao acréscimo."
        )

    return valor_base, total


def montar_previa_pedido_vale_transporte(
    competencia,
    data_inicial,
    data_final,
    quantidade_dias,
    equipe_id=None,
    forma_pagamento=None,
    empresa_transporte=None,
    prazo_pagamento=None,
):
    competencia, data_inicio, data_fim, quantidade, prazo = validar_cabecalho_pedido(
        competencia,
        data_inicial,
        data_final,
        quantidade_dias,
        prazo_pagamento,
    )

    vinculos = buscar_vinculos_para_pedido(
        equipe_id=equipe_id,
        forma_pagamento=forma_pagamento,
        empresa_transporte=empresa_transporte,
        prazo_pagamento=prazo,
    )

    itens = []
    for vinculo in vinculos:
        linha = vinculo.linha_onibus
        colaborador = vinculo.colaborador
        tarifa = Decimal(linha.valor_tarifa_dia).quantize(Decimal("0.01"))
        valor_base = calcular_valor_base(tarifa, quantidade)

        itens.append({
            "vinculo": vinculo,
            "competencia": competencia,
            "matricula": colaborador.matricula,
            "nome_colaborador": colaborador.nome,
            "equipe": colaborador.equipe.nome if colaborador.equipe else "-",
            "empresa_transporte": linha.empresa_transporte,
            "forma_pagamento": TIPOS_PAGAMENTO.get(vinculo.tipo_pagamento, vinculo.tipo_pagamento),
            "linha_transporte": montar_linha_snapshot(linha),
            "tarifa_diaria": tarifa,
            "quantidade_dias": quantidade,
            "valor_acrescimo": Decimal("0.00"),
            "valor_desconto": Decimal("0.00"),
            "valor_total": valor_base,
            "observacao": "",
        })

    return {
        "competencia": competencia,
        "data_inicial": data_inicio,
        "data_final": data_fim,
        "quantidade_dias": quantidade,
        "prazo_pagamento": prazo,
        "itens": itens,
    }


def buscar_pedidos_vale_transporte(status=None):
    query = ValeTransportePedido.query

    status = normalizar_filtro_opcional(status)
    if status:
        query = query.filter(ValeTransportePedido.status == status)

    return (
        query
        .order_by(
            ValeTransportePedido.criado_em.desc(),
            ValeTransportePedido.id.desc(),
        )
        .all()
    )


def buscar_pedido_vale_transporte_por_id(pedido_id):
    return ValeTransportePedido.query.get(pedido_id)


def pedido_vale_transporte_pode_ser_cancelado(pedido):
    return bool(pedido and pedido.status != STATUS_PEDIDO_CANCELADO)


def buscar_pedido_duplicado(
    competencia,
    data_inicial,
    data_final,
    equipe_id,
    forma_pagamento,
    empresa_transporte,
    prazo_pagamento,
):
    return (
        ValeTransportePedido.query
        .filter(
            ValeTransportePedido.status != STATUS_PEDIDO_CANCELADO,
            ValeTransportePedido.competencia == competencia,
            ValeTransportePedido.data_inicial == data_inicial,
            ValeTransportePedido.data_final == data_final,
            ValeTransportePedido.equipe_id == equipe_id,
            ValeTransportePedido.forma_pagamento_filtro == forma_pagamento,
            ValeTransportePedido.empresa_transporte_filtro == empresa_transporte,
            ValeTransportePedido.prazo_pagamento == prazo_pagamento,
        )
        .first()
    )


def montar_item_pedido(vinculo, quantidade_dias, valor_acrescimo, valor_desconto, observacao):
    colaborador = vinculo.colaborador
    linha = vinculo.linha_onibus
    tarifa = Decimal(linha.valor_tarifa_dia).quantize(Decimal("0.01"))
    valor_base, valor_total = calcular_totais_item(
        tarifa,
        quantidade_dias,
        valor_acrescimo,
        valor_desconto,
    )

    return ValeTransportePedidoItem(
        colaborador_id=colaborador.id,
        linha_onibus_id=linha.id,
        matricula_snapshot=colaborador.matricula,
        nome_colaborador_snapshot=colaborador.nome,
        equipe_snapshot=colaborador.equipe.nome if colaborador.equipe else "",
        empresa_transporte_snapshot=linha.empresa_transporte,
        linha_transporte_snapshot=montar_linha_snapshot(linha),
        forma_pagamento=vinculo.tipo_pagamento,
        tarifa_diaria=tarifa,
        quantidade_dias=quantidade_dias,
        valor_base=valor_base,
        valor_acrescimo=valor_acrescimo,
        valor_desconto=valor_desconto,
        valor_total=valor_total,
        observacao=(observacao or "").strip(),
        ativo=True,
    )


def criar_pedido_vale_transporte(
    competencia,
    data_inicial,
    data_final,
    quantidade_dias,
    equipe_id=None,
    forma_pagamento=None,
    empresa_transporte=None,
    prazo_pagamento=None,
    ajustes_itens=None,
    criado_por_id=None,
):
    try:
        competencia, data_inicio, data_fim, quantidade, prazo = validar_cabecalho_pedido(
            competencia,
            data_inicial,
            data_final,
            quantidade_dias,
            prazo_pagamento,
        )
    except ValueError as erro:
        return False, str(erro), None

    equipe_id = normalizar_filtro_opcional(equipe_id)
    forma_pagamento = normalizar_filtro_opcional(forma_pagamento)
    empresa_transporte = normalizar_filtro_opcional(empresa_transporte)
    ajustes_itens = ajustes_itens or {}

    vinculos = buscar_vinculos_para_pedido(
        equipe_id=equipe_id,
        forma_pagamento=forma_pagamento,
        empresa_transporte=empresa_transporte,
        prazo_pagamento=prazo,
    )

    if not vinculos:
        return False, "Nenhum colaborador encontrado para os filtros informados.", None

    pedido_duplicado = buscar_pedido_duplicado(
        competencia=competencia,
        data_inicial=data_inicio,
        data_final=data_fim,
        equipe_id=int(equipe_id) if equipe_id else None,
        forma_pagamento=forma_pagamento,
        empresa_transporte=empresa_transporte,
        prazo_pagamento=prazo,
    )

    if pedido_duplicado:
        return (
            False,
            "Já existe pedido ativo para esta competência, período e filtros.",
            pedido_duplicado,
        )

    pedido = ValeTransportePedido(
        competencia=competencia,
        data_inicial=data_inicio,
        data_final=data_fim,
        quantidade_dias_padrao=quantidade,
        equipe_id=int(equipe_id) if equipe_id else None,
        forma_pagamento_filtro=forma_pagamento,
        empresa_transporte_filtro=empresa_transporte,
        prazo_pagamento=prazo,
        status=STATUS_PEDIDO_GERADO,
        criado_por_id=criado_por_id,
    )

    chaves_itens = set()

    try:
        for vinculo in vinculos:
            chave = (vinculo.colaborador_id, vinculo.linha_onibus_id)
            if chave in chaves_itens:
                raise ValueError(
                    "Mesmo colaborador e linha de transporte duplicados no pedido."
                )
            chaves_itens.add(chave)

            ajuste = ajustes_itens.get(str(vinculo.id), {})
            quantidade_item = converter_quantidade_dias(
                ajuste.get("quantidade_dias", quantidade),
                "Quantidade de dias do item",
            )
            acrescimo = parse_decimal_brasileiro_nao_negativo(
                ajuste.get("valor_acrescimo"),
                "Valor a Acrescentar",
            )
            desconto = parse_decimal_brasileiro_nao_negativo(
                ajuste.get("valor_desconto"),
                "Valor a Descontar",
            )
            item = montar_item_pedido(
                vinculo,
                quantidade_item,
                acrescimo,
                desconto,
                ajuste.get("observacao", ""),
            )
            pedido.itens.append(item)
    except ValueError as erro:
        db.session.rollback()
        return False, str(erro), None

    if not pedido.itens:
        return False, "Não é possível criar pedido vazio.", None

    db.session.add(pedido)
    db.session.commit()

    return True, "Pedido de Vale Transporte criado com sucesso.", pedido


def cancelar_pedido_vale_transporte(pedido):
    if not pedido_vale_transporte_pode_ser_cancelado(pedido):
        return False, "Pedido de Vale Transporte não pode ser cancelado."

    pedido.status = STATUS_PEDIDO_CANCELADO
    db.session.commit()

    return True, "Pedido de Vale Transporte cancelado com sucesso."
