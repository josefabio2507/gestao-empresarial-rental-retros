from datetime import date, timedelta
from decimal import Decimal
import unittest

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FinanceiroContaReceberTitulo,
    LogAcesso,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.services.financeiro_contas_receber_service import (
    gerar_dashboard,
    listar_titulos_receber,
    salvar_titulo_receber,
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


if __name__ == "__main__":
    unittest.main()
