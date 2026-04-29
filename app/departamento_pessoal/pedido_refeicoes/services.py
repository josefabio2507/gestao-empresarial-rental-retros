import re
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import Restaurante, ItemCardapio


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