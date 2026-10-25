from datetime import date

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import OperacaoOrdemServico, Equipe, Colaborador
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao


class OrdemServicoCadastroErro(Exception):
    pass


CAMPOS_OBRIGATORIOS = (
    "local",
    "equipe",
    "data_programada_inicial",
    "data_programada_final",
)


def _texto(valor):
    return str(valor or "").strip().upper()


def _data(valor, campo):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise OrdemServicoCadastroErro(f"Informe {campo} no formato correto.") from exc


def _validar_dados(dados):
    normalizados = {
        campo: _texto(dados.get(campo))
        for campo in (
            "numero_os_cliente",
            "local",
            "equipe",
            "trabalho_previsto",
            "supervisor",
            "encarregado",
        )
    }
    # Valores escolhidos em listas preservam a grafia oficial do cadastro.
    for campo in ("equipe", "supervisor", "encarregado"):
        normalizados[campo] = str(dados.get(campo) or "").strip()
    if normalizados["numero_os_cliente"] and not normalizados["numero_os_cliente"].isdigit():
        raise OrdemServicoCadastroErro("O número da OS do cliente deve conter apenas números inteiros.")
    if not Equipe.query.filter_by(nome=normalizados["equipe"], ativo=True).first():
        raise OrdemServicoCadastroErro("Selecione uma equipe ativa válida.")
    for campo, trecho in (("supervisor", "Supervisor"), ("encarregado", "Encarregado")):
        if normalizados[campo] and not Colaborador.query.filter(Colaborador.nome == normalizados[campo], Colaborador.ativo.is_(True), Colaborador.cargo.ilike(f"%{trecho}%")).first():
            raise OrdemServicoCadastroErro(f"Selecione um {campo} válido da lista.")
    obrigatorios = {
        "local": normalizados["local"],
        "equipe": normalizados["equipe"],
        "data_programada_inicial": _texto(dados.get("data_programada_inicial")),
        "data_programada_final": _texto(dados.get("data_programada_final")),
    }
    faltantes = [campo for campo in CAMPOS_OBRIGATORIOS if not obrigatorios[campo]]
    if faltantes:
        raise OrdemServicoCadastroErro(
            "Preencha os campos obrigatórios: " + ", ".join(faltantes) + "."
        )

    normalizados["data_programada_inicial"] = _data(
        _texto(dados.get("data_programada_inicial")),
        "a data programada inicial",
    )
    normalizados["data_programada_final"] = _data(
        _texto(dados.get("data_programada_final")),
        "a data programada final",
    )
    normalizados["data_inicial"] = _data(_texto(dados.get("data_inicial")), "a data inicial realizada")
    normalizados["data_final"] = _data(_texto(dados.get("data_final")), "a data final realizada")

    if normalizados["data_programada_final"] < normalizados["data_programada_inicial"]:
        raise OrdemServicoCadastroErro("A data programada final não pode ser anterior à inicial.")
    return normalizados


def criar_ordem_servico(dados, chave_idempotencia, usuario):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", "criar"):
        raise OrdemServicoCadastroErro("Você não possui permissão para criar Ordens de Serviço.")
    chave_idempotencia = _texto(chave_idempotencia)
    if not chave_idempotencia:
        raise OrdemServicoCadastroErro("Não foi possível identificar esta solicitação. Atualize a página e tente novamente.")

    existente = OperacaoOrdemServico.query.filter_by(
        chave_idempotencia=chave_idempotencia
    ).first()
    if existente:
        return existente, True

    dados = _validar_dados(dados)
    ordem = OperacaoOrdemServico(
        chave_idempotencia=chave_idempotencia,
        numero_os_cliente=dados["numero_os_cliente"] or None,
        local=dados["local"],
        equipe=dados["equipe"],
        data_programada_inicial=dados["data_programada_inicial"],
        data_programada_final=dados["data_programada_final"],
        data_inicial=dados["data_inicial"],
        data_final=dados["data_final"],
        trabalho_previsto=dados["trabalho_previsto"] or None,
        supervisor=dados["supervisor"] or None,
        encarregado=dados["encarregado"] or None,
        status_identificacao="Informado" if dados["numero_os_cliente"] else "Pendente",
        status_operacional="Concluída" if dados["data_final"] else "Programada",
        criado_por_usuario_id=usuario.id,
    )
    db.session.add(ordem)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        existente = OperacaoOrdemServico.query.filter_by(
            chave_idempotencia=chave_idempotencia
        ).first()
        if existente:
            return existente, True
        raise OrdemServicoCadastroErro("Não foi possível confirmar a criação da Ordem de Serviço.") from exc

    registrar_log(
        "operacao_ordem_servico_criada",
        f"OS {ordem.codigo_os_rental} criada no banco operacional.",
        usuario=usuario,
    )
    return ordem, False


def editar_ordem_servico(dados, id_os_interno, usuario):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", "editar"):
        raise OrdemServicoCadastroErro("Você não possui permissão para editar Ordens de Serviço.")

    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem:
        raise OrdemServicoCadastroErro("Ordem de Serviço não encontrada.")

    dados = _validar_dados(dados)
    for campo in (
        "numero_os_cliente", "local", "equipe", "data_programada_inicial",
        "data_programada_final", "data_inicial", "data_final", "trabalho_previsto",
        "supervisor", "encarregado",
    ):
        setattr(ordem, campo, dados[campo] or None)

    ordem.status_identificacao = "Informado" if ordem.numero_os_cliente else "Pendente"
    ordem.status_operacional = "Concluída" if ordem.data_final else ("Em Andamento" if ordem.data_inicial else "Programada")
    ordem.atualizado_por_usuario_id = usuario.id
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise OrdemServicoCadastroErro("Não foi possível salvar as alterações da Ordem de Serviço.") from exc

    registrar_log(
        "operacao_ordem_servico_editada",
        f"OS {ordem.codigo_os_rental} atualizada no banco operacional.",
        usuario=usuario,
    )
    return ordem
