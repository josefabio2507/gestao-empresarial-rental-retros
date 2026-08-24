from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import OperacaoImpostoTaxa, OperacaoVeiculoEquipamento

TIPOS_IMPOSTO_TAXA = ["IPVA", "Licenciamento"]
PARCELAS_IMPOSTO_TAXA = [
    ("Cota Unica", "Cota Única"),
    ("1a", "1ª"),
    ("2a", "2ª"),
    ("3a", "3ª"),
    ("4a", "4ª"),
    ("5a", "5ª"),
]


def texto(valor):
    return valor.strip() if valor else ""


def data_form(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def decimal_brl(valor):
    valor = texto(valor).replace("R$", "").replace(".", "").replace(",", ".")
    if not valor:
        return None
    try:
        return Decimal(valor).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None



def inteiro_form(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        return int(valor)
    except ValueError:
        return None
def veiculos_para_impostos_taxas():
    return OperacaoVeiculoEquipamento.query.filter_by(ativo=True).order_by(
        OperacaoVeiculoEquipamento.placa.asc(),
        OperacaoVeiculoEquipamento.identificacao.asc(),
    ).all()


def listar_impostos_taxas():
    return OperacaoImpostoTaxa.query.order_by(
        OperacaoImpostoTaxa.data_vencimento.desc(),
        OperacaoImpostoTaxa.id.desc(),
    ).all()


def buscar_imposto_taxa(lancamento_id):
    return OperacaoImpostoTaxa.query.get(lancamento_id)


def salvar_impostos_taxas(dados, usuario):
    veiculo_id = inteiro_form(dados.get("veiculo_id"))
    veiculo = OperacaoVeiculoEquipamento.query.get(veiculo_id) if veiculo_id else None
    tipo_custo = texto(dados.get("tipo_custo"))
    datas = dados.getlist("data_vencimento") if hasattr(dados, "getlist") else []
    parcelas = dados.getlist("numero_parcela") if hasattr(dados, "getlist") else []
    valores = dados.getlist("valor") if hasattr(dados, "getlist") else []
    observacoes = texto(dados.get("observacoes")) or None

    if not veiculo:
        return False, "Selecione uma placa valida.", []
    if tipo_custo not in TIPOS_IMPOSTO_TAXA:
        return False, "Selecione um tipo de custo valido.", []

    lancamentos = []
    for indice, data_raw in enumerate(datas):
        parcela = texto(parcelas[indice]) if indice < len(parcelas) else ""
        valor = decimal_brl(valores[indice]) if indice < len(valores) else None
        data_vencimento = data_form(data_raw)

        if not data_vencimento and not parcela and valor is None:
            continue
        if not data_vencimento or not parcela or valor is None:
            return False, "Preencha data, parcela e valor em cada linha informada.", []
        if parcela not in dict(PARCELAS_IMPOSTO_TAXA):
            return False, "Numero de parcela invalido.", []

        lancamentos.append(
            OperacaoImpostoTaxa(
                veiculo_id=veiculo.id,
                usuario_id=usuario.id,
                tipo_custo=tipo_custo,
                numero_parcela=parcela,
                data_vencimento=data_vencimento,
                valor=valor,
                observacoes=observacoes,
            )
        )

    if not lancamentos:
        return False, "Informe ao menos uma parcela.", []

    db.session.add_all(lancamentos)
    db.session.commit()
    return True, "Impostos e taxas cadastrados com sucesso.", lancamentos
