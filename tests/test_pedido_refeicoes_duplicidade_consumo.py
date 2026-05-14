import unittest
from datetime import date
from decimal import Decimal

from flask import Flask

from app.departamento_pessoal.pedido_refeicoes.services import (
    DIA_SEMANA_TODOS,
    MENSAGEM_DUPLICIDADE_BEBIDA,
    MENSAGEM_DUPLICIDADE_REFEICAO,
    MENSAGEM_DUPLICIDADE_REFEICAO_BEBIDA,
    STATUS_PEDIDO_ABERTO,
    TIPO_CARDAPIO_BEBIDA,
    TIPO_CARDAPIO_REFEICAO,
    atualizar_consumos_refeicao_bebida,
    criar_consumos_refeicao_bebida,
)
from app.extensions import db
from app.models import (
    Colaborador,
    ConsumoRefeicao,
    Equipe,
    ItemCardapio,
    PedidoRefeicao,
    Restaurante,
)


class PedidoRefeicoesDuplicidadeConsumoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()
        self._criar_cenario_base()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _criar_cenario_base(self):
        self.equipe = Equipe(nome="Equipe Operacional", slug="equipe-operacional")
        self.restaurante = Restaurante(nome="Restaurante Teste", ativo=True)
        self.joao = Colaborador(
            matricula="001",
            nome="João",
            cpf="00000000001",
            equipe=self.equipe,
            ativo=True,
        )
        self.maria = Colaborador(
            matricula="002",
            nome="Maria",
            cpf="00000000002",
            equipe=self.equipe,
            ativo=True,
        )
        db.session.add_all([self.equipe, self.restaurante, self.joao, self.maria])
        db.session.flush()

        self.refeicao = ItemCardapio(
            restaurante_id=self.restaurante.id,
            tipo=TIPO_CARDAPIO_REFEICAO,
            nome="Prato do Dia",
            preco=Decimal("20.00"),
            dia_semana=DIA_SEMANA_TODOS,
            ativo=True,
        )
        self.bebida = ItemCardapio(
            restaurante_id=self.restaurante.id,
            tipo=TIPO_CARDAPIO_BEBIDA,
            nome="Suco",
            preco=Decimal("5.00"),
            dia_semana=DIA_SEMANA_TODOS,
            ativo=True,
        )
        db.session.add_all([self.refeicao, self.bebida])
        db.session.flush()

        self.pedido = PedidoRefeicao(
            numero_pedido="PED-TESTE",
            equipe_id=self.equipe.id,
            restaurante_id=self.restaurante.id,
            data_pedido=date(2026, 5, 14),
            status=STATUS_PEDIDO_ABERTO,
            enviado_whatsapp=False,
            quantidade_envios=0,
        )
        db.session.add(self.pedido)
        db.session.commit()

    def _lancar_consumo(
        self,
        colaborador,
        refeicao=True,
        bebida=False,
        observacao="",
    ):
        return criar_consumos_refeicao_bebida(
            pedido=self.pedido,
            colaborador_id=colaborador.id,
            refeicao_id=self.refeicao.id if refeicao else None,
            bebida_id=self.bebida.id if bebida else None,
            quantidade_refeicao=1,
            quantidade_bebida=1,
            observacao=observacao,
        )

    def _contar_consumos(self, colaborador, tipo):
        return (
            ConsumoRefeicao.query
            .join(ItemCardapio)
            .filter(
                ConsumoRefeicao.pedido_id == self.pedido.id,
                ConsumoRefeicao.colaborador_id == colaborador.id,
                ItemCardapio.tipo == tipo,
            )
            .count()
        )

    def _primeiro_consumo(self, colaborador, tipo):
        return (
            ConsumoRefeicao.query
            .join(ItemCardapio)
            .filter(
                ConsumoRefeicao.pedido_id == self.pedido.id,
                ConsumoRefeicao.colaborador_id == colaborador.id,
                ItemCardapio.tipo == tipo,
            )
            .order_by(ConsumoRefeicao.id.asc())
            .first()
        )

    def test_colaborador_sem_consumo_pode_receber_refeicao_e_bebida(self):
        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=True, bebida=True)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_REFEICAO), 1)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_BEBIDA), 1)

    def test_bloqueia_segunda_refeicao_e_permite_bebida_se_ainda_nao_existir(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=True, bebida=False)[0])

        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=True, bebida=False)
        self.assertFalse(sucesso)
        self.assertEqual(mensagem, MENSAGEM_DUPLICIDADE_REFEICAO)

        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=False, bebida=True)
        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_REFEICAO), 1)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_BEBIDA), 1)

    def test_bloqueia_segunda_bebida_e_permite_refeicao_se_ainda_nao_existir(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=False, bebida=True)[0])

        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=False, bebida=True)
        self.assertFalse(sucesso)
        self.assertEqual(mensagem, MENSAGEM_DUPLICIDADE_BEBIDA)

        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=True, bebida=False)
        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_REFEICAO), 1)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_BEBIDA), 1)

    def test_colaborador_com_refeicao_e_bebida_bloqueia_novo_consumo_conjunto(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=True, bebida=True)[0])

        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=True, bebida=True)

        self.assertFalse(sucesso)
        self.assertEqual(mensagem, MENSAGEM_DUPLICIDADE_REFEICAO_BEBIDA)

    def test_edicao_do_proprio_consumo_nao_bloqueia_indevidamente(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=True, bebida=True)[0])
        consumo = self._primeiro_consumo(self.joao, TIPO_CARDAPIO_REFEICAO)

        sucesso, mensagem = atualizar_consumos_refeicao_bebida(
            consumo_referencia=consumo,
            colaborador_id=self.joao.id,
            refeicao_id=self.refeicao.id,
            bebida_id=self.bebida.id,
            quantidade_refeicao=2,
            quantidade_bebida=1,
            observacao="Sem cebola",
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_REFEICAO), 1)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_BEBIDA), 1)

    def test_edicao_para_colaborador_com_refeicao_existente_bloqueia(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=True, bebida=False)[0])
        self.assertTrue(self._lancar_consumo(self.maria, refeicao=True, bebida=False)[0])
        consumo = self._primeiro_consumo(self.joao, TIPO_CARDAPIO_REFEICAO)

        sucesso, mensagem = atualizar_consumos_refeicao_bebida(
            consumo_referencia=consumo,
            colaborador_id=self.maria.id,
            refeicao_id=self.refeicao.id,
            bebida_id=None,
            quantidade_refeicao=1,
            quantidade_bebida=1,
        )

        self.assertFalse(sucesso)
        self.assertEqual(mensagem, MENSAGEM_DUPLICIDADE_REFEICAO)

    def test_edicao_para_colaborador_com_bebida_existente_bloqueia(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=False, bebida=True)[0])
        self.assertTrue(self._lancar_consumo(self.maria, refeicao=False, bebida=True)[0])
        consumo = self._primeiro_consumo(self.joao, TIPO_CARDAPIO_BEBIDA)

        sucesso, mensagem = atualizar_consumos_refeicao_bebida(
            consumo_referencia=consumo,
            colaborador_id=self.maria.id,
            refeicao_id=None,
            bebida_id=self.bebida.id,
            quantidade_refeicao=1,
            quantidade_bebida=1,
        )

        self.assertFalse(sucesso)
        self.assertEqual(mensagem, MENSAGEM_DUPLICIDADE_BEBIDA)

    def test_remover_refeicao_em_edicao_libera_futura_refeicao(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=True, bebida=True)[0])
        consumo = self._primeiro_consumo(self.joao, TIPO_CARDAPIO_REFEICAO)

        sucesso, mensagem = atualizar_consumos_refeicao_bebida(
            consumo_referencia=consumo,
            colaborador_id=self.joao.id,
            refeicao_id=None,
            bebida_id=self.bebida.id,
            quantidade_refeicao=1,
            quantidade_bebida=1,
        )
        self.assertTrue(sucesso, mensagem)

        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=True, bebida=False)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_REFEICAO), 1)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_BEBIDA), 1)

    def test_remover_bebida_em_edicao_libera_futura_bebida(self):
        self.assertTrue(self._lancar_consumo(self.joao, refeicao=True, bebida=True)[0])
        consumo = self._primeiro_consumo(self.joao, TIPO_CARDAPIO_REFEICAO)

        sucesso, mensagem = atualizar_consumos_refeicao_bebida(
            consumo_referencia=consumo,
            colaborador_id=self.joao.id,
            refeicao_id=self.refeicao.id,
            bebida_id=None,
            quantidade_refeicao=1,
            quantidade_bebida=1,
        )
        self.assertTrue(sucesso, mensagem)

        sucesso, mensagem = self._lancar_consumo(self.joao, refeicao=False, bebida=True)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_REFEICAO), 1)
        self.assertEqual(self._contar_consumos(self.joao, TIPO_CARDAPIO_BEBIDA), 1)


if __name__ == "__main__":
    unittest.main()
