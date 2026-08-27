from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    Colaborador,
    SegurancaTrabalhoEntregaEpi,
    SuprimentosItem,
    SuprimentosMovimentacaoEstoque,
)
from app.services.suprimentos_service import (
    STATUS_MOVIMENTACAO_ESTOQUE_CANCELADA,
    STATUS_MOVIMENTACAO_ESTOQUE_REGISTRADA,
    TIPO_MOVIMENTACAO_ESTOQUE_SAIDA,
    buscar_por_id,
    data_ou_none,
    decimal_ou_none,
    inteiro_ou_none,
    texto,
    texto_maiusculo,
)
from app.utils.datas import agora_brasil


ORIGEM_MOVIMENTACAO_ENTREGA_EPI = "Entrega EPI"
STATUS_ENTREGA_EPI_ATIVA = "Ativa"
STATUS_ENTREGA_EPI_CANCELADA = "Cancelada"
TIPOS_MATERIAL_ENTREGA = ["EPI", "Uniforme"]
MOTIVOS_ENTREGA_EPI = [
    "Admissao",
    "Reposicao",
    "Desgaste",
    "Troca de funcao",
    "Perda",
    "Uniforme",
    "Outro",
]


def buscar_colaboradores_ativos():
    return (
        Colaborador.query
        .filter(Colaborador.ativo.is_(True))
        .order_by(Colaborador.nome.asc())
        .all()
    )


def buscar_itens_estoque_para_entrega():
    return (
        SuprimentosItem.query
        .options(joinedload(SuprimentosItem.unidade_medida), joinedload(SuprimentosItem.movimentacoes_estoque))
        .filter(
            SuprimentosItem.ativo.is_(True),
            SuprimentosItem.item_estocavel.is_(True),
        )
        .order_by(SuprimentosItem.descricao.asc())
        .all()
    )


def buscar_entregas_epi(colaborador_id=None, item_id=None, tipo_material=None):
    colaborador_id = inteiro_ou_none(colaborador_id)
    item_id = inteiro_ou_none(item_id)
    tipo_material = texto(tipo_material)

    query = (
        SegurancaTrabalhoEntregaEpi.query
        .options(
            joinedload(SegurancaTrabalhoEntregaEpi.colaborador).joinedload(Colaborador.equipe),
            joinedload(SegurancaTrabalhoEntregaEpi.item).joinedload(SuprimentosItem.unidade_medida),
            joinedload(SegurancaTrabalhoEntregaEpi.entregue_por),
            joinedload(SegurancaTrabalhoEntregaEpi.cancelado_por),
            joinedload(SegurancaTrabalhoEntregaEpi.movimentacao_estoque),
        )
    )

    if colaborador_id:
        query = query.filter(SegurancaTrabalhoEntregaEpi.colaborador_id == colaborador_id)

    if item_id:
        query = query.filter(SegurancaTrabalhoEntregaEpi.item_id == item_id)

    if tipo_material in TIPOS_MATERIAL_ENTREGA:
        query = query.filter(SegurancaTrabalhoEntregaEpi.tipo_material == tipo_material)

    return query.order_by(SegurancaTrabalhoEntregaEpi.data_entrega.desc(), SegurancaTrabalhoEntregaEpi.id.desc()).all()


def _dados_entrega(form_data):
    return {
        "colaborador_id": inteiro_ou_none(form_data.get("colaborador_id")),
        "item_id": inteiro_ou_none(form_data.get("item_id")),
        "tipo_material": texto(form_data.get("tipo_material")),
        "quantidade": decimal_ou_none(form_data.get("quantidade")),
        "data_entrega": data_ou_none(form_data.get("data_entrega")) or date.today(),
        "ca_numero": texto_maiusculo(form_data.get("ca_numero")) or None,
        "tamanho": texto_maiusculo(form_data.get("tamanho")) or None,
        "motivo_entrega": texto_maiusculo(form_data.get("motivo_entrega")),
        "observacoes": texto_maiusculo(form_data.get("observacoes")) or None,
    }


def _validar_entrega(dados):
    colaborador = Colaborador.query.get(dados["colaborador_id"]) if dados["colaborador_id"] else None
    if not colaborador or not colaborador.ativo:
        return False, "Informe um colaborador ativo.", None, None

    item = (
        SuprimentosItem.query
        .options(joinedload(SuprimentosItem.movimentacoes_estoque))
        .get(dados["item_id"])
        if dados["item_id"]
        else None
    )
    if not item or not item.ativo or not item.item_estocavel:
        return False, "Informe um item estocavel ativo do estoque de Suprimentos.", None, None

    if dados["tipo_material"] not in TIPOS_MATERIAL_ENTREGA:
        return False, "Informe se o material entregue e EPI ou Uniforme.", None, None

    if dados["quantidade"] is None or dados["quantidade"] <= 0:
        return False, "Quantidade deve ser maior que zero.", None, None

    if not dados["data_entrega"]:
        return False, "Data da entrega e obrigatoria.", None, None

    if not dados["motivo_entrega"]:
        return False, "Motivo da entrega e obrigatorio.", None, None

    return True, "", colaborador, item


def _observacao_movimentacao(colaborador, tipo_material, motivo_entrega, observacoes=None):
    return (
        f"Entrega para {colaborador.matricula} - {colaborador.nome}. "
        f"Tipo: {tipo_material}. Motivo: {motivo_entrega}."
        f"{' ' + observacoes if observacoes else ''}"
    )


