import io
import unittest
from datetime import date
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FinanceiroContaPagarBaixa,
    FinanceiroContaPagarTitulo,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
)
from app.services.financeiro_contas_pagar_service import (
    calcular_saldo_titulo,
    cancelar_baixa_titulo,
    registrar_baixa_titulo,
)


class FinanceiroBaixasPagamentosTestCase(unittest.TestCase):
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

        nivel = NivelAcesso(nome="Usuario", slug="usuario", ativo=True)
        db.session.add(nivel)
        db.session.flush()
        self.usuario = Usuario(nome="Financeiro", email="financeiro@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False)
        self.usuario.definir_senha("teste")
        self.departamento = Departamento(nome="Financeiro", slug="financeiro", descricao="Teste", ativo=True, ordem=1)
        db.session.add_all([self.usuario, self.departamento])
        db.session.flush()
        self.modulo = Modulo(departamento_id=self.departamento.id, nome="Contas a Pagar", slug="contas_a_pagar", ativo=True, ordem=1)
        self.fornecedor = SuprimentosFornecedor(
            razao_social="FORNECEDOR BAIXA TESTE LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="11222333000181",
            ativo=True,
        )
        db.session.add_all([self.modulo, self.fornecedor])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _titulo(self, valor="1000.00", status="Agendado"):
        titulo = FinanceiroContaPagarTitulo(
            fornecedor_id=self.fornecedor.id,
            fornecedor_nome_snapshot=self.fornecedor.razao_social,
            fornecedor_cnpj_cpf_snapshot=self.fornecedor.cnpj_cpf,
            descricao="TITULO TESTE BAIXA",
            numero_documento="BAIXA-001",
            origem_lancamento="Manual",
            tipo_pagamento="Faturado",
            forma_pagamento="Pix",
            data_emissao=date(2026, 8, 1),
            data_vencimento=date(2026, 8, 20),
            competencia=date(2026, 8, 1),
            valor_original=Decimal(valor),
            valor_desconto=Decimal("0.00"),
            valor_acrescimo=Decimal("0.00"),
            valor_juros_multa=Decimal("0.00"),
            valor_pago=Decimal("0.00"),
            status=status,
            parcela_numero=1,
            total_parcelas=1,
        )
        db.session.add(titulo)
        db.session.commit()
        return titulo

    def _dados_baixa(self, valor="500,00"):
        return {
            "data_pagamento": "2026-08-25",
            "valor_pago": valor,
            "forma_pagamento": "Pix",
            "conta_pagamento_descricao": "Banco teste",
            "observacoes": "Pagamento teste",
        }

    def _autenticar(self):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id)
            sessao["_fresh"] = True

    def _liberar(self, **acoes):
        permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=self.modulo.id,
            pode_visualizar=acoes.get("visualizar", False),
            pode_criar=acoes.get("criar", False),
            pode_editar=acoes.get("editar", False),
            pode_excluir=acoes.get("excluir", False),
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def test_registra_baixa_parcial_e_recalcula_saldo(self):
        titulo = self._titulo()
        sucesso, mensagem, baixa = registrar_baixa_titulo(titulo, self._dados_baixa("400,00"), usuario=self.usuario)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(baixa.status, "Ativa")
        self.assertEqual(titulo.status, "Pago parcialmente")
        self.assertEqual(titulo.valor_pago, Decimal("400.00"))
        self.assertEqual(calcular_saldo_titulo(titulo), Decimal("600.00"))

    def test_registra_baixa_total_e_marca_pago(self):
        titulo = self._titulo()
        sucesso, mensagem, _ = registrar_baixa_titulo(titulo, self._dados_baixa("1000,00"), usuario=self.usuario)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(titulo.status, "Pago")
        self.assertEqual(titulo.valor_pago, Decimal("1000.00"))
        self.assertEqual(calcular_saldo_titulo(titulo), Decimal("0.00"))

    def test_bloqueia_baixa_acima_do_saldo(self):
        titulo = self._titulo()
        sucesso, mensagem, baixa = registrar_baixa_titulo(titulo, self._dados_baixa("1000,01"), usuario=self.usuario)

        self.assertFalse(sucesso)
        self.assertIsNone(baixa)
        self.assertIn("excede o saldo", mensagem)

    def test_bloqueia_baixa_em_titulo_cancelado(self):
        titulo = self._titulo(status="Cancelado")
        sucesso, mensagem, baixa = registrar_baixa_titulo(titulo, self._dados_baixa("100,00"), usuario=self.usuario)

        self.assertFalse(sucesso)
        self.assertIsNone(baixa)
        self.assertIn("cancelado", mensagem.lower())

    def test_estorna_baixa_sem_apagar_historico(self):
        titulo = self._titulo()
        sucesso, _, baixa = registrar_baixa_titulo(titulo, self._dados_baixa("250,00"), usuario=self.usuario)
        self.assertTrue(sucesso)

        sucesso, mensagem = cancelar_baixa_titulo(baixa, "Pagamento duplicado", usuario=self.usuario)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(baixa.status, "Estornada")
        self.assertEqual(titulo.valor_pago, Decimal("0.00"))
        self.assertEqual(calcular_saldo_titulo(titulo), Decimal("1000.00"))
        self.assertEqual(FinanceiroContaPagarBaixa.query.count(), 1)

    def test_upload_e_download_comprovante_com_permissao(self):
        titulo = self._titulo()
        self._liberar(visualizar=True, editar=True)
        self._autenticar()

        resposta = self.client.post(
            f"/financeiro/contas-a-pagar/{titulo.id}/pagamentos/novo",
            data={
                **self._dados_baixa("120,00"),
                "comprovante": (io.BytesIO(b"comprovante teste"), "comprovante.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        self.assertEqual(resposta.status_code, 302)
        baixa = FinanceiroContaPagarBaixa.query.filter_by(titulo_id=titulo.id).first()
        self.assertTrue(baixa.comprovante_disponivel)
        download = self.client.get(f"/financeiro/contas-a-pagar/baixas/{baixa.id}/comprovante")
        self.assertEqual(download.status_code, 200)

    def test_rota_registrar_pagamento_bloqueia_sem_permissao(self):
        titulo = self._titulo()
        self._autenticar()

        resposta = self.client.get(f"/financeiro/contas-a-pagar/{titulo.id}/pagamentos/novo")

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/acesso-negado", resposta.headers["Location"])


if __name__ == "__main__":
    unittest.main()
