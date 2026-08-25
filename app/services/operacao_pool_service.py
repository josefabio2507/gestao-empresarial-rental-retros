from decimal import Decimal, InvalidOperation

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    CentroCusto,
    Colaborador,
    Equipe,
    OperacaoLeituraAtivo,
    OperacaoVeiculoEquipamento,
    OperacaoVeiculoResponsavel,
)
from app.utils.datas import agora_brasil

STATUS_DISPONIVEL = "Disponivel"
STATUS_EM_USO = "Em uso"
STATUS_INDISPONIVEL = "Indisponivel"

STATUS_VINCULO_ATIVO = "Ativo"
STATUS_VINCULO_ENCERRADO = "Encerrado"
STATUS_VINCULO_CORRIGIDO = "Corrigido"
STATUS_VINCULO_CANCELADO = "Cancelado"
STATUS_VINCULO_RETIFICADO = "Retificado"

TIPOS_VEICULO = ["Veiculo leve", "Caminhao", "Maquina", "Equipamento", "EGP", "Outro"]
SITUACOES_AQUISICAO = ["Quitado", "Financiado"]
TIPOS_LEITURA = ["odometro", "horimetro"]


def texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def texto_maiusculo(valor):
    return texto(valor).upper()


def decimal_ou_none(valor):
    valor = texto(valor).replace(".", "").replace(",", ".")
    if not valor:
        return None
    try:
        numero = Decimal(valor)
    except (InvalidOperation, ValueError):
        return None
    return numero.quantize(Decimal("0.01"))


def inteiro_ou_none(valor):
    try:
        return int(texto(valor))
    except (TypeError, ValueError):
        return None


def centro_custo_calculado(identificacao, descricao):
    return f"{texto_maiusculo(identificacao)}-{texto_maiusculo(descricao)}"


def buscar_por_id(modelo, registro_id):
    if not registro_id:
        return None
    return db.session.get(modelo, registro_id)


def buscar_veiculos_pool(termo=None, status=None, tipo=None):
    consulta = OperacaoVeiculoEquipamento.query.options(
        joinedload(OperacaoVeiculoEquipamento.vinculos_responsaveis).joinedload(
            OperacaoVeiculoResponsavel.colaborador
        )
    )

    termo = texto_maiusculo(termo)
    if termo:
        busca = f"%{termo}%"
        consulta = consulta.filter(
            or_(
                OperacaoVeiculoEquipamento.identificacao.ilike(busca),
                OperacaoVeiculoEquipamento.placa.ilike(busca),
                OperacaoVeiculoEquipamento.descricao.ilike(busca),
                OperacaoVeiculoEquipamento.chassi.ilike(busca),
                OperacaoVeiculoEquipamento.centro_custo.ilike(busca),
            )
        )

    if status:
        consulta = consulta.filter(OperacaoVeiculoEquipamento.status_operacional == status)

    if tipo:
        consulta = consulta.filter(OperacaoVeiculoEquipamento.tipo == tipo)

    return consulta.order_by(OperacaoVeiculoEquipamento.identificacao.asc()).all()


def buscar_colaboradores_ativos():
    return Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome.asc()).all()


def buscar_equipes_ativas():
    return Equipe.query.filter_by(ativo=True).order_by(Equipe.nome.asc()).all()


def buscar_centros_custo_ativos():
    return CentroCusto.query.filter_by(ativo=True).order_by(CentroCusto.nome.asc()).all()


