import logging
import sys
from contextlib import redirect_stdout
from io import StringIO


logger = logging.getLogger(__name__)


def executar_seeds_startup(app):
    if not app.config.get("AUTO_SEED_MODULES_ON_START"):
        return

    if "db" in sys.argv:
        return

    try:
        with app.app_context():
            from app.seed_modulos_base_producao import executar_seed

            with redirect_stdout(StringIO()):
                executar_seed()
        logger.info("Seeds de modulos base aplicados no startup.")
    except Exception:
        logger.exception("Falha ao aplicar seeds de modulos base no startup.")
        raise
