import unittest

from app import create_app
from app.extensions import db
from app.models import Departamento, Modulo
from app.startup_seeds import executar_seeds_startup


class StartupSeedsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            AUTO_MIGRATE_ON_START=False,
            AUTO_SEED_MODULES_ON_START=False,
        )

        self.contexto = self.app.app_context()
        self.contexto.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_nao_executa_seed_quando_configuracao_desligada(self):
        executar_seeds_startup(self.app)

        self.assertIsNone(Departamento.query.filter_by(slug="suprimentos").first())

    def test_executa_seed_de_modulos_base_quando_configuracao_ligada(self):
        self.app.config["AUTO_SEED_MODULES_ON_START"] = True

        executar_seeds_startup(self.app)

        departamento = Departamento.query.filter_by(slug="suprimentos").first()
        self.assertIsNotNone(departamento)
        self.assertTrue(departamento.ativo)

        modulo = Modulo.query.filter_by(
            departamento_id=departamento.id,
            slug="cotacoes",
        ).first()
        self.assertIsNotNone(modulo)
        self.assertTrue(modulo.ativo)


if __name__ == "__main__":
    unittest.main()
