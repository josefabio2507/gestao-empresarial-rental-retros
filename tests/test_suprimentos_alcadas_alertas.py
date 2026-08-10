import unittest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    Modulo,
    NivelAcesso,
    SuprimentosAlcadaAprovacao,
    SuprimentosAlerta,
    Usuario,
)
from app.services.suprimentos_service import (
    buscar_alertas_usuario,
    marcar_alerta_como_lido,
    salvar_alcada_aprovacao,
)


class SuprimentosAlcadasAlertasTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )

        self.contexto = self.app.app_context()
        self.contexto.push()
        db.drop_all()
        db.create_all()

        admin = NivelAcesso(nome="Administrador", slug="administrador", ativo=True)
        db.session.add(admin)
        db.session.flush()

        self.admin = Usuario(
            nome="Admin",
            email="admin@teste.com",
            nivel_acesso=admin,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.admin.definir_senha("teste")
        db.session.add(self.admin)

        departamento = Departamento(nome="Suprimentos", slug="suprimentos", ativo=True, ordem=2)
        db.session.add(departamento)
        db.session.flush()

        db.session.add_all(
            [
                Modulo(
                    departamento_id=departamento.id,
                    nome="Alcadas de Aprovacao",
                    slug="alcadas_aprovacao",
                    ativo=True,
                    ordem=12,
                ),
                Modulo(
                    departamento_id=departamento.id,
                    nome="Alertas",
                    slug="alertas",
                    ativo=True,
                    ordem=13,
                ),
            ]
        )
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _autenticar(self, usuario):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True

    def test_salva_alcada_de_aprovacao(self):
        sucesso, mensagem, alcada = salvar_alcada_aprovacao(
            {
                "usuario_aprovador_id": str(self.admin.id),
                "valor_minimo": "0,00",
                "valor_maximo": "1000,00",
                "telefone_whatsapp": "(13) 99999-0001",
                "ativo": "on",
                "observacoes": "aprovacao inicial",
            }
        )

        self.assertTrue(sucesso)
        self.assertEqual("Alcada de aprovacao salva com sucesso.", mensagem)
        self.assertEqual(self.admin.id, alcada.usuario_aprovador_id)
        self.assertEqual(Decimal("1000.00"), alcada.valor_maximo)
        self.assertEqual("5513999990001", alcada.telefone_whatsapp)
        self.assertEqual("APROVACAO INICIAL", alcada.observacoes)

    def test_rota_lista_alcadas_para_admin(self):
        db.session.add(
            SuprimentosAlcadaAprovacao(
                usuario_aprovador_id=self.admin.id,
                valor_minimo=Decimal("0.00"),
                valor_maximo=None,
                ativo=True,
            )
        )
        db.session.commit()
        self._autenticar(self.admin)

        resposta = self.client.get("/suprimentos/alcadas-aprovacao/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Alcadas de Aprovacao", resposta.data)
        self.assertIn(b"Admin", resposta.data)

    def test_alerta_usuario_pode_ser_lido(self):
        alerta = SuprimentosAlerta(
            usuario_destinatario_id=self.admin.id,
            tipo="Aprovacao",
            titulo="Cotacao aguardando aprovacao",
            mensagem="Existe uma cotacao aguardando aprovacao.",
            link_destino="/suprimentos/cotacoes/",
        )
        db.session.add(alerta)
        db.session.commit()

        self.assertEqual(1, len(buscar_alertas_usuario(self.admin, "Nao lido")))

        sucesso, mensagem = marcar_alerta_como_lido(alerta, self.admin)

        self.assertTrue(sucesso)
        self.assertEqual("Alerta marcado como lido.", mensagem)
        self.assertEqual("Lido", alerta.status)
        self.assertIsNotNone(alerta.lido_em)


if __name__ == "__main__":
    unittest.main()
