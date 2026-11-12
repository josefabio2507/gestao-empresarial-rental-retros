from datetime import date, time

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import OperacaoApontamentoDiario, OperacaoIntervencaoAdversa, OperacaoOrdemServico
from app.operacao.ordens_servico.localizacao_service import OPCOES
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao


class IntervencaoErro(Exception):
    pass


INTERVENCOES_POR_CATEGORIA = {
    "ACESSO � FRENTE DE SERVI�O": (
        "EQUIPE IMPEDIDA DE ACESSAR O LOCAL DEVIDO COMPOSI��O TRANCANDO PN",
        "EQUIPE IMPEDIDA DE ACESSAR O LOCAL DEVIDO COMPOSI��O NO P�TIO IMPEDINDO TRAVESSIA",
        "EQUIPE IMPEDIDA DE MONTAR �REA DE VIV�NCIA DEVIDO COMPOSI��O NO LOCAL",
    ),
    "ACIDENTE OU INCIDENTE": (
        "EQUIPE ACIONADA PARA ATENDIMENTO DE ACIDENTE FERROVI�RIO",
        "EQUIPE ACIONADA PARA ATENDIMENTO DE INCIDENTE FERROVI�RIO",
    ),
    "AGUARDANDO ASSINATURA DE PT": ("N�O H� RESPONS�VEL PARA ASSINAR NO LOCAL",),
    "CHUVA": ("CHUVA FORTE C/ INCID�NCIA DE RAIOS E TROV�ES", "CHUVA FORTE C/ TEMPESTADE DE VENTO"),
    "DESLOCAMENTO PARA FRENTE DE SERVI�O": (
        "CAMINH�O IMPEDIDO DE CHEGAR NO LOCAL DEVIDO TR�NSITO",
        "CAMINH�O IMPEDIDO DE CHEGAR NO LOCAL DEVIDO COMPOSI��O TRANCANDO ACESSO",
    ),
    "FALTA DE BOLETIM DE VIA": (
        "INFORMA��O INCORRETA NO BOLETIM",
        "BOLETIM CADASTRADO COMO COMPARTILHADO, SEM O RESPONS�VEL LOCAL PRESENTE",
    ),
    "FALTA DE INTERVALO P/ INICIAR ATIVIDADES": (
        "ATRASO DO CCP PARA AUTORIZAR O INTERVALO",
        "INTERVALO N�O SOLICITADO AO CCP",
    ),
    "FALTA DE MATERIAL NO LOCAL": (
        "AUS�NCIA DE MATERIAL NO LOCAL", "MATERIAL SEM CONDI��O DE USO", "MATERIAL INSUFICIENTE",
    ),
    "FALTA DE O.S. NO LOCAL": ("ORDEM DE SERVI�O N�O FOI CRIADA", "ORDEM DE SERVI�O N�O FOI ENTREGUE � EQUIPE"),
    "INSPE��O": (
        "INSPE��O DA FIPS COM NECESSIDADE DE PARALISA��O DA EQUIPE",
        "INSPE��O DA RENTAL COM NECESSIDADE DE PARALISA��O DA EQUIPE",
    ),
    "TREINAMENTO OU PALESTRA": (
        "PARAD�O DE SEGURAN�A", "DDS REALIZADO PELA ADMINISTRA��O RENTAL", "DDS REALIZADO PELA ADMINISTRA��O FIPS",
    ),
}
CATEGORIAS = tuple(sorted(INTERVENCOES_POR_CATEGORIA))


def _texto(valor): return str(valor or "").strip()


def _autorizar(usuario, acao):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", acao): raise IntervencaoErro("Voc� n�o possui permiss�o para esta opera��o de Interven��es Adversas.")


def _validar(dados):
    try: data_evento = date.fromisoformat(_texto(dados.get("data_evento")))
    except ValueError as exc: raise IntervencaoErro("Informe uma data operacional v�lida.") from exc
    registro = {"data_evento": data_evento, "equipe": _texto(dados.get("equipe")), "intervencao": _texto(dados.get("intervencao")).upper(), "categoria": _texto(dados.get("categoria")), "observacoes": _texto(dados.get("observacoes"))}
    for campo in ("hora_inicio", "hora_fim"):
        valor = _texto(dados.get(campo))
        try: registro[campo] = time.fromisoformat(valor) if valor else None
        except ValueError as exc: raise IntervencaoErro("Informe hor�rios v�lidos.") from exc
    if not all((registro["equipe"], registro["intervencao"], registro["categoria"])): raise IntervencaoErro("Preencha todos os campos obrigat�rios.")
    if registro["equipe"] not in OPCOES["equipe"]: raise IntervencaoErro("Selecione uma equipe v�lida.")
    if registro["categoria"] not in CATEGORIAS: raise IntervencaoErro("Selecione uma categoria v�lida da lista.")
    if registro["intervencao"] not in INTERVENCOES_POR_CATEGORIA[registro["categoria"]]: raise IntervencaoErro("Selecione uma interven��o v�lida para a categoria informada.")
    return registro


