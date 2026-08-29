import os
import unittest
from datetime import date, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    FinanceiroCartaoCredito,
    FinanceiroCartaoFatura,
    FiscalDocumento,
    FinanceiroContaPagarBaixa,
    FinanceiroContaPagarLoteBaixa,
    FinanceiroContaPagarTitulo,
    LogAcesso,
    SuprimentosOrdemCompra,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
)
from app.services.financeiro_relatorios_service import (
    dashboard_avancado,
    filtros_padrao,
    gerar_csv_relatorio,
    montar_relatorio,
)


class FinanceiroRelatoriosContasPagarTestCase(unittest.TestCase):
    def setUp(self):
        self.database_url_anterior = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        self.test_tables = [
            NivelAcesso.__table__,
            Departamento.__table__,
            Modulo.__table__,
            Usuario.__table__,
            PermissaoUsuarioModulo.__table__,
            LogAcesso.__table__,
            CentroCusto.__table__,
            SuprimentosFornecedor.__table__,
            FinanceiroCartaoCredito.__table__,
            FinanceiroCartaoFatura.__table__,
            SuprimentosOrdemCompra.__table__,
            FiscalDocumento.__table__,
            FinanceiroContaPagarTitulo.__table__,
            FinanceiroContaPagarLoteBaixa.__table__,
            FinanceiroContaPagarBaixa.__table__,
        ]
        db.metadata.create_all(db.engine, tables=self.test_tables)

        nivel = NivelAcesso(nome="Usuario", slug="usuario", ativo=True)
        db.session.add(nivel)
        db.session.flush()
        self.usuario = Usuario(nome="Financeiro Relatorios", email="financeiro.relatorios@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False)
        self.usuario.definir_senha("teste")
        self.departamento = Departamento(nome="Financeiro", slug="financeiro", descricao="Teste", ativo=True, ordem=1)
        db.session.add_all([self.usuario, self.departamento])
        db.session.flush()
        self.modulo = Modulo(departamento_id=self.departamento.id, nome="Contas a Pagar", slug="contas_a_pagar", ativo=True, ordem=1)
        self.modulo_relatorios = Modulo(departamento_id=self.departamento.id, nome="Relatorios", slug="relatorios", ativo=True, ordem=2)
        self.centro = CentroCusto(codigo="FIN-01", nome="Administrativo", ativo=True)
        self.fornecedor = SuprimentosFornecedor(
            razao_social="FORNECEDOR RELATORIOS LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="11222333000144",
            ativo=True,
        )
        self.cartao = FinanceiroCartaoCredito(
            nome="Cartao Teste",
            banco="Banco Teste",
            bandeira="Visa",
            ultimos_4_digitos="1234",
            titular_responsavel="Financeiro",
            dia_fechamento=20,
            dia_vencimento=28,
            limite=Decimal("5000.00"),
            ativo=True,
        )
        db.session.add_all([self.modulo, self.modulo_relatorios, self.centro, self.fornecedor, self.cartao])
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

    def _liberar(self, visualizar=True, exportar=False):
        permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=self.modulo_relatorios.id,
            pode_visualizar=visualizar,
            pode_criar=True,
            pode_editar=True,
            pode_excluir=False,
            pode_exportar=exportar,
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def _titulo(self, documento, valor="100.00", status="Agendado", vencimento=None, pago="0.00", origem="Manual", forma="Pix", fatura=None):
        hoje = date.today()
        titulo = FinanceiroContaPagarTitulo(
            fornecedor_id=self.fornecedor.id,
            fornecedor_nome_snapshot=self.fornecedor.razao_social,
            fornecedor_cnpj_cpf_snapshot=self.fornecedor.cnpj_cpf,
            descricao=f"Titulo {documento}",
            numero_documento=documento,
            numero_nfe=documento.replace("DOC", "NFE"),
            origem_lancamento=origem,
            tipo_pagamento="Cartao de Credito" if fatura else "Faturado",
            forma_pagamento="Cartao de Credito" if fatura else forma,
            data_emissao=hoje.replace(day=1),
            data_vencimento=vencimento or hoje,
            competencia=hoje.replace(day=1),
            valor_original=Decimal(valor),
            valor_desconto=Decimal("0.00"),
            valor_acrescimo=Decimal("0.00"),
            valor_juros_multa=Decimal("0.00"),
            valor_pago=Decimal(pago),
            status=status,
            parcela_numero=1,
            total_parcelas=1,
            centro_custo_id=self.centro.id,
            cartao_credito_id=self.cartao.id if fatura else None,
            fatura_cartao_id=fatura.id if fatura else None,
        )
        db.session.add(titulo)
        db.session.commit()
        return titulo

    def _baixa(self, titulo, valor="50.00", lote=None, comprovante=False):
        baixa = FinanceiroContaPagarBaixa(
            titulo_id=titulo.id,
            lote_baixa_id=lote.id if lote else None,
            data_pagamento=date.today(),
            valor_pago=Decimal(valor),
            forma_pagamento="Pix",
            conta_pagamento_descricao="Conta teste",
            status="Ativa",
            comprovante_nome_original="comprovante.pdf" if comprovante else None,
            comprovante_nome_armazenado="comprovante.pdf" if comprovante else None,
            comprovante_path="/tmp/comprovante.pdf" if comprovante else None,
            comprovante_extensao="pdf" if comprovante else None,
            comprovante_tamanho=100 if comprovante else None,
            registrado_por_usuario_id=self.usuario.id,
        )
        db.session.add(baixa)
        db.session.commit()
        return baixa

    def test_dashboard_avancado_consolida_cards_e_resumos(self):
        hoje = date.today()
        fatura = FinanceiroCartaoFatura(
            cartao_credito_id=self.cartao.id,
            competencia=hoje.replace(day=1),
            data_fechamento=hoje,
            data_vencimento=hoje + timedelta(days=5),
            valor_total=Decimal("300.00"),
            valor_pago=Decimal("100.00"),
            status="Aberta",
        )
        db.session.add(fatura)
        db.session.commit()
        self._titulo("DOC-001", valor="400.00", vencimento=hoje - timedelta(days=3))
        self._titulo("DOC-002", valor="250.00", vencimento=hoje + timedelta(days=4), origem="XML Fiscal")
        self._titulo("DOC-003", valor="300.00", status="Pago parcialmente", vencimento=hoje + timedelta(days=10), pago="120.00", fatura=fatura)

        filtros = filtros_padrao({"sem_periodo": "1"})
        dados = dashboard_avancado(filtros)

        self.assertEqual(dados["cards"]["qtd_abertos"], 3)
        self.assertEqual(dados["cards"]["qtd_vencidos"], 1)
        self.assertEqual(dados["cards"]["valor_xml_integrado"], Decimal("250.00"))
        self.assertTrue(dados["resumos"]["por_fornecedor"])
        self.assertTrue(dados["tabelas"]["maiores_abertos"])

    def test_relatorios_cobrem_vencidas_pagamentos_fornecedor_e_lotes(self):
        hoje = date.today()
        vencido = self._titulo("DOC-010", valor="500.00", vencimento=hoje - timedelta(days=10))
        pago = self._titulo("DOC-011", valor="200.00", status="Pago", vencimento=hoje, pago="200.00")
        lote = FinanceiroContaPagarLoteBaixa(
            data_pagamento=hoje,
            forma_pagamento="Pix",
            total_titulos=1,
            valor_total_baixado=Decimal("200.00"),
            status="Ativo",
            criado_por_usuario_id=self.usuario.id,
        )
        db.session.add(lote)
        db.session.commit()
        self._baixa(pago, valor="200.00", lote=lote, comprovante=True)

        filtros = filtros_padrao({"sem_periodo": "1"})
        vencidas = montar_relatorio("vencidas", filtros)
        pagamentos = montar_relatorio("pagamentos", filtros)
        fornecedor = montar_relatorio("fornecedor", filtros)
        lotes = montar_relatorio("lotes_baixa", filtros)

        self.assertEqual(vencidas["linhas"][0]["titulo_id"], vencido.id)
        self.assertEqual(vencidas["linhas"][0]["dias_atraso"], 10)
        self.assertEqual(pagamentos["totais"]["valor_pago"], Decimal("200.00"))
        self.assertEqual(pagamentos["linhas"][0]["lote_id"], lote.id)
        self.assertEqual(fornecedor["linhas"][0]["grupo"], self.fornecedor.razao_social)
        self.assertEqual(lotes["linhas"][0]["lote_id"], lote.id)

    def test_rotas_relatarios_e_exportacao_respeitam_permissao(self):
        self._titulo("DOC-020", valor="150.00", vencimento=date.today())
        self._autenticar()
        self._liberar(exportar=False)

        resposta = self.client.get("/financeiro/relatorios")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Relatorios operacionais", resposta.data)
        self.assertIn(b"Financeiro &gt; Relatorios", resposta.data)

        bloqueado = self.client.get("/financeiro/relatorios/exportar")
        self.assertIn(b"Redirecting", bloqueado.data)

        PermissaoUsuarioModulo.query.filter_by(usuario_id=self.usuario.id, modulo_id=self.modulo_relatorios.id).update({"pode_exportar": True})
        db.session.commit()
        exportacao = self.client.get("/financeiro/relatorios/exportar?tipo_relatorio=periodo")
        self.assertEqual(exportacao.status_code, 200)
        self.assertIn("text/csv", exportacao.headers["Content-Type"])
        self.assertIn("contas_a_pagar_periodo", exportacao.headers["Content-Disposition"])
        self.assertIn("Contas a pagar por periodo", exportacao.data.decode("utf-8"))

        legado = self.client.get("/financeiro/contas-a-pagar/relatorios?tipo_relatorio=vencidas", follow_redirects=False)
        self.assertEqual(legado.status_code, 302)
        self.assertIn("/financeiro/relatorios", legado.headers["Location"])

        relatorio = montar_relatorio("periodo", filtros_padrao({"sem_periodo": "1"}))
        csv = gerar_csv_relatorio(relatorio)
        self.assertIn("Valor original", csv)


if __name__ == "__main__":
    unittest.main()
