import threading
from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import text

from app.extensions import db
from app.models import FiscalControleNSU
from app.services.fiscal_service import consultar_documentos_sefaz, somente_digitos
from app.services.logs_service import registrar_log
from app.utils.datas import agora_brasil


CHAVE_TRAVA_POSTGRES = 8026664000131
_trava_local = threading.Lock()


def _proxima_execucao_automatica(controle, margem_minutos):
    if not controle or not controle.consultado_em:
        return None
    return controle.consultado_em + timedelta(hours=1, minutes=margem_minutos)


def executar_consulta_automatica_sefaz(cliente_cls=None, agora=None):
    from flask import current_app

    cnpj = somente_digitos(current_app.config.get("FISCAL_SEFAZ_CNPJ_AUTOMATICO", ""))
    if cnpj != "08026664000131":
        return False, "CNPJ automático não autorizado.", None

    controle = FiscalControleNSU.query.filter_by(cnpj_empresa=cnpj).first()
    margem = current_app.config.get("FISCAL_CONSULTA_AUTOMATICA_MARGEM_MINUTOS", 5)
    proxima_execucao = _proxima_execucao_automatica(controle, margem)
    if proxima_execucao and proxima_execucao > (agora or agora_brasil()):
        return False, "Consulta automática aguardando o horário de liberação.", controle

    sucesso, mensagem, controle = consultar_documentos_sefaz(cnpj, cliente_cls=cliente_cls)
    if controle:
        registrar_log(
            "fiscal_consulta_nsu_automatica",
            f"Consulta fiscal automática registrada. Controle NSU ID: {controle.id}. Resultado: {mensagem}",
        )
    return sucesso, mensagem, controle


@contextmanager
def _trava_consulta_automatica():
    if db.engine.dialect.name != "postgresql":
        adquiriu = _trava_local.acquire(blocking=False)
        try:
            yield adquiriu
        finally:
            if adquiriu:
                _trava_local.release()
        return

    adquiriu = bool(
        db.session.execute(
            text("SELECT pg_try_advisory_xact_lock(:chave)"),
            {"chave": CHAVE_TRAVA_POSTGRES},
        ).scalar()
    )
    try:
        yield adquiriu
    finally:
        db.session.rollback()


def _ciclo_consulta_automatica(app, parar):
    intervalo = max(30, app.config.get("FISCAL_CONSULTA_AUTOMATICA_INTERVALO_SEGUNDOS", 60))
    while not parar.wait(intervalo):
        with app.app_context():
            try:
                with _trava_consulta_automatica() as adquiriu:
                    if adquiriu:
                        executar_consulta_automatica_sefaz()
            except Exception:
                db.session.rollback()
                app.logger.exception("Falha no ciclo automático de consulta à Sefaz.")
            finally:
                db.session.remove()


def iniciar_consulta_automatica_sefaz(app):
    if not app.config.get("FISCAL_CONSULTA_AUTOMATICA_ENABLED", False):
        return None

    parar = threading.Event()
    thread = threading.Thread(
        target=_ciclo_consulta_automatica,
        args=(app, parar),
        name="consulta-sefaz-automatica",
        daemon=True,
    )
    thread.start()
    app.extensions["fiscal_consulta_automatica"] = {"thread": thread, "parar": parar}
    return thread