def _ordem(id_os_interno):
    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem: raise IntervencaoErro("Ordem de Servi�o n�o encontrada.")
    return ordem


def criar_intervencao(dados, id_os_interno, chave_idempotencia, usuario):
    _autorizar(usuario, "criar"); chave_idempotencia = _texto(chave_idempotencia)
    if not chave_idempotencia: raise IntervencaoErro("N�o foi poss�vel identificar esta solicita��o. Atualize a p�gina e tente novamente.")
    ordem = _ordem(id_os_interno); existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
    if existente:
        if existente.id_os_interno != ordem.id_os_interno or not existente.intervencao_adversa: raise IntervencaoErro("N�o foi poss�vel confirmar este apontamento.")
        return existente, True
    dados = _validar(dados); apontamento = OperacaoApontamentoDiario(id_os_interno=ordem.id_os_interno, chave_idempotencia=chave_idempotencia, data_evento=dados["data_evento"], equipe=dados["equipe"], criado_por_usuario_id=usuario.id)
    filho = OperacaoIntervencaoAdversa(apontamento=apontamento, hora_inicio=dados["hora_inicio"], hora_fim=dados["hora_fim"], intervencao=dados["intervencao"], categoria=dados["categoria"], observacoes=dados["observacoes"])
    db.session.add_all([apontamento, filho])
    try: db.session.commit()
    except IntegrityError as exc:
        db.session.rollback(); existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
        if existente and existente.id_os_interno == ordem.id_os_interno and existente.intervencao_adversa: return existente, True
        raise IntervencaoErro("N�o foi poss�vel confirmar a interven��o adversa.") from exc
    except SQLAlchemyError as exc: db.session.rollback(); raise IntervencaoErro("N�o foi poss�vel salvar a interven��o adversa.") from exc
    registrar_log("operacao_intervencao_criada", f"Interven��o {apontamento.id_apontamento_diario} criada para OS {ordem.codigo_os_rental}.", usuario=usuario); return apontamento, False


def consultar_intervencoes(id_os_interno, usuario):
    _autorizar(usuario, "visualizar")
    return (OperacaoApontamentoDiario.query.join(OperacaoIntervencaoAdversa).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno).order_by(OperacaoApontamentoDiario.data_evento.desc(), OperacaoApontamentoDiario.criado_em.desc()).all())


def buscar_intervencao(id_os_interno, id_apontamento_diario, usuario, acao="visualizar"):
    _autorizar(usuario, acao); apontamento = (OperacaoApontamentoDiario.query.join(OperacaoIntervencaoAdversa).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno, OperacaoApontamentoDiario.id_apontamento_diario == id_apontamento_diario).first())
    if not apontamento: raise IntervencaoErro("Interven��o adversa n�o encontrada para esta Ordem de Servi�o.")
    return apontamento


def editar_intervencao(dados, id_os_interno, id_apontamento_diario, versao, usuario):
    _autorizar(usuario, "editar")
    try: versao = int(versao)
    except (TypeError, ValueError) as exc: raise IntervencaoErro("N�o foi poss�vel identificar a vers�o do apontamento.") from exc
    dados = _validar(dados)
    try:
        atualizados = OperacaoApontamentoDiario.query.filter_by(id_apontamento_diario=id_apontamento_diario, id_os_interno=id_os_interno, versao=versao).update({"data_evento": dados["data_evento"], "equipe": dados["equipe"], "atualizado_por_usuario_id": usuario.id, "versao": versao + 1}, synchronize_session=False)
        if atualizados != 1: db.session.rollback(); raise IntervencaoErro("Este apontamento foi alterado por outro usu�rio. Atualize a p�gina antes de salvar.")
        OperacaoIntervencaoAdversa.query.filter_by(id_apontamento_diario=id_apontamento_diario).update({campo: dados[campo] for campo in ("hora_inicio", "hora_fim", "intervencao", "categoria", "observacoes")}, synchronize_session=False); db.session.commit()
    except IntervencaoErro: raise
    except SQLAlchemyError as exc: db.session.rollback(); raise IntervencaoErro("N�o foi poss�vel atualizar a interven��o adversa.") from exc
    apontamento = buscar_intervencao(id_os_interno, id_apontamento_diario, usuario, "editar"); registrar_log("operacao_intervencao_editada", f"Interven��o {id_apontamento_diario} atualizada para a OS {id_os_interno}.", usuario=usuario); return apontamento

