from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import (
    OperacaoApontamentoDiario,
    OperacaoDiarioMaterial,
    OperacaoDiarioServico,
    OperacaoOrdemServico,
    OperacaoServicoCatalogo,
    OperacaoMaterialCatalogo,
)
from app.operacao.ordens_servico.localizacao_service import OPCOES
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao


class DiarioProducaoErro(Exception):
    pass


def _texto(valor):
    return str(valor or "").strip()


def _configuracao(diario):
    if diario == "servico":
        return OperacaoDiarioServico, "Serviço", "servico"
    if diario == "material":
        return OperacaoDiarioMaterial, "Material", "material_aplicado"
    raise DiarioProducaoErro("Diário de produção inválido.")


def _autorizar(usuario, acao, nome):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", acao):
        raise DiarioProducaoErro(f"Você não possui permissão para esta operação de {nome}.")


def _validar_dados(dados, diario):
    _, _, campo = _configuracao(diario)
    try:
        data_evento = date.fromisoformat(_texto(dados.get("data_evento")))
    except ValueError as exc:
        raise DiarioProducaoErro("Informe uma data operacional válida.") from exc
    quantidade_texto = _texto(dados.get("quantidade"))
    if "." in quantidade_texto or not quantidade_texto.replace(",", "").isdigit() or quantidade_texto.count(",") > 1 or ("," in quantidade_texto and len(quantidade_texto.split(",", 1)[1]) > 2):
        raise DiarioProducaoErro("Informe a quantidade usando vírgula e até duas casas decimais.")
    try:
        quantidade = Decimal(quantidade_texto.replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise DiarioProducaoErro("Informe uma quantidade numérica válida.") from exc
    if quantidade <= 0:
        raise DiarioProducaoErro("A quantidade deve ser maior que zero.")
    registro = {"data_evento": data_evento, "equipe": _texto(dados.get("equipe")), campo: _texto(dados.get(campo)), "quantidade": quantidade}
    if not registro["equipe"] or not registro[campo]:
        raise DiarioProducaoErro("Preencha todos os campos obrigatórios.")
    if diario == "servico" and not OperacaoServicoCatalogo.query.filter_by(nome=registro[campo], ativo=True).first():
        raise DiarioProducaoErro("Selecione um serviço válido do cadastro.")
    if diario == "material" and not OperacaoMaterialCatalogo.query.filter_by(nome=registro[campo], ativo=True).first():
        raise DiarioProducaoErro("Selecione um material válido do cadastro.")
    if registro["equipe"] not in OPCOES["equipe"]:
        raise DiarioProducaoErro("Selecione uma equipe válida.")
    if diario == "material":
        registro["tipo_material"] = _texto(dados.get("tipo_material"))
        if registro["tipo_material"] not in ("NOVO", "RECUPERADO"):
            raise DiarioProducaoErro("Selecione um tipo de material válido.")
    return registro


def _ordem(id_os_interno):
    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem:
        raise DiarioProducaoErro("Ordem de Serviço não encontrada.")
    return ordem


def criar_registro(dados, id_os_interno, chave_idempotencia, usuario, diario):
    modelo, nome, campo = _configuracao(diario)
    _autorizar(usuario, "criar", nome)
    chave_idempotencia = _texto(chave_idempotencia)
    if not chave_idempotencia:
        raise DiarioProducaoErro("Não foi possível identificar esta solicitação. Atualize a página e tente novamente.")
    ordem = _ordem(id_os_interno)
    existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
    if existente:
        if existente.id_os_interno != ordem.id_os_interno or not getattr(existente, f"diario_{diario}"):
            raise DiarioProducaoErro("Não foi possível confirmar este apontamento.")
        return existente, True
    dados = _validar_dados(dados, diario)
    apontamento = OperacaoApontamentoDiario(
        id_os_interno=ordem.id_os_interno, chave_idempotencia=chave_idempotencia,
        data_evento=dados["data_evento"], equipe=dados["equipe"], criado_por_usuario_id=usuario.id,
    )
    if diario == "servico":
        filho = modelo(apontamento=apontamento, servico=dados[campo], quantidade=dados["quantidade"])
    else:
        filho = modelo(apontamento=apontamento, tipo_material=dados["tipo_material"], material_aplicado=dados[campo], quantidade=dados["quantidade"])
    db.session.add_all([apontamento, filho])
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        existente = OperacaoApontamentoDiario.query.filter_by(chave_idempotencia=chave_idempotencia).first()
        if existente and existente.id_os_interno == ordem.id_os_interno and getattr(existente, f"diario_{diario}"):
            return existente, True
        raise DiarioProducaoErro(f"Não foi possível confirmar o apontamento de {nome}.") from exc
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise DiarioProducaoErro(f"Não foi possível salvar o apontamento de {nome}.") from exc
    registrar_log(f"operacao_{diario}_criado", f"{nome} {apontamento.id_apontamento_diario} criado para OS {ordem.codigo_os_rental}.", usuario=usuario)
    return apontamento, False


def consultar_registros(id_os_interno, usuario, diario):
    modelo, nome, _ = _configuracao(diario)
    _autorizar(usuario, "visualizar", nome)
    try:
        return (OperacaoApontamentoDiario.query.join(modelo).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno).order_by(OperacaoApontamentoDiario.data_evento.desc(), OperacaoApontamentoDiario.criado_em.desc()).all())
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise DiarioProducaoErro(f"Não foi possível consultar os apontamentos de {nome}.") from exc


