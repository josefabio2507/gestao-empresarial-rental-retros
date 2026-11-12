from datetime import date, time

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import OperacaoApontamentoDiario, OperacaoIntervencaoAdversa, OperacaoOrdemServico
from app.operacao.ordens_servico.localizacao_service import OPCOES
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.operacao.ordens_servico.status_service import atualizar_status_operacional


class IntervencaoErro(Exception):
    pass


INTERVENCOES_POR_CATEGORIA = {
    "ACESSO À FRENTE DE SERVIÇO": ("EQUIPE IMPEDIDA DE ACESSAR O LOCAL DEVIDO COMPOSIÇÃO TRANCANDO PN", "EQUIPE IMPEDIDA DE ACESSAR O LOCAL DEVIDO COMPOSIÇÃO NO PÁTIO IMPEDINDO TRAVESSIA", "EQUIPE IMPEDIDA DE MONTAR ÁREA DE VIVÊNCIA DEVIDO COMPOSIÇÃO NO LOCAL"),
    "ACIDENTE OU INCIDENTE": ("EQUIPE ACIONADA PARA ATENDIMENTO DE ACIDENTE FERROVIÁRIO", "EQUIPE ACIONADA PARA ATENDIMENTO DE INCIDENTE FERROVIÁRIO"),
    "AGUARDANDO ASSINATURA DE PT": ("NÃO HÁ RESPONSÁVEL PARA ASSINAR NO LOCAL",),
    "CHUVA": ("CHUVA FORTE C/ INCIDÊNCIA DE RAIOS E TROVÕES", "CHUVA FORTE C/ TEMPESTADE DE VENTO"),
    "DESLOCAMENTO PARA FRENTE DE SERVIÇO": ("CAMINHÃO IMPEDIDO DE CHEGAR NO LOCAL DEVIDO TRÂNSITO", "CAMINHÃO IMPEDIDO DE CHEGAR NO LOCAL DEVIDO COMPOSIÇÃO TRANCANDO ACESSO"),
    "FALTA DE BOLETIM DE VIA": ("INFORMAÇÃO INCORRETA NO BOLETIM", "BOLETIM CADASTRADO COMO COMPARTILHADO, SEM O RESPONSÁVEL LOCAL PRESENTE"),
    "FALTA DE INTERVALO P/ INICIAR ATIVIDADES": ("ATRASO DO CCP PARA AUTORIZAR O INTERVALO", "INTERVALO NÃO SOLICITADO AO CCP"),
    "FALTA DE MATERIAL NO LOCAL": ("AUSÊNCIA DE MATERIAL NO LOCAL", "MATERIAL SEM CONDIÇÃO DE USO", "MATERIAL INSUFICIENTE"),
    "FALTA DE O.S. NO LOCAL": ("ORDEM DE SERVIÇO NÃO FOI CRIADA", "ORDEM DE SERVIÇO NÃO FOI ENTREGUE À EQUIPE"),
    "INSPEÇÃO": ("INSPEÇÃO DA FIPS COM NECESSIDADE DE PARALISAÇÃO DA EQUIPE", "INSPEÇÃO DA RENTAL COM NECESSIDADE DE PARALISAÇÃO DA EQUIPE"),
    "TREINAMENTO OU PALESTRA": ("PARADÃO DE SEGURANÇA", "DDS REALIZADO PELA ADMINISTRAÇÃO RENTAL", "DDS REALIZADO PELA ADMINISTRAÇÃO FIPS"),
}
CATEGORIAS = tuple(sorted(INTERVENCOES_POR_CATEGORIA))


def _texto(valor): return str(valor or "").strip()


def _autorizar(usuario, acao):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", acao): raise IntervencaoErro("Você não possui permissão para esta operação de Intervenções Adversas.")


def _validar(dados):
    try: data_evento = date.fromisoformat(_texto(dados.get("data_evento")))
    except ValueError as exc: raise IntervencaoErro("Informe uma data operacional válida.") from exc
    registro = {"data_evento": data_evento, "equipe": _texto(dados.get("equipe")), "intervencao": _texto(dados.get("intervencao")).upper(), "categoria": _texto(dados.get("categoria")), "observacoes": _texto(dados.get("observacoes"))}
    for campo in ("hora_inicio", "hora_fim"):
        valor = _texto(dados.get(campo))
        try: registro[campo] = time.fromisoformat(valor) if valor else None
        except ValueError as exc: raise IntervencaoErro("Informe horários válidos.") from exc
    if not all((registro["equipe"], registro["intervencao"], registro["categoria"])): raise IntervencaoErro("Preencha todos os campos obrigatórios.")
    if registro["equipe"] not in OPCOES["equipe"]: raise IntervencaoErro("Selecione uma equipe válida.")
    if registro["categoria"] not in CATEGORIAS: raise IntervencaoErro("Selecione uma categoria válida da lista.")
    if registro["intervencao"] not in INTERVENCOES_POR_CATEGORIA[registro["categoria"]]: raise IntervencaoErro("Selecione uma intervenção válida para a categoria informada.")
    return registro


