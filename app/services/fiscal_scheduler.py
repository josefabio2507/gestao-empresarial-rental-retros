import threading
from datetime import timedelta

from app.extensions import db
from app.models import FiscalControleNSU
from app.services.fiscal_service import consultar_documentos_sefaz, somente_digitos
from app.services.logs_service import registrar_log
from app.utils.datas import agora_brasil


def _nsu_inteiro(valor):
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _proxima_execucao_automatica(controle, margem_minutos):
    if not controle or not controle.consultado_em:
        return None
    if controle.proxima_consulta_em:
        return controle.proxima_consulta_em
    if _nsu_inteiro(controle.ultimo_nsu) < _nsu_inteiro(controle.max_nsu):
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

    sucesso, mensagem, controle = consultar_documentos_sefaz(
        cnpj,
        cliente_cls=cliente_cls,
        origem="automatica",
    )
    if controle:
        registrar_log(
            "fiscal_consulta_nsu_automatica",
            f"Consulta fiscal automática registrada. Controle NSU ID: {controle.id}. Resultado: {mensagem}",
        )
    return sucesso, mensagem, controle


def _ciclo_consulta_automatica(app, parar):
    intervalo = max(30, app.config.get("FISCAL_CONSULTA_AUTOMATICA_INTERVALO_SEGUNDOS", 60))
    while not parar.wait(intervalo):
        with app.app_context():
            try:
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
