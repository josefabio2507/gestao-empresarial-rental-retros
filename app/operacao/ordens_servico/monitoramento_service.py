from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import (
    OperacaoApontamentoDiario,
    OperacaoCirculacaoTrem,
    OperacaoDiarioLocalizacao,
    OperacaoDiarioMaterial,
    OperacaoDiarioServico,
    OperacaoIntervencaoAdversa,
    OperacaoControleLiberacao,
)
from app.services.permissoes_service import usuario_tem_permissao


class MonitoramentoErro(Exception):
    pass


@dataclass(frozen=True)
class MonitoramentoOrdemServico:
    localizacoes: int
    servicos: int
    materiais: int
    circulacoes: int
    intervencoes: int
    total: int
    ultimo_apontamento: object
    ultimo_cadastro: object
    total_jornada: str
    total_intervalos: str
    total_controle_liberacao: str
    total_circulacao: str
    total_intervencao: str
    tempo_improdutivo: str
    percentual_tempo_produtivo: str

    @property
    def total_apontamentos(self):
        return self.total

    @property
    def possui_apontamentos(self):
        return self.total_apontamentos > 0

    @staticmethod
    def _segundos(valor):
        horas, minutos, segundos = (int(parte) for parte in valor.split(":"))
        return horas * 3600 + minutos * 60 + segundos

    @property
    def jornada_segundos(self):
        return self._segundos(self.total_jornada)

    @property
    def produtivo_segundos(self):
        return max(self.jornada_segundos - self._segundos(self.tempo_improdutivo), 0)

    @property
    def tempo_produtivo(self):
        segundos = self.produtivo_segundos
        return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}:{segundos % 60:02d}"

    @property
    def percentual_improdutivo(self):
        return max(100 - float(self.percentual_tempo_produtivo.replace(',', '.').replace('%', '')), 0)

    @property
    def grafico_tempos(self):
        total = self.jornada_segundos or 1
        itens = [
            ("produtivo", "Tempo produtivo", self.produtivo_segundos, "#ff575d"),
            ("controle", "Controles de liberação", self._segundos(self.total_controle_liberacao), "#ffb400"),
            ("circulacao", "Circulação de trens", self._segundos(self.total_circulacao), "#3989ed"),
            ("intervencao", "Intervenções adversas", self._segundos(self.total_intervencao), "#8052d6"),
        ]
        return [(chave, nome, duracao, round(duracao / total * 100, 2), cor) for chave, nome, duracao, cor in itens]


def _autorizar(usuario):
    if not usuario_tem_permissao(usuario, "operacao", "ordens_de_servico", "visualizar"):
        raise MonitoramentoErro("Você não possui permissão para consultar o monitoramento da Ordem de Serviço.")


