import unittest
from datetime import datetime
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FinanceiroContaPagarTitulo,
    FiscalDocumento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
)
from app.services.financeiro_contas_pagar_service import (
    gerar_contas_pagar_xml,
    listar_agendamentos_xml_contas_pagar,
    status_financeiro_xml,
)


class FinanceiroXmlContasPagarTestCase(unittest.TestCase):
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
        self.admin = Usuario(nome="Admin", email="admin@teste.com", nivel_acesso=admin, ativo=True, precisa_trocar_senha=False)
        self.usuario = Usuario(nome="Comum", email="comum@teste.com", nivel_acesso=comum, ativo=True, precisa_trocar_senha=False)
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])
        self.departamento = Departamento(nome="Financeiro", slug="financeiro", descricao="Teste", ativo=True, ordem=1)
        db.session.add(self.departamento)
        db.session.flush()
        self.modulo = Modulo(departamento_id=self.departamento.id, nome="Contas a Pagar", slug="contas_a_pagar", ativo=True, ordem=1)
        db.session.add(self.modulo)
        self.fornecedor = SuprimentosFornecedor(
            razao_social="XML FORNECEDOR TESTE LTDA",
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

    def _documento(self, chave="35260811222333000181550010000174011000174011", **extra):
        dados = {
            "chave_acesso": chave,
            "modelo": "55",
            "serie": "1",
            "numero": "17401",
            "data_emissao": datetime(2026, 8, 20, 10, 0),
            "emitente_nome": self.fornecedor.razao_social,
            "emitente_cnpj": self.fornecedor.cnpj_cpf,
            "destinatario_nome": "RENTAL RETROS TESTE",
            "destinatario_cnpj": "12345678000190",
            "valor_total": Decimal("1000.00"),
            "xml_path": "local/xml.xml",
            "danfe_path": "local/danfe.pdf",
            "tem_xml_completo": True,
            "status": "XML baixado",
        }
        dados.update(extra)
        documento = FiscalDocumento(**dados)
        db.session.add(documento)
        db.session.commit()
        return documento

    def test_xml_sem_oc_gera_titulos_faturados(self):
        documento = self._documento()

        sucesso, mensagem, titulos = gerar_contas_pagar_xml(
            documento,
            {
                "tipo_pagamento": "Faturado",
                "forma_pagamento": "Boleto",
                "numero_parcelas": "3",
                "data_primeiro_vencimento": "2026-09-10",
            },
            usuario=self.admin,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(3, len(titulos))
        self.assertEqual("XML Fiscal", titulos[0].origem_lancamento)
        self.assertEqual(documento.id, titulos[0].fiscal_documento_id)
        self.assertEqual(Decimal("1000.00"), sum((titulo.valor_original for titulo in titulos), Decimal("0.00")))
        self.assertEqual("Aguardando conferencia", status_financeiro_xml(documento))

    def test_xml_vinculado_a_oc_integrada_bloqueia_duplicidade(self):
        ordem_compra_id = 999
        titulo = FinanceiroContaPagarTitulo(
            fornecedor_nome_snapshot=self.fornecedor.razao_social,
            fornecedor_cnpj_cpf_snapshot=self.fornecedor.cnpj_cpf,
            descricao="OC ja integrada",
            numero_documento="OC-XML-001-01/01",
            ordem_compra_id=ordem_compra_id,
            origem_lancamento="Ordem de Compra",
            tipo_pagamento="Faturado",
            forma_pagamento="Boleto",
            data_vencimento=datetime(2026, 9, 10).date(),
            valor_original=Decimal("1000.00"),
            valor_desconto=Decimal("0.00"),
            valor_acrescimo=Decimal("0.00"),
            valor_juros_multa=Decimal("0.00"),
            valor_pago=Decimal("0.00"),
            status="Agendado",
        )
        db.session.add(titulo)
        db.session.commit()
        documento = self._documento(ordem_compra_id=ordem_compra_id)

        sucesso, mensagem, titulos = gerar_contas_pagar_xml(
            documento,
            {"tipo_pagamento": "Faturado", "forma_pagamento": "Boleto", "numero_parcelas": "1", "data_primeiro_vencimento": "2026-09-10"},
            usuario=self.admin,
        )

        self.assertFalse(sucesso)
        self.assertIn("Ordem de Compra", mensagem)
        self.assertEqual([titulo.id], [item.id for item in titulos])
        self.assertEqual("Ja integrado via O.C.", status_financeiro_xml(documento))

    def test_tela_agendamentos_xml_exige_permissao_e_lista_documento(self):
        self._documento(numero="17409")
        self._autenticar(self.usuario)
        sem_permissao = self.client.get("/financeiro/contas-a-pagar/agendamentos-xml")
        self.assertEqual(302, sem_permissao.status_code)

        self._liberar(visualizar=True)
        resposta = self.client.get("/financeiro/contas-a-pagar/agendamentos-xml")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Agendamentos XML", resposta.data)
        self.assertIn(b"17409", resposta.data)
        self.assertEqual(1, len(listar_agendamentos_xml_contas_pagar({})))


if __name__ == "__main__":
    unittest.main()
