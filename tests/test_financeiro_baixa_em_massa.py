import io
import os
import unittest
from datetime import date
from decimal import Decimal

from werkzeug.datastructures import MultiDict

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FinanceiroContaPagarBaixa,
    FinanceiroContaPagarLoteBaixa,
    FinanceiroContaPagarTitulo,
    LogAcesso,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
)
from app.services.financeiro_contas_pagar_service import (
    calcular_saldo_titulo,
    estornar_lote_baixa,
    registrar_baixa_em_massa,
)


class FinanceiroBaixaEmMassaTestCase(unittest.TestCase):
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
            SuprimentosFornecedor.__table__,
            FinanceiroContaPagarTitulo.__table__,
            FinanceiroContaPagarLoteBaixa.__table__,
            FinanceiroContaPagarBaixa.__table__,
        ]
        db.metadata.create_all(db.engine, tables=self.test_tables)

        nivel = NivelAcesso(nome="Usuario", slug="usuario", ativo=True)
        db.session.add(nivel)
        db.session.flush()
        self.usuario = Usuario(nome="Financeiro", email="financeiro.massa@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False)
        self.usuario.definir_senha("teste")
        self.departamento = Departamento(nome="Financeiro", slug="financeiro", descricao="Teste", ativo=True, ordem=1)
        db.session.add_all([self.usuario, self.departamento])
        db.session.flush()
        self.modulo = Modulo(departamento_id=self.departamento.id, nome="Contas a Pagar", slug="contas_a_pagar", ativo=True, ordem=1)
        self.fornecedor = SuprimentosFornecedor(
            razao_social="FORNECEDOR MASSA TESTE LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="44999888000177",
            ativo=True,
        )
        db.session.add_all([self.modulo, self.fornecedor])
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

    def _titulo(self, valor="1000.00", status="Agendado", documento="MASSA-001", pago="0.00"):
        titulo = FinanceiroContaPagarTitulo(
            fornecedor_id=self.fornecedor.id,
            fornecedor_nome_snapshot=self.fornecedor.razao_social,
            fornecedor_cnpj_cpf_snapshot=self.fornecedor.cnpj_cpf,
            descricao="TITULO TESTE BAIXA EM MASSA",
            numero_documento=documento,
            origem_lancamento="Manual",
            tipo_pagamento="Faturado",
            forma_pagamento="Pix",
            data_emissao=date(2026, 8, 1),
            data_vencimento=date(2026, 8, 25),
            competencia=date(2026, 8, 1),
            valor_original=Decimal(valor),
            valor_desconto=Decimal("0.00"),
            valor_acrescimo=Decimal("0.00"),
            valor_juros_multa=Decimal("0.00"),
            valor_pago=Decimal(pago),
            status=status,
            parcela_numero=1,
            total_parcelas=1,
        )
        db.session.add(titulo)
        db.session.commit()
        return titulo

    def _dados_lote(self, titulos, valores=None):
        valores = valores or {titulo.id: str(calcular_saldo_titulo(titulo)).replace(".", ",") for titulo in titulos}
        dados = MultiDict([
            ("data_pagamento", "2026-08-26"),
            ("forma_pagamento", "Pix"),
            ("conta_pagamento_descricao", "Banco teste"),
            ("observacoes", "Baixa em massa teste"),
        ])
        for titulo in titulos:
            dados.add("titulos_ids", str(titulo.id))
            dados.add(f"valor_baixa_{titulo.id}", valores[titulo.id])
        return dados

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

    def test_registra_baixa_em_massa_total_e_vincula_lote(self):
        titulo_1 = self._titulo(valor="300.00", documento="MASSA-001")
        titulo_2 = self._titulo(valor="700.00", documento="MASSA-002")

        sucesso, mensagem, lote = registrar_baixa_em_massa(self._dados_lote([titulo_1, titulo_2]), usuario=self.usuario)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(lote.total_titulos, 2)
        self.assertEqual(lote.valor_total_baixado, Decimal("1000.00"))
        self.assertEqual(FinanceiroContaPagarBaixa.query.filter_by(lote_baixa_id=lote.id).count(), 2)
        self.assertEqual(titulo_1.status, "Pago")
        self.assertEqual(titulo_2.status, "Pago")
        self.assertEqual(calcular_saldo_titulo(titulo_1), Decimal("0.00"))

    def test_registra_baixa_em_massa_parcial(self):
        titulo_1 = self._titulo(valor="500.00", documento="MASSA-003")
        titulo_2 = self._titulo(valor="500.00", documento="MASSA-004")
        dados = self._dados_lote([titulo_1, titulo_2], {titulo_1.id: "200,00", titulo_2.id: "500,00"})

        sucesso, mensagem, lote = registrar_baixa_em_massa(dados, usuario=self.usuario)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(lote.valor_total_baixado, Decimal("700.00"))
        self.assertEqual(titulo_1.status, "Pago parcialmente")
        self.assertEqual(calcular_saldo_titulo(titulo_1), Decimal("300.00"))
        self.assertEqual(titulo_2.status, "Pago")

    def test_bloqueia_titulo_inelegivel_no_lote(self):
        titulo_pago = self._titulo(valor="200.00", status="Pago", documento="MASSA-005", pago="200.00")

        sucesso, mensagem, lote = registrar_baixa_em_massa(self._dados_lote([titulo_pago], {titulo_pago.id: "10,00"}), usuario=self.usuario)

        self.assertFalse(sucesso)
        self.assertIsNone(lote)
        self.assertIn("elegiveis", mensagem)

    def test_bloqueia_valor_acima_do_saldo_no_lote(self):
        titulo = self._titulo(valor="100.00", documento="MASSA-006")

        sucesso, mensagem, lote = registrar_baixa_em_massa(self._dados_lote([titulo], {titulo.id: "100,01"}), usuario=self.usuario)

        self.assertFalse(sucesso)
        self.assertIsNone(lote)
        self.assertIn("excede o saldo", mensagem)

    def test_upload_comprovante_unico_no_lote(self):
        titulo_1 = self._titulo(valor="120.00", documento="MASSA-007")
        titulo_2 = self._titulo(valor="130.00", documento="MASSA-008")
        arquivo = type("ArquivoTeste", (), {})()
        arquivo.filename = "comprovante.pdf"
        arquivo.content_length = 20
        arquivo.mimetype = "application/pdf"
        arquivo.stream = io.BytesIO(b"comprovante em massa")
        def salvar_arquivo(caminho):
            with open(caminho, "wb") as destino:
                destino.write(arquivo.stream.getvalue())
        arquivo.save = salvar_arquivo

        sucesso, mensagem, lote = registrar_baixa_em_massa(self._dados_lote([titulo_1, titulo_2]), arquivo=arquivo, usuario=self.usuario)

        self.assertTrue(sucesso, mensagem)
        self.assertTrue(lote.comprovante_disponivel)
        baixas = FinanceiroContaPagarBaixa.query.filter_by(lote_baixa_id=lote.id).all()
        self.assertTrue(all(baixa.comprovante_disponivel for baixa in baixas))

    def test_estorna_lote_sem_apagar_historico(self):
        titulo_1 = self._titulo(valor="250.00", documento="MASSA-009")
        titulo_2 = self._titulo(valor="250.00", documento="MASSA-010")
        sucesso, _, lote = registrar_baixa_em_massa(self._dados_lote([titulo_1, titulo_2]), usuario=self.usuario)
        self.assertTrue(sucesso)

        sucesso, mensagem = estornar_lote_baixa(lote, "Pagamento em duplicidade", usuario=self.usuario)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(lote.status, "Estornado")
        self.assertEqual(FinanceiroContaPagarBaixa.query.filter_by(lote_baixa_id=lote.id, status="Estornada").count(), 2)
        self.assertEqual(titulo_1.valor_pago, Decimal("0.00"))
        self.assertEqual(calcular_saldo_titulo(titulo_1), Decimal("250.00"))

    def test_rota_baixa_em_massa_bloqueia_sem_permissao(self):
        self._titulo(valor="100.00", documento="MASSA-011")
        self._autenticar()

        resposta = self.client.get("/financeiro/contas-a-pagar/titulos/baixa-em-massa")

        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_rota_baixa_em_massa_com_permissao_carrega(self):
        titulo = self._titulo(valor="100.00", documento="MASSA-012")
        self._liberar(visualizar=True, editar=True)
        self._autenticar()

        resposta = self.client.get(f"/financeiro/contas-a-pagar/titulos/baixa-em-massa?titulos_ids={titulo.id}")

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(b"Baixa em Massa", resposta.data)


if __name__ == "__main__":
    unittest.main()