def obter_monitoramento(id_os_interno, usuario):
    """Consolida apenas contagens e a última data; não carrega os apontamentos."""
    _autorizar(usuario)
    try:
        resultado = (
            db.session.query(
                func.count(OperacaoDiarioLocalizacao.id_apontamento_diario).label("localizacoes"),
                func.count(OperacaoDiarioServico.id_apontamento_diario).label("servicos"),
                func.count(OperacaoDiarioMaterial.id_apontamento_diario).label("materiais"),
                func.count(OperacaoCirculacaoTrem.id_apontamento_diario).label("circulacoes"),
                func.count(OperacaoIntervencaoAdversa.id_apontamento_diario).label("intervencoes"),
                func.count(OperacaoApontamentoDiario.id_apontamento_diario).label("total"),
                func.max(OperacaoApontamentoDiario.data_evento).label("ultimo_apontamento"),
                func.max(OperacaoApontamentoDiario.criado_em).label("ultimo_cadastro"),
            )
            .select_from(OperacaoApontamentoDiario)
            .outerjoin(OperacaoDiarioLocalizacao)
            .outerjoin(OperacaoDiarioServico)
            .outerjoin(OperacaoDiarioMaterial)
            .outerjoin(OperacaoCirculacaoTrem)
            .outerjoin(OperacaoIntervencaoAdversa)
            .filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno)
            .one()
        )
        jornadas = db.session.query(OperacaoDiarioLocalizacao).join(OperacaoApontamentoDiario).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno).all()
        segundos_jornada = 0
        segundos_intervalos = 0
        for jornada in jornadas:
            if jornada.hora_inicial and jornada.hora_final:
                inicio = jornada.hora_inicial.hour * 3600 + jornada.hora_inicial.minute * 60 + jornada.hora_inicial.second
                fim = jornada.hora_final.hour * 3600 + jornada.hora_final.minute * 60 + jornada.hora_final.second
                if fim < inicio:
                    fim += 86400
                intervalo = jornada.intervalo_jornada.hour * 3600 + jornada.intervalo_jornada.minute * 60 + jornada.intervalo_jornada.second if jornada.intervalo_jornada else 3600
                segundos_intervalos += intervalo
                segundos_jornada += max(fim - inicio - intervalo, 0)
        controles = OperacaoControleLiberacao.query.filter_by(id_os_interno=id_os_interno).all()
        segundos_controle = 0
        for controle in controles:
            if controle.pedido_liberacao_ccp and controle.termino_embandeiramento:
                inicio = controle.pedido_liberacao_ccp.hour * 3600 + controle.pedido_liberacao_ccp.minute * 60 + controle.pedido_liberacao_ccp.second
                fim = controle.termino_embandeiramento.hour * 3600 + controle.termino_embandeiramento.minute * 60 + controle.termino_embandeiramento.second
                if fim < inicio:
                    fim += 86400
                segundos_controle += fim - inicio
        circulacoes = OperacaoCirculacaoTrem.query.join(OperacaoApontamentoDiario).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno).all()
        segundos_circulacao = 0
        for circulacao in circulacoes:
            if circulacao.hora_inicio and circulacao.hora_fim:
                inicio = circulacao.hora_inicio.hour * 3600 + circulacao.hora_inicio.minute * 60 + circulacao.hora_inicio.second
                fim = circulacao.hora_fim.hour * 3600 + circulacao.hora_fim.minute * 60 + circulacao.hora_fim.second
                if fim < inicio:
                    fim += 86400
                segundos_circulacao += fim - inicio
        intervencoes = OperacaoIntervencaoAdversa.query.join(OperacaoApontamentoDiario).filter(OperacaoApontamentoDiario.id_os_interno == id_os_interno).all()
        segundos_intervencao = 0
        for intervencao in intervencoes:
            if intervencao.hora_inicio and intervencao.hora_fim:
                inicio = intervencao.hora_inicio.hour * 3600 + intervencao.hora_inicio.minute * 60 + intervencao.hora_inicio.second
                fim = intervencao.hora_fim.hour * 3600 + intervencao.hora_fim.minute * 60 + intervencao.hora_fim.second
                if fim < inicio:
                    fim += 86400
                segundos_intervencao += fim - inicio
        segundos_improdutivo = segundos_controle + segundos_circulacao + segundos_intervencao
        percentual_tempo_produtivo = (
            max(segundos_jornada - segundos_improdutivo, 0) / segundos_jornada * 100
            if segundos_jornada
            else 0
        )
        return MonitoramentoOrdemServico(
            localizacoes=resultado.localizacoes or 0,
            servicos=resultado.servicos or 0,
            materiais=resultado.materiais or 0,
            circulacoes=resultado.circulacoes or 0,
            intervencoes=resultado.intervencoes or 0,
            total=resultado.total or 0,
            ultimo_apontamento=resultado.ultimo_apontamento,
            ultimo_cadastro=resultado.ultimo_cadastro,
            total_jornada=f"{segundos_jornada // 3600:02d}:{(segundos_jornada % 3600) // 60:02d}:{segundos_jornada % 60:02d}",
            total_intervalos=f"{segundos_intervalos // 3600:02d}:{(segundos_intervalos % 3600) // 60:02d}:{segundos_intervalos % 60:02d}",
            total_controle_liberacao=f"{segundos_controle // 3600:02d}:{(segundos_controle % 3600) // 60:02d}:{segundos_controle % 60:02d}",
            total_circulacao=f"{segundos_circulacao // 3600:02d}:{(segundos_circulacao % 3600) // 60:02d}:{segundos_circulacao % 60:02d}",
            total_intervencao=f"{segundos_intervencao // 3600:02d}:{(segundos_intervencao % 3600) // 60:02d}:{segundos_intervencao % 60:02d}",
            tempo_improdutivo=f"{segundos_improdutivo // 3600:02d}:{(segundos_improdutivo % 3600) // 60:02d}:{segundos_improdutivo % 60:02d}",
            percentual_tempo_produtivo=f"{percentual_tempo_produtivo:.2f}%".replace(".", ","),
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise MonitoramentoErro("Não foi possível consolidar o monitoramento da Ordem de Serviço no momento.") from exc
