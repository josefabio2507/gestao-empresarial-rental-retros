from datetime import date, time

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import (
    OperacaoApontamentoDiario,
    OperacaoDiarioLocalizacao,
    OperacaoOrdemServico,
    OperacaoChefeBoletim,
)
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao


class LocalizacaoErro(Exception):
    pass


OPCOES = {
    "equipe": (
        "TMC AMV", "TMC AMV II", "TMC CALCETARIA", "TMC GUARUJÁ",
        "TMC INFRAESTRUTURA", "TMC LIMPEZA", "TMC LIMPEZA II", "TMC SANTOS",
    ),
    "encarregado": (
        "ALTAMIRO PEREIRA FILHO", "CLODOALDO OLIVEIRA SILVA DOS SANTOS",
        "DEIVISION JÚLIO DOS SANTOS", "JOÉLIO DOS SANTOS",
        "LUIS FERNANDO DOS SANTOS SOUZA", "JOÃO RICARDO DOS SANTOS",
        "MARCOS FERNANDES MATHIAS", "MERO DE AZEVEDO", "WILLIAN LINO DA SILVA",
        "VALDEMIR QUINTINO DOS SANTOS", "WAGNY DOS SANTOS JUNIOR",
    ),
    "chefe_boletim": (),
}
_CAMPOS_HORARIO = (
    "intervalo_inicio", "intervalo_fim", "pedido_liberacao_ccp",
    "liberacao_embandeiramento", "termino_embandeiramento",
)


def _texto(valor):
    return str(valor or "").strip()


def _autorizar(usuario, acao):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", acao):
        raise LocalizacaoErro("Você não possui permissão para esta operação de Localização.")


def _data(valor):
    try:
        return date.fromisoformat(_texto(valor))
    except ValueError as exc:
        raise LocalizacaoErro("Informe uma data operacional válida.") from exc


def _horario(valor):
    if not _texto(valor):
        return None
    try:
        return time.fromisoformat(_texto(valor))
    except ValueError as exc:
        raise LocalizacaoErro("Informe horários válidos.") from exc


def _validar_dados(dados):
    registro = {
        "data_evento": _data(dados.get("data_evento")),
        "equipe": _texto(dados.get("equipe")),
        "encarregado": _texto(dados.get("encarregado")),
        "chefe_boletim": _texto(dados.get("chefe_boletim")),
        "local": _texto(dados.get("local")),
        "numero_amv": _texto(dados.get("amv")) or None,
        "sub": _texto(dados.get("sub")) or None,
        "km_inicio": _texto(dados.get("km_inicio")) or None,
        "km_fim": _texto(dados.get("km_fim")) or None,
        "hora_inicial": _horario(dados.get("hora_inicial")),
        "intervalo_jornada": _horario(dados.get("intervalo_jornada")) or time(1, 0),
        "hora_final": _horario(dados.get("hora_final")),
        "observacao": _texto(dados.get("observacao")).upper() or None,
    }
    faltantes = [campo for campo in ("equipe", "encarregado", "chefe_boletim", "local", "hora_inicial") if not registro[campo]]
    if faltantes:
        raise LocalizacaoErro("Preencha os campos obrigatórios: " + ", ".join(faltantes) + ".")
    opcoes_validacao = dict(OPCOES)
    opcoes_validacao["chefe_boletim"] = tuple(c.nome for c in OperacaoChefeBoletim.query.filter_by(ativo=True).order_by(OperacaoChefeBoletim.nome).all())
    for campo, opcoes in opcoes_validacao.items():
        if registro[campo] not in opcoes:
            raise LocalizacaoErro("Selecione uma opção válida para " + campo + ".")
    for campo in _CAMPOS_HORARIO:
        registro[campo] = _horario(dados.get(campo))
    return registro


def _ordem(id_os_interno):
    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem:
        raise LocalizacaoErro("Ordem de Serviço não encontrada.")
    return ordem


