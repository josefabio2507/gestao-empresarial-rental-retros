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
    STATUS_MOVIMENTACAO_ESTOQUE_REGISTRADA,
    TIPO_MOVIMENTACAO_ESTOQUE_SAIDA,
    data_ou_none,
    decimal_ou_none,
    inteiro_ou_none,
    texto,
    texto_maiusculo,
)


ORIGEM_MOVIMENTACAO_ENTREGA_EPI = "Entrega EPI"
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


def registrar_entrega_epi(form_data, usuario):
    colaborador_id = inteiro_ou_none(form_data.get("colaborador_id"))
    item_id = inteiro_ou_none(form_data.get("item_id"))
    tipo_material = texto(form_data.get("tipo_material"))
    quantidade = decimal_ou_none(form_data.get("quantidade"))
    data_entrega = data_ou_none(form_data.get("data_entrega")) or date.today()
    ca_numero = texto_maiusculo(form_data.get("ca_numero")) or None
    tamanho = texto_maiusculo(form_data.get("tamanho")) or None
    motivo_entrega = texto_maiusculo(form_data.get("motivo_entrega"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    colaborador = Colaborador.query.get(colaborador_id) if colaborador_id else None
    if not colaborador or not colaborador.ativo:
        return False, "Informe um colaborador ativo.", None

    item = SuprimentosItem.query.options(joinedload(SuprimentosItem.movimentacoes_estoque)).get(item_id) if item_id else None
    if not item or not item.ativo or not item.item_estocavel:
        return False, "Informe um item estocavel ativo do estoque de Suprimentos.", None

    if tipo_material not in TIPOS_MATERIAL_ENTREGA:
        return False, "Informe se o material entregue e EPI ou Uniforme.", None

    if quantidade is None or quantidade <= 0:
        return False, "Quantidade deve ser maior que zero.", None

    saldo_atual = Decimal(item.saldo_estoque)
    if quantidade > saldo_atual:
        return False, "Entrega nao pode ser maior que o saldo atual do item.", None

    if not data_entrega:
        return False, "Data da entrega e obrigatoria.", None

    if not motivo_entrega:
        return False, "Motivo da entrega e obrigatorio.", None

    entrega = SegurancaTrabalhoEntregaEpi(
        colaborador_id=colaborador.id,
        item_id=item.id,
        entregue_por_usuario_id=usuario.id,
        tipo_material=tipo_material,
        quantidade=quantidade,
        data_entrega=data_entrega,
        ca_numero=ca_numero,
        tamanho=tamanho,
        motivo_entrega=motivo_entrega,
        observacoes=observacoes,
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
        quantidade=quantidade * Decimal("-1"),
        observacoes=(
            f"Entrega para {colaborador.matricula} - {colaborador.nome}. "
            f"Tipo: {tipo_material}. Motivo: {motivo_entrega}."
            f"{' ' + observacoes if observacoes else ''}"
        ),
        movimentado_em=datetime.combine(data_entrega, datetime.min.time()),
    )
    db.session.add(movimentacao)
    db.session.flush()

    entrega.movimentacao_estoque_id = movimentacao.id
    db.session.commit()

    return True, "Entrega registrada e estoque abatido com sucesso.", entrega
