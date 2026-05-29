import re
from urllib.parse import quote
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

TIPO_CARDAPIO_REFEICAO = TIPOS_CARDAPIO[0]
TIPO_CARDAPIO_BEBIDA = TIPOS_CARDAPIO[1]

MENSAGEM_DUPLICIDADE_REFEICAO = (
    "Já foi solicitada refeição para este colaborador neste pedido."
)
MENSAGEM_DUPLICIDADE_BEBIDA = (
    "Já foi solicitada bebida para este colaborador neste pedido."
)
MENSAGEM_DUPLICIDADE_REFEICAO_BEBIDA = (
    "Este colaborador já possui refeição e bebida solicitadas neste pedido."
)

DIA_SEMANA_TODOS = "Todos os Dias"

DIAS_SEMANA_CARDAPIO = [
    "Domingo",
    "Segunda-Feira",
    "Terça-Feira",
    "Quarta-Feira",
    "Quinta-Feira",
    "Sexta-Feira",
    "Sábado",
    DIA_SEMANA_TODOS,
]

DIAS_SEMANA_POR_WEEKDAY = {
    0: "Segunda-Feira",
    1: "Terça-Feira",
    2: "Quarta-Feira",
    3: "Quinta-Feira",
    4: "Sexta-Feira",
    5: "Sábado",
    6: "Domingo",
}


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


def dia_semana_por_data(data_pedido):
    if not data_pedido:
        return None

    return DIAS_SEMANA_POR_WEEKDAY.get(data_pedido.weekday())


def normalizar_dia_semana_cardapio(dia_semana):
    dia = (dia_semana or "").strip()

    if not dia:
        return DIA_SEMANA_TODOS

    return dia


def item_disponivel_para_data(item, data_pedido):
    if not item:
        return False

    if item.tipo != "Refeição":
        return True

    dia_item = normalizar_dia_semana_cardapio(getattr(item, "dia_semana", None))

    if dia_item == DIA_SEMANA_TODOS:
        return True

    dia_pedido = dia_semana_por_data(data_pedido)

    if not dia_pedido:
        return False

    return dia_item == dia_pedido


def buscar_item_cardapio_por_id(item_id):
    return ItemCardapio.query.get(item_id)


def validar_item_cardapio(restaurante_id, tipo, nome, preco, dia_semana=None):
    if not restaurante_id:
        return False, "Restaurante é obrigatório."

    restaurante = Restaurante.query.filter_by(id=restaurante_id).first()

    if not restaurante:
        return False, "Restaurante não encontrado."

    if tipo not in TIPOS_CARDAPIO:
        return False, "Tipo de item inválido."

    dia_semana = normalizar_dia_semana_cardapio(dia_semana)

    if dia_semana not in DIAS_SEMANA_CARDAPIO:
        return False, "Dia da semana inválido."

    nome = nome.strip()

    if not nome:
        return False, "Nome do item é obrigatório."

    preco_convertido = converter_preco(preco)

    if preco_convertido is None:
        return False, "Preço inválido."

    if preco_convertido < 0:
        return False, "Preço não pode ser negativo."

    return True, ""


def criar_item_cardapio(restaurante_id, tipo, nome, preco, ativo=True, dia_semana=None):
    valido, mensagem = validar_item_cardapio(
        restaurante_id=restaurante_id,
        tipo=tipo,
        nome=nome,
        preco=preco,
        dia_semana=dia_semana,
    )

    if not valido:
        return False, mensagem

    item = ItemCardapio(
        restaurante_id=restaurante_id,
        tipo=tipo,
        nome=nome.strip(),
        preco=converter_preco(preco),
        dia_semana=(
            normalizar_dia_semana_cardapio(dia_semana)
            if tipo == "Refeição"
            else DIA_SEMANA_TODOS
        ),
        ativo=ativo,
    )

    db.session.add(item)
    db.session.commit()

    return True, "Item de cardápio criado com sucesso."


def atualizar_item_cardapio(item, restaurante_id, tipo, nome, preco, ativo=True, dia_semana=None):
    valido, mensagem = validar_item_cardapio(
        restaurante_id=restaurante_id,
        tipo=tipo,
        nome=nome,
        preco=preco,
        dia_semana=dia_semana,
    )

    if not valido:
        return False, mensagem

    item.restaurante_id = restaurante_id
    item.tipo = tipo
    item.nome = nome.strip()
    item.preco = converter_preco(preco)
    item.dia_semana = (
        normalizar_dia_semana_cardapio(dia_semana)
        if tipo == "Refeição"
        else DIA_SEMANA_TODOS
    )
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


