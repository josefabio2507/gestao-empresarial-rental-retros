import logging
import sys
from contextlib import redirect_stdout
from io import StringIO


logger = logging.getLogger(__name__)


def executar_seeds_startup(app):
    executar_seed_modulos = app.config.get("AUTO_SEED_MODULES_ON_START")
    executar_seed_itens = app.config.get("AUTO_SEED_SUPRIMENTOS_ITENS_ON_START")

    if not executar_seed_modulos and not executar_seed_itens:
        return

    if "db" in sys.argv:
        return

    if executar_seed_modulos:
        try:
            with app.app_context():
                from app.seed_modulos_base_producao import executar_seed

                with redirect_stdout(StringIO()):
                    executar_seed()
            logger.info("Seeds de modulos base aplicados no startup.")
        except Exception:
            logger.exception("Falha ao aplicar seeds de modulos base no startup.")
            raise

    if executar_seed_itens:
        try:
            with app.app_context():
                from app.seed_suprimentos_itens_nota_fiscal import executar_seed

                with redirect_stdout(StringIO()):
                    executar_seed()
            logger.info("Seed de itens de nota fiscal aplicado no startup.")
        except Exception:
            logger.exception("Falha ao aplicar seed de itens de nota fiscal no startup.")
            raise