def salvar_veiculo_equipamento(form_data, veiculo=None):
    identificacao = texto_maiusculo(form_data.get("identificacao"))
    placa = texto_maiusculo(form_data.get("placa")) or None
    descricao = texto_maiusculo(form_data.get("descricao"))
    chassi = texto_maiusculo(form_data.get("chassi")) or None
    renavam = texto_maiusculo(form_data.get("renavam")) or None
    situacao = texto(form_data.get("situacao_aquisicao")) or "Quitado"
    tipo = texto(form_data.get("tipo")) or "Outro"
    centro_custo_id = inteiro_ou_none(form_data.get("centro_custo_id"))

    if not identificacao:
        return False, "Identificacao e obrigatoria.", None
    if not descricao:
        return False, "Descricao e obrigatoria.", None
    if situacao not in SITUACOES_AQUISICAO:
        return False, "Situacao de aquisicao invalida.", None
    if tipo not in TIPOS_VEICULO:
        return False, "Tipo invalido.", None

    consulta = OperacaoVeiculoEquipamento.query.filter_by(identificacao=identificacao)
    if veiculo:
        consulta = consulta.filter(OperacaoVeiculoEquipamento.id != veiculo.id)
    if consulta.first():
        return False, "Ja existe veiculo/equipamento com esta identificacao.", None

    if chassi:
        consulta_chassi = OperacaoVeiculoEquipamento.query.filter_by(chassi=chassi)
        if veiculo:
            consulta_chassi = consulta_chassi.filter(OperacaoVeiculoEquipamento.id != veiculo.id)
        if consulta_chassi.first():
            return False, "Ja existe veiculo/equipamento com este chassi.", None

    if not veiculo:
        veiculo = OperacaoVeiculoEquipamento(status_operacional=STATUS_DISPONIVEL, ativo=True)
        db.session.add(veiculo)

    veiculo.identificacao = identificacao
    veiculo.placa = placa
    veiculo.descricao = descricao
    veiculo.chassi = chassi
    veiculo.renavam = renavam
    veiculo.centro_custo = centro_custo_calculado(identificacao, descricao)
    veiculo.centro_custo_id = centro_custo_id
    veiculo.situacao_aquisicao = situacao
    veiculo.tipo = tipo
    veiculo.observacoes = texto(form_data.get("observacoes")) or None
    veiculo.ativo = bool(form_data.get("ativo", True))

    db.session.commit()
    return True, "Veiculo/equipamento salvo com sucesso.", veiculo


def vinculo_ativo_do_veiculo(veiculo):
    return OperacaoVeiculoResponsavel.query.filter_by(
        veiculo_id=veiculo.id,
        status=STATUS_VINCULO_ATIVO,
        encerrado_em=None,
    ).first()


def ultima_leitura_valida(veiculo_id, tipo):
    return (
        OperacaoLeituraAtivo.query.filter_by(veiculo_id=veiculo_id, tipo=tipo, valida=True)
        .order_by(OperacaoLeituraAtivo.registrada_em.desc(), OperacaoLeituraAtivo.id.desc())
        .first()
    )


def leitura_final_anterior_sugerida(veiculo):
    ativo_anterior = vinculo_ativo_do_veiculo(veiculo) if veiculo else None
    if not ativo_anterior:
        return None
    if ativo_anterior.leitura_inicial is not None:
        return ativo_anterior.leitura_inicial
    if ativo_anterior.tipo_leitura:
        ultima = (
            OperacaoLeituraAtivo.query.filter_by(
                veiculo_id=veiculo.id,
                vinculo_id=ativo_anterior.id,
                tipo=ativo_anterior.tipo_leitura,
                valida=True,
            )
            .order_by(OperacaoLeituraAtivo.registrada_em.desc(), OperacaoLeituraAtivo.id.desc())
            .first()
        )
        return ultima.leitura if ultima else None
    return None