def buscar_registro(id_os_interno, id_apontamento_diario, usuario, diario, acao="visualizar"):
    modelo, nome, _ = _configuracao(diario)
    _autorizar(usuario, acao, nome)
    try:
        apontamento = (OperacaoApontamentoDiario.query.join(modelo).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno, OperacaoApontamentoDiario.id_apontamento_diario == id_apontamento_diario).first())
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise DiarioProducaoErro(f"Não foi possível consultar o apontamento de {nome}.") from exc
    if not apontamento:
        raise DiarioProducaoErro(f"Apontamento de {nome} não encontrado para esta Ordem de Serviço.")
    return apontamento


def editar_registro(dados, id_os_interno, id_apontamento_diario, versao, usuario, diario):
    modelo, nome, campo = _configuracao(diario)
    _autorizar(usuario, "editar", nome)
    try:
        versao = int(versao)
    except (TypeError, ValueError) as exc:
        raise DiarioProducaoErro("Não foi possível identificar a versão do apontamento.") from exc
    if versao < 1:
        raise DiarioProducaoErro("Não foi possível identificar a versão do apontamento.")
    dados = _validar_dados(dados, diario)
    try:
        atualizados = OperacaoApontamentoDiario.query.filter_by(id_apontamento_diario=id_apontamento_diario, id_os_interno=id_os_interno, versao=versao).update({"data_evento": dados["data_evento"], "equipe": dados["equipe"], "atualizado_por_usuario_id": usuario.id, "versao": versao + 1}, synchronize_session=False)
        if atualizados != 1:
            db.session.rollback()
            raise DiarioProducaoErro("Este apontamento foi alterado por outro usuário. Atualize a página antes de salvar.")
        valores = {campo: dados[campo], "quantidade": dados["quantidade"]}
        if diario == "material":
            valores["tipo_material"] = dados["tipo_material"]
        modelo.query.filter_by(id_apontamento_diario=id_apontamento_diario).update(valores, synchronize_session=False)
        db.session.commit()
    except DiarioProducaoErro:
        raise
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise DiarioProducaoErro(f"Não foi possível atualizar o apontamento de {nome}.") from exc
    apontamento = buscar_registro(id_os_interno, id_apontamento_diario, usuario, diario, "editar")
    registrar_log(f"operacao_{diario}_editado", f"{nome} {id_apontamento_diario} atualizado para a OS {id_os_interno}.", usuario=usuario)
    return apontamento
