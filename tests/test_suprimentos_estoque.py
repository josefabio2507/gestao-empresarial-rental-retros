import unittest
from datetime import datetime
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosCategoriaItem,
    SuprimentosFornecedor,
    SuprimentosItem,
    SuprimentosMovimentacaoEstoque,
    SuprimentosUnidadeMedida,
    Usuario,
)


class SuprimentosEstoqueTestCase(unittest.TestCase):
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

        departamento = Departamento(
            nome="Suprimentos",
            slug="suprimentos",
            ativo=True,
            ordem=2,
        )
        db.session.add(departamento)
        db.session.flush()

        self.modulo = Modulo(
            departamento_id=departamento.id,
            nome="Estoque",
            slug="estoque",
            ativo=True,
            ordem=10,
        )
        db.session.add(self.modulo)

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
        db.session.add_all([self.categoria, self.unidade, self.fornecedor])
        db.session.flush()

        self.item = SuprimentosItem(
            codigo_interno="PEC-001",
            descricao="FILTRO DE OLEO",
            categoria_id=self.categoria.id,
            unidade_medida_id=self.unidade.id,
            tipo="peca",
            item_estocavel=True,
            estoque_minimo=Decimal("3.000"),
            ativo=True,
        )
        self.item_normal = SuprimentosItem(
            codigo_interno="PEC-002",
            descricao="FILTRO DE AR",
            categoria_id=self.categoria.id,
            unidade_medida_id=self.unidade.id,
            tipo="peca",
            item_estocavel=True,
            estoque_minimo=Decimal("1.000"),
            ativo=True,
        )
        self.servico = SuprimentosItem(
            codigo_interno="SRV-001",
            descricao="SERVICO DE CALIBRAGEM",
            categoria_id=self.categoria.id,
            unidade_medida_id=self.unidade.id,
            tipo="servico",
            item_estocavel=False,
            ativo=True,
        )
        db.session.add_all([self.item, self.item_normal, self.servico])
        db.session.flush()

        db.session.add_all(
            [
                SuprimentosMovimentacaoEstoque(
                    item_id=self.item.id,
                    fornecedor_id=self.fornecedor.id,
                    tipo="Entrada",
                    origem="Recebimento OC",
                    status="Registrada",
                    documento_tipo="Nota Fiscal",
                    documento_numero="NF 123",
                    quantidade=Decimal("2.000"),
                    valor_unitario=Decimal("125.50"),
                    valor_total_snapshot=Decimal("251.00"),
                    movimentado_em=datetime(2026, 8, 9, 10, 30),
                ),
                SuprimentosMovimentacaoEstoque(
                    item_id=self.item_normal.id,
                    fornecedor_id=self.fornecedor.id,
                    tipo="Entrada",
                    origem="Recebimento OC",
                    status="Registrada",
                    documento_tipo="Romaneio",
                    documento_numero="ROM 55",
                    quantidade=Decimal("5.000"),
                    valor_unitario=Decimal("10.00"),
                    valor_total_snapshot=Decimal("50.00"),
                    movimentado_em=datetime(2026, 8, 9, 11, 0),
                ),
            ]
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
        permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=self.modulo.id,
            pode_visualizar=True,
            ativo=True,
        )
        db.session.add(permissao)
        db.session.commit()

    def test_usuario_sem_permissao_nao_acessa_estoque(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/estoque/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_lista_saldos_de_itens_estocaveis(self):
        self._liberar_usuario()
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/estoque/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Estoque", resposta.data)
        self.assertIn(b"FILTRO DE OLEO", resposta.data)
        self.assertIn(b"2,000", resposta.data)
        self.assertIn(b"Abaixo do minimo", resposta.data)
        self.assertNotIn(b"SERVICO DE CALIBRAGEM", resposta.data)

    def test_card_estoque_no_departamento_aponta_para_estoque(self):
        self._liberar_usuario()
        self._autenticar(self.usuario)

        resposta = self.client.get("/departamentos/suprimentos")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b'href="/suprimentos/estoque/"', resposta.data)

    def test_filtro_abaixo_minimo(self):
        self._liberar_usuario()
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/estoque/?abaixo_minimo=1")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"FILTRO DE OLEO", resposta.data)
        self.assertNotIn(b"FILTRO DE AR", resposta.data)

    def test_historico_movimentacoes_filtra_por_item_e_documento(self):
        self._liberar_usuario()
        self._autenticar(self.usuario)

        resposta = self.client.get(
            f"/suprimentos/estoque/movimentacoes?item_id={self.item.id}&documento=NF"
        )

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Historico de Estoque", resposta.data)
        self.assertIn(b"NF 123", resposta.data)
        self.assertIn(b"R$ 125,50", resposta.data)
        self.assertNotIn(b"ROM 55", resposta.data)


if __name__ == "__main__":
    unittest.main()
