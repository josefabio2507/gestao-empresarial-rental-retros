import unittest

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FinanceiroContaPagarTitulo,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
)
from app.services.financeiro_contas_pagar_service import (
    indicadores_dashboard,
    salvar_titulo,
)


class FinanceiroContasPagarTestCase(unittest.TestCase):
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
            nome="Contas a Pagar",
            slug="contas_a_pagar",
            ativo=True,
            ordem=1,
        )
        db.session.add(self.modulo)

        self.fornecedor = SuprimentosFornecedor(
            razao_social="FORNECEDOR TESTE LTDA",
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

    def _dados_titulo(self, **extra):
        dados = {
            "fornecedor_id": str(self.fornecedor.id),
            "fornecedor_nome_snapshot": "",
            "fornecedor_cnpj_cpf_snapshot": "",
            "descricao": "Nota de manutencao",
            "numero_documento": "DOC-001",
            "numero_nfe": "12345",
            "chave_acesso_nfe": "35260811222333000181550010000012341000012345",
            "data_emissao": "2026-08-20",
            "data_vencimento": "2026-08-30",
            "competencia": "2026-08",
            "valor_original": "100,00",
            "valor_desconto": "0,00",
            "valor_acrescimo": "0,00",
            "valor_juros_multa": "0,00",
            "valor_pago": "0,00",
            "origem_lancamento": "Manual",
            "tipo_pagamento": "Faturado",
            "forma_pagamento": "Boleto",
            "parcela_numero": "1",
            "total_parcelas": "1",
            "status": "Agendado",
            "observacoes": "Teste",
        }
        dados.update(extra)
        return dados

    def test_usuario_sem_permissao_nao_acessa_rota_direta(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/financeiro/contas-a-pagar/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_usuario_com_visualizar_acessa_dashboard_e_sem_criar_nao_acessa_novo(self):
        self._liberar(visualizar=True)
        self._autenticar(self.usuario)

        dashboard = self.client.get("/financeiro/contas-a-pagar/")
        novo = self.client.get("/financeiro/contas-a-pagar/novo")

        self.assertEqual(200, dashboard.status_code)
        self.assertIn(b"Contas a Pagar", dashboard.data)
        self.assertEqual(302, novo.status_code)
        self.assertIn("/acesso-negado", novo.headers["Location"])

    def test_cria_edita_filtra_e_cancela_titulo_manual(self):
        self._autenticar(self.admin)

        resposta = self.client.post(
            "/financeiro/contas-a-pagar/novo",
            data=self._dados_titulo(),
            follow_redirects=True,
        )
        titulo = FinanceiroContaPagarTitulo.query.one()

        self.assertEqual(200, resposta.status_code)
        self.assertEqual("FORNECEDOR TESTE LTDA", titulo.fornecedor_nome_snapshot)
        self.assertEqual("11222333000181", titulo.fornecedor_cnpj_cpf_snapshot)
        self.assertEqual("NOTA DE MANUTENCAO", titulo.descricao)
        self.assertEqual("Manual", titulo.origem_lancamento)
        self.assertEqual("Agendado", titulo.status)
        self.assertEqual(1, titulo.parcela_numero)

        editar = self.client.post(
            f"/financeiro/contas-a-pagar/{titulo.id}/editar",
            data=self._dados_titulo(descricao="Nota editada", status="Aguardando conferencia"),
            follow_redirects=True,
        )
        db.session.refresh(titulo)
        self.assertEqual(200, editar.status_code)
        self.assertEqual("NOTA EDITADA", titulo.descricao)
        self.assertEqual("Aguardando conferencia", titulo.status)

        filtrado = self.client.get("/financeiro/contas-a-pagar/titulos?status=Aguardando+conferencia")
        self.assertEqual(200, filtrado.status_code)
        self.assertIn(b"NOTA EDITADA", filtrado.data)

        cancelar = self.client.post(
            f"/financeiro/contas-a-pagar/{titulo.id}/cancelar",
            follow_redirects=True,
        )
        db.session.refresh(titulo)
        self.assertEqual(200, cancelar.status_code)
        self.assertEqual("Cancelado", titulo.status)

    def test_validacoes_basicas_do_titulo(self):
        sucesso, mensagem, _ = salvar_titulo(
            self._dados_titulo(valor_original="0,00"),
            usuario=self.admin,
        )
        self.assertFalse(sucesso)
        self.assertEqual("Valor original deve ser maior que zero.", mensagem)

        sucesso, mensagem, _ = salvar_titulo(
            self._dados_titulo(parcela_numero="2", total_parcelas="1"),
            usuario=self.admin,
        )
        self.assertFalse(sucesso)
        self.assertEqual("Parcela atual nao pode ser maior que total de parcelas.", mensagem)

    def test_dashboard_contabiliza_titulos(self):
        sucesso, mensagem, _ = salvar_titulo(
            self._dados_titulo(status="Aguardando conferencia"),
            usuario=self.admin,
        )
        self.assertTrue(sucesso, mensagem)

        indicadores = indicadores_dashboard()

        self.assertEqual(1, indicadores["qtd_aguardando_conferencia"])
        self.assertEqual(1, indicadores["qtd_manuais"])
        self.assertEqual(100, int(indicadores["total_aberto"]))


if __name__ == "__main__":
    unittest.main()
