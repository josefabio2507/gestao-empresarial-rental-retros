import unittest
from datetime import datetime
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosCategoriaItem,
    SuprimentosCotacao,
    SuprimentosCotacaoProposta,
    SuprimentosFornecedor,
    SuprimentosItem,
    SuprimentosMovimentacaoEstoque,
    SuprimentosOrdemCompra,
    SuprimentosOrdemCompraItem,
    SuprimentosRequisicaoCompra,
    SuprimentosRequisicaoCompraItem,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.suprimentos_service import indicadores_suprimentos


class SuprimentosIndicadoresTestCase(unittest.TestCase):
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

        departamento = Departamento(nome="Suprimentos", slug="suprimentos", ativo=True, ordem=2)
        db.session.add(departamento)
        db.session.flush()

        self.modulo = Modulo(
            departamento_id=departamento.id,
            nome="Indicadores",
            slug="indicadores",
            ativo=True,
            ordem=11,
        )
        db.session.add(self.modulo)

        self.centro = CentroCusto(codigo="MAN", nome="MANUTENCAO", ativo=True)
        self.categoria = SuprimentosCategoriaItem(nome="PECAS", slug="pecas", ativo=True)
        self.unidade = SuprimentosUnidadeMedida(nome="UNIDADE", sigla="UN", ativo=True)
        self.fornecedor = SuprimentosFornecedor(
            razao_social="FORNECEDOR TESTE LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="11222333000181",
            email="fornecedor@teste.com",
            telefone="5513999998888",
            ativo=True,
        )
        db.session.add_all([self.centro, self.categoria, self.unidade, self.fornecedor])
        db.session.flush()

        self.item = SuprimentosItem(
            codigo_interno="PEC-001",
            descricao="FILTRO DE OLEO",
            categoria_id=self.categoria.id,
            unidade_medida_id=self.unidade.id,
            centro_custo_padrao_id=self.centro.id,
            tipo="peca",
            item_estocavel=True,
            estoque_minimo=Decimal("3.000"),
            ativo=True,
        )
        db.session.add(self.item)
        db.session.flush()

        self.requisicao = SuprimentosRequisicaoCompra(
            numero="REQ-2026-0001",
            solicitante_usuario_id=self.admin.id,
            centro_custo_id=self.centro.id,
            justificativa="COMPRAR FILTROS",
            status="Aprovada",
            criado_em=datetime(2026, 8, 9, 8, 0),
        )
        db.session.add(self.requisicao)
        db.session.flush()

        self.requisicao_item = SuprimentosRequisicaoCompraItem(
            requisicao_id=self.requisicao.id,
            item_id=self.item.id,
            item_codigo_snapshot=self.item.codigo_interno,
            item_descricao_snapshot=self.item.descricao,
            unidade_medida_snapshot=self.unidade.sigla,
            quantidade=Decimal("2.000"),
        )
        db.session.add(self.requisicao_item)
        db.session.flush()

        self.cotacao = SuprimentosCotacao(
            numero="COT-2026-0001",
            requisicao_id=self.requisicao.id,
            criado_por_usuario_id=self.admin.id,
            status="Aprovada",
            criado_em=datetime(2026, 8, 9, 9, 0),
        )
        db.session.add(self.cotacao)
        db.session.flush()

        self.proposta = SuprimentosCotacaoProposta(
            cotacao_id=self.cotacao.id,
            fornecedor_id=self.fornecedor.id,
            requisicao_item_id=self.requisicao_item.id,
            item_id=self.item.id,
            fornecedor_razao_social_snapshot=self.fornecedor.razao_social,
            item_descricao_snapshot=self.item.descricao,
            unidade_medida_snapshot=self.unidade.sigla,
            quantidade_snapshot=Decimal("2.000"),
            preco_unitario=Decimal("125.50"),
            selecionada=True,
        )
        db.session.add(self.proposta)
        db.session.flush()

        self.ordem = SuprimentosOrdemCompra(
            numero="OC-2026-0001",
            cotacao_id=self.cotacao.id,
            requisicao_id=self.requisicao.id,
            fornecedor_id=self.fornecedor.id,
            criado_por_usuario_id=self.admin.id,
            fornecedor_razao_social_snapshot=self.fornecedor.razao_social,
            fornecedor_cnpj_cpf_snapshot=self.fornecedor.cnpj_cpf,
            status="Recebida",
            gerada_em=datetime(2026, 8, 9, 10, 0),
        )
        db.session.add(self.ordem)
        db.session.flush()

        db.session.add(
            SuprimentosOrdemCompraItem(
                ordem_compra_id=self.ordem.id,
                cotacao_proposta_id=self.proposta.id,
                requisicao_item_id=self.requisicao_item.id,
                item_id=self.item.id,
                item_codigo_snapshot=self.item.codigo_interno,
                item_descricao_snapshot=self.item.descricao,
                unidade_medida_snapshot=self.unidade.sigla,
                quantidade=Decimal("2.000"),
                preco_unitario=Decimal("125.50"),
            )
        )
        db.session.add(
            SuprimentosMovimentacaoEstoque(
                item_id=self.item.id,
                fornecedor_id=self.fornecedor.id,
                tipo="Entrada",
                origem="Recebimento OC",
                status="Registrada",
                quantidade=Decimal("2.000"),
                movimentado_em=datetime(2026, 8, 9, 11, 0),
            )
        )
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

    def _liberar_usuario(self):
        db.session.add(
            PermissaoUsuarioModulo(
                usuario_id=self.usuario.id,
                modulo_id=self.modulo.id,
                pode_visualizar=True,
                ativo=True,
            )
        )
        db.session.commit()

    def test_indicadores_consolida_compras_e_status(self):
        resultado = indicadores_suprimentos(
            "2026-08-01",
            "2026-08-31",
            self.fornecedor.id,
            self.centro.id,
            self.categoria.id,
        )

        self.assertEqual(Decimal("251.00"), resultado["cards"]["total_compras"])
        self.assertEqual(1, resultado["cards"]["ordens"])
        self.assertEqual(1, resultado["cards"]["requisicoes"])
        self.assertEqual(1, resultado["cards"]["cotacoes"])
        self.assertEqual(1, resultado["cards"]["itens_abaixo_minimo"])
        self.assertEqual([("FORNECEDOR TESTE LTDA", Decimal("251.00"))], resultado["compras_por_fornecedor"])
        self.assertEqual([("MANUTENCAO", Decimal("251.00"))], resultado["compras_por_centro_custo"])
        self.assertIn(("Recebida", 1), resultado["ordens_por_status"])
        self.assertIn(("Entrada - Recebimento OC", Decimal("2.000")), resultado["movimentacoes_por_tipo"])

    def test_usuario_sem_permissao_nao_acessa_indicadores(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/indicadores/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_usuario_com_visualizar_acessa_painel(self):
        self._liberar_usuario()
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/indicadores/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Indicadores", resposta.data)
        self.assertIn(b"R$ 251,00", resposta.data)
        self.assertIn(b"FORNECEDOR TESTE LTDA", resposta.data)


if __name__ == "__main__":
    unittest.main()
