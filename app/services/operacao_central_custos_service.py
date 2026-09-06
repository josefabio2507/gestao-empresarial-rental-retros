from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import or_

from app.models import OperacaoAbastecimento, OperacaoHistoricoManutencao, OperacaoImpostoTaxa, OperacaoMultaTransito, OperacaoVeiculoEquipamento

STATUS_CENTRAL_CUSTOS = ["ativos", "inativos", "todos"]
TIPOS_CUSTO_CENTRAL = ["Abastecimento", "Manutenção", "Multas", "Impostos e Taxas"]


def texto(valor):
    return valor.strip() if valor else ""


def data_ou_none(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def decimal_zero(valor):
    return valor if valor is not None else Decimal("0")


def periodo_filtros(args):
    return data_ou_none(args.get("data_inicio")), data_ou_none(args.get("data_fim"))


def buscar_veiculos_central_custos(filtros):
    status = texto(filtros.get("status")) or "ativos"
    if status not in STATUS_CENTRAL_CUSTOS:
        status = "ativos"

    query = OperacaoVeiculoEquipamento.query
    termo = texto(filtros.get("termo"))
    if termo:
        busca = f"%{termo}%"
        query = query.filter(
            or_(
                OperacaoVeiculoEquipamento.identificacao.ilike(busca),
                OperacaoVeiculoEquipamento.placa.ilike(busca),
                OperacaoVeiculoEquipamento.descricao.ilike(busca),
                OperacaoVeiculoEquipamento.centro_custo.ilike(busca),
            )
        )

    if status == "ativos":
        query = query.filter(OperacaoVeiculoEquipamento.ativo.is_(True))
    elif status == "inativos":
        query = query.filter(OperacaoVeiculoEquipamento.ativo.is_(False))

    return query.order_by(
        OperacaoVeiculoEquipamento.ativo.desc(),
        OperacaoVeiculoEquipamento.identificacao.asc(),
    ).all(), status


def _filtrar_data_abastecimento(query, inicio, fim):
    if inicio:
        query = query.filter(OperacaoAbastecimento.data_abastecimento >= inicio)
    if fim:
        query = query.filter(OperacaoAbastecimento.data_abastecimento <= fim)
    return query


def _filtrar_data_manutencao(query, inicio, fim):
    if inicio:
        query = query.filter(OperacaoHistoricoManutencao.realizada_em >= datetime.combine(inicio, time.min))
    if fim:
        query = query.filter(OperacaoHistoricoManutencao.realizada_em <= datetime.combine(fim, time.max))
    return query


def linhas_abastecimento(veiculo, inicio=None, fim=None):
    query = OperacaoAbastecimento.query.filter_by(veiculo_id=veiculo.id)
    query = _filtrar_data_abastecimento(query, inicio, fim)
    registros = query.order_by(OperacaoAbastecimento.data_abastecimento.desc(), OperacaoAbastecimento.id.desc()).all()

    linhas = []
    total = Decimal("0")
    for registro in registros:
        valor = decimal_zero(registro.valor_total_combustivel)
        total += valor
        linhas.append(
            {
                "id": registro.id,
                "data": registro.data_abastecimento,
                "descricao": f"{registro.tipo_combustivel} | {registro.qtd_litros} L",
                "responsavel": registro.colaborador.nome if registro.colaborador else "-",
                "valor": valor,
                "registro": registro,
            }
        )
    return linhas, total


def linhas_manutencao(veiculo, inicio=None, fim=None):
    query = OperacaoHistoricoManutencao.query.filter_by(veiculo_id=veiculo.id)
    query = _filtrar_data_manutencao(query, inicio, fim)
    registros = query.order_by(OperacaoHistoricoManutencao.realizada_em.desc(), OperacaoHistoricoManutencao.id.desc()).all()

    linhas = []
    total = Decimal("0")
    for registro in registros:
        ordem = registro.ordem_compra
        valor = decimal_zero(ordem.valor_total if ordem else None)
        total += valor
        linhas.append(
            {
                "id": registro.id,
                "data": registro.realizada_em.date() if registro.realizada_em else None,
                "descricao": registro.descricao,
                "documento": ordem.numero if ordem else "Sem OC vinculada",
                "valor": valor,
                "ordem_compra_id": ordem.id if ordem else None,
                "registro": registro,
            }
        )
    return linhas, total


def _filtrar_data_multa(query, inicio, fim):
    if inicio:
        query = query.filter(OperacaoMultaTransito.data_infracao >= inicio)
    if fim:
        query = query.filter(OperacaoMultaTransito.data_infracao <= fim)
    return query


def linhas_multas(veiculo, inicio=None, fim=None):
    query = OperacaoMultaTransito.query.filter_by(veiculo_id=veiculo.id)
    query = _filtrar_data_multa(query, inicio, fim)
    registros = query.order_by(OperacaoMultaTransito.data_infracao.desc(), OperacaoMultaTransito.id.desc()).all()

    linhas = []
    total = Decimal("0")
    for registro in registros:
        valor = decimal_zero(registro.custo_total)
        total += valor
        linhas.append(
            {
                "id": registro.id,
                "data": registro.data_infracao,
                "descricao": registro.descricao_infracao,
                "documento": registro.numero_auto_infracao,
                "valor": valor,
                "registro": registro,
            }
        )
    return linhas, total


def _filtrar_data_imposto_taxa(query, inicio, fim):
    if inicio:
        query = query.filter(OperacaoImpostoTaxa.data_vencimento >= inicio)
    if fim:
        query = query.filter(OperacaoImpostoTaxa.data_vencimento <= fim)
    return query


def linhas_impostos_taxas(veiculo, inicio=None, fim=None):
    query = OperacaoImpostoTaxa.query.filter_by(veiculo_id=veiculo.id)
    query = _filtrar_data_imposto_taxa(query, inicio, fim)
    registros = query.order_by(OperacaoImpostoTaxa.data_vencimento.desc(), OperacaoImpostoTaxa.id.desc()).all()

    linhas = []
    total = Decimal("0")
    for registro in registros:
        valor = decimal_zero(registro.valor)
        total += valor
        linhas.append(
            {
                "id": registro.id,
                "data": registro.data_vencimento,
                "descricao": registro.tipo_custo,
                "documento": registro.numero_parcela,
                "valor": valor,
                "registro": registro,
            }
        )
    return linhas, total

def central_custos_veiculo(veiculo, inicio=None, fim=None):
    abastecimentos, total_abastecimento = linhas_abastecimento(veiculo, inicio, fim)
    manutencoes, total_manutencao = linhas_manutencao(veiculo, inicio, fim)
    multas, total_multas = linhas_multas(veiculo, inicio, fim)
    impostos_taxas, total_impostos_taxas = linhas_impostos_taxas(veiculo, inicio, fim)

    grupos = {
        "abastecimento": {
            "titulo": "Abastecimento",
            "linhas": abastecimentos,
            "total": total_abastecimento,
            "mensagem_vazio": "Nenhum abastecimento no período.",
        },
        "manutencao": {
            "titulo": "Manutenção",
            "linhas": manutencoes,
            "total": total_manutencao,
            "mensagem_vazio": "Nenhuma manutenção no período.",
        },
        "multas": {
            "titulo": "Multas",
            "linhas": multas,
            "total": total_multas,
            "mensagem_vazio": "Nenhuma multa de trânsito no período.",
        },
        "impostos_taxas": {
            "titulo": "Impostos e Taxas",
            "linhas": impostos_taxas,
            "total": total_impostos_taxas,
            "mensagem_vazio": "Nenhum imposto ou taxa no período.",
        },
    }
    total_geral = sum((grupo["total"] for grupo in grupos.values()), start=Decimal("0"))
    return grupos, total_geral