def buscar_colaboradores_ativos():
    return (
        Colaborador.query
        .filter(Colaborador.ativo.is_(True))
        .order_by(Colaborador.nome.asc())
        .all()
    )


def texto_colaborador_historico(colaborador):
    if not colaborador:
        return ""

    return f"{colaborador.nome} - {colaborador.matricula}"


def buscar_colaborador_ativo_por_texto(texto):
    texto_normalizado = (texto or "").strip()

    if not texto_normalizado:
        return None

    colaboradores = buscar_colaboradores_ativos()
    texto_busca = texto_normalizado.lower()

    for colaborador in colaboradores:
        opcoes = {
            texto_colaborador_historico(colaborador).lower(),
            (colaborador.nome or "").strip().lower(),
            (colaborador.matricula or "").strip().lower(),
            (colaborador.cpf or "").strip().lower(),
        }

        if texto_busca in opcoes:
            return colaborador

    encontrados_por_nome = [
        colaborador
        for colaborador in colaboradores
        if texto_busca in (colaborador.nome or "").strip().lower()
    ]

    if len(encontrados_por_nome) == 1:
        return encontrados_por_nome[0]

    return None


def buscar_pedidos(status=None):
    query = PedidoRefeicao.query

    if status:
        query = query.filter(PedidoRefeicao.status == status)

    return (
        query
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


def pedido_enviado_com_correcao_permitida(pedido):
    if not pedido:
        return False

    return (
        pedido.status == STATUS_PEDIDO_ENVIADO
        and pedido.quantidade_envios == 1
    )


def pedido_pode_ser_editado(pedido):
    if not pedido:
        return False

    if pedido.status == STATUS_PEDIDO_ABERTO:
        return True

    if pedido.status == STATUS_PEDIDO_FECHADO:
        return True

    if pedido_enviado_com_correcao_permitida(pedido):
        return True

    return False

def pedido_pode_ser_cancelado(pedido):
    if not pedido:
        return False

    return pedido.status in {
        STATUS_PEDIDO_ABERTO,
        STATUS_PEDIDO_FECHADO,
        STATUS_PEDIDO_ENVIADO,
    }


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
    if not pedido_pode_ser_cancelado(pedido):
        return False, "Somente pedidos abertos, fechados ou enviados podem ser cancelados."

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


def buscar_itens_do_pedido(pedido, incluir_item_ids=None):
    if not pedido:
        return []

    incluir_item_ids = set(incluir_item_ids or [])
    itens = (
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

    return [
        item for item in itens
        if item.id in incluir_item_ids or item_disponivel_para_data(item, pedido.data_pedido)
    ]


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


def buscar_consumo_existente_por_tipo(
    pedido_id,
    colaborador_id,
    tipo_item,
    excluir_consumo_ids=None,
):
    if not pedido_id or not colaborador_id or not tipo_item:
        return None

    excluir_consumo_ids = [
        consumo_id
        for consumo_id in (excluir_consumo_ids or [])
        if consumo_id
    ]

    query = (
        ConsumoRefeicao.query
        .join(ItemCardapio)
        .filter(
            ConsumoRefeicao.pedido_id == pedido_id,
            ConsumoRefeicao.colaborador_id == colaborador_id,
            ConsumoRefeicao.quantidade > 0,
            ItemCardapio.tipo == tipo_item,
        )
    )

    if excluir_consumo_ids:
        query = query.filter(~ConsumoRefeicao.id.in_(excluir_consumo_ids))

    return query.first()


def validar_duplicidade_consumo_colaborador(
    pedido,
    colaborador_id,
    possui_refeicao=False,
    possui_bebida=False,
    excluir_consumo_ids=None,
):
    if not pedido or not colaborador_id:
        return True, ""

    duplicidade_refeicao = False
    duplicidade_bebida = False

    if possui_refeicao:
        duplicidade_refeicao = buscar_consumo_existente_por_tipo(
            pedido_id=pedido.id,
            colaborador_id=colaborador_id,
            tipo_item=TIPO_CARDAPIO_REFEICAO,
            excluir_consumo_ids=excluir_consumo_ids,
        ) is not None

    if possui_bebida:
        duplicidade_bebida = buscar_consumo_existente_por_tipo(
            pedido_id=pedido.id,
            colaborador_id=colaborador_id,
            tipo_item=TIPO_CARDAPIO_BEBIDA,
            excluir_consumo_ids=excluir_consumo_ids,
        ) is not None

    if duplicidade_refeicao and duplicidade_bebida:
        return False, MENSAGEM_DUPLICIDADE_REFEICAO_BEBIDA

    if duplicidade_refeicao:
        return False, MENSAGEM_DUPLICIDADE_REFEICAO

    if duplicidade_bebida:
        return False, MENSAGEM_DUPLICIDADE_BEBIDA

    return True, ""


def validar_consumo(
    pedido,
    colaborador_id,
    item_cardapio_id,
    quantidade,
    permitir_item_indisponivel_id=None,
):
    if not pedido:
        return False, "Pedido não encontrado.", None, None, None

    if not pedido_pode_ser_editado(pedido):
        return False, "Este pedido não permite mais alterações de consumo.", None, None, None

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

    item_indisponivel_permitido = (
        permitir_item_indisponivel_id
        and item.id == permitir_item_indisponivel_id
    )

    if item.tipo == "Refeição" and not item_disponivel_para_data(item, pedido.data_pedido):
        if not item_indisponivel_permitido:
            return (
                False,
                "Refeição indisponível para o dia da semana deste pedido.",
                None,
                None,
                None,
            )

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

    valido, mensagem = validar_duplicidade_consumo_colaborador(
        pedido=pedido,
        colaborador_id=colaborador.id,
        possui_refeicao=item.tipo == TIPO_CARDAPIO_REFEICAO,
        possui_bebida=item.tipo == TIPO_CARDAPIO_BEBIDA,
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


def criar_consumos_refeicao_bebida(
    pedido,
    colaborador_id,
    refeicao_id=None,
    bebida_id=None,
    quantidade_refeicao=1,
    quantidade_bebida=1,
    observacao=None
):
    itens_para_lancar = []

    if refeicao_id:
        itens_para_lancar.append(
            {
                "item_id": refeicao_id,
                "quantidade": quantidade_refeicao,
                "tipo_esperado": "Refeição",
            }
        )

    if bebida_id:
        itens_para_lancar.append(
            {
                "item_id": bebida_id,
                "quantidade": quantidade_bebida,
                "tipo_esperado": "Bebida",
            }
        )

    if not itens_para_lancar:
        return False, "Selecione uma refeição ou uma bebida para cadastrar o consumo."

    consumos_validados = []

    for dados_item in itens_para_lancar:
        valido, mensagem, colaborador, item, quantidade_convertida = validar_consumo(
            pedido=pedido,
            colaborador_id=colaborador_id,
            item_cardapio_id=dados_item["item_id"],
            quantidade=dados_item["quantidade"],
        )

        if not valido:
            return False, mensagem

        if item.tipo != dados_item["tipo_esperado"]:
            return False, "Item selecionado inválido para este campo."

        consumos_validados.append(
            {
                "colaborador": colaborador,
                "item": item,
                "quantidade": quantidade_convertida,
            }
        )

    colaborador_validado = consumos_validados[0]["colaborador"]
    valido, mensagem = validar_duplicidade_consumo_colaborador(
        pedido=pedido,
        colaborador_id=colaborador_validado.id,
        possui_refeicao=any(
            dados["item"].tipo == TIPO_CARDAPIO_REFEICAO
            for dados in consumos_validados
        ),
        possui_bebida=any(
            dados["item"].tipo == TIPO_CARDAPIO_BEBIDA
            for dados in consumos_validados
        ),
    )

    if not valido:
        return False, mensagem

    observacao_normalizada = observacao.strip() if observacao else ""

    for dados_consumo in consumos_validados:
        item = dados_consumo["item"]
        quantidade_convertida = dados_consumo["quantidade"]
        valor_unitario = item.preco
        valor_total = valor_unitario * quantidade_convertida

        consumo = ConsumoRefeicao(
            pedido_id=pedido.id,
            colaborador_id=dados_consumo["colaborador"].id,
            item_cardapio_id=item.id,
            quantidade=quantidade_convertida,
            valor_unitario=valor_unitario,
            valor_total=valor_total,
            observacao=observacao_normalizada,
        )
        db.session.add(consumo)

    db.session.commit()

    if len(consumos_validados) == 1:
        return True, "Consumo lançado com sucesso."

    return True, "Consumos lançados com sucesso."


def buscar_consumos_relacionados(consumo):
    if not consumo:
        return None, None

    observacao_base = (consumo.observacao or "").strip()
    consumo_refeicao = None
    consumo_bebida = None

    consumos = (
        ConsumoRefeicao.query
        .join(ItemCardapio)
        .filter(
            ConsumoRefeicao.pedido_id == consumo.pedido_id,
            ConsumoRefeicao.colaborador_id == consumo.colaborador_id,
        )
        .order_by(ConsumoRefeicao.id.asc())
        .all()
    )

    for consumo_relacionado in consumos:
        observacao_relacionada = (consumo_relacionado.observacao or "").strip()

        if observacao_relacionada != observacao_base:
            continue

        item = consumo_relacionado.item_cardapio

        if not item:
            continue

        if item.tipo == "Refeição" and (
            consumo_relacionado.id == consumo.id or consumo_refeicao is None
        ):
            consumo_refeicao = consumo_relacionado

        if item.tipo == "Bebida" and (
            consumo_relacionado.id == consumo.id or consumo_bebida is None
        ):
            consumo_bebida = consumo_relacionado

    return consumo_refeicao, consumo_bebida


def atualizar_consumos_refeicao_bebida(
    consumo_referencia,
    colaborador_id,
    refeicao_id=None,
    bebida_id=None,
    quantidade_refeicao=1,
    quantidade_bebida=1,
    observacao=None
):
    if not consumo_referencia:
        return False, "Consumo não encontrado."

    pedido = consumo_referencia.pedido

    if not pedido_pode_ser_editado(pedido):
        return False, "Este pedido não permite mais alterações de consumo."

    if not refeicao_id and not bebida_id:
        return False, "Selecione uma refeição ou uma bebida para atualizar o consumo."

    consumo_refeicao, consumo_bebida = buscar_consumos_relacionados(consumo_referencia)
    excluir_consumo_ids = []

    for consumo_atual in (consumo_referencia, consumo_refeicao, consumo_bebida):
        if consumo_atual and consumo_atual.id not in excluir_consumo_ids:
            excluir_consumo_ids.append(consumo_atual.id)

    consumos_validados = {}

    for chave, item_id, quantidade, tipo_esperado in [
        ("refeicao", refeicao_id, quantidade_refeicao, "Refeição"),
        ("bebida", bebida_id, quantidade_bebida, "Bebida"),
    ]:
        if not item_id:
            continue

        valido, mensagem, colaborador, item, quantidade_convertida = validar_consumo(
            pedido=pedido,
            colaborador_id=colaborador_id,
            item_cardapio_id=item_id,
            quantidade=quantidade,
            permitir_item_indisponivel_id=(
                consumo_refeicao.item_cardapio_id
                if chave == "refeicao" and consumo_refeicao
                else None
            ),
        )

        if not valido:
            return False, mensagem

        if item.tipo != tipo_esperado:
            return False, "Item selecionado inválido para este campo."

        consumos_validados[chave] = {
            "colaborador": colaborador,
            "item": item,
            "quantidade": quantidade_convertida,
        }

    colaborador_validado = next(iter(consumos_validados.values()))["colaborador"]
    valido, mensagem = validar_duplicidade_consumo_colaborador(
        pedido=pedido,
        colaborador_id=colaborador_validado.id,
        possui_refeicao="refeicao" in consumos_validados,
        possui_bebida="bebida" in consumos_validados,
        excluir_consumo_ids=excluir_consumo_ids,
    )

    if not valido:
        return False, mensagem

    observacao_normalizada = observacao.strip() if observacao else ""

    def salvar_consumo(consumo, dados_consumo):
        item = dados_consumo["item"]
        quantidade_convertida = dados_consumo["quantidade"]
        valor_unitario = item.preco
        valor_total = valor_unitario * quantidade_convertida

        if not consumo:
            consumo = ConsumoRefeicao(pedido_id=pedido.id)
            db.session.add(consumo)

        consumo.colaborador_id = dados_consumo["colaborador"].id
        consumo.item_cardapio_id = item.id
        consumo.quantidade = quantidade_convertida
        consumo.valor_unitario = valor_unitario
        consumo.valor_total = valor_total
        consumo.observacao = observacao_normalizada

        return consumo

    if "refeicao" in consumos_validados:
        salvar_consumo(consumo_refeicao, consumos_validados["refeicao"])
    elif consumo_refeicao:
        db.session.delete(consumo_refeicao)

    if "bebida" in consumos_validados:
        salvar_consumo(consumo_bebida, consumos_validados["bebida"])
    elif consumo_bebida:
        db.session.delete(consumo_bebida)

    db.session.commit()

    return True, "Consumo atualizado com sucesso."


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

    valido, mensagem = validar_duplicidade_consumo_colaborador(
        pedido=pedido,
        colaborador_id=colaborador.id,
        possui_refeicao=item.tipo == TIPO_CARDAPIO_REFEICAO,
        possui_bebida=item.tipo == TIPO_CARDAPIO_BEBIDA,
        excluir_consumo_ids=[consumo.id],
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
        return False, "Este pedido não permite mais alterações de consumo."

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

def pedido_tem_consumo(pedido):
    if not pedido:
        return False

    return ConsumoRefeicao.query.filter_by(pedido_id=pedido.id).first() is not None


def pedido_pode_ser_fechado(pedido):
    if not pedido:
        return False, "Pedido não encontrado."

    if pedido.status != STATUS_PEDIDO_ABERTO:
        return False, "Somente pedidos em aberto podem ser fechados."

    if not pedido_tem_consumo(pedido):
        return False, "Não é possível fechar um pedido sem consumo lançado."

    return True, ""


def fechar_pedido_refeicao(pedido):
    permitido, mensagem = pedido_pode_ser_fechado(pedido)

    if not permitido:
        return False, mensagem

    pedido.status = STATUS_PEDIDO_FECHADO
    db.session.commit()

    return True, "Pedido fechado com sucesso."


def pedido_pode_enviar_whatsapp(pedido):
    if not pedido:
        return False, "Pedido não encontrado."

    if pedido.status == STATUS_PEDIDO_CANCELADO:
        return False, "Pedido cancelado não pode ser enviado por WhatsApp."

    if pedido.status not in [STATUS_PEDIDO_FECHADO, STATUS_PEDIDO_ENVIADO]:
        return False, "Somente pedidos fechados ou enviados podem ser enviados por WhatsApp."

    if not pedido_tem_consumo(pedido):
        return False, "Pedido sem consumo não pode ser enviado por WhatsApp."

    if pedido.quantidade_envios >= 2:
        return False, "Limite de envios atingido para este pedido."

    return True, ""


def icone_item_por_tipo(tipo):
    if tipo == "Refeição":
        return "🍽️"

    if tipo == "Bebida":
        return "🥤"

    return "▫️"


def titulo_resumo_por_tipo(tipo):
    if tipo == "Refeição":
        return "🍽️ *Refeições*"

    if tipo == "Bebida":
        return "🥤 *Bebidas*"

    return "*Outros*"


def normalizar_observacao_whatsapp(observacao):
    return observacao.strip() if observacao else ""


def gerar_mensagem_whatsapp(pedido):
    consumos = buscar_consumos_do_pedido(pedido)
    resumo_pedido, total_geral = calcular_resumo_pedido(pedido)

    linhas = []

    linhas.append("📝 *Pedido de Refeição - Rental Retros*")
    linhas.append("")
    linhas.append(f"🆔 Pedido: {pedido.numero_pedido}")
    linhas.append(f"Data: {formatar_data(pedido.data_pedido)}")
    linhas.append(f"Equipe: {pedido.equipe.nome if pedido.equipe else '-'}")
    linhas.append(f"Restaurante: {pedido.restaurante.nome if pedido.restaurante else '-'}")

    observacao_pedido = normalizar_observacao_whatsapp(getattr(pedido, "observacao", ""))

    if observacao_pedido:
        linhas.append(f"Obs. do pedido: {observacao_pedido}")

    linhas.append("")
    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append("")
    linhas.append("👤 *Consumo por colaborador*")
    linhas.append("")

    consumos_por_colaborador = {}

    for consumo in consumos:
        colaborador = consumo.colaborador

        if not colaborador:
            continue

        if colaborador.id not in consumos_por_colaborador:
            consumos_por_colaborador[colaborador.id] = {
                "colaborador": colaborador,
                "consumos": [],
            }

        consumos_por_colaborador[colaborador.id]["consumos"].append(consumo)

    contador = 1

    for grupo in consumos_por_colaborador.values():
        colaborador = grupo["colaborador"]
        linhas.append(f"{contador}. *{colaborador.nome}*")

        observacoes = []
        observacoes_registradas = set()

        for consumo in grupo["consumos"]:
            item = consumo.item_cardapio

            if not item:
                continue

            icone = icone_item_por_tipo(item.tipo)
            linhas.append(f"{icone} {item.nome} | Qtd: {consumo.quantidade}")

            observacao_consumo = normalizar_observacao_whatsapp(consumo.observacao)
            chave_observacao = observacao_consumo.lower()

            if observacao_consumo and chave_observacao not in observacoes_registradas:
                observacoes.append(observacao_consumo)
                observacoes_registradas.add(chave_observacao)

        for observacao in observacoes:
            linhas.append(f"💬 Obs: {observacao}")

        linhas.append("")
        contador += 1

    linhas.append("━━━━━━━━━━━━━━━━━━━━")
    linhas.append("")
    linhas.append("🧮 *Resumo do Pedido*")
    linhas.append("")

    for tipo, itens in resumo_pedido.items():
        linhas.append(titulo_resumo_por_tipo(tipo))

        for nome_item, dados in itens.items():
            linhas.append(
                f"- {nome_item} | Qtd: {dados['quantidade']}"
            )

        linhas.append("")

    linhas.append(f"💰 *Total geral:* {formatar_moeda(total_geral)}")

    return "\n".join(linhas)


def gerar_link_whatsapp(pedido):
    permitido, mensagem = pedido_pode_enviar_whatsapp(pedido)

    if not permitido:
        return False, mensagem, None

    mensagem_whatsapp = gerar_mensagem_whatsapp(pedido)
    mensagem_codificada = quote(mensagem_whatsapp)

    link = f"https://wa.me/?text={mensagem_codificada}"

    return True, "Link do WhatsApp gerado com sucesso.", link


def registrar_envio_whatsapp(pedido):
    permitido, mensagem = pedido_pode_enviar_whatsapp(pedido)

    if not permitido:
        return False, mensagem

    pedido.enviado_whatsapp = True
    pedido.quantidade_envios = (pedido.quantidade_envios or 0) + 1
    pedido.status = STATUS_PEDIDO_ENVIADO

    db.session.commit()

    return True, "Envio por WhatsApp registrado com sucesso."


def status_whatsapp_pedido(pedido):
    if pedido.status == STATUS_PEDIDO_CANCELADO:
        return STATUS_PEDIDO_CANCELADO

    if not pedido.enviado_whatsapp:
        return "Não enviado"

    if pedido.quantidade_envios == 1:
        return "Reenvio disponível"

    if pedido.quantidade_envios >= 2:
        return "Limite atingido"

    return "Não enviado"

def buscar_pedidos_relatorio_refeicoes(
    data_inicial,
    data_final,
    equipe_id=None,
    restaurante_id=None,
    status="Enviado",
):
    data_inicio = converter_data(data_inicial)
    data_fim = converter_data(data_final)

    if not data_inicio or not data_fim:
        return []

    query = (
        PedidoRefeicao.query
        .join(ConsumoRefeicao, ConsumoRefeicao.pedido_id == PedidoRefeicao.id)
        .filter(PedidoRefeicao.data_pedido >= data_inicio)
        .filter(PedidoRefeicao.data_pedido <= data_fim)
        .filter(PedidoRefeicao.status != STATUS_PEDIDO_CANCELADO)
    )

    if equipe_id:
        query = query.filter(PedidoRefeicao.equipe_id == equipe_id)

    if restaurante_id:
        query = query.filter(PedidoRefeicao.restaurante_id == restaurante_id)

    if status and status != "Todos":
        query = query.filter(PedidoRefeicao.status == status)

        if status == STATUS_PEDIDO_ENVIADO:
            query = query.filter(PedidoRefeicao.quantidade_envios >= 1)

    return (
        query
        .distinct()
        .order_by(PedidoRefeicao.data_pedido.asc(), PedidoRefeicao.id.asc())
        .all()
    )


def calcular_total_pedido_relatorio(pedido):
    if not pedido:
        return Decimal("0.00")

    total = Decimal("0.00")

    for consumo in pedido.consumos:
        item = consumo.item_cardapio

        if not item or item.tipo not in {"Refeição", "Bebida"}:
            continue

        total += consumo.valor_total or Decimal("0.00")

    return total


def calcular_resumo_totais_relatorio(pedidos):
    resumo = {
        "quantidade_refeicoes": 0,
        "valor_refeicoes": Decimal("0.00"),
        "quantidade_bebidas": 0,
        "valor_bebidas": Decimal("0.00"),
    }

    for pedido in pedidos:
        for consumo in pedido.consumos:
            item = consumo.item_cardapio

            if not item:
                continue

            quantidade = consumo.quantidade or 0
            total = consumo.valor_total or Decimal("0.00")

            if item.tipo == "Refeição":
                resumo["quantidade_refeicoes"] += quantidade
                resumo["valor_refeicoes"] += total
            elif item.tipo == "Bebida":
                resumo["quantidade_bebidas"] += quantidade
                resumo["valor_bebidas"] += total

    return resumo


def calcular_resumo_itens_relatorio(pedidos):
    resumo = {}

    for pedido in pedidos:
        for consumo in pedido.consumos:
            item = consumo.item_cardapio

            if not item or item.tipo not in {"Refeição", "Bebida"}:
                continue

            chave = (item.tipo, item.nome)

            if chave not in resumo:
                resumo[chave] = {
                    "tipo": item.tipo,
                    "nome": item.nome,
                    "quantidade": 0,
                    "total": Decimal("0.00"),
                }

            resumo[chave]["quantidade"] += consumo.quantidade
            resumo[chave]["total"] += consumo.valor_total or Decimal("0.00")

    return list(resumo.values())


def calcular_resumo_pedidos_relatorio(pedidos):
    resumo = []

    for pedido in pedidos:
        resumo.append({
            "data": pedido.data_pedido,
            "numero": pedido.numero_pedido,
            "total": calcular_total_pedido_relatorio(pedido),
        })

    return resumo


def agrupar_relatorio_por_restaurante(pedidos):
    grupos = {}

    for pedido in pedidos:
        restaurante = pedido.restaurante
        grupo_id = restaurante.id if restaurante else 0
        nome_grupo = restaurante.nome if restaurante else "Sem restaurante"

        if grupo_id not in grupos:
            grupos[grupo_id] = {
                "titulo": nome_grupo,
                "tipo": "Restaurante",
                "pedidos": [],
                "resumo_itens": [],
                "total_grupo": Decimal("0.00"),
            }

        total_pedido = calcular_total_pedido_relatorio(pedido)

        grupos[grupo_id]["pedidos"].append({
            "numero": pedido.numero_pedido,
            "data": pedido.data_pedido,
            "equipe": pedido.equipe.nome if pedido.equipe else "-",
            "restaurante": nome_grupo,
            "status": pedido.status,
            "quantidade_envios": pedido.quantidade_envios,
            "total": total_pedido,
        })

        grupos[grupo_id]["total_grupo"] += total_pedido

    for grupo in grupos.values():
        pedidos_do_grupo = [
            pedido
            for pedido in pedidos
            if (pedido.restaurante.nome if pedido.restaurante else "Sem restaurante") == grupo["titulo"]
        ]
        grupo["resumo_itens"] = calcular_resumo_itens_relatorio(pedidos_do_grupo)

    return list(grupos.values())


def agrupar_relatorio_por_equipe(pedidos):
    grupos = {}

    for pedido in pedidos:
        equipe = pedido.equipe
        grupo_id = equipe.id if equipe else 0
        nome_grupo = equipe.nome if equipe else "Sem equipe"

        if grupo_id not in grupos:
            grupos[grupo_id] = {
                "titulo": nome_grupo,
                "tipo": "Equipe",
                "pedidos": [],
                "resumo_itens": [],
                "total_grupo": Decimal("0.00"),
            }

        total_pedido = calcular_total_pedido_relatorio(pedido)

        grupos[grupo_id]["pedidos"].append({
            "numero": pedido.numero_pedido,
            "data": pedido.data_pedido,
            "equipe": nome_grupo,
            "restaurante": pedido.restaurante.nome if pedido.restaurante else "-",
            "status": pedido.status,
            "quantidade_envios": pedido.quantidade_envios,
            "total": total_pedido,
        })

        grupos[grupo_id]["total_grupo"] += total_pedido

    for grupo in grupos.values():
        pedidos_do_grupo = [
            pedido
            for pedido in pedidos
            if (pedido.equipe.nome if pedido.equipe else "Sem equipe") == grupo["titulo"]
        ]
        grupo["resumo_itens"] = calcular_resumo_itens_relatorio(pedidos_do_grupo)

    return list(grupos.values())


def montar_relatorio_refeicoes(
    data_inicial,
    data_final,
    equipe_id=None,
    restaurante_id=None,
    status="Enviado",
    agrupamento="restaurante",
):
    pedidos = buscar_pedidos_relatorio_refeicoes(
        data_inicial=data_inicial,
        data_final=data_final,
        equipe_id=equipe_id,
        restaurante_id=restaurante_id,
        status=status,
    )

    if agrupamento == "equipe":
        grupos = agrupar_relatorio_por_equipe(pedidos)
        agrupamento_label = "Equipe"
    else:
        grupos = agrupar_relatorio_por_restaurante(pedidos)
        agrupamento_label = "Restaurante"

    resumo_totais = calcular_resumo_totais_relatorio(pedidos)
    resumo_pedidos = calcular_resumo_pedidos_relatorio(pedidos)
    total_geral = resumo_totais["valor_refeicoes"] + resumo_totais["valor_bebidas"]

    return {
        "periodo": {
            "data_inicial": data_inicial,
            "data_final": data_final,
        },
        "status": status,
        "agrupamento": agrupamento,
        "agrupamento_label": agrupamento_label,
        "grupos": grupos,
        "total_geral": total_geral,
        "quantidade_refeicoes": resumo_totais["quantidade_refeicoes"],
        "valor_refeicoes": resumo_totais["valor_refeicoes"],
        "quantidade_bebidas": resumo_totais["quantidade_bebidas"],
        "valor_bebidas": resumo_totais["valor_bebidas"],
        "quantidade_pedidos": len(pedidos),
        "resumo_pedidos": resumo_pedidos,
    }


def status_relatorio_opcoes():
    return [
        "Enviado",
        "Aberto",
        "Fechado",
        "Cancelado",
        "Todos",
    ]


def buscar_consumos_historico_colaborador(colaborador, data_inicial, data_final):
    data_inicio = converter_data(data_inicial)
    data_fim = converter_data(data_final)

    if not colaborador or not data_inicio or not data_fim:
        return []

    if data_inicio > data_fim:
        return []

    return (
        ConsumoRefeicao.query
        .join(PedidoRefeicao, ConsumoRefeicao.pedido_id == PedidoRefeicao.id)
        .join(ItemCardapio, ConsumoRefeicao.item_cardapio_id == ItemCardapio.id)
        .join(Restaurante, PedidoRefeicao.restaurante_id == Restaurante.id)
        .outerjoin(Equipe, PedidoRefeicao.equipe_id == Equipe.id)
        .filter(
            ConsumoRefeicao.colaborador_id == colaborador.id,
            PedidoRefeicao.data_pedido >= data_inicio,
            PedidoRefeicao.data_pedido <= data_fim,
            PedidoRefeicao.status != STATUS_PEDIDO_CANCELADO,
            ItemCardapio.tipo.in_([TIPO_CARDAPIO_REFEICAO, TIPO_CARDAPIO_BEBIDA]),
        )
        .order_by(
            PedidoRefeicao.data_pedido.asc(),
            PedidoRefeicao.id.asc(),
            ItemCardapio.tipo.asc(),
            ItemCardapio.nome.asc(),
        )
        .all()
    )


def montar_historico_colaborador_refeicoes(colaborador, data_inicial, data_final):
    consumos = buscar_consumos_historico_colaborador(
        colaborador=colaborador,
        data_inicial=data_inicial,
        data_final=data_final,
    )

    resumo = {
        "quantidade_refeicoes": 0,
        "valor_refeicoes": Decimal("0.00"),
        "quantidade_bebidas": 0,
        "valor_bebidas": Decimal("0.00"),
        "total_geral": Decimal("0.00"),
        "quantidade_consumos": len(consumos),
    }
    itens = []

    for consumo in consumos:
        item = consumo.item_cardapio
        pedido = consumo.pedido

        if not item or not pedido:
            continue

        quantidade = consumo.quantidade or 0
        valor_total = consumo.valor_total or Decimal("0.00")

        if item.tipo == TIPO_CARDAPIO_REFEICAO:
            resumo["quantidade_refeicoes"] += quantidade
            resumo["valor_refeicoes"] += valor_total
        elif item.tipo == TIPO_CARDAPIO_BEBIDA:
            resumo["quantidade_bebidas"] += quantidade
            resumo["valor_bebidas"] += valor_total

        resumo["total_geral"] += valor_total

        itens.append({
            "data": pedido.data_pedido,
            "numero_pedido": pedido.numero_pedido,
            "equipe": pedido.equipe.nome if pedido.equipe else "-",
            "restaurante": pedido.restaurante.nome if pedido.restaurante else "-",
            "status": pedido.status,
            "tipo": item.tipo,
            "nome_item": item.nome,
            "quantidade": quantidade,
            "valor_unitario": consumo.valor_unitario,
            "valor_total": valor_total,
            "observacao": consumo.observacao or "",
        })

    return {
        "colaborador": colaborador,
        "resumo": resumo,
        "itens": itens,
    }