def registrar_leitura(
    veiculo,
    tipo,
    leitura,
    origem="pool",
    usuario=None,
    vinculo=None,
    permitir_regressao=False,
    motivo_correcao=None,
):
    tipo = texto(tipo)
    leitura = decimal_ou_none(leitura)
    motivo_correcao = texto(motivo_correcao) or None

    if tipo not in TIPOS_LEITURA:
        return False, "Tipo de leitura invalido.", None
    if leitura is None or leitura < 0:
        return False, "Leitura invalida.", None

    ultima = ultima_leitura_valida(veiculo.id, tipo)
    if ultima and leitura < ultima.leitura and not (permitir_regressao and motivo_correcao):
        return False, "Leitura menor que a ultima valida do ativo.", None

    registro = OperacaoLeituraAtivo(
        veiculo_id=veiculo.id,
        vinculo_id=vinculo.id if vinculo else None,
        tipo=tipo,
        leitura=leitura,
        origem=origem,
        motivo_correcao=motivo_correcao,
        registrado_por_usuario_id=getattr(usuario, "id", None),
        valida=True,
    )
    db.session.add(registro)
    return True, "Leitura registrada com sucesso.", registro


def atualizar_status_pool(veiculo):
    if veiculo.status_operacional == STATUS_INDISPONIVEL and texto(veiculo.motivo_indisponibilidade):
        return
    veiculo.status_operacional = STATUS_EM_USO if vinculo_ativo_do_veiculo(veiculo) else STATUS_DISPONIVEL


def vincular_responsavel(form_data, usuario=None, veiculo=None):
    veiculo = veiculo or buscar_por_id(OperacaoVeiculoEquipamento, inteiro_ou_none(form_data.get("veiculo_id")))
    colaborador = buscar_por_id(Colaborador, inteiro_ou_none(form_data.get("colaborador_id")))
    equipe = buscar_por_id(Equipe, inteiro_ou_none(form_data.get("equipe_id")))
    tipo_leitura = texto(form_data.get("tipo_leitura")) or None
    leitura_inicial = decimal_ou_none(form_data.get("leitura_inicial"))
    leitura_final_anterior = decimal_ou_none(form_data.get("leitura_final_anterior"))
    agora = agora_brasil()

    if not veiculo or not veiculo.ativo:
        return False, "Veiculo/equipamento nao encontrado ou inativo.", None
    atualizar_status_pool(veiculo)
    if veiculo.status_operacional == STATUS_INDISPONIVEL:
        return False, "Veiculo/equipamento indisponivel para vinculo.", None
    if not colaborador or not colaborador.ativo:
        return False, "Colaborador nao encontrado ou inativo.", None
    if equipe and not equipe.ativo:
        return False, "Equipe nao encontrada ou inativa.", None
    if not tipo_leitura or tipo_leitura not in TIPOS_LEITURA:
        return False, "Tipo de leitura e obrigatorio.", None
    if leitura_inicial is None:
        return False, "Leitura inicial e obrigatoria.", None
    ativo_anterior = vinculo_ativo_do_veiculo(veiculo)
    if ativo_anterior:
        if leitura_final_anterior is not None and ativo_anterior.tipo_leitura:
            sucesso, mensagem, _ = registrar_leitura(
                veiculo,
                ativo_anterior.tipo_leitura,
                leitura_final_anterior,
                origem="pool",
                usuario=usuario,
                vinculo=ativo_anterior,
            )
            if not sucesso:
                return False, mensagem, None
            ativo_anterior.leitura_final = leitura_final_anterior
        ativo_anterior.status = STATUS_VINCULO_ENCERRADO
        ativo_anterior.encerrado_em = agora

    vinculo = OperacaoVeiculoResponsavel(
        veiculo_id=veiculo.id,
        colaborador_id=colaborador.id,
        equipe_id=equipe.id if equipe else colaborador.equipe_id,
        usuario_responsavel_id=getattr(colaborador.usuarios[0], "id", None) if colaborador.usuarios else None,
        iniciado_em=agora,
        leitura_inicial=leitura_inicial,
        tipo_leitura=tipo_leitura,
        status=STATUS_VINCULO_ATIVO,
        criado_por_usuario_id=getattr(usuario, "id", None),
        observacoes=texto(form_data.get("observacoes")) or None,
    )
    db.session.add(vinculo)
    db.session.flush()

    if leitura_inicial is not None:
        sucesso, mensagem, _ = registrar_leitura(
            veiculo,
            tipo_leitura,
            leitura_inicial,
            origem="pool",
            usuario=usuario,
            vinculo=vinculo,
        )
        if not sucesso:
            db.session.rollback()
            return False, mensagem, None

    veiculo.status_operacional = STATUS_EM_USO
    db.session.commit()
    return True, "Vinculo operacional criado com sucesso.", vinculo


