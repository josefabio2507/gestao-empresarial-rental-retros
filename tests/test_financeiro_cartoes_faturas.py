import unittest

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FinanceiroCartaoCredito,
    FinanceiroCartaoFatura,
    FinanceiroContaPagarTitulo,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
)
from app.services.financeiro_contas_pagar_service import (
    calcular_ciclo_fatura,
    salvar_cartao,
    salvar_titulo,
)


class FinanceiroCartoesFaturasTestCase(unittest.TestCase):
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
        comum = NivelAcesso(nome="Usuario", slug="usuario", ativo=True)
        db.session.add_all([admin, comum])
        db.session.flush()

        self.admin = Usuario(
            nome="Admin",
            email="admin.cartoes@teste.com",
            nivel_acesso=admin,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario = Usuario(
            nome="Comum",
            email="comum.cartoes@teste.com",
            nivel_acesso=comum,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])

        self.departamento = Departamento(
            nome="Financeiro",
            slug="financeiro",
            descricao="Teste",
            ativo=True,
            ordem=1,
        )
        db.session.add(self.departamento)
        db.session.flush()

        self.modulo = Modulo(
            departamento_id=self.departamento.id,
            nome="Contas a Pagar",
            slug="contas_a_pagar",
            ativo=True,
            ordem=1,
        )
        db.session.add(self.modulo)

        self.fornecedor = SuprimentosFornecedor(
            razao_social="FORNECEDOR CARTAO LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="11222333000181",
            ativo=True,
        )
        db.session.add(self.fornecedor)
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

    def _dados_cartao(self, **extra):
        dados = {
            "nome": "Cartao Administrativo",
            "banco": "Banco Teste",
            "bandeira": "Visa",
            "ultimos_4_digitos": "1234",
            "titular_responsavel": "Financeiro",
            "dia_fechamento": "20",
            "dia_vencimento": "28",
            "limite": "10000,00",
            "ativo": "on",
            "observacoes": "Teste",
        }
        dados.update(extra)
        return dados

    def _criar_cartao(self):
        sucesso, mensagem, cartao = salvar_cartao(self._dados_cartao(), usuario=self.admin)
        self.assertTrue(sucesso, mensagem)
        return cartao

    def _dados_titulo_cartao(self, cartao, **extra):
        dados = {
            "fornecedor_id": str(self.fornecedor.id),
            "fornecedor_nome_snapshot": "",
            "fornecedor_cnpj_cpf_snapshot": "",
            "descricao": "Compra no cartao",
            "numero_documento": "CARD-001",
            "data_emissao": "2026-09-15",
            "data_compra_cartao": "2026-09-15",
            "data_vencimento": "2026-10-15",
            "competencia": "2026-09",
            "valor_original": "150,00",
            "valor_desconto": "0,00",
            "valor_acrescimo": "0,00",
            "valor_juros_multa": "0,00",
            "valor_pago": "0,00",
            "origem_lancamento": "Manual",
            "tipo_pagamento": "Cartao de Credito",
            "forma_pagamento": "Cartao de Credito",
            "cartao_credito_id": str(cartao.id),
            "parcela_numero": "1",
            "total_parcelas": "1",
            "status": "Agendado",
        }
        dados.update(extra)
        return dados

    def test_cria_edita_inativa_e_reativa_cartao(self):
        self._autenticar(self.admin)

        resposta = self.client.post(
            "/financeiro/contas-a-pagar/cartoes/novo",
            data=self._dados_cartao(),
            follow_redirects=True,
        )
        cartao = FinanceiroCartaoCredito.query.one()

        self.assertEqual(200, resposta.status_code)
        self.assertEqual("CARTAO ADMINISTRATIVO", cartao.nome)
        self.assertEqual("1234", cartao.ultimos_4_digitos)

        editar = self.client.post(
            f"/financeiro/contas-a-pagar/cartoes/{cartao.id}/editar",
            data=self._dados_cartao(nome="Cartao Diretoria"),
            follow_redirects=True,
        )
        db.session.refresh(cartao)
        self.assertEqual(200, editar.status_code)
        self.assertEqual("CARTAO DIRETORIA", cartao.nome)

        inativar = self.client.post(
            f"/financeiro/contas-a-pagar/cartoes/{cartao.id}/status",
            data={"ativo": "0"},
            follow_redirects=True,
        )
        db.session.refresh(cartao)
        self.assertEqual(200, inativar.status_code)
        self.assertFalse(cartao.ativo)

        reativar = self.client.post(
            f"/financeiro/contas-a-pagar/cartoes/{cartao.id}/status",
            data={"ativo": "1"},
            follow_redirects=True,
        )
        db.session.refresh(cartao)
        self.assertEqual(200, reativar.status_code)
        self.assertTrue(cartao.ativo)

    def test_calcula_ciclo_da_fatura_pelo_fechamento(self):
        cartao = self._criar_cartao()

        competencia, fechamento, vencimento = calcular_ciclo_fatura(
            cartao,
            __import__("datetime").date(2026, 9, 15),
        )
        self.assertEqual("2026-09-01", competencia.isoformat())
        self.assertEqual("2026-09-20", fechamento.isoformat())
        self.assertEqual("2026-09-28", vencimento.isoformat())

        competencia, fechamento, vencimento = calcular_ciclo_fatura(
            cartao,
            __import__("datetime").date(2026, 9, 25),
        )
        self.assertEqual("2026-10-01", competencia.isoformat())
        self.assertEqual("2026-10-20", fechamento.isoformat())
        self.assertEqual("2026-10-28", vencimento.isoformat())

    def test_titulo_cartao_cria_reutiliza_fatura_e_recalcula_total(self):
        cartao = self._criar_cartao()

        sucesso, mensagem, primeiro = salvar_titulo(self._dados_titulo_cartao(cartao), usuario=self.admin)
        self.assertTrue(sucesso, mensagem)
        self.assertIsNotNone(primeiro.fatura_cartao_id)
        self.assertEqual("2026-09-01", primeiro.competencia_fatura_cartao.isoformat())

        sucesso, mensagem, segundo = salvar_titulo(
            self._dados_titulo_cartao(cartao, numero_documento="CARD-002", valor_original="50,00"),
            usuario=self.admin,
        )
        self.assertTrue(sucesso, mensagem)
        self.assertEqual(primeiro.fatura_cartao_id, segundo.fatura_cartao_id)

        fatura = FinanceiroCartaoFatura.query.one()
        self.assertEqual(200, int(fatura.valor_total))

        primeiro.status = "Cancelado"
        db.session.flush()
        sucesso, mensagem, _ = salvar_titulo(
            self._dados_titulo_cartao(cartao, numero_documento="CARD-001", status="Cancelado"),
            titulo=primeiro,
            usuario=self.admin,
        )
        self.assertTrue(sucesso, mensagem)
        db.session.refresh(fatura)
        self.assertEqual(50, int(fatura.valor_total))

    def test_telas_de_cartoes_faturas_e_permissao(self):
        self._liberar(visualizar=True)
        self._autenticar(self.usuario)

        self.assertEqual(200, self.client.get("/financeiro/contas-a-pagar/cartoes").status_code)
        self.assertEqual(200, self.client.get("/financeiro/contas-a-pagar/faturas").status_code)
        novo_cartao = self.client.get("/financeiro/contas-a-pagar/cartoes/novo")
        self.assertEqual(302, novo_cartao.status_code)
        self.assertIn("/acesso-negado", novo_cartao.headers["Location"])

    def test_cartao_inativo_nao_aparece_em_novo_lancamento(self):
        cartao = self._criar_cartao()
        cartao.ativo = False
        db.session.commit()
        self._autenticar(self.admin)

        resposta = self.client.get("/financeiro/contas-a-pagar/novo")

        self.assertEqual(200, resposta.status_code)
        self.assertNotIn(b"CARTAO ADMINISTRATIVO", resposta.data)


if __name__ == "__main__":
    unittest.main()
