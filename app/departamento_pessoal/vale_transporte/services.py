from decimal import Decimal, InvalidOperation

from sqlalchemy import or_

from app.extensions import db
from app.models import Colaborador, LinhaOnibus, ValeTransporteColaboradorLinha


TIPOS_PAGAMENTO = {
    "dinheiro": "Dinheiro",
    "cartao_transporte": "Cartão Transporte",
}

PERIODICIDADES_PAGAMENTO = {
    "mensal": "Mensal",
    "semanal": "Semanal",
}


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
