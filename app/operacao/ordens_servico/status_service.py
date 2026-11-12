from sqlalchemy import func

from app.extensions import db
from app.models import OperacaoApontamentoDiario, OperacaoOrdemServico


STATUS_OPERACIONAIS = (
    "Programada",
    "Em Andamento",
    "Em Andamento c/ Atraso",
    "Concluída",
    "Concluída c/ Atraso",
    "Cancelada",
)


def atualizar_status_operacional(ordem):
    """Atualiza o status conforme os dias distintos apontados para a OS."""
    if not ordem.ativo or ordem.status_operacional == "Cancelada":
        return ordem.status_operacional
    total_dias_programados = (
        (ordem.data_programada_final - ordem.data_programada_inicial).days + 1
    )
    dias_trabalhados = (
        db.session.query(func.count(func.distinct(OperacaoApontamentoDiario.data_evento)))
        .filter(OperacaoApontamentoDiario.id_os_interno == ordem.id_os_interno)
        .scalar()
        or 0
    )
    em_atraso = dias_trabalhados > total_dias_programados

    if ordem.data_final:
        ordem.status_operacional = "Concluída c/ Atraso" if em_atraso else "Concluída"
    elif dias_trabalhados or ordem.data_inicial:
        ordem.status_operacional = "Em Andamento c/ Atraso" if em_atraso else "Em Andamento"
    else:
        ordem.status_operacional = "Programada"
    return ordem.status_operacional


def sincronizar_statuses_operacionais():
    """Atualiza OS históricas que tenham apontamentos registrados antes desta regra."""
    alteradas = False
    for ordem in OperacaoOrdemServico.query.filter_by(ativo=True).all():
        status_anterior = ordem.status_operacional
        atualizar_status_operacional(ordem)
        alteradas = alteradas or ordem.status_operacional != status_anterior
    if alteradas:
        db.session.commit()