def registrar_entrega_epi(form_data, usuario):
    dados = _dados_entrega(form_data)
    valido, mensagem, colaborador, item = _validar_entrega(dados)

    if not valido:
        return False, mensagem, None

    saldo_atual = Decimal(item.saldo_estoque)
    if dados["quantidade"] > saldo_atual:
        return False, "Entrega nao pode ser maior que o saldo atual do item.", None

    entrega = SegurancaTrabalhoEntregaEpi(
        colaborador_id=colaborador.id,
        item_id=item.id,
        entregue_por_usuario_id=usuario.id,
        tipo_material=dados["tipo_material"],
        quantidade=dados["quantidade"],
        data_entrega=dados["data_entrega"],
        ca_numero=dados["ca_numero"],
        tamanho=dados["tamanho"],
        motivo_entrega=dados["motivo_entrega"],
        observacoes=dados["observacoes"],
        status=STATUS_ENTREGA_EPI_ATIVA,
    )
    db.session.add(entrega)
    db.session.flush()

    documento_numero = f"ENT-EPI-{entrega.id:06d}"
    movimentacao = SuprimentosMovimentacaoEstoque(
        item_id=item.id,
        responsavel_usuario_id=usuario.id,
        tipo=TIPO_MOVIMENTACAO_ESTOQUE_SAIDA,
        origem=ORIGEM_MOVIMENTACAO_ENTREGA_EPI,
        status=STATUS_MOVIMENTACAO_ESTOQUE_REGISTRADA,
        documento_tipo="ENTREGA EPI",
        documento_numero=documento_numero,
        quantidade=dados["quantidade"] * Decimal("-1"),
        observacoes=_observacao_movimentacao(
            colaborador,
            dados["tipo_material"],
            dados["motivo_entrega"],
            dados["observacoes"],
        ),
        movimentado_em=datetime.combine(dados["data_entrega"], datetime.min.time()),
    )
    db.session.add(movimentacao)
    db.session.flush()

    entrega.movimentacao_estoque_id = movimentacao.id
    db.session.commit()

    return True, "Entrega registrada e estoque abatido com sucesso.", entrega


def buscar_entrega_epi_por_id(entrega_id):
    return buscar_por_id(SegurancaTrabalhoEntregaEpi, entrega_id)


def editar_entrega_epi(entrega, form_data, usuario):
    if not entrega:
        return False, "Entrega nao encontrada.", None

    if entrega.status == STATUS_ENTREGA_EPI_CANCELADA:
        return False, "Entrega cancelada nao pode ser editada.", None

    dados = _dados_entrega(form_data)
    valido, mensagem, colaborador, item = _validar_entrega(dados)

    if not valido:
        return False, mensagem, None

    movimentacao = entrega.movimentacao_estoque
    quantidade_atual = Decimal(entrega.quantidade)
    item_atual_id = entrega.item_id

    if item.id == item_atual_id:
        saldo_disponivel = Decimal(item.saldo_estoque) + quantidade_atual
    else:
        saldo_disponivel = Decimal(item.saldo_estoque)

    if dados["quantidade"] > saldo_disponivel:
        return False, "Entrega nao pode ser maior que o saldo atual disponivel do item.", None

    entrega.colaborador_id = colaborador.id
    entrega.item_id = item.id
    entrega.tipo_material = dados["tipo_material"]
    entrega.quantidade = dados["quantidade"]
    entrega.data_entrega = dados["data_entrega"]
    entrega.ca_numero = dados["ca_numero"]
    entrega.tamanho = dados["tamanho"]
    entrega.motivo_entrega = dados["motivo_entrega"]
    entrega.observacoes = dados["observacoes"]

    if movimentacao:
        movimentacao.item_id = item.id
        movimentacao.responsavel_usuario_id = usuario.id if usuario else movimentacao.responsavel_usuario_id
        movimentacao.status = STATUS_MOVIMENTACAO_ESTOQUE_REGISTRADA
        movimentacao.quantidade = dados["quantidade"] * Decimal("-1")
        movimentacao.observacoes = _observacao_movimentacao(
            colaborador,
            dados["tipo_material"],
            dados["motivo_entrega"],
            dados["observacoes"],
        )
        movimentacao.movimentado_em = datetime.combine(dados["data_entrega"], datetime.min.time())

    db.session.commit()
    return True, "Entrega atualizada e estoque recalculado com sucesso.", entrega


def cancelar_entrega_epi(entrega, usuario, motivo=None):
    if not entrega:
        return False, "Entrega nao encontrada."

    if entrega.status == STATUS_ENTREGA_EPI_CANCELADA:
        return False, "Entrega ja esta cancelada."

    motivo_cancelamento = texto_maiusculo(motivo) or "CANCELAMENTO MANUAL"
    entrega.status = STATUS_ENTREGA_EPI_CANCELADA
    entrega.cancelado_em = agora_brasil()
    entrega.cancelado_por_usuario_id = usuario.id if usuario else None
    entrega.motivo_cancelamento = motivo_cancelamento

    if entrega.movimentacao_estoque:
        entrega.movimentacao_estoque.status = STATUS_MOVIMENTACAO_ESTOQUE_CANCELADA
        entrega.movimentacao_estoque.observacoes = (
            f"{entrega.movimentacao_estoque.observacoes or ''} | ENTREGA CANCELADA: {motivo_cancelamento}"
        ).strip()

    db.session.commit()
    return True, "Entrega cancelada e estoque atualizado com sucesso."