def criar_apontamento(dados, id_os_interno, chave_idempotencia, usuario):
    _autorizar(usuario, "criar")
    chave_idempotencia = _texto(chave_idempotencia)
    if not chave_idempotencia:
        raise LocalizacaoErro("Não foi possível identificar esta solicitação. Atualize a página e tente novamente.")
    ordem = _ordem(id_os_interno)
    existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
    if existente:
        if existente.id_os_interno != ordem.id_os_interno:
            raise LocalizacaoErro("Não foi possível confirmar este apontamento.")
        return existente, True

    jornada_aberta = (
        OperacaoApontamentoDiario.query.join(OperacaoDiarioLocalizacao)
        .filter(
            OperacaoApontamentoDiario.id_os_interno == ordem.id_os_interno,
            OperacaoDiarioLocalizacao.hora_final.is_(None),
        )
        .first()
    )
    if jornada_aberta:
        raise LocalizacaoErro(
            "Há uma jornada de trabalho aberta nesta Ordem de Serviço. "
            "Verifique e feche a jornada antes de cadastrar uma nova Localização."
        )

    dados = _validar_dados(dados)
    apontamento = OperacaoApontamentoDiario(
        id_os_interno=ordem.id_os_interno,
        chave_idempotencia=chave_idempotencia,
        data_evento=dados["data_evento"],
        equipe=dados["equipe"],
        criado_por_usuario_id=usuario.id,
    )
    localizacao = OperacaoDiarioLocalizacao(
        apontamento=apontamento,
        encarregado=dados["encarregado"], chefe_boletim=dados["chefe_boletim"],
        local=dados["local"], numero_amv=dados["numero_amv"], sub=dados["sub"],
        km_inicio=dados["km_inicio"], km_fim=dados["km_fim"],
        hora_inicial=dados["hora_inicial"], intervalo_jornada=dados["intervalo_jornada"], hora_final=dados["hora_final"],
        intervalo_inicio=dados["intervalo_inicio"], intervalo_fim=dados["intervalo_fim"],
        pedido_liberacao_ccp=dados["pedido_liberacao_ccp"],
        liberacao_embandeiramento=dados["liberacao_embandeiramento"],
        termino_embandeiramento=dados["termino_embandeiramento"], observacao=dados["observacao"],
    )
    db.session.add_all([apontamento, localizacao])
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
        if existente and existente.id_os_interno == ordem.id_os_interno:
            return existente, True
        raise LocalizacaoErro("Não foi possível confirmar o apontamento de Localização.") from exc
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LocalizacaoErro("Não foi possível salvar o apontamento de Localização.") from exc

    registrar_log("operacao_localizacao_criada", f"Localização {apontamento.id_apontamento_diario} criada para OS {ordem.codigo_os_rental}.", usuario=usuario)
    return apontamento, False


def consultar_apontamentos(id_os_interno, usuario):
    _autorizar(usuario, "visualizar")
    try:
        return (
            OperacaoApontamentoDiario.query.join(OperacaoDiarioLocalizacao)
            .filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno)
            .order_by(OperacaoApontamentoDiario.data_evento.desc(), OperacaoApontamentoDiario.criado_em.desc())
            .all()
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LocalizacaoErro("Não foi possível consultar os apontamentos de Localização.") from exc


def buscar_apontamento(id_os_interno, id_apontamento_diario, usuario, acao="visualizar"):
    _autorizar(usuario, acao)
    try:
        apontamento = (
            OperacaoApontamentoDiario.query.join(OperacaoDiarioLocalizacao)
            .filter(
                OperacaoApontamentoDiario.id_os_interno == id_os_interno,
                OperacaoApontamentoDiario.id_apontamento_diario == id_apontamento_diario,
            ).first()
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LocalizacaoErro("Não foi possível consultar o apontamento de Localização.") from exc
    if not apontamento:
        raise LocalizacaoErro("Apontamento de Localização não encontrado para esta Ordem de Serviço.")
    return apontamento


def editar_apontamento(dados, id_os_interno, id_apontamento_diario, versao, usuario):
    _autorizar(usuario, "editar")
    try:
        versao = int(versao)
    except (TypeError, ValueError) as exc:
        raise LocalizacaoErro("Não foi possível identificar a versão do apontamento.") from exc
    if versao < 1:
        raise LocalizacaoErro("Não foi possível identificar a versão do apontamento.")
    dados = _validar_dados(dados)
    try:
        atualizados = OperacaoApontamentoDiario.query.filter_by(
            id_apontamento_diario=id_apontamento_diario,
            id_os_interno=id_os_interno,
            versao=versao,
        ).update(
            {
                "data_evento": dados["data_evento"], "equipe": dados["equipe"],
                "atualizado_por_usuario_id": usuario.id, "versao": versao + 1,
            },
            synchronize_session=False,
        )
        if atualizados != 1:
            db.session.rollback()
            raise LocalizacaoErro("Este apontamento foi alterado por outro usuário. Atualize a página antes de salvar.")
        OperacaoDiarioLocalizacao.query.filter_by(id_apontamento_diario=id_apontamento_diario).update(
            {campo: dados[campo] for campo in (
                "encarregado", "chefe_boletim", "local", "numero_amv", "sub", "km_inicio", "km_fim",
                "hora_inicial", "intervalo_jornada", "hora_final",
                "intervalo_inicio", "intervalo_fim", "pedido_liberacao_ccp", "liberacao_embandeiramento",
                "termino_embandeiramento", "observacao",
            )},
            synchronize_session=False,
        )
        db.session.commit()
    except LocalizacaoErro:
        raise
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LocalizacaoErro("Não foi possível atualizar o apontamento de Localização.") from exc

    apontamento = buscar_apontamento(id_os_interno, id_apontamento_diario, usuario, "editar")
    registrar_log("operacao_localizacao_editada", f"Localização {id_apontamento_diario} atualizada para a OS {id_os_interno}.", usuario=usuario)
    return apontamento
