import logging
import sys

from flask_migrate import upgrade


logger = logging.getLogger(__name__)


def executar_migrations_startup(app):
    if not app.config.get("AUTO_MIGRATE_ON_START"):
        return

    if "db" in sys.argv:
        return

    try:
        with app.app_context():
            upgrade(directory="migrations", revision="head")
        logger.info("Migrations aplicadas no startup.")
    except Exception:
        logger.exception("Falha ao aplicar migrations no startup.")
        raise
