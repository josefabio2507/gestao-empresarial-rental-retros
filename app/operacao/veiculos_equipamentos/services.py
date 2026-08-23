from sqlalchemy import func, or_

from app.extensions import db
from app.models import OperacaoVeiculoEquipamento


SITUACOES_AQUISICAO = ["Quitado", "Financiado"]
TIPOS_VEICULO_EQUIPAMENTO = [
    "Veiculo leve",
    "Caminhao",
    "Maquina",
    "Equipamento",
    "EGP",
    "Outro",
]


def texto(valor):
    return valor.strip() if valor else ""


def texto_maiusculo(valor):
    valor = texto(valor)
    return valor.upper() if valor else ""


def centro_custo_calculado(identificacao, descricao):
    return f"{identificacao}-{descricao}"


def identificar_tipo(descricao):
    descricao = texto_maiusculo(descricao)

    if any(termo in descricao for termo in ["CASE", "JOHN DEERE", "NEW HOLLAND"]):
        return "Maquina"

    if any(termo in descricao for termo in ["CARGO", "ACCELO", "DELIVERY", "CONSTELATION", "EXPRESS"]):
        return "Caminhao"

    if any(termo in descricao for termo in ["MOBI", "VOYAGE", "SAVEIRO", "JUMPY", "BASALT"]):
        return "Veiculo leve"

    return "Outro"


def buscar_veiculos_equipamentos(filtros):
    query = OperacaoVeiculoEquipamento.query
    termo = texto(filtros.get("termo"))

    if termo:
        busca = f"%{termo}%"
        query = query.filter(
            or_(
                OperacaoVeiculoEquipamento.identificacao.ilike(busca),
                OperacaoVeiculoEquipamento.placa.ilike(busca),
                OperacaoVeiculoEquipamento.descricao.ilike(busca),
                OperacaoVeiculoEquipamento.chassi.ilike(busca),
                OperacaoVeiculoEquipamento.centro_custo.ilike(busca),
            )
        )

    situacao = texto(filtros.get("situacao_aquisicao"))
    if situacao:
        query = query.filter(OperacaoVeiculoEquipamento.situacao_aquisicao == situacao)

    tipo = texto(filtros.get("tipo"))
    if tipo:
        query = query.filter(OperacaoVeiculoEquipamento.tipo == tipo)

    status = texto(filtros.get("status"))
    if status == "ativos":
        query = query.filter(OperacaoVeiculoEquipamento.ativo.is_(True))
    elif status == "inativos":
        query = query.filter(OperacaoVeiculoEquipamento.ativo.is_(False))

    return query.order_by(
        OperacaoVeiculoEquipamento.ativo.desc(),
        OperacaoVeiculoEquipamento.identificacao.asc(),
    ).all()


def buscar_por_id(registro_id):
    return db.session.get(OperacaoVeiculoEquipamento, registro_id)


def identificacao_ja_existe(identificacao, registro_id_ignorado=None):
    query = OperacaoVeiculoEquipamento.query.filter(
        func.upper(func.trim(OperacaoVeiculoEquipamento.identificacao)) == identificacao
    )

    if registro_id_ignorado is not None:
        query = query.filter(OperacaoVeiculoEquipamento.id != registro_id_ignorado)

    return query.first() is not None


def chassi_ja_existe(chassi, registro_id_ignorado=None):
    if not chassi:
        return False

    query = OperacaoVeiculoEquipamento.query.filter(
        func.upper(func.trim(OperacaoVeiculoEquipamento.chassi)) == chassi
    )

    if registro_id_ignorado is not None:
        query = query.filter(OperacaoVeiculoEquipamento.id != registro_id_ignorado)

    return query.first() is not None


def salvar_veiculo_equipamento(form_data, registro=None):
    identificacao = texto_maiusculo(form_data.get("identificacao"))
    placa = texto_maiusculo(form_data.get("placa")) or None
    descricao = texto_maiusculo(form_data.get("descricao"))
    chassi = texto_maiusculo(form_data.get("chassi")) or None
    renavam = texto_maiusculo(form_data.get("renavam")) or None
    situacao_aquisicao = texto(form_data.get("situacao_aquisicao"))
    tipo = texto(form_data.get("tipo"))

    if not identificacao:
        return False, "Identificacao e obrigatoria.", registro

    if not descricao:
        return False, "Descricao e obrigatoria.", registro

    if situacao_aquisicao not in SITUACOES_AQUISICAO:
        return False, "Situacao de aquisicao invalida.", registro

    if tipo not in TIPOS_VEICULO_EQUIPAMENTO:
        return False, "Tipo invalido.", registro

    if identificacao_ja_existe(identificacao, getattr(registro, "id", None)):
        return False, "Ja existe veiculo/equipamento com esta identificacao.", registro

    if chassi_ja_existe(chassi, getattr(registro, "id", None)):
        return False, "Ja existe veiculo/equipamento com este chassi.", registro

    if registro is None:
        registro = OperacaoVeiculoEquipamento(ativo=True)
        db.session.add(registro)

    registro.identificacao = identificacao
    registro.placa = placa
    registro.descricao = descricao
    registro.chassi = chassi
    registro.renavam = renavam
    registro.situacao_aquisicao = situacao_aquisicao
    registro.tipo = tipo
    registro.observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    if registro.id is not None:
        registro.ativo = form_data.get("ativo") == "on"

    registro.recalcular_centro_custo()
    db.session.commit()

    return True, "Veiculo/equipamento salvo com sucesso.", registro


def alterar_status(registro):
    registro.ativo = not registro.ativo
    db.session.commit()
    return True, "Registro reativado com sucesso." if registro.ativo else "Registro inativado com sucesso."
