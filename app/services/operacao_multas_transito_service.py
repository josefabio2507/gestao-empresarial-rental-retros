from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import or_

from app.extensions import db
from app.models import Colaborador, OperacaoMultaTransito, OperacaoVeiculoEquipamento, OperacaoVeiculoResponsavel

CIDADES_MULTA = [
    ("CUBATAO", "CUBATÃO"),
    ("SANTOS", "SANTOS"),
    ("SAO VICENTE", "SÃO VICENTE"),
    ("GUARUJA", "GUARUJÁ"),
    ("PRAIA GRANDE", "PRAIA GRANDE"),
    ("ITANHAEM", "ITANHAÉM"),
    ("MONGAGUA", "MONGAGUÁ"),
    ("SAO PAULO", "SÃO PAULO"),
]
GRAVIDADES_MULTA = [
    ("Leve", "Leve"),
    ("Media", "Média"),
    ("Grave", "Grave"),
    ("Gravissima", "Gravíssima"),
]


def texto(valor):
    return valor.strip() if valor else ""


def decimal_brl(valor):
    valor = texto(valor).replace("R$", "").replace(".", "").replace(",", ".")
    if not valor:
        return None
    try:
        return Decimal(valor).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def data_form(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def hora_form(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%H:%M").time()
    except ValueError:
        return None


def inteiro_form(valor):
    valor = texto(valor)
    if not valor:
        return None
    try:
        return int(valor)
    except ValueError:
        return None


def veiculos_para_multas():
    return OperacaoVeiculoEquipamento.query.filter_by(ativo=True).order_by(
        OperacaoVeiculoEquipamento.placa.asc(),
        OperacaoVeiculoEquipamento.identificacao.asc(),
    ).all()


def colaboradores_para_indicacao():
    return Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome.asc()).all()


def listar_motoristas_vinculados_multas():
    return Colaborador.query.join(
        OperacaoMultaTransito,
        OperacaoMultaTransito.motorista_vinculado_id == Colaborador.id,
    ).distinct().order_by(Colaborador.nome.asc()).all()


def listar_multas_transito(filtros=None):
    filtros = filtros or {}
    data_inicio = data_form(filtros.get("data_inicio"))
    data_fim = data_form(filtros.get("data_fim"))
    placa = texto(filtros.get("placa"))
    motorista_vinculado_id = inteiro_form(filtros.get("motorista_vinculado_id"))

    query = OperacaoMultaTransito.query.join(OperacaoMultaTransito.veiculo)
    if data_inicio:
        query = query.filter(OperacaoMultaTransito.data_infracao >= data_inicio)
    if data_fim:
        query = query.filter(OperacaoMultaTransito.data_infracao <= data_fim)
    if placa:
        busca = f"%{placa}%"
        query = query.filter(
            or_(
                OperacaoVeiculoEquipamento.placa.ilike(busca),
                OperacaoVeiculoEquipamento.identificacao.ilike(busca),
            )
        )
    if motorista_vinculado_id:
        query = query.filter(OperacaoMultaTransito.motorista_vinculado_id == motorista_vinculado_id)

    return query.order_by(
        OperacaoMultaTransito.data_infracao.desc(),
        OperacaoMultaTransito.id.desc(),
    ).all()


def motorista_vinculado_na_data(veiculo_id, data_infracao, hora_infracao):
    if not veiculo_id or not data_infracao or not hora_infracao:
        return None

    momento = datetime.combine(data_infracao, hora_infracao)
    query_base = OperacaoVeiculoResponsavel.query.filter(
        OperacaoVeiculoResponsavel.veiculo_id == veiculo_id,
        OperacaoVeiculoResponsavel.iniciado_em <= momento,
        OperacaoVeiculoResponsavel.status.in_(["Ativo", "Encerrado", "Retificado"]),
    )
    vinculo = query_base.filter(
        or_(
            OperacaoVeiculoResponsavel.encerrado_em.is_(None),
            OperacaoVeiculoResponsavel.encerrado_em >= momento,
        )
    ).order_by(OperacaoVeiculoResponsavel.iniciado_em.desc()).first()
    if not vinculo:
        vinculo = query_base.order_by(OperacaoVeiculoResponsavel.iniciado_em.desc()).first()
    return vinculo.colaborador if vinculo else None


def buscar_multa(multa_id):
    return OperacaoMultaTransito.query.get(multa_id)


def salvar_multa_transito(dados, usuario, multa=None):
    veiculo_id = inteiro_form(dados.get("veiculo_id"))
    veiculo = OperacaoVeiculoEquipamento.query.get(veiculo_id) if veiculo_id else None
    data_infracao = data_form(dados.get("data_infracao"))
    hora_infracao = hora_form(dados.get("hora_infracao"))
    numero_auto = texto(dados.get("numero_auto_infracao"))
    local = texto(dados.get("local_infracao"))
    cidade = texto(dados.get("cidade"))
    descricao = texto(dados.get("descricao_infracao"))
    valor_multa = decimal_brl(dados.get("valor_multa"))
    data_vencimento = data_form(dados.get("data_vencimento"))
    motorista_indicado_nome = texto(dados.get("motorista_indicado_nome"))
    gravidade = texto(dados.get("gravidade"))
    pontuacao = inteiro_form(dados.get("pontuacao"))
    data_segunda = data_form(dados.get("data_vencimento_segunda_cobranca"))
    valor_segunda = decimal_brl(dados.get("valor_segunda_cobranca"))

    if not veiculo:
        return False, "Selecione uma placa valida.", None
    if not data_infracao or not hora_infracao:
        return False, "Informe data e hora da infracao.", None
    if not numero_auto:
        return False, "Informe o numero do auto de infracao.", None
    existe = OperacaoMultaTransito.query.filter_by(numero_auto_infracao=numero_auto).first()
    if existe and (not multa or existe.id != multa.id):
        return False, "Numero do auto de infracao ja cadastrado.", None
    if not local or not cidade or not descricao:
        return False, "Preencha local, cidade e descricao da infracao.", None
    if cidade not in dict(CIDADES_MULTA):
        return False, "Cidade invalida.", None
    if valor_multa is None:
        return False, "Informe o valor da multa.", None
    if not data_vencimento:
        return False, "Informe a data de vencimento.", None
    if gravidade not in dict(GRAVIDADES_MULTA):
        return False, "Gravidade invalida.", None
    if pontuacao is None or pontuacao < 0:
        return False, "Informe a pontuacao.", None
    if bool(data_segunda) != bool(valor_segunda is not None):
        return False, "Informe data e valor da segunda cobranca juntos.", None

    motorista_vinculado = motorista_vinculado_na_data(veiculo.id, data_infracao, hora_infracao)
    multa = multa or OperacaoMultaTransito(usuario_id=usuario.id)
    multa.veiculo_id = veiculo.id
    multa.motorista_vinculado_id = motorista_vinculado.id if motorista_vinculado else None
    multa.motorista_indicado_id = None
    multa.motorista_indicado_nome = motorista_indicado_nome or None
    multa.usuario_id = usuario.id
    multa.data_infracao = data_infracao
    multa.hora_infracao = hora_infracao
    multa.numero_auto_infracao = numero_auto
    multa.local_infracao = local
    multa.cidade = cidade
    multa.descricao_infracao = descricao
    multa.valor_multa = valor_multa
    multa.data_vencimento = data_vencimento
    multa.gravidade = gravidade
    multa.pontuacao = pontuacao
    multa.data_vencimento_segunda_cobranca = data_segunda
    multa.valor_segunda_cobranca = valor_segunda
    multa.observacoes = texto(dados.get("observacoes")) or None

    db.session.add(multa)
    db.session.commit()
    return True, "Multa de transito salva com sucesso.", multa
