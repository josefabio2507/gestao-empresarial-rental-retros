from datetime import date, timedelta
from decimal import Decimal
import io
import unittest

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FinanceiroContaReceberBaixa,
    FinanceiroContaReceberLoteBaixa,
    FinanceiroContaReceberTitulo,
    FinanceiroContratoCliente,
    FinanceiroContratoMedicao,
    FinanceiroNotaFiscalEmitida,
    LogAcesso,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.services.financeiro_contas_receber_service import (
    cancelar_recebimento_titulo,
    gerar_dashboard,
    gerar_titulos_da_medicao,
    gerar_titulos_da_nota,
    listar_titulos_receber,
    salvar_contrato_cliente,
    salvar_medicao_contrato,
    salvar_nota_emitida,
    registrar_recebimento_em_massa,
    registrar_recebimento_titulo,
    salvar_titulo_receber,
    vincular_medicao_a_nota,
    vincular_medicao_a_titulo,
    vincular_nota_a_titulo,
)


class FinanceiroContasReceberTestCase(unittest.TestCase):
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
            email="admin@teste.com",
            nivel_acesso=admin,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario = Usuario(
            nome="Comum",
            email="comum@teste.com",
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
            nome="Contas a Receber",
            slug="contas_a_receber",
            ativo=True,
            ordem=2,
        )
        db.session.add(self.modulo)
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
            pode_excluir=acoes.get("cancelar", False),
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def _dados_titulo(self, **extras):
        dados = {
            "cliente_nome_snapshot": "Cliente Teste",
            "cliente_cnpj_cpf_snapshot": "11.222.333/0001-81",
            "cliente_email_financeiro_snapshot": "financeiro@cliente.com",
            "cliente_telefone_snapshot": "13999998888",
            "descricao": "Locacao de equipamento",
            "numero_documento": "DOC-1",
            "numero_nota_fiscal": "NF-1",
            "chave_acesso_nfe_nfse": "ABC123",
            "origem_lancamento": "Manual",
            "competencia": "2026-08",
            "data_emissao": "2026-08-01",
            "data_vencimento": "2026-08-30",
            "valor_original": "1000.00",
            "valor_desconto": "100.00",
            "valor_acrescimo": "50.00",
            "valor_juros_multa": "10.00",
            "valor_recebido": "200.00",
            "parcela_numero": "1",
            "total_parcelas": "2",
            "status": "Faturado",
            "observacoes": "Teste",
        }
        dados.update(extras)
        return dados


    def _dados_nota(self, **extras):
        dados = {
            "tipo_nota": "NFS-e",
            "numero_nota": "NFSE-100",
            "serie": "A",
            "chave_acesso": "",
            "codigo_verificacao_nfse": "COD-100",
            "cliente_nome_snapshot": "Cliente Teste",
            "cliente_cnpj_cpf_snapshot": "11.222.333/0001-81",
            "cliente_email_financeiro_snapshot": "financeiro@cliente.com",
            "cliente_telefone_snapshot": "13999998888",
            "data_emissao": "2026-08-01",
            "competencia": "2026-08",
            "descricao": "Servico faturado",
            "valor_bruto": "10000.00",
            "valor_desconto": "0.00",
            "valor_impostos_retidos": "0.00",
            "valor_liquido": "10000.00",
            "valor_total": "10000.00",
            "data_vencimento_padrao": "2026-08-30",
            "numero_parcelas": "1",
            "condicao_recebimento": "A vista",
            "status_fiscal": "Emitida",
            "status_financeiro": "Não integrado",
            "observacoes_fiscais": "Teste fiscal",
            "observacoes_financeiras": "Teste financeiro",
        }
        dados.update(extras)
        return dados


    def _dados_contrato(self, **extras):
        dados = {
            "numero_contrato": "CTR-100",
            "cliente_nome_snapshot": "Cliente Teste",
            "cliente_cnpj_cpf_snapshot": "11.222.333/0001-81",
            "cliente_email_financeiro_snapshot": "financeiro@cliente.com",
            "cliente_telefone_snapshot": "13999998888",
            "descricao_objeto": "Contrato de serviços",
            "data_inicio": "2026-08-01",
            "data_fim": "2027-07-31",
            "valor_contratual": "120000.00",
            "tipo_cobranca": "Medição variável",
            "periodicidade_medicao": "Mensal",
            "dia_padrao_vencimento": "10",
            "condicao_recebimento": "Mensal",
            "status": "Ativo",
            "observacoes": "Teste",
        }
        dados.update(extras)
        return dados

    def _criar_contrato(self, **extras):
        sucesso, mensagem, contrato = salvar_contrato_cliente(self._dados_contrato(**extras), usuario=self.admin)
        self.assertTrue(sucesso, mensagem)
        return contrato

    def _dados_medicao(self, contrato, **extras):
        dados = {
            "contrato_id": str(contrato.id),
            "numero_medicao": "MED-100",
            "competencia": "2026-08",
            "data_medicao": "2026-08-31",
            "periodo_inicio": "2026-08-01",
            "periodo_fim": "2026-08-31",
            "descricao": "Medição mensal",
            "valor_bruto_medido": "10000.00",
            "valor_desconto": "0.00",
            "valor_acrescimo": "0.00",
            "valor_retencoes": "0.00",
            "valor_liquido_medido": "10000.00",
            "data_prevista_faturamento": "2026-09-01",
            "data_prevista_vencimento": "2026-09-10",
            "status_medicao": "Aprovada",
            "status_financeiro": "Não integrado",
            "observacoes_tecnicas": "Teste técnico",
            "observacoes_financeiras": "Teste financeiro",
        }
        dados.update(extras)
        return dados

    def test_cria_titulo_manual_e_calcula_saldo(self):
        sucesso, mensagem, titulo, _ = salvar_titulo_receber(self._dados_titulo(), usuario=self.admin)

        self.assertTrue(sucesso)
        self.assertEqual("Título a receber cadastrado com sucesso.", mensagem)
        self.assertEqual(Decimal("960.00"), titulo.valor_liquido)
        self.assertEqual(Decimal("760.00"), titulo.saldo_aberto)
        self.assertEqual("CLIENTE TESTE", titulo.cliente_nome_snapshot)

    def test_valida_cliente_obrigatorio_e_valor_maior_que_zero(self):
        sucesso, mensagem, _, _ = salvar_titulo_receber(
            self._dados_titulo(cliente_nome_snapshot=""),
            usuario=self.admin,
        )
        self.assertFalse(sucesso)
        self.assertEqual("Informe o cliente.", mensagem)

        sucesso, mensagem, _, _ = salvar_titulo_receber(
            self._dados_titulo(valor_original="0"),
            usuario=self.admin,
        )
        self.assertFalse(sucesso)
        self.assertEqual("Informe um valor maior que zero.", mensagem)

    def test_dashboard_identifica_vencidos_abertos_e_a_vencer(self):
        hoje = date.today()
        salvar_titulo_receber(self._dados_titulo(data_vencimento=(hoje - timedelta(days=1)).isoformat()), usuario=self.admin)
        salvar_titulo_receber(self._dados_titulo(numero_documento="DOC-2", data_vencimento=(hoje + timedelta(days=5)).isoformat(), valor_recebido="0"), usuario=self.admin)
        salvar_titulo_receber(self._dados_titulo(numero_documento="DOC-3", status="Cancelado"), usuario=self.admin)

        dados = gerar_dashboard({"mes": hoje.strftime("%Y-%m")})

        self.assertEqual(2, dados["cards"]["quantidade_abertos"])
        self.assertEqual(1, dados["cards"]["quantidade_vencidos"])
        self.assertGreater(dados["cards"]["total_vencido"], Decimal("0.00"))
        self.assertEqual(1, len(dados["proximos_vencimentos"]))

    def test_filtra_titulos_por_cliente_status_e_vencido(self):
        ontem = (date.today() - timedelta(days=1)).isoformat()
        salvar_titulo_receber(self._dados_titulo(cliente_nome_snapshot="Alpha", data_vencimento=ontem), usuario=self.admin)
        salvar_titulo_receber(self._dados_titulo(cliente_nome_snapshot="Beta", numero_documento="DOC-2", status="Rascunho"), usuario=self.admin)

        filtrados = listar_titulos_receber({"cliente": "alp", "vencidos": "1"})

        self.assertEqual(1, len(filtrados))
        self.assertEqual("ALPHA", filtrados[0].cliente_nome_snapshot)

    def test_rotas_dashboard_listbox_tooltip_crud_e_cancelamento(self):
        self._autenticar(self.admin)

        dashboard = self.client.get("/financeiro/contas-a-receber/dashboard")
        self.assertEqual(200, dashboard.status_code)
        self.assertIn("Soma dos títulos com vencimento dentro do mês selecionado".encode(), dashboard.data)
        self.assertIn(b"listbox-10-linhas", dashboard.data)

        resposta = self.client.post(
            "/financeiro/contas-a-receber/novo",
            data=self._dados_titulo(),
            follow_redirects=True,
        )
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Título a receber cadastrado com sucesso.".encode(), resposta.data)

        titulo = FinanceiroContaReceberTitulo.query.one()
        resposta = self.client.post(
            f"/financeiro/contas-a-receber/{titulo.id}/editar",
            data=self._dados_titulo(descricao="Locacao revisada", status="A vencer"),
            follow_redirects=True,
        )
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Título a receber atualizado com sucesso.".encode(), resposta.data)

        resposta = self.client.post(
            f"/financeiro/contas-a-receber/{titulo.id}/cancelar",
            data={"motivo_cancelamento": "Erro de lançamento"},
            follow_redirects=True,
        )
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Título a receber cancelado com sucesso.".encode(), resposta.data)
        self.assertEqual("Cancelado", FinanceiroContaReceberTitulo.query.get(titulo.id).status)

    def test_permissao_bloqueia_rota_direta_e_registra_log(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/financeiro/contas-a-receber/dashboard")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])
        self.assertEqual(1, LogAcesso.query.filter_by(acao="financeiro_contas_receber_permissao_bloqueada").count())

    def test_usuario_sem_criar_nao_ve_novo_lancamento(self):
        self._liberar(visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/financeiro/contas-a-receber/titulos")

        self.assertEqual(200, resposta.status_code)
        self.assertNotIn(b"+ Novo Lancamento", resposta.data)
        self.assertEqual(0, LogAcesso.query.filter_by(acao="financeiro_contas_receber_permissao_bloqueada").count())


    def test_recebimento_parcial_recalcula_saldo_e_status(self):
        sucesso, _, titulo, _ = salvar_titulo_receber(self._dados_titulo(valor_recebido="0"), usuario=self.admin)
        self.assertTrue(sucesso)

        sucesso, mensagem, baixa = registrar_recebimento_titulo(
            titulo,
            {"data_recebimento": "2026-08-15", "valor_recebido": "300.00", "forma_recebimento": "Pix", "conta_recebimento_descricao": "Banco teste", "observacoes": "Primeira baixa"},
            usuario=self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Recebimento parcial registrado com sucesso.", mensagem)
        self.assertEqual("Recebido parcialmente", titulo.status)
        self.assertEqual(Decimal("300.00"), titulo.valor_recebido)
        self.assertEqual(Decimal("660.00"), titulo.saldo_aberto)
        self.assertEqual("Ativa", baixa.status)

    def test_recebimento_total_quita_titulo_e_bloqueia_excesso(self):
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0"), usuario=self.admin)
        titulo = FinanceiroContaReceberTitulo.query.one()

        sucesso, mensagem, _ = registrar_recebimento_titulo(
            titulo,
            {"data_recebimento": "2026-08-20", "valor_recebido": "961.00", "forma_recebimento": "Transferência"},
            usuario=self.admin,
        )
        self.assertFalse(sucesso)
        self.assertEqual("O valor informado excede o saldo em aberto.", mensagem)

        sucesso, mensagem, _ = registrar_recebimento_titulo(
            titulo,
            {"data_recebimento": "2026-08-20", "valor_recebido": "960.00", "forma_recebimento": "Transferência"},
            usuario=self.admin,
        )
        self.assertTrue(sucesso)
        self.assertEqual("Título recebido com sucesso.", mensagem)
        self.assertEqual("Recebido", titulo.status)
        self.assertEqual(Decimal("0.00"), Decimal(titulo.saldo_aberto).quantize(Decimal("0.01")))

        sucesso, mensagem, _ = registrar_recebimento_titulo(
            titulo,
            {"data_recebimento": "2026-08-21", "valor_recebido": "1.00", "forma_recebimento": "Pix"},
            usuario=self.admin,
        )
        self.assertFalse(sucesso)
        self.assertEqual("Título já está totalmente recebido.", mensagem)

    def test_bloqueia_recebimento_titulo_cancelado_e_campos_obrigatorios(self):
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0", status="Cancelado"), usuario=self.admin)
        titulo = FinanceiroContaReceberTitulo.query.one()

        sucesso, mensagem, _ = registrar_recebimento_titulo(
            titulo,
            {"data_recebimento": "2026-08-20", "valor_recebido": "100.00", "forma_recebimento": "Pix"},
            usuario=self.admin,
        )
        self.assertFalse(sucesso)
        self.assertEqual("Título cancelado não pode receber baixa.", mensagem)

        titulo.status = "Faturado"
        db.session.commit()
        sucesso, mensagem, _ = registrar_recebimento_titulo(titulo, {"valor_recebido": "100.00", "forma_recebimento": "Pix"}, usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Informe a data do recebimento.", mensagem)

        sucesso, mensagem, _ = registrar_recebimento_titulo(titulo, {"data_recebimento": "2026-08-20", "valor_recebido": "0", "forma_recebimento": "Pix"}, usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Informe o valor recebido.", mensagem)

        sucesso, mensagem, _ = registrar_recebimento_titulo(titulo, {"data_recebimento": "2026-08-20", "valor_recebido": "100.00"}, usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Informe a forma de recebimento.", mensagem)

    def test_estorno_preserva_historico_e_recalcula_titulo(self):
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0"), usuario=self.admin)
        titulo = FinanceiroContaReceberTitulo.query.one()
        sucesso, _, baixa = registrar_recebimento_titulo(titulo, {"data_recebimento": "2026-08-20", "valor_recebido": "400.00", "forma_recebimento": "Boleto"}, usuario=self.admin)
        self.assertTrue(sucesso)

        sucesso, mensagem = cancelar_recebimento_titulo(baixa, "Cliente contestou", usuario=self.admin)

        self.assertTrue(sucesso)
        self.assertEqual("Recebimento cancelado/estornado com sucesso. O saldo do título foi recalculado.", mensagem)
        self.assertEqual("Estornada", baixa.status)
        self.assertEqual(Decimal("0.00"), titulo.valor_recebido)
        self.assertEqual("Faturado", titulo.status)
        self.assertEqual(1, FinanceiroContaReceberBaixa.query.count())

    def test_rotas_recebimento_upload_download_estorno_e_dashboard(self):
        self._autenticar(self.admin)
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0"), usuario=self.admin)
        titulo = FinanceiroContaReceberTitulo.query.one()

        resposta = self.client.post(
            f"/financeiro/contas-a-receber/{titulo.id}/recebimentos/novo",
            data={"data_recebimento": "2026-08-20", "valor_recebido": "500.00", "forma_recebimento": "Pix", "conta_recebimento_descricao": "Banco teste", "comprovante": (io.BytesIO(b"comprovante teste"), "comprovante.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Recebimento parcial registrado com sucesso.".encode(), resposta.data)
        self.assertIn(b"Recebimentos / Baixas", resposta.data)
        self.assertIn(b"listbox-10-linhas", resposta.data)

        baixa = FinanceiroContaReceberBaixa.query.one()
        self.assertTrue(baixa.comprovante_disponivel)
        download = self.client.get(f"/financeiro/contas-a-receber/baixas/{baixa.id}/comprovante")
        self.assertEqual(200, download.status_code)
        self.assertEqual(b"comprovante teste", download.data)


        dashboard = self.client.get("/financeiro/contas-a-receber/dashboard?mes=2026-08")
        self.assertEqual(200, dashboard.status_code)
        self.assertIn("Soma dos recebimentos ativos registrados dentro do mês selecionado.".encode(), dashboard.data)
        self.assertIn(b"Total recebido no", dashboard.data)
        self.assertIn(b"Valor recebido por forma", dashboard.data)

        resposta = self.client.post(
            f"/financeiro/contas-a-receber/{titulo.id}/recebimentos/{baixa.id}/estornar",
            data={"motivo_cancelamento": "Erro de baixa"},
            follow_redirects=True,
        )
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Recebimento cancelado/estornado com sucesso.".encode(), resposta.data)
        self.assertEqual("Estornada", FinanceiroContaReceberBaixa.query.get(baixa.id).status)

    def test_rota_registrar_recebimento_bloqueia_sem_permissao(self):
        self._liberar(visualizar=True)
        self._autenticar(self.usuario)
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0"), usuario=self.admin)
        titulo = FinanceiroContaReceberTitulo.query.one()

        resposta = self.client.get(f"/financeiro/contas-a-receber/{titulo.id}/recebimentos/novo")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])


    def test_baixa_em_massa_cria_lote_baixas_e_recalcula_status(self):
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0", numero_documento="DOC-M1", valor_original="1000.00", valor_desconto="0", valor_acrescimo="0", valor_juros_multa="0"), usuario=self.admin)
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0", numero_documento="DOC-M2", valor_original="800.00", valor_desconto="0", valor_acrescimo="0", valor_juros_multa="0"), usuario=self.admin)
        titulos = FinanceiroContaReceberTitulo.query.order_by(FinanceiroContaReceberTitulo.id).all()

        sucesso, mensagem, lote = registrar_recebimento_em_massa(
            {
                "titulos_ids": [str(titulos[0].id), str(titulos[1].id)],
                "data_recebimento": "2026-08-29",
                "forma_recebimento": "Pix",
                "conta_recebimento_descricao": "Banco teste",
                "observacoes": "Lote teste",
                f"valor_receber_{titulos[0].id}": "1000.00",
                f"valor_receber_{titulos[1].id}": "300.00",
            },
            usuario=self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Recebimento em massa registrado com sucesso.", mensagem)
        self.assertEqual(2, lote.total_titulos)
        self.assertEqual(Decimal("1300.00"), lote.valor_total_recebido)
        self.assertEqual(2, FinanceiroContaReceberBaixa.query.filter_by(lote_baixa_id=lote.id).count())
        self.assertEqual("Recebido", titulos[0].status)
        self.assertEqual("Recebido parcialmente", titulos[1].status)
        self.assertEqual(Decimal("500.00"), titulos[1].saldo_aberto)

    def test_baixa_em_massa_bloqueia_inelegivel_e_valor_acima_do_saldo(self):
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0", numero_documento="DOC-M1", valor_original="1000.00", valor_desconto="0", valor_acrescimo="0", valor_juros_multa="0"), usuario=self.admin)
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0", numero_documento="DOC-M2", status="Cancelado", valor_original="800.00", valor_desconto="0", valor_acrescimo="0", valor_juros_multa="0"), usuario=self.admin)
        titulos = FinanceiroContaReceberTitulo.query.order_by(FinanceiroContaReceberTitulo.id).all()

        sucesso, mensagem, _ = registrar_recebimento_em_massa({"titulos_ids": [str(titulos[1].id)], "data_recebimento": "2026-08-29", "forma_recebimento": "Pix", f"valor_receber_{titulos[1].id}": "100.00"}, usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Um ou mais títulos não estão elegíveis para recebimento.", mensagem)

        sucesso, mensagem, _ = registrar_recebimento_em_massa({"titulos_ids": [str(titulos[0].id)], "data_recebimento": "2026-08-29", "forma_recebimento": "Pix", f"valor_receber_{titulos[0].id}": "1000.01"}, usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("O valor informado excede o saldo de um dos títulos.", mensagem)

    def test_rotas_baixa_em_massa_lote_comprovante_e_estorno(self):
        self._autenticar(self.admin)
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0", numero_documento="DOC-M1", valor_original="1000.00", valor_desconto="0", valor_acrescimo="0", valor_juros_multa="0"), usuario=self.admin)
        salvar_titulo_receber(self._dados_titulo(valor_recebido="0", numero_documento="DOC-M2", valor_original="800.00", valor_desconto="0", valor_acrescimo="0", valor_juros_multa="0"), usuario=self.admin)
        titulos = FinanceiroContaReceberTitulo.query.order_by(FinanceiroContaReceberTitulo.id).all()

        selecao = self.client.post("/financeiro/contas-a-receber/baixa-em-massa", data={"titulos_ids": [str(titulos[0].id), str(titulos[1].id)]})
        self.assertEqual(200, selecao.status_code)
        self.assertIn(b"Baixa em Massa", selecao.data)
        self.assertIn(b"listbox-10-linhas", selecao.data)

        resposta = self.client.post(
            "/financeiro/contas-a-receber/baixa-em-massa",
            data={
                "confirmar": "1",
                "titulos_ids": [str(titulos[0].id), str(titulos[1].id)],
                "data_recebimento": "2026-08-29",
                "forma_recebimento": "Pix",
                "conta_recebimento_descricao": "Banco teste",
                "observacoes": "Lote rota",
                f"valor_receber_{titulos[0].id}": "1000.00",
                f"valor_receber_{titulos[1].id}": "300.00",
                "comprovante": (io.BytesIO(b"comprovante lote"), "lote.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Recebimento em massa registrado com sucesso.".encode(), resposta.data)
        self.assertIn("Títulos vinculados ao lote".encode(), resposta.data)
        self.assertIn(b"listbox-10-linhas", resposta.data)
        lote = FinanceiroContaReceberLoteBaixa.query.one()
        download = self.client.get(f"/financeiro/contas-a-receber/lotes/{lote.id}/comprovante")
        self.assertEqual(200, download.status_code)
        self.assertEqual(b"comprovante lote", download.data)

        com_comprovante = self.client.get("/financeiro/contas-a-receber/titulos?comprovante=com")
        self.assertEqual(200, com_comprovante.status_code)
        self.assertIn(b"DOC-M1", com_comprovante.data)

        dashboard = self.client.get("/financeiro/contas-a-receber/dashboard?mes=2026-08")
        self.assertIn("Soma das baixas ativas vinculadas a lotes de recebimento".encode(), dashboard.data)
        self.assertIn(b"Lotes de recebimento no", dashboard.data)

        estorno = self.client.post(f"/financeiro/contas-a-receber/lotes/{lote.id}/estornar", data={"motivo_cancelamento": "Erro no lote"}, follow_redirects=True)
        self.assertEqual(200, estorno.status_code)
        self.assertIn("Lote de recebimento estornado com sucesso.".encode(), estorno.data)
        self.assertEqual("Estornado", FinanceiroContaReceberLoteBaixa.query.get(lote.id).status)
        self.assertEqual(2, FinanceiroContaReceberBaixa.query.filter_by(status="Estornada").count())

    def test_notas_emitidas_cadastro_arquivos_e_validacoes(self):
        sucesso, mensagem, nota = salvar_nota_emitida(self._dados_nota(), usuario=self.admin)
        self.assertTrue(sucesso)
        self.assertEqual("Nota fiscal emitida cadastrada com sucesso.", mensagem)
        self.assertEqual(Decimal("10000.00"), nota.valor_total)

        sucesso, mensagem, _ = salvar_nota_emitida(self._dados_nota(), usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertIn("Já existe nota fiscal emitida", mensagem)

        sucesso, mensagem, _ = salvar_nota_emitida(self._dados_nota(numero_nota=""), usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Informe o número da nota.", mensagem)
        sucesso, mensagem, _ = salvar_nota_emitida(self._dados_nota(numero_nota="NFSE-101", cliente_nome_snapshot=""), usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Informe o cliente.", mensagem)
        sucesso, mensagem, _ = salvar_nota_emitida(self._dados_nota(numero_nota="NFSE-102", valor_total="0"), usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Informe um valor maior que zero.", mensagem)

    def test_gera_titulos_parcelados_da_nota_com_centavos_e_bloqueia_duplicidade(self):
        sucesso, _, nota = salvar_nota_emitida(self._dados_nota(valor_total="10000.00", valor_bruto="10000.00", valor_liquido="10000.00", numero_parcelas="3"), usuario=self.admin)
        self.assertTrue(sucesso)

        sucesso, mensagem, titulos = gerar_titulos_da_nota(
            nota,
            {"data_primeiro_vencimento": "2026-08-31", "numero_parcelas": "3", "competencia": "2026-08", "descricao": "Servico parcelado"},
            usuario=self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Título(s) a receber gerado(s) com sucesso.", mensagem)
        self.assertEqual(3, len(titulos))
        self.assertEqual([Decimal("3333.33"), Decimal("3333.33"), Decimal("3333.34")], [titulo.valor_original for titulo in titulos])
        self.assertEqual([date(2026, 8, 31), date(2026, 9, 30), date(2026, 10, 31)], [titulo.data_vencimento for titulo in titulos])
        self.assertEqual("Título gerado", nota.status_financeiro)
        self.assertEqual("Nota Fiscal Emitida", titulos[0].origem_lancamento)
        self.assertEqual(nota.id, titulos[0].nota_emitida_id)

        sucesso, mensagem, _ = gerar_titulos_da_nota(nota, {"data_primeiro_vencimento": "2026-08-31", "numero_parcelas": "1"}, usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Esta nota fiscal já possui título(s) a receber vinculado(s).", mensagem)

    def test_vincula_nota_a_titulo_existente_e_exibe_nas_rotas(self):
        self._autenticar(self.admin)
        salvar_titulo_receber(self._dados_titulo(numero_nota_fiscal="", chave_acesso_nfe_nfse="", origem_lancamento="Manual"), usuario=self.admin)
        titulo = FinanceiroContaReceberTitulo.query.one()
        sucesso, _, nota = salvar_nota_emitida(self._dados_nota(numero_nota="NFSE-200", valor_total="960.00", valor_bruto="960.00", valor_liquido="960.00"), usuario=self.admin)
        self.assertTrue(sucesso)

        sucesso, mensagem, titulo = vincular_nota_a_titulo(nota, titulo.id, usuario=self.admin)
        self.assertTrue(sucesso)
        self.assertEqual("Nota fiscal vinculada ao título com sucesso.", mensagem)
        self.assertEqual(nota.id, titulo.nota_emitida_id)
        self.assertEqual("NFSE-200", titulo.numero_nota_fiscal)
        self.assertEqual("Vinculado a título existente", nota.status_financeiro)

        detalhe_titulo = self.client.get(f"/financeiro/contas-a-receber/{titulo.id}")
        self.assertEqual(200, detalhe_titulo.status_code)
        self.assertIn("Nota Fiscal Emitida Vinculada".encode(), detalhe_titulo.data)
        self.assertIn(b"NFSE-200", detalhe_titulo.data)

        detalhe_nota = self.client.get(f"/financeiro/contas-a-receber/notas-emitidas/{nota.id}")
        self.assertEqual(200, detalhe_nota.status_code)
        self.assertIn("Títulos a receber vinculados".encode(), detalhe_nota.data)
        self.assertIn(b"listbox-10-linhas", detalhe_nota.data)

    def test_rotas_notas_emitidas_menu_dashboard_geracao_e_arquivos(self):
        self._autenticar(self.admin)
        resposta = self.client.post(
            "/financeiro/contas-a-receber/notas-emitidas/nova",
            data={**self._dados_nota(numero_nota="NFSE-300", valor_total="500.00", valor_bruto="500.00", valor_liquido="500.00"), "arquivo_pdf": (io.BytesIO(b"pdf nota"), "nota.pdf"), "arquivo_xml": (io.BytesIO(b"<xml />"), "nota.xml")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Nota fiscal emitida cadastrada com sucesso.".encode(), resposta.data)
        nota = FinanceiroNotaFiscalEmitida.query.filter_by(numero_nota="NFSE-300").one()

        lista = self.client.get("/financeiro/contas-a-receber/notas-emitidas")
        self.assertEqual(200, lista.status_code)
        self.assertIn(b"Notas Emitidas", lista.data)
        self.assertIn(b"listbox-10-linhas", lista.data)
        self.assertIn(b"NFSE-300", lista.data)

        pdf = self.client.get(f"/financeiro/contas-a-receber/notas-emitidas/{nota.id}/arquivo/pdf")
        xml = self.client.get(f"/financeiro/contas-a-receber/notas-emitidas/{nota.id}/arquivo/xml")
        self.assertEqual(200, pdf.status_code)
        self.assertEqual(200, xml.status_code)
        self.assertEqual(b"pdf nota", pdf.data)
        self.assertEqual(b"<xml />", xml.data)

        gerar = self.client.post(
            f"/financeiro/contas-a-receber/notas-emitidas/{nota.id}/gerar",
            data={"data_primeiro_vencimento": "2026-08-30", "numero_parcelas": "1", "competencia": "2026-08", "descricao": "Nota teste"},
            follow_redirects=True,
        )
        self.assertEqual(200, gerar.status_code)
        self.assertIn("Título(s) a receber gerado(s) com sucesso.".encode(), gerar.data)
        self.assertEqual(1, FinanceiroContaReceberTitulo.query.filter_by(nota_emitida_id=nota.id).count())

        dashboard = self.client.get("/financeiro/contas-a-receber/dashboard?mes=2026-08")
        self.assertEqual(200, dashboard.status_code)
        self.assertIn("Quantidade de notas fiscais emitidas que ainda não possuem título financeiro vinculado.".encode(), dashboard.data)
        self.assertIn(b"Notas emitidas recentes", dashboard.data)

    def test_permissao_bloqueia_notas_emitidas_sem_visualizar(self):
        self._autenticar(self.usuario)
        resposta = self.client.get("/financeiro/contas-a-receber/notas-emitidas")
        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_cria_contrato_e_bloqueia_duplicado(self):
        contrato = self._criar_contrato()
        self.assertEqual("CTR-100", contrato.numero_contrato)
        sucesso, mensagem, _ = salvar_contrato_cliente(self._dados_contrato(), usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertIn("Já existe contrato", mensagem)

    def test_cria_medicao_valida_periodo_e_gera_titulos_parcelados(self):
        contrato = self._criar_contrato()
        sucesso, mensagem, medicao = salvar_medicao_contrato(self._dados_medicao(contrato, valor_liquido_medido="10000.00"), usuario=self.admin)
        self.assertTrue(sucesso, mensagem)
        sucesso, mensagem, _ = salvar_medicao_contrato(self._dados_medicao(contrato, numero_medicao="MED-101", periodo_fim="2026-07-31"), usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Período final não pode ser menor que o período inicial.", mensagem)
        sucesso, mensagem, titulos = gerar_titulos_da_medicao(medicao, {"data_vencimento": "2026-09-30", "numero_parcelas": "3", "competencia": "2026-08"}, usuario=self.admin)
        self.assertTrue(sucesso, mensagem)
        self.assertEqual([Decimal("3333.33"), Decimal("3333.33"), Decimal("3333.34")], [titulo.valor_original for titulo in titulos])
        self.assertEqual("Título gerado", FinanceiroContratoMedicao.query.get(medicao.id).status_financeiro)
        sucesso, mensagem, _ = gerar_titulos_da_medicao(medicao, {"data_vencimento": "2026-09-30"}, usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertIn("já possui título", mensagem)

    def test_vincula_medicao_a_titulo_e_nota_emitida(self):
        contrato = self._criar_contrato()
        sucesso, _, medicao = salvar_medicao_contrato(self._dados_medicao(contrato), usuario=self.admin)
        self.assertTrue(sucesso)
        sucesso, _, nota = salvar_nota_emitida(self._dados_nota(numero_nota="NFSE-MED-1"), usuario=self.admin)
        self.assertTrue(sucesso)
        sucesso, mensagem, nota = vincular_medicao_a_nota(medicao, nota.id, usuario=self.admin)
        self.assertTrue(sucesso, mensagem)
        self.assertEqual(medicao.id, nota.medicao_id)
        sucesso, _, titulo, _ = salvar_titulo_receber(self._dados_titulo(numero_documento="DOC-MED", nota_emitida_id=""), usuario=self.admin)
        self.assertTrue(sucesso)
        sucesso, mensagem, titulo = vincular_medicao_a_titulo(medicao, titulo.id, usuario=self.admin)
        self.assertTrue(sucesso, mensagem)
        self.assertEqual(medicao.id, titulo.medicao_id)
        self.assertEqual(contrato.id, titulo.contrato_id)

    def test_rotas_contratos_medicoes_dashboard_e_listbox(self):
        self._liberar(visualizar=True, criar=True, editar=True, cancelar=True)
        self._autenticar(self.usuario)
        contrato = self._criar_contrato()
        sucesso, _, medicao = salvar_medicao_contrato(self._dados_medicao(contrato), usuario=self.admin)
        self.assertTrue(sucesso)
        rotas_com_listbox = [
            "/financeiro/contas-a-receber/contratos",
            f"/financeiro/contas-a-receber/contratos/{contrato.id}",
            "/financeiro/contas-a-receber/medicoes",
            f"/financeiro/contas-a-receber/medicoes/{medicao.id}",
        ]
        for rota in rotas_com_listbox:
            resposta = self.client.get(rota)
            self.assertEqual(200, resposta.status_code, rota)
            self.assertIn(b"listbox-10-linhas", resposta.data)
        gerar = self.client.get(f"/financeiro/contas-a-receber/medicoes/{medicao.id}/gerar")
        self.assertEqual(200, gerar.status_code)
        self.assertIn("Gerar Contas a Receber".encode("utf-8"), gerar.data)
        dashboard = self.client.get("/financeiro/contas-a-receber/dashboard")
        self.assertEqual(200, dashboard.status_code)
        self.assertIn("Contratos ativos".encode("utf-8"), dashboard.data)
        self.assertIn("Medições pendentes".encode("utf-8"), dashboard.data)
        self.assertIn(b"title=", dashboard.data)

if __name__ == "__main__":
    unittest.main()
