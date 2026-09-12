import unittest
from datetime import datetime
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    Colaborador,
    Equipe,
    NivelAcesso,
    SuprimentosCategoriaItem,
    SuprimentosItem,
    SuprimentosMovimentacaoEstoque,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.seguranca_trabalho_service import (
    buscar_itens_estoque_para_entrega,
    registrar_entrega_epi,
)


class SegurancaTrabalhoEpisTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.drop_all()
        db.create_all()

        nivel = NivelAcesso(nome="Administrador", slug="administrador", ativo=True)
        equipe = Equipe(nome="Operacao", slug="operacao", ativo=True)
        unidade = SuprimentosUnidadeMedida(nome="Unidade", sigla="UN", ativo=True)
        categorias = {
            "epi": SuprimentosCategoriaItem(nome="EPI", slug="epi", ativo=True),
            "uniforme": SuprimentosCategoriaItem(
                nome="UNIFORMES", slug="uniformes", ativo=True
            ),
            "outro": SuprimentosCategoriaItem(nome="PECAS", slug="pecas", ativo=True),
        }
        db.session.add_all([nivel, equipe, unidade, *categorias.values()])
        db.session.flush()

        self.usuario = Usuario(
            nome="Admin",
            email="admin@teste.com",
            nivel_acesso=nivel,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario.definir_senha("teste")
        self.colaborador = Colaborador(
            matricula="0001",
            nome="Colaborador Teste",
            cpf="12345678901",
            equipe_id=equipe.id,
            ativo=True,
        )
        db.session.add_all([self.usuario, self.colaborador])

        def criar_item(codigo, descricao, categoria, tipo="material", ativo=True):
            item = SuprimentosItem(
                codigo_interno=codigo,
                descricao=descricao,
                categoria_id=categorias[categoria].id,
                unidade_medida_id=unidade.id,
                tipo=tipo,
                item_estocavel=True,
                ativo=ativo,
            )
            db.session.add(item)
            db.session.flush()
            return item

        self.epi_com_saldo = criar_item("EPI-1", "CAPACETE", "outro", tipo="epi")
        self.uniforme_com_saldo = criar_item("UNI-1", "CAMISA", "uniforme")
        self.epi_sem_saldo = criar_item("EPI-2", "LUVA", "epi", tipo="epi")
        self.item_outro_tipo = criar_item("PEC-1", "FILTRO", "outro", tipo="peca")
        self.epi_inativo = criar_item("EPI-3", "OCULOS", "epi", tipo="epi", ativo=False)

        for item, quantidade in (
            (self.epi_com_saldo, "5.000"),
            (self.uniforme_com_saldo, "3.000"),
            (self.epi_sem_saldo, "2.000"),
            (self.epi_sem_saldo, "-2.000"),
            (self.item_outro_tipo, "10.000"),
            (self.epi_inativo, "4.000"),
        ):
            db.session.add(
                SuprimentosMovimentacaoEstoque(
                    item_id=item.id,
                    tipo="Entrada" if not quantidade.startswith("-") else "Saida",
                    origem="Teste",
                    status="Registrada",
                    quantidade=Decimal(quantidade),
                    movimentado_em=datetime(2026, 9, 12, 10, 0),
                )
            )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _form_entrega(self, item_id, quantidade="1"):
        return {
            "colaborador_id": str(self.colaborador.id),
            "item_id": str(item_id),
            "tipo_material": "EPI",
            "quantidade": quantidade,
            "data_entrega": "2026-09-12",
            "motivo_entrega": "Reposicao",
        }

    def test_consulta_inclui_epi_ou_uniforme_com_estoque_zerado(self):
        itens = buscar_itens_estoque_para_entrega()

        self.assertEqual(
            {self.epi_com_saldo.id, self.uniforme_com_saldo.id, self.epi_sem_saldo.id},
            {item.id for item in itens},
        )

    def test_nova_entrega_exibe_apenas_itens_com_saldo_disponivel(self):
        itens = buscar_itens_estoque_para_entrega(somente_com_saldo=True)

        self.assertEqual(
            {self.epi_com_saldo.id, self.uniforme_com_saldo.id},
            {item.id for item in itens},
        )

    def test_entrega_valida_gera_baixa_automatica_no_estoque(self):
        saldo_anterior = Decimal(self.epi_com_saldo.saldo_estoque)

        sucesso, _, entrega = registrar_entrega_epi(
            self._form_entrega(self.epi_com_saldo.id, "2"), self.usuario
        )

        self.assertTrue(sucesso)
        self.assertIsNotNone(entrega.movimentacao_estoque_id)
        self.assertEqual(Decimal("-2.000"), entrega.movimentacao_estoque.quantidade)
        self.assertEqual(saldo_anterior - Decimal("2"), self.epi_com_saldo.saldo_estoque)

    def test_backend_rejeita_item_de_outro_tipo(self):
        sucesso, mensagem, entrega = registrar_entrega_epi(
            self._form_entrega(self.item_outro_tipo.id), self.usuario
        )

        self.assertFalse(sucesso)
        self.assertIn("EPI ou Uniforme", mensagem)
        self.assertIsNone(entrega)

    def test_backend_rejeita_item_sem_saldo(self):
        sucesso, mensagem, entrega = registrar_entrega_epi(
            self._form_entrega(self.epi_sem_saldo.id), self.usuario
        )

        self.assertFalse(sucesso)
        self.assertIn("saldo disponivel", mensagem)
        self.assertIsNone(entrega)


if __name__ == "__main__":
    unittest.main()
