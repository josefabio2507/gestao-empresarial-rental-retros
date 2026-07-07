from decimal import Decimal
import unittest

from app import create_app
from app.extensions import db
from app.models import Colaborador, Equipe, LinhaOnibus, ValeTransportePedido
from app.departamento_pessoal.vale_transporte.services import (
    STATUS_PEDIDO_CANCELADO,
    cancelar_pedido_vale_transporte,
    criar_pedido_vale_transporte,
    montar_previa_pedido_vale_transporte,
    salvar_vinculo_colaborador_linha,
)


class ValeTransportePedidosTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            WTF_CSRF_ENABLED=False,
            AUTO_MIGRATE_ON_START=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

        self.equipe = Equipe(nome="Operacao", slug="operacao", ativo=True)
        outra_equipe = Equipe(nome="Administrativo", slug="administrativo", ativo=True)
        self.colaborador = Colaborador(
            matricula="100",
            nome="Colaborador Teste",
            cpf="12345678901",
            cargo="Operador",
            equipe=self.equipe,
            vale_transporte_optante=True,
            ativo=True,
        )
        self.colaborador_fora_filtro = Colaborador(
            matricula="200",
            nome="Colaborador Fora",
            cpf="12345678902",
            cargo="Auxiliar",
            equipe=outra_equipe,
            vale_transporte_optante=True,
            ativo=True,
        )
        self.linha = LinhaOnibus(
            nome="Centro",
            codigo="001",
            empresa_transporte="Transporte Teste",
            valor_tarifa_dia=Decimal("10.00"),
            ativo=True,
        )
        self.outra_linha = LinhaOnibus(
            nome="Bairro",
            codigo="002",
            empresa_transporte="Outra Empresa",
            valor_tarifa_dia=Decimal("8.50"),
            ativo=True,
        )
        db.session.add_all([
            self.equipe,
            outra_equipe,
            self.colaborador,
            self.colaborador_fora_filtro,
            self.linha,
            self.outra_linha,
        ])
        db.session.commit()

        sucesso, mensagem = salvar_vinculo_colaborador_linha(
            colaborador=self.colaborador,
            linha_onibus_id=self.linha.id,
            tipo_pagamento="dinheiro",
            periodicidade_pagamento="mensal",
        )
        self.assertTrue(sucesso, mensagem)

        sucesso, mensagem = salvar_vinculo_colaborador_linha(
            colaborador=self.colaborador_fora_filtro,
            linha_onibus_id=self.outra_linha.id,
            tipo_pagamento="cartao_transporte",
            periodicidade_pagamento="semanal",
        )
        self.assertTrue(sucesso, mensagem)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_monta_previa_filtrando_por_equipe_forma_empresa_e_prazo(self):
        previa = montar_previa_pedido_vale_transporte(
            competencia="05.2026",
            data_inicial="2026-05-01",
            data_final="2026-05-31",
            quantidade_dias="22",
            equipe_id=str(self.equipe.id),
            forma_pagamento="dinheiro",
            empresa_transporte="Transporte Teste",
            prazo_pagamento="mensal",
        )

        self.assertEqual(1, len(previa["itens"]))
        item = previa["itens"][0]
        self.assertEqual("100", item["matricula"])
        self.assertEqual(Decimal("220.00"), item["valor_total"])

    def test_cria_pedido_com_snapshot_e_recalculo_backend(self):
        vinculo = self.colaborador.linhas_vale_transporte[0]

        sucesso, mensagem, pedido = criar_pedido_vale_transporte(
            competencia="05.2026",
            data_inicial="2026-05-01",
            data_final="2026-05-31",
            quantidade_dias="22",
            equipe_id=str(self.equipe.id),
            forma_pagamento="dinheiro",
            empresa_transporte="Transporte Teste",
            prazo_pagamento="mensal",
            ajustes_itens={
                str(vinculo.id): {
                    "quantidade_dias": "20",
                    "valor_acrescimo": "5,50",
                    "valor_desconto": "2,00",
                    "observacao": "Ajuste manual",
                }
            },
        )

        self.assertTrue(sucesso, mensagem)
        self.assertIsNotNone(pedido.id)
        self.assertEqual(1, len(pedido.itens))

        item = pedido.itens[0]
        self.assertEqual("Colaborador Teste", item.nome_colaborador_snapshot)
        self.assertEqual("Centro - 001", item.linha_transporte_snapshot)
        self.assertEqual(Decimal("200.00"), item.valor_base)
        self.assertEqual(Decimal("203.50"), item.valor_total)
        self.assertEqual("Ajuste manual", item.observacao)

    def test_bloqueia_desconto_maior_que_base_mais_acrescimo(self):
        vinculo = self.colaborador.linhas_vale_transporte[0]

        sucesso, mensagem, pedido = criar_pedido_vale_transporte(
            competencia="06.2026",
            data_inicial="2026-06-01",
            data_final="2026-06-30",
            quantidade_dias="1",
            equipe_id=str(self.equipe.id),
            forma_pagamento="dinheiro",
            empresa_transporte="Transporte Teste",
            prazo_pagamento="mensal",
            ajustes_itens={
                str(vinculo.id): {
                    "valor_acrescimo": "0,00",
                    "valor_desconto": "11,00",
                }
            },
        )

        self.assertFalse(sucesso)
        self.assertIsNone(pedido)
        self.assertIn("Valor a descontar", mensagem)

    def test_nao_permite_duplicar_pedido_ativo_mesmo_filtro(self):
        sucesso, mensagem, pedido = criar_pedido_vale_transporte(
            competencia="07.2026",
            data_inicial="2026-07-01",
            data_final="2026-07-31",
            quantidade_dias="22",
            equipe_id=str(self.equipe.id),
            forma_pagamento="dinheiro",
            empresa_transporte="Transporte Teste",
            prazo_pagamento="mensal",
        )
        self.assertTrue(sucesso, mensagem)

        sucesso, mensagem, duplicado = criar_pedido_vale_transporte(
            competencia="07.2026",
            data_inicial="2026-07-01",
            data_final="2026-07-31",
            quantidade_dias="22",
            equipe_id=str(self.equipe.id),
            forma_pagamento="dinheiro",
            empresa_transporte="Transporte Teste",
            prazo_pagamento="mensal",
        )

        self.assertFalse(sucesso)
        self.assertEqual(pedido.id, duplicado.id)
        self.assertIn("Já existe pedido ativo", mensagem)

    def test_cancela_pedido_sem_excluir_historico(self):
        sucesso, mensagem, pedido = criar_pedido_vale_transporte(
            competencia="08.2026",
            data_inicial="2026-08-01",
            data_final="2026-08-31",
            quantidade_dias="22",
            equipe_id=str(self.equipe.id),
            forma_pagamento="dinheiro",
            empresa_transporte="Transporte Teste",
            prazo_pagamento="mensal",
        )
        self.assertTrue(sucesso, mensagem)

        sucesso, mensagem = cancelar_pedido_vale_transporte(pedido)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(STATUS_PEDIDO_CANCELADO, pedido.status)
        self.assertEqual(1, ValeTransportePedido.query.count())
        self.assertEqual(1, len(pedido.itens))


if __name__ == "__main__":
    unittest.main()
