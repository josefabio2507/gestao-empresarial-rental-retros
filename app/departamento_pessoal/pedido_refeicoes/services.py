import re
from decimal import Decimal, InvalidOperation

from app.extensions import db
from datetime import datetime
from app.models import (
    Restaurante,
    ItemCardapio,
    Equipe,
    PedidoRefeicao,
    Colaborador,
    ConsumoRefeicao,
)


TIPOS_CARDAPIO = [
    "Refeição",
    "Bebida",
    "Outros",
]


def limpar_numeros(valor):
    if not valor:
        return ""

    return re.sub(r"\D", "", valor)


def limpar_telefone(telefone):
    return limpar_numeros(telefone)


def formatar_telefone(telefone):
    telefone = limpar_telefone(telefone)

    if not telefone:
        return "-"

    if len(telefone) == 13 and telefone.startswith("55"):
        return f"+{telefone[:2]} ({telefone[2:4]}) {telefone[4:9]}-{telefone[9:]}"

    if len(telefone) == 12 and telefone.startswith("55"):
        return f"+{telefone[:2]} ({telefone[2:4]}) {telefone[4:8]}-{telefone[8:]}"

    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"

    if len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"

    return telefone


def converter_preco(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        preco = Decimal(texto)
    except InvalidOperation:
        return None

    return preco.quantize(Decimal("0.01"))


def formatar_moeda(valor):
    if valor is None:
        return "R$ 0,00"

    valor_decimal = Decimal(valor).quantize(Decimal("0.01"))
    texto = f"{valor_decimal:,.2f}"

    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"R$ {texto}"


def buscar_restaurantes():
    return Restaurante.query.order_by(Restaurante.nome.asc()).all()


def buscar_restaurantes_ativos():
    return (
        Restaurante.query
        .filter_by(ativo=True)
        .order_by(Restaurante.nome.asc())
        .all()
    )


def buscar_restaurante_por_id(restaurante_id):
    return Restaurante.query.get(restaurante_id)


def criar_restaurante(nome, telefone, ativo=True):
    nome = nome.strip()
    telefone_limpo = limpar_telefone(telefone)

    if not nome:
        return False, "Nome do restaurante é obrigatório."

    restaurante = Restaurante(
        nome=nome,
        telefone=telefone_limpo,
        ativo=ativo,
    )

    db.session.add(restaurante)
    db.session.commit()

    return True, "Restaurante criado com sucesso."


def atualizar_restaurante(restaurante, nome, telefone, ativo=True):
    nome = nome.strip()
    telefone_limpo = limpar_telefone(telefone)

    if not nome:
        return False, "Nome do restaurante é obrigatório."

    restaurante.nome = nome
    restaurante.telefone = telefone_limpo
    restaurante.ativo = ativo

    db.session.commit()

    return True, "Restaurante atualizado com sucesso."


def alterar_status_restaurante(restaurante):
    restaurante.ativo = not restaurante.ativo
    db.session.commit()

    if restaurante.ativo:
        return True, "Restaurante ativado com sucesso."

    return True, "Restaurante inativado com sucesso."


def buscar_itens_cardapio(restaurante_id=None, tipo=None):
    query = ItemCardapio.query.join(Restaurante)

    if restaurante_id:
        query = query.filter(ItemCardapio.restaurante_id == restaurante_id)

    if tipo:
        query = query.filter(ItemCardapio.tipo == tipo)

    return (
        query
        .order_by(Restaurante.nome.asc(), ItemCardapio.tipo.asc(), ItemCardapio.nome.asc())
        .all()
    )


def buscar_item_cardapio_por_id(item_id):
    return ItemCardapio.query.get(item_id)


def validar_item_cardapio(restaurante_id, tipo, nome, preco):
    if not restaurante_id:
        return False, "Restaurante é obrigatório."

    restaurante = Restaurante.query.filter_by(id=restaurante_id).first()

    if not restaurante:
        return False, "Restaurante não encontrado."

    if tipo not in TIPOS_CARDAPIO:
        return False, "Tipo de item inválido."

    nome = nome.strip()

    if not nome:
        return False, "Nome do item é obrigatório."

    preco_convertido = converter_preco(preco)

    if preco_convertido is None:
        return False, "Preço inválido."

    if preco_convertido < 0:
        return False, "Preço não pode ser negativo."

    return True, ""


def criar_item_cardapio(restaurante_id, tipo, nome, preco, ativo=True):
    valido, mensagem = validar_item_cardapio(
        restaurante_id=restaurante_id,
        tipo=tipo,
        nome=nome,
        preco=preco,
    )

    if not valido:
        return False, mensagem

    item = ItemCardapio(
        restaurante_id=restaurante_id,
        tipo=tipo,
        nome=nome.strip(),
        preco=converter_preco(preco),
        ativo=ativo,
    )

    db.session.add(item)
    db.session.commit()

    return True, "Item de cardápio criado com sucesso."


def atualizar_item_cardapio(item, restaurante_id, tipo, nome, preco, ativo=True):
    valido, mensagem = validar_item_cardapio(
        restaurante_id=restaurante_id,
        tipo=tipo,
        nome=nome,
        preco=preco,
    )

    if not valido:
        return False, mensagem

    item.restaurante_id = restaurante_id
    item.tipo = tipo
    item.nome = nome.strip()
    item.preco = converter_preco(preco)
    item.ativo = ativo

    db.session.commit()

    return True, "Item de cardápio atualizado com sucesso."


def alterar_status_item_cardapio(item):
    item.ativo = not item.ativo
    db.session.commit()

    if item.ativo:
        return True, "Item de cardápio ativado com sucesso."

    return True, "Item de cardápio inativado com sucesso."

STATUS_PEDIDO_ABERTO = "Aberto"
STATUS_PEDIDO_FECHADO = "Fechado"
STATUS_PEDIDO_ENVIADO = "Enviado"
STATUS_PEDIDO_CANCELADO = "Cancelado"


def buscar_equipes_ativas():
    return (
        Equipe.query
        .filter_by(ativo=True)
        .order_by(Equipe.nome.asc())
        .all()
    )


def buscar_pedidos():
    return (
        PedidoRefeicao.query
        .order_by(
            PedidoRefeicao.data_pedido.desc(),
            PedidoRefeicao.id.desc()
        )
        .all()
    )


def buscar_pedido_por_id(pedido_id):
    return PedidoRefeicao.query.get(pedido_id)


def gerar_numero_pedido(pedido_id):
    return f"PED-{pedido_id:06d}"


def pedido_pode_ser_editado(pedido):
    return pedido and pedido.status == STATUS_PEDIDO_ABERTO


def converter_data(data_texto):
    if not data_texto:
        return None

    try:
        return datetime.strptime(data_texto, "%Y-%m-%d").date()
    except ValueError:
        return None


def formatar_data(data):
    if not data:
        return "-"

    return data.strftime("%d/%m/%Y")


def formatar_status_pedido(status):
    return status or "-"


def validar_dados_pedido(equipe_id, restaurante_id, data_pedido):
    if not equipe_id:
        return False, "Equipe é obrigatória."

    equipe = Equipe.query.filter_by(id=equipe_id, ativo=True).first()

    if not equipe:
        return False, "Equipe inválida ou inativa."

    if not restaurante_id:
        return False, "Restaurante é obrigatório."

    restaurante = Restaurante.query.filter_by(id=restaurante_id, ativo=True).first()

    if not restaurante:
        return False, "Restaurante inválido ou inativo."

    data_convertida = converter_data(data_pedido)

    if not data_convertida:
        return False, "Data do pedido é obrigatória ou inválida."

    return True, ""


def criar_pedido_refeicao(equipe_id, restaurante_id, data_pedido, observacao=None):
    valido, mensagem = validar_dados_pedido(
        equipe_id=equipe_id,
        restaurante_id=restaurante_id,
        data_pedido=data_pedido,
    )

    if not valido:
        return False, mensagem, None

    pedido = PedidoRefeicao(
        equipe_id=equipe_id,
        restaurante_id=restaurante_id,
        data_pedido=converter_data(data_pedido),
        status=STATUS_PEDIDO_ABERTO,
        observacao=observacao.strip() if observacao else "",
        enviado_whatsapp=False,
        quantidade_envios=0,
    )

    db.session.add(pedido)
    db.session.flush()

    pedido.numero_pedido = gerar_numero_pedido(pedido.id)

    db.session.commit()

    return True, "Pedido criado com sucesso.", pedido


def atualizar_pedido_refeicao(pedido, equipe_id, restaurante_id, data_pedido, observacao=None):
    if not pedido_pode_ser_editado(pedido):
        return False, "Somente pedidos em aberto podem ser editados."

    valido, mensagem = validar_dados_pedido(
        equipe_id=equipe_id,
        restaurante_id=restaurante_id,
        data_pedido=data_pedido,
    )

    if not valido:
        return False, mensagem

    pedido.equipe_id = equipe_id
    pedido.restaurante_id = restaurante_id
    pedido.data_pedido = converter_data(data_pedido)
    pedido.observacao = observacao.strip() if observacao else ""

    db.session.commit()

    return True, "Pedido atualizado com sucesso."


def cancelar_pedido_refeicao(pedido):
    if not pedido_pode_ser_editado(pedido):
        return False, "Somente pedidos em aberto podem ser cancelados."

    pedido.status = STATUS_PEDIDO_CANCELADO
    db.session.commit()

    return True, "Pedido cancelado com sucesso."

def buscar_colaboradores_do_pedido(pedido):
    if not pedido:
        return []

    return (
        Colaborador.query
        .filter(
            Colaborador.ativo.is_(True),
            Colaborador.equipe_id == pedido.equipe_id,
        )
        .order_by(Colaborador.nome.asc())
        .all()
    )


def buscar_itens_do_pedido(pedido):
    if not pedido:
        return []

    return (
        ItemCardapio.query
        .filter(
            ItemCardapio.ativo.is_(True),
            ItemCardapio.restaurante_id == pedido.restaurante_id,
        )
        .order_by(
            ItemCardapio.tipo.asc(),
            ItemCardapio.nome.asc(),
        )
        .all()
    )


def buscar_consumos_do_pedido(pedido):
    if not pedido:
        return []

    return (
        ConsumoRefeicao.query
        .filter_by(pedido_id=pedido.id)
        .join(Colaborador)
        .join(ItemCardapio)
        .order_by(
            Colaborador.nome.asc(),
            ItemCardapio.tipo.asc(),
            ItemCardapio.nome.asc(),
        )
        .all()
    )


def buscar_consumo_por_id(consumo_id):
    return ConsumoRefeicao.query.get(consumo_id)


def converter_quantidade(valor):
    try:
        quantidade = int(valor)
    except (TypeError, ValueError):
        return None

    if quantidade <= 0:
        return None

    return quantidade


def validar_consumo(pedido, colaborador_id, item_cardapio_id, quantidade):
    if not pedido:
        return False, "Pedido não encontrado.", None, None, None

    if not pedido_pode_ser_editado(pedido):
        return False, "Somente pedidos em aberto podem ter consumo alterado.", None, None, None

    if not colaborador_id:
        return False, "Colaborador é obrigatório.", None, None, None

    colaborador = Colaborador.query.filter_by(
        id=colaborador_id,
        ativo=True,
    ).first()

    if not colaborador:
        return False, "Colaborador não encontrado ou inativo.", None, None, None

    if colaborador.equipe_id != pedido.equipe_id:
        return False, "Colaborador inválido para este pedido.", None, None, None

    if not item_cardapio_id:
        return False, "Item do cardápio é obrigatório.", None, None, None

    item = ItemCardapio.query.filter_by(
        id=item_cardapio_id,
        ativo=True,
    ).first()

    if not item:
        return False, "Item do cardápio não encontrado ou inativo.", None, None, None

    if item.restaurante_id != pedido.restaurante_id:
        return False, "Item inválido para este pedido.", None, None, None

    quantidade_convertida = converter_quantidade(quantidade)

    if not quantidade_convertida:
        return False, "Quantidade deve ser maior que zero.", None, None, None

    return True, "", colaborador, item, quantidade_convertida


def criar_consumo_refeicao(
    pedido,
    colaborador_id,
    item_cardapio_id,
    quantidade,
    observacao=None
):
    valido, mensagem, colaborador, item, quantidade_convertida = validar_consumo(
        pedido=pedido,
        colaborador_id=colaborador_id,
        item_cardapio_id=item_cardapio_id,
        quantidade=quantidade,
    )

    if not valido:
        return False, mensagem

    valor_unitario = item.preco
    valor_total = valor_unitario * quantidade_convertida

    consumo = ConsumoRefeicao(
        pedido_id=pedido.id,
        colaborador_id=colaborador.id,
        item_cardapio_id=item.id,
        quantidade=quantidade_convertida,
        valor_unitario=valor_unitario,
        valor_total=valor_total,
        observacao=observacao.strip() if observacao else "",
    )

    db.session.add(consumo)
    db.session.commit()

    return True, "Consumo lançado com sucesso."


def atualizar_consumo_refeicao(
    consumo,
    colaborador_id,
    item_cardapio_id,
    quantidade,
    observacao=None
):
    if not consumo:
        return False, "Consumo não encontrado."

    pedido = consumo.pedido

    valido, mensagem, colaborador, item, quantidade_convertida = validar_consumo(
        pedido=pedido,
        colaborador_id=colaborador_id,
        item_cardapio_id=item_cardapio_id,
        quantidade=quantidade,
    )

    if not valido:
        return False, mensagem

    valor_unitario = item.preco
    valor_total = valor_unitario * quantidade_convertida

    consumo.colaborador_id = colaborador.id
    consumo.item_cardapio_id = item.id
    consumo.quantidade = quantidade_convertida
    consumo.valor_unitario = valor_unitario
    consumo.valor_total = valor_total
    consumo.observacao = observacao.strip() if observacao else ""

    db.session.commit()

    return True, "Consumo atualizado com sucesso."


def remover_consumo_refeicao(consumo):
    if not consumo:
        return False, "Consumo não encontrado."

    pedido = consumo.pedido

    if not pedido_pode_ser_editado(pedido):
        return False, "Somente pedidos em aberto podem ter consumo alterado."

    db.session.delete(consumo)
    db.session.commit()

    return True, "Consumo removido com sucesso."


def calcular_resumo_pedido(pedido):
    consumos = buscar_consumos_do_pedido(pedido)

    resumo = {}
    total_geral = Decimal("0.00")

    for consumo in consumos:
        item = consumo.item_cardapio
        tipo = item.tipo
        nome_item = item.nome

        if tipo not in resumo:
            resumo[tipo] = {}

        if nome_item not in resumo[tipo]:
            resumo[tipo][nome_item] = {
                "tipo": tipo,
                "nome": nome_item,
                "quantidade": 0,
                "valor_total": Decimal("0.00"),
            }

        resumo[tipo][nome_item]["quantidade"] += consumo.quantidade
        resumo[tipo][nome_item]["valor_total"] += consumo.valor_total
        total_geral += consumo.valor_total

    return resumo, total_geral