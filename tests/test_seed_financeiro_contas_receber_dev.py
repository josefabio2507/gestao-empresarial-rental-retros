import os
import unittest

from app import create_app
from app.extensions import db
from app.models import (
    FinanceiroContaReceberBaixa,
    FinanceiroContaReceberTitulo,
    FinanceiroContratoCliente,
    FinanceiroContratoMedicao,
    FinanceiroNotaFiscalEmitida,
    Modulo,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.seed_financeiro_contas_receber_dev import USUARIO_DEMO_EMAIL, executar_seed


class SeedFinanceiroContasReceberDevTestCase(unittest.TestCase):
    def setUp(self):
        self.env_backup = {
            "ALLOW_DEV_SEED": os.environ.get("ALLOW_DEV_SEED"),
            "APP_ENV": os.environ.get("APP_ENV"),
        }
        os.environ["ALLOW_DEV_SEED"] = "1"
        os.environ["APP_ENV"] = "local"

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
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()
        for chave, valor in self.env_backup.items():
            if valor is None:
                os.environ.pop(chave, None)
            else:
                os.environ[chave] = valor

    def _autenticar_demo(self):
        usuario = Usuario.query.filter_by(email=USUARIO_DEMO_EMAIL).one()
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True
        return usuario

    def test_seed_cria_dados_ficticios_idempotentes_para_missoes_18(self):
        self.assertTrue(executar_seed(self.app))

        total_titulos = FinanceiroContaReceberTitulo.query.count()
        total_baixas = FinanceiroContaReceberBaixa.query.count()
        self.assertGreaterEqual(total_titulos, 15)
        self.assertGreaterEqual(total_baixas, 4)
        self.assertIsNotNone(FinanceiroContaReceberTitulo.query.filter_by(numero_documento="CR-TESTE-0015").first())
        self.assertGreaterEqual(FinanceiroNotaFiscalEmitida.query.filter(FinanceiroNotaFiscalEmitida.numero_nota.like("%TESTE%")).count(), 6)
        self.assertIsNotNone(FinanceiroNotaFiscalEmitida.query.filter_by(numero_nota="NFSE-TESTE-1005", status_financeiro="Título gerado").first())
        self.assertIsNotNone(FinanceiroContaReceberTitulo.query.filter_by(numero_documento="CR-TESTE-0001", status="Recebido").first())
        self.assertGreaterEqual(FinanceiroContratoCliente.query.filter(FinanceiroContratoCliente.numero_contrato.like("CTR-TESTE-CR-%")).count(), 4)
        self.assertGreaterEqual(FinanceiroContratoMedicao.query.filter(FinanceiroContratoMedicao.numero_medicao.like("MED-TESTE-CR-%")).count(), 5)
        self.assertIsNotNone(FinanceiroContratoMedicao.query.filter_by(numero_medicao="MED-TESTE-CR-004", status_financeiro="Título gerado").first())
        self.assertIsNotNone(FinanceiroContratoMedicao.query.filter_by(numero_medicao="MED-TESTE-CR-005", status_medicao="Cancelada").first())
        self.assertGreater(FinanceiroContaReceberBaixa.query.filter_by(status="Ativa").count(), 0)
        self.assertGreater(FinanceiroContaReceberBaixa.query.filter_by(status="Estornada").count(), 0)
        self.assertGreater(
            FinanceiroContaReceberBaixa.query.filter(FinanceiroContaReceberBaixa.comprovante_path.isnot(None)).count(),
            0,
        )

        executar_seed(self.app)
        total_notas = FinanceiroNotaFiscalEmitida.query.count()
        total_contratos = FinanceiroContratoCliente.query.count()
        total_medicoes = FinanceiroContratoMedicao.query.count()
        self.assertEqual(total_titulos, FinanceiroContaReceberTitulo.query.count())
        self.assertEqual(total_baixas, FinanceiroContaReceberBaixa.query.count())
        self.assertEqual(total_notas, FinanceiroNotaFiscalEmitida.query.count())
        self.assertEqual(total_contratos, FinanceiroContratoCliente.query.count())
        self.assertEqual(total_medicoes, FinanceiroContratoMedicao.query.count())

    def test_seed_demo_preserva_listboxs_e_tooltips_do_contas_a_receber(self):
        executar_seed(self.app)
        usuario = self._autenticar_demo()
        modulo = Modulo.query.filter_by(slug="contas_a_receber").one()
        permissao = PermissaoUsuarioModulo.query.filter_by(usuario_id=usuario.id, modulo_id=modulo.id).one()
        self.assertTrue(permissao.pode_visualizar)
        self.assertTrue(permissao.pode_criar)
        self.assertTrue(permissao.pode_editar)
        self.assertTrue(permissao.pode_excluir)

        dashboard = self.client.get("/financeiro/contas-a-receber/dashboard")
        self.assertEqual(200, dashboard.status_code)
        self.assertIn(b"listbox-10-linhas", dashboard.data)
        self.assertIn("Soma dos recebimentos ativos registrados dentro do mês selecionado.".encode(), dashboard.data)
        self.assertIn("Soma dos títulos com vencimento dentro do mês selecionado".encode(), dashboard.data)
        self.assertIn("Contratos ativos".encode("utf-8"), dashboard.data)
        self.assertIn("Medições pendentes".encode("utf-8"), dashboard.data)

        titulos = self.client.get("/financeiro/contas-a-receber/titulos")
        self.assertEqual(200, titulos.status_code)
        self.assertIn(b"listbox-10-linhas", titulos.data)
        self.assertIn(b"CR-TESTE-0015", titulos.data)
        self.assertIn(b"Receber", titulos.data)

        titulo_com_baixa = FinanceiroContaReceberTitulo.query.filter_by(numero_documento="CR-TESTE-0011").one()
        detalhe = self.client.get(f"/financeiro/contas-a-receber/{titulo_com_baixa.id}")
        self.assertEqual(200, detalhe.status_code)
        self.assertIn(b"Recebimentos / Baixas", detalhe.data)
        self.assertIn(b"listbox-10-linhas", detalhe.data)
        self.assertIn(b"Baixar", detalhe.data)



        contratos = self.client.get("/financeiro/contas-a-receber/contratos")
        self.assertEqual(200, contratos.status_code)
        self.assertIn(b"listbox-10-linhas", contratos.data)
        self.assertIn(b"CTR-TESTE-CR-001", contratos.data)

        medicoes = self.client.get("/financeiro/contas-a-receber/medicoes")
        self.assertEqual(200, medicoes.status_code)
        self.assertIn(b"listbox-10-linhas", medicoes.data)
        self.assertIn(b"MED-TESTE-CR-001", medicoes.data)

        sem_comprovante = self.client.get("/financeiro/contas-a-receber/titulos?comprovante=sem")
        self.assertEqual(200, sem_comprovante.status_code)
        self.assertIn(b"listbox-10-linhas", sem_comprovante.data)
        self.assertIn(b"CR-TESTE-0014", sem_comprovante.data)


if __name__ == "__main__":
    unittest.main()
