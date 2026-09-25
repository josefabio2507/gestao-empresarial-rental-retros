import unittest

from app import create_app
from app.departamento_pessoal.pedido_refeicoes.services import criar_pedido_refeicao
from app.extensions import db
from app.models import Equipe, Restaurante


class PedidoRefeicoesCriacaoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            WTF_CSRF_ENABLED=False,
            AUTO_MIGRATE_ON_START=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

        self.equipe = Equipe(nome="Operação", slug="operacao", ativo=True)
        self.restaurante = Restaurante(nome="Restaurante Teste", ativo=True)
        db.session.add_all([self.equipe, self.restaurante])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_cria_pedido_normalizando_ids_textuais_do_formulario(self):
        sucesso, mensagem, pedido = criar_pedido_refeicao(
            equipe_id=f" {self.equipe.id} ",
            restaurante_id=f" {self.restaurante.id} ",
            data_pedido="2026-09-25",
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self.equipe.id, pedido.equipe_id)
        self.assertEqual(self.restaurante.id, pedido.restaurante_id)


if __name__ == "__main__":
    unittest.main()
