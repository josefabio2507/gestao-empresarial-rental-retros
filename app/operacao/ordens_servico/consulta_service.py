import uuid
from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import OperacaoOrdemServico
from app.models import Equipe
from app.services.permissoes_service import usuario_tem_permissao


TAMANHO_PAGINA = 10


class OrdemServicoConsultaErro(Exception):
    pass


class ResultadoConsultaOrdensServico:
    def __init__(self, itens, total, pagina, tamanho_pagina):
        self.itens = itens
        self.total = total
        self.pagina = pagina
        self.tamanho_pagina = tamanho_pagina
        self.total_paginas = max(1, (total + tamanho_pagina - 1) // tamanho_pagina)

    @property
    def possui_anterior(self):
        return self.pagina > 1

    @property
    def possui_proxima(self):
        return self.pagina < self.total_paginas


def _texto(valor):
    return str(valor or "").strip()


def _data_filtro(valor, descricao):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError as exc:
        raise OrdemServicoConsultaErro(f"Informe {descricao} no formato correto.") from exc


def _pagina(valor):
    try:
        return max(int(valor or 1), 1)
    except (TypeError, ValueError):
        return 1


def _autorizar(usuario):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", "visualizar"):
        raise OrdemServicoConsultaErro("Você não possui permissão para consultar Ordens de Serviço.")


def consultar_ordens(filtros, pagina, usuario, tamanho_pagina=TAMANHO_PAGINA):
    _autorizar(usuario)
    filtros = filtros or {}
    pagina = _pagina(pagina)
    tamanho_pagina = min(max(int(tamanho_pagina), 1), 100)

    try:
        consulta = OperacaoOrdemServico.query
        equipe = _texto(filtros.get("equipe"))
        if equipe and not Equipe.query.filter_by(nome=equipe, ativo=True).first():
            raise OrdemServicoConsultaErro("Selecione uma equipe válida da lista.")
        status_operacional = _texto(filtros.get("status_operacional"))
        if status_operacional and status_operacional not in ("Programada", "Em Andamento", "Concluída", "Cancelada"):
            raise OrdemServicoConsultaErro("Selecione um status válido da lista.")
        for campo in (
            "codigo_os_rental",
            "numero_os_cliente",
            "local",
            "equipe",
            "status_operacional",
            "status_identificacao",
        ):
            valor = _texto(filtros.get(campo))
            if valor:
                consulta = consulta.filter(getattr(OperacaoOrdemServico, campo).ilike(f"%{valor}%"))

        periodo_inicial = _data_filtro(_texto(filtros.get("periodo_inicial")), "o período inicial")
        periodo_final = _data_filtro(_texto(filtros.get("periodo_final")), "o período final")
        if periodo_inicial:
            consulta = consulta.filter(OperacaoOrdemServico.data_programada_final >= periodo_inicial)
        if periodo_final:
            consulta = consulta.filter(OperacaoOrdemServico.data_programada_inicial <= periodo_final)

        total = consulta.count()
        total_paginas = max(1, (total + tamanho_pagina - 1) // tamanho_pagina)
        pagina = min(pagina, total_paginas)
        itens = (
            consulta.order_by(OperacaoOrdemServico.codigo_os_rental.desc())
            .offset((pagina - 1) * tamanho_pagina)
            .limit(tamanho_pagina)
            .all()
        )
        return ResultadoConsultaOrdensServico(itens, total, pagina, tamanho_pagina)
    except OrdemServicoConsultaErro:
        raise
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise OrdemServicoConsultaErro("Não foi possível consultar as Ordens de Serviço no momento.") from exc


def buscar_ordem_por_id(id_os_interno, usuario):
    _autorizar(usuario)
    try:
        identificador = str(uuid.UUID(str(id_os_interno)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise OrdemServicoConsultaErro("Identificador da Ordem de Serviço inválido.") from exc

    try:
        return db.session.query(OperacaoOrdemServico).filter(
            OperacaoOrdemServico.id_os_interno == identificador,
            OperacaoOrdemServico.ativo.is_(True),
        ).first()
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise OrdemServicoConsultaErro("Não foi possível consultar a Ordem de Serviço no momento.") from exc
