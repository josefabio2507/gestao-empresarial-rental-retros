import threading
from datetime import date, timedelta

from app.extensions import db
from app.models import FeriasColaborador
from app.services.logs_service import registrar_log


def contar_alertas_prazo():
    hoje = date.today()
    limite = hoje + timedelta(days=90)
    registros = FeriasColaborador.query.filter(
        FeriasColaborador.status.notin_(["concluida", "cancelada"])
    ).all()
    vencidos = 0
    proximos = 0
    for registro in registros:
        prazo = registro.periodo_aquisitivo_fim + timedelta(days=365)
        if prazo < hoje:
            vencidos += 1
        elif prazo <= limite:
            proximos += 1
    return vencidos, proximos


def verificar_alertas_ferias():
    vencidos, proximos = contar_alertas_prazo()
    total = vencidos + proximos
    if total:
        registrar_log("ferias_alertas_prazo", f"Verifica��o autom�tica: {vencidos} vencido(s) e {proximos} pr�ximo(s) do vencimento.")
    return vencidos, proximos


def _ciclo(app, parar):
    intervalo = max(300, app.config.get("FERIAS_ALERTAS_INTERVALO_SEGUNDOS", 86400))
    while not parar.wait(intervalo):
        with app.app_context():
            try:
                verificar_alertas_ferias()
            except Exception:
                db.session.rollback()
                app.logger.exception("Falha na verifica��o autom�tica de alertas de f�rias.")
            finally:
                db.session.remove()


def iniciar_verificacao_automatica_ferias(app):
    if not app.config.get("FERIAS_ALERTAS_AUTOMATICOS_ENABLED", False):
        return None
    parar = threading.Event()
    thread = threading.Thread(target=_ciclo, args=(app, parar), name="ferias-alertas-automaticos", daemon=True)
    thread.start()
    app.extensions["ferias_alertas_automaticos"] = {"thread": thread, "parar": parar}
    return thread