def _ordem(id_os_interno):
    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem: raise IntervencaoErro("Ordem de Serviço não encontrada.")
    return ordem


def criar_intervencao(dados, id_os_interno, chave_idempotencia, usuario):
    _autorizar(usuario, "criar"); chave_idempotencia = _texto(chave_idempotencia)
    if not chave_idempotencia: raise IntervencaoErro("Não foi possível identificar esta solicitação. Atualize a página e tente novamente.")
    ordem = _ordem(id_os_interno); existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
    if existente:
        if existente.id_os_interno != ordem.id_os_interno or not existente.intervencao_adversa: raise IntervencaoErro("Não foi possível confirmar este apontamento.")
        return existente, True
    dados = _validar(dados); apontamento = OperacaoApontamentoDiario(id_os_interno=ordem.id_os_interno, chave_idempotencia=chave_idempotencia, data_evento=dados["data_evento"], equipe=dados["equipe"], criado_por_usuario_id=usuario.id)
    filho = OperacaoIntervencaoAdversa(apontamento=apontamento, hora_inicio=dados["hora_inicio"], hora_fim=dados["hora_fim"], intervencao=dados["intervencao"], categoria=dados["categoria"], observacoes=dados["observacoes"])
    db.session.add_all([apontamento, filho])
    try: db.session.commit()        atualizar_status_operacional(ordem)

    except IntegrityError as exc:
        db.session.rollback(); existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
        if existente and existente.id_os_interno == ordem.id_os_interno and existente.intervencao_adversa: return existente, True
        raise IntervencaoErro("Não foi possível confirmar a intervenção adversa.") from exc
    except SQLAlchemyError as exc: db.session.rollback(); raise IntervencaoErro("Não foi possível salvar a intervenção adversa.") from exc
    registrar_log("operacao_intervencao_criada", f"Intervenção {apontamento.id_apontamento_diario} criada para OS {ordem.codigo_os_rental}.", usuario=usuario); return apontamento, False


def consultar_intervencoes(id_os_interno, usuario):
    _autorizar(usuario, "visualizar")
    return (OperacaoApontamentoDiario.query.join(OperacaoIntervencaoAdversa).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno).order_by(OperacaoApontamentoDiario.data_evento.desc(), OperacaoApontamentoDiario.criado_em.desc()).all())


def buscar_intervencao(id_os_interno, id_apontamento_diario, usuario, acao="visualizar"):
    _autorizar(usuario, acao); apontamento = (OperacaoApontamentoDiario.query.join(OperacaoIntervencaoAdversa).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno, OperacaoApontamentoDiario.id_apontamento_diario == id_apontamento_diario).first())
    if not apontamento: raise IntervencaoErro("Intervenção adversa não encontrada para esta Ordem de Serviço.")
    return apontamento


def editar_intervencao(dados, id_os_interno, id_apontamento_diario, versao, usuario):
    _autorizar(usuario, "editar")
    try: versao = int(versao)
    except (TypeError, ValueError) as exc: raise IntervencaoErro("Não foi possível identificar a versão do apontamento.") from exc
    dados = _validar(dados)
    try:
        atualizados = OperacaoApontamentoDiario.query.filter_by(id_apontamento_diario=id_apontamento_diario, id_os_interno=id_os_interno, versao=versao).update({"data_evento": dados["data_evento"], "equipe": dados["equipe"], "atualizado_por_usuario_id": usuario.id, "versao": versao + 1}, synchronize_session=False)
        if atualizados != 1: db.session.rollback(); raise IntervencaoErro("Este apontamento foi alterado por outro usuário. Atualize a página antes de salvar.")
        OperacaoIntervencaoAdversa.query.filter_by(id_apontamento_diario=id_apontamento_diario).update({campo: dados[campo] for campo in ("hora_inicio", "hora_fim", "intervencao", "categoria", "observacoes")}, synchronize_session=False)
        atualizar_status_operacional(_ordem(id_os_interno))
        db.session.commit()
    except IntervencaoErro: raise
    except SQLAlchemyError as exc: db.session.rollback(); raise IntervencaoErro("Não foi possível atualizar a intervenção adversa.") from exc
    apontamento = buscar_intervencao(id_os_interno, id_apontamento_diario, usuario, "editar"); registrar_log("operacao_intervencao_editada", f"Intervenção {id_apontamento_diario} atualizada para a OS {id_os_interno}.", usuario=usuario); return apontamento