def encerrar_vinculo(vinculo, form_data=None, usuario=None):
    form_data = form_data or {}
    if not vinculo or not vinculo.ativo:
        return False, "Vinculo ativo nao encontrado."

    leitura_final = decimal_ou_none(form_data.get("leitura_final"))
    if leitura_final is not None and vinculo.tipo_leitura:
        sucesso, mensagem, _ = registrar_leitura(
            vinculo.veiculo,
            vinculo.tipo_leitura,
            leitura_final,
            origem="pool",
            usuario=usuario,
            vinculo=vinculo,
        )
        if not sucesso:
            return False, mensagem
        vinculo.leitura_final = leitura_final

    vinculo.status = STATUS_VINCULO_ENCERRADO
    vinculo.encerrado_em = agora_brasil()
    atualizar_status_pool(vinculo.veiculo)
    db.session.commit()
    return True, "Vinculo encerrado com sucesso."


def corrigir_vinculo(vinculo, form_data, usuario=None):
    motivo = texto(form_data.get("motivo_correcao"))
    status_correcao = texto(form_data.get("status_correcao")) or STATUS_VINCULO_RETIFICADO

    if not vinculo:
        return False, "Vinculo nao encontrado.", None
    if not motivo:
        return False, "Motivo da correcao e obrigatorio.", None
    if status_correcao not in [STATUS_VINCULO_CORRIGIDO, STATUS_VINCULO_CANCELADO, STATUS_VINCULO_RETIFICADO]:
        return False, "Status de correcao invalido.", None

    vinculo.status = status_correcao
    vinculo.motivo_correcao = motivo
    vinculo.corrigido_por_usuario_id = getattr(usuario, "id", None)
    vinculo.corrigido_em = agora_brasil()
    if vinculo.encerrado_em is None:
        vinculo.encerrado_em = vinculo.corrigido_em
    atualizar_status_pool(vinculo.veiculo)

    novo_vinculo = None
    if form_data.get("criar_novo_vinculo"):
        dados_novo = dict(form_data)
        dados_novo["veiculo_id"] = str(vinculo.veiculo_id)
        sucesso, mensagem, novo_vinculo = vincular_responsavel(dados_novo, usuario=usuario)
        if not sucesso:
            db.session.rollback()
            return False, mensagem, None
    else:
        db.session.commit()

    return True, "Correcao auditavel registrada com sucesso.", novo_vinculo


def alterar_indisponibilidade_veiculo(veiculo, indisponivel=True, motivo=None):
    if not veiculo:
        return False, "Veiculo/equipamento nao encontrado."
    if indisponivel:
        veiculo.status_operacional = STATUS_INDISPONIVEL
        veiculo.motivo_indisponibilidade = texto(motivo) or "Indisponivel operacionalmente."
    else:
        veiculo.motivo_indisponibilidade = None
        atualizar_status_pool(veiculo)
    db.session.commit()
    return True, "Status operacional atualizado com sucesso."


def veiculos_vinculados_ao_colaborador(colaborador_id):
    return (
        OperacaoVeiculoEquipamento.query.join(OperacaoVeiculoResponsavel)
        .filter(
            OperacaoVeiculoResponsavel.colaborador_id == colaborador_id,
            OperacaoVeiculoResponsavel.status == STATUS_VINCULO_ATIVO,
            OperacaoVeiculoResponsavel.encerrado_em.is_(None),
            OperacaoVeiculoEquipamento.ativo.is_(True),
        )
        .order_by(OperacaoVeiculoEquipamento.identificacao.asc())
        .all()
    )
