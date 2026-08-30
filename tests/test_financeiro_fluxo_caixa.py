import os
import unittest
from datetime import date, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Equipe,
    FinanceiroContaPagarBaixa,
    FinanceiroContaPagarLoteBaixa,
    FinanceiroContaPagarTitulo,
    FinanceiroContaReceberBaixa,
    FinanceiroContaReceberLoteBaixa,
    FinanceiroContaReceberTitulo,
    LogAcesso,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
)
from app.services.financeiro_fluxo_caixa_service import (
    dashboard_fluxo_caixa,
    filtros_padrao_fluxo,
    movimentos_fluxo_caixa,
    visao_fluxo_caixa,
)


class FinanceiroFluxoCaixaTestCase(unittest.TestCase):
    def setUp(self):
        self.database_url_anterior = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        self.app = create_app()
        self.app.config.update(SECRET_KEY="test", TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", SQLALCHEMY_TRACK_MODIFICATIONS=False)
        self.contexto = self.app.app_context()
        self.contexto.push()
        self.test_tables = [
            NivelAcesso.__table__, Departamento.__table__, Modulo.__table__, Usuario.__table__, PermissaoUsuarioModulo.__table__, LogAcesso.__table__,
            CentroCusto.__table__, Equipe.__table__, SuprimentosFornecedor.__table__, FinanceiroContaReceberTitulo.__table__, FinanceiroContaReceberLoteBaixa.__table__, FinanceiroContaReceberBaixa.__table__,
            FinanceiroContaPagarTitulo.__table__, FinanceiroContaPagarLoteBaixa.__table__, FinanceiroContaPagarBaixa.__table__,
        ]
        db.metadata.create_all(db.engine, tables=self.test_tables)
        nivel = NivelAcesso(nome="Usuario", slug="usuario", ativo=True)
        dep = Departamento(nome="Financeiro", slug="financeiro", ativo=True, ordem=1)
        db.session.add_all([nivel, dep])
        db.session.flush()
        self.modulo = Modulo(departamento_id=dep.id, nome="Fluxo de Caixa", slug="fluxo_de_caixa", ativo=True, ordem=3)
        self.usuario = Usuario(nome="Fluxo", email="fluxo@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False)
        self.usuario.definir_senha("teste")
        self.centro = CentroCusto(codigo="FLX", nome="Fluxo", ativo=True)
        self.fornecedor = SuprimentosFornecedor(razao_social="Fornecedor Fluxo", tipo_pessoa="juridica", cnpj_cpf="11111111000111", ativo=True)
        db.session.add_all([self.modulo, self.usuario, self.centro, self.fornecedor])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.metadata.drop_all(db.engine, tables=list(reversed(self.test_tables)))
        self.contexto.pop()
        if self.database_url_anterior is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.database_url_anterior

    def _autenticar(self):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id)
            sessao["_fresh"] = True

    def _liberar(self, exportar=False):
        permissao = PermissaoUsuarioModulo(usuario_id=self.usuario.id, modulo_id=self.modulo.id, pode_visualizar=True, pode_exportar=exportar, ativo=True)
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def _titulo_receber(self, documento, valor="100.00", recebido="0.00", status="Agendado", vencimento=None):
        titulo = FinanceiroContaReceberTitulo(
            cliente_nome_snapshot="Cliente Fluxo", cliente_cnpj_cpf_snapshot="22222222000122", descricao=documento, numero_documento=documento,
            origem_lancamento="Manual", competencia="2026-08", data_emissao=date.today(), data_vencimento=vencimento or date.today(),
            valor_original=Decimal(valor), valor_desconto=Decimal("0.00"), valor_acrescimo=Decimal("0.00"), valor_juros_multa=Decimal("0.00"), valor_recebido=Decimal(recebido),
            parcela_numero=1, total_parcelas=1, centro_custo_id=self.centro.id, status=status,
        )
        db.session.add(titulo)
        db.session.commit()
        return titulo

    def _baixa_receber(self, titulo, valor="50.00"):
        baixa = FinanceiroContaReceberBaixa(titulo_id=titulo.id, data_recebimento=date.today(), valor_recebido=Decimal(valor), forma_recebimento="Pix", status="Ativa")
        db.session.add(baixa)
        db.session.commit()
        return baixa

    def _titulo_pagar(self, documento, valor="100.00", pago="0.00", status="Agendado", vencimento=None):
        titulo = FinanceiroContaPagarTitulo(
            fornecedor_id=self.fornecedor.id, fornecedor_nome_snapshot=self.fornecedor.razao_social, fornecedor_cnpj_cpf_snapshot=self.fornecedor.cnpj_cpf,
            descricao=documento, numero_documento=documento, origem_lancamento="Manual", tipo_pagamento="Faturado", forma_pagamento="Pix", competencia=date.today().replace(day=1),
            data_emissao=date.today(), data_vencimento=vencimento or date.today(), valor_original=Decimal(valor), valor_desconto=Decimal("0.00"), valor_acrescimo=Decimal("0.00"), valor_juros_multa=Decimal("0.00"),
            valor_pago=Decimal(pago), parcela_numero=1, total_parcelas=1, centro_custo_id=self.centro.id, status=status,
        )
        db.session.add(titulo)
        db.session.commit()
        return titulo

    def _baixa_pagar(self, titulo, valor="40.00"):
        baixa = FinanceiroContaPagarBaixa(titulo_id=titulo.id, data_pagamento=date.today(), valor_pago=Decimal(valor), forma_pagamento="Pix", status="Ativa")
        db.session.add(baixa)
        db.session.commit()
        return baixa

    def test_movimentos_consolidam_previsto_realizado_e_parciais(self):
        cr_parcial = self._titulo_receber("CR-FLX-1", valor="150.00", recebido="50.00", status="Recebido parcialmente", vencimento=date.today() + timedelta(days=2))
        cp_parcial = self._titulo_pagar("CP-FLX-1", valor="100.00", pago="30.00", status="Pago parcialmente", vencimento=date.today() + timedelta(days=2))
        self._baixa_receber(cr_parcial, "50.00")
        self._baixa_pagar(cp_parcial, "30.00")
        movimentos = movimentos_fluxo_caixa(filtros_padrao_fluxo({"sem_periodo": "1"}))
        self.assertEqual(sum(m["valor_previsto"] for m in movimentos if m["tipo"] == "Entrada" and m["natureza"] == "Previsto"), Decimal("100.00"))
        self.assertEqual(sum(m["valor_realizado"] for m in movimentos if m["tipo"] == "Entrada" and m["natureza"] == "Realizado"), Decimal("50.00"))
        self.assertEqual(sum(m["valor_previsto"] for m in movimentos if m["tipo"] == "Saída" and m["natureza"] == "Previsto"), Decimal("70.00"))
        self.assertEqual(sum(m["valor_realizado"] for m in movimentos if m["tipo"] == "Saída" and m["natureza"] == "Realizado"), Decimal("30.00"))
        self.assertTrue(all(m["status"] != "Cancelado" for m in movimentos))

    def test_dashboard_e_visoes_calculam_saldos(self):
        self._titulo_receber("CR-FLX-2", valor="200.00", vencimento=date.today())
        self._titulo_pagar("CP-FLX-2", valor="80.00", vencimento=date.today())
        filtros = filtros_padrao_fluxo({"sem_periodo": "1"})
        dados = dashboard_fluxo_caixa(filtros)
        self.assertEqual(dados["cards"]["saldo_previsto"], Decimal("120.00"))
        self.assertTrue(dados["tabelas"]["resumo_mes"])
        self.assertTrue(visao_fluxo_caixa("dia", filtros)["linhas"])
        self.assertTrue(visao_fluxo_caixa("semana", filtros)["linhas"])
        self.assertTrue(visao_fluxo_caixa("mes", filtros)["linhas"])

    def test_rotas_permissao_exportacao_listbox_tooltip(self):
        self._titulo_receber("CR-FLX-3", valor="200.00", vencimento=date.today())
        self._autenticar()
        bloqueado = self.client.get("/financeiro/fluxo-caixa")
        self.assertIn(b"Redirecting", bloqueado.data)
        self._liberar(exportar=True)
        resposta = self.client.get("/financeiro/fluxo-caixa")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Saldo previsto do", resposta.data)
        self.assertIn(b"title=", resposta.data)
        self.assertIn(b"listbox-10-linhas", resposta.data)
        for rota in ["/financeiro/fluxo-caixa/movimentos", "/financeiro/fluxo-caixa/diario", "/financeiro/fluxo-caixa/semanal", "/financeiro/fluxo-caixa/mensal"]:
            self.assertEqual(self.client.get(rota).status_code, 200)
        exportacao = self.client.get("/financeiro/fluxo-caixa/exportar?sem_periodo=1")
        self.assertEqual(exportacao.status_code, 200)
        self.assertIn("text/csv", exportacao.headers["Content-Type"])
        self.assertIn("fluxo_caixa_movimentos", exportacao.headers["Content-Disposition"])


if __name__ == "__main__":
    unittest.main()
