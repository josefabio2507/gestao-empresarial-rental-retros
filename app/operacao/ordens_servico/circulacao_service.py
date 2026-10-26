from datetime import date, time

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import OperacaoApontamentoDiario, OperacaoCirculacaoTrem, OperacaoOrdemServico
from app.operacao.ordens_servico.localizacao_service import OPCOES
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao


class CirculacaoErro(Exception):
    pass


OPCOES_CORTE = ("SIM", "NÃO", "NÃO FOI NECESSÁRIO")
OPCOES_MOTIVO_PARALISACAO = ("TREM PARADO", "INTERVALO ENTRE TRENS", "CIRCULAÇÃO DE TREM")


def _texto(valor):
    return str(valor or "").strip()


def _autorizar(usuario, acao):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", acao):
        raise CirculacaoErro("Você não possui permissão para esta operação de Circulação de Trens.")


def _validar_dados(dados):
    try:
        data_evento = date.fromisoformat(_texto(dados.get("data_evento")))
    except ValueError as exc:
        raise CirculacaoErro("Informe uma data operacional válida.") from exc
    registro = {
        "data_evento": data_evento,
        "equipe": _texto(dados.get("equipe")),
        "prefixo": _texto(dados.get("prefixo")).upper() or None,
        "motivo_paralisacao": _texto(dados.get("motivo_paralisacao")),
        "via_linha": _texto(dados.get("via_linha")).upper(),
        "operador_ccp_maquinista": _texto(dados.get("operador_ccp_maquinista")),
        "pedido_corte_composicao": _texto(dados.get("pedido_corte_composicao")),
        "corte_composicao": _texto(dados.get("corte_composicao")),
    }
    for campo in ("hora_inicio", "hora_fim"):
        valor = _texto(dados.get(campo))
        try:
            registro[campo] = time.fromisoformat(valor) if valor else None
        except ValueError as exc:
            raise CirculacaoErro("Informe horários válidos.") from exc
    if registro["hora_inicio"] and registro["hora_fim"] and registro["hora_fim"] < registro["hora_inicio"]:
        raise CirculacaoErro("Hora fim deve ser maior que a Hora início")
    if not registro["equipe"] or not registro["via_linha"]:
        raise CirculacaoErro("Preencha todos os campos obrigatórios.")
    if registro["motivo_paralisacao"] not in OPCOES_MOTIVO_PARALISACAO:
        raise CirculacaoErro("Selecione um motivo de paralisação válido.")
    if registro["equipe"] not in OPCOES["equipe"]:
        raise CirculacaoErro("Selecione uma equipe válida.")
    for campo in ("pedido_corte_composicao", "corte_composicao"):
        if registro[campo] not in OPCOES_CORTE:
            raise CirculacaoErro("Selecione uma resposta válida para o corte da composição.")
    return registro


def _ordem(id_os_interno):
    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem:
        raise CirculacaoErro("Ordem de Serviço não encontrada.")
    return ordem


def criar_circulacao(dados, id_os_interno, chave_idempotencia, usuario):
    _autorizar(usuario, "criar")
    chave_idempotencia = _texto(chave_idempotencia)
    if not chave_idempotencia:
        raise CirculacaoErro("Não foi possível identificar esta solicitação. Atualize a página e tente novamente.")
    ordem = _ordem(id_os_interno)
    existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
    if existente:
        if existente.id_os_interno != ordem.id_os_interno or not existente.circulacao_trem:
            raise CirculacaoErro("Não foi possível confirmar este apontamento.")
        return existente, True
    dados = _validar_dados(dados)
    apontamento = OperacaoApontamentoDiario(id_os_interno=ordem.id_os_interno, chave_idempotencia=chave_idempotencia, data_evento=dados["data_evento"], equipe=dados["equipe"], criado_por_usuario_id=usuario.id)
    circulacao = OperacaoCirculacaoTrem(apontamento=apontamento, **{campo: dados[campo] for campo in ("prefixo", "motivo_paralisacao", "hora_inicio", "hora_fim", "via_linha", "operador_ccp_maquinista", "pedido_corte_composicao", "corte_composicao")})
    db.session.add_all([apontamento, circulacao])
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
        if existente and existente.id_os_interno == ordem.id_os_interno and existente.circulacao_trem:
            return existente, True
        raise CirculacaoErro("Não foi possível confirmar o apontamento de Circulação de Trens.") from exc
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise CirculacaoErro("Não foi possível salvar o apontamento de Circulação de Trens.") from exc
    registrar_log("operacao_circulacao_criada", f"Circulação {apontamento.id_apontamento_diario} criada para OS {ordem.codigo_os_rental}.", usuario=usuario)
    return apontamento, False


def consultar_circulacoes(id_os_interno, usuario):
    _autorizar(usuario, "visualizar")
    try:
        return (OperacaoApontamentoDiario.query.join(OperacaoCirculacaoTrem).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno).order_by(OperacaoApontamentoDiario.data_evento.desc(), OperacaoApontamentoDiario.criado_em.desc()).all())
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise CirculacaoErro("Não foi possível consultar as circulações de trens.") from exc


def buscar_circulacao(id_os_interno, id_apontamento_diario, usuario, acao="visualizar"):
    _autorizar(usuario, acao)
    apontamento = (OperacaoApontamentoDiario.query.join(OperacaoCirculacaoTrem).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno, OperacaoApontamentoDiario.id_apontamento_diario == id_apontamento_diario).first())
    if not apontamento:
        raise CirculacaoErro("Circulação de Trens não encontrada para esta Ordem de Serviço.")
    return apontamento


def editar_circulacao(dados, id_os_interno, id_apontamento_diario, versao, usuario):
    _autorizar(usuario, "editar")
    try:
        versao = int(versao)
    except (TypeError, ValueError) as exc:
        raise CirculacaoErro("Não foi possível identificar a versão do apontamento.") from exc
    dados = _validar_dados(dados)
    try:
        atualizados = OperacaoApontamentoDiario.query.filter_by(id_apontamento_diario=id_apontamento_diario, id_os_interno=id_os_interno, versao=versao).update({"data_evento": dados["data_evento"], "equipe": dados["equipe"], "atualizado_por_usuario_id": usuario.id, "versao": versao + 1}, synchronize_session=False)
        if atualizados != 1:
            db.session.rollback()
            raise CirculacaoErro("Este apontamento foi alterado por outro usuário. Atualize a página antes de salvar.")
        OperacaoCirculacaoTrem.query.filter_by(id_apontamento_diario=id_apontamento_diario).update({campo: dados[campo] for campo in ("prefixo", "motivo_paralisacao", "hora_inicio", "hora_fim", "via_linha", "operador_ccp_maquinista", "pedido_corte_composicao", "corte_composicao")}, synchronize_session=False)
        db.session.commit()
    except CirculacaoErro:
        raise
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise CirculacaoErro("Não foi possível atualizar a Circulação de Trens.") from exc
    apontamento = buscar_circulacao(id_os_interno, id_apontamento_diario, usuario, "editar")
    registrar_log("operacao_circulacao_editada", f"Circulação {id_apontamento_diario} atualizada para a OS {id_os_interno}.", usuario=usuario)
    return apontamento
