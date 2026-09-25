from decimal import Decimal
from datetime import date
from types import SimpleNamespace
import unittest

from flask import Flask

from app.departamento_pessoal.pedido_refeicoes.services import (
    buscar_fretes,
    buscar_pedidos_relatorio_refeicoes,
    calcular_resumo_pedidos_relatorio,
    calcular_resumo_totais_relatorio,
    calcular_total_pedido_relatorio,
)
from app.extensions import db
from app.models import (
    Colaborador,
    ConsumoRefeicao,
    Equipe,
    FretePedidoRefeicao,
    ItemCardapio,
    PedidoRefeicao,
    Restaurante,
)


def montar_consumo(tipo, quantidade, valor_total):
    return SimpleNamespace(
        item_cardapio=SimpleNamespace(tipo=tipo, nome=f"Item {tipo}"),
        quantidade=quantidade,
        valor_total=Decimal(valor_total),
    )


def montar_pedido(consumos, data_pedido=None, numero_pedido=None):
    return SimpleNamespace(
        consumos=consumos,
        data_pedido=data_pedido,
        numero_pedido=numero_pedido,
    )


class PedidoRefeicoesRelatorioTestCase(unittest.TestCase):
    def test_total_do_pedido_soma_refeicoes_e_bebidas(self):
        pedido = montar_pedido([
            montar_consumo("Refeição", 2, "40.00"),
            montar_consumo("Bebida", 3, "15.00"),
        ])

        self.assertEqual(calcular_total_pedido_relatorio(pedido), Decimal("55.00"))

    def test_resumo_totaliza_quantidades_e_valores_por_tipo(self):
        pedidos = [
            montar_pedido([
                montar_consumo("Refeição", 2, "40.00"),
                montar_consumo("Bebida", 1, "5.00"),
            ]),
            montar_pedido([
                montar_consumo("Refeição", 1, "20.00"),
                montar_consumo("Bebida", 2, "10.00"),
            ]),
        ]

        resumo = calcular_resumo_totais_relatorio(pedidos)

        self.assertEqual(resumo["quantidade_refeicoes"], 3)
        self.assertEqual(resumo["valor_refeicoes"], Decimal("60.00"))
        self.assertEqual(resumo["quantidade_bebidas"], 3)
        self.assertEqual(resumo["valor_bebidas"], Decimal("15.00"))

    def test_resumo_por_pedidos_lista_data_numero_e_total(self):
        pedidos = [
            montar_pedido(
                [
                    montar_consumo("Refeição", 2, "40.00"),
                    montar_consumo("Bebida", 1, "5.00"),
                ],
                data_pedido="2026-05-20",
                numero_pedido="PED-000001",
            ),
            montar_pedido(
                [
                    montar_consumo("Refeição", 1, "20.00"),
                    montar_consumo("Outros", 1, "99.00"),
                ],
                data_pedido="2026-05-21",
                numero_pedido="PED-000002",
            ),
        ]

        resumo = calcular_resumo_pedidos_relatorio(pedidos)

        self.assertEqual(resumo, [
            {
                "data": "2026-05-20",
                "numero": "PED-000001",
                "total": Decimal("45.00"),
                "total_dia": Decimal("45.00"),
                "linhas_dia": 1,
            },
            {
                "data": "2026-05-21",
                "numero": "PED-000002",
                "total": Decimal("20.00"),
                "total_dia": Decimal("20.00"),
                "linhas_dia": 1,
            },
        ])

    def test_resumo_por_pedidos_totaliza_pedidos_do_mesmo_dia(self):
        pedidos = [
            montar_pedido(
                [montar_consumo("Refeição", 1, "20.00")],
                data_pedido="2026-05-20",
                numero_pedido="PED-000001",
            ),
            montar_pedido(
                [montar_consumo("Bebida", 2, "10.00")],
                data_pedido="2026-05-20",
                numero_pedido="PED-000002",
            ),
            montar_pedido(
                [montar_consumo("Refeição", 1, "30.00")],
                data_pedido="2026-05-21",
                numero_pedido="PED-000003",
            ),
        ]

        resumo = calcular_resumo_pedidos_relatorio(pedidos)

        self.assertEqual(resumo[0]["total_dia"], Decimal("30.00"))
        self.assertEqual(resumo[0]["linhas_dia"], 2)
        self.assertEqual(resumo[1]["total_dia"], Decimal("0.00"))
        self.assertEqual(resumo[1]["linhas_dia"], 0)
        self.assertEqual(resumo[2]["total_dia"], Decimal("30.00"))
        self.assertEqual(resumo[2]["linhas_dia"], 1)


class FiltrosRelatorioRefeicoesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

        equipe = Equipe(nome="Equipe Relatório", slug="equipe-relatorio")
        restaurante = Restaurante(nome="Restaurante Relatório", ativo=True)
        colaborador = Colaborador(
            matricula="REL-001",
            nome="Colaborador Relatório",
            cpf="99999999991",
            equipe=equipe,
            ativo=True,
        )
        db.session.add_all([equipe, restaurante, colaborador])
        db.session.flush()

        item = ItemCardapio(
            restaurante_id=restaurante.id,
            tipo="Refeição",
            nome="Prato Relatório",
            preco=Decimal("25.00"),
            dia_semana="Todos os Dias",
            ativo=True,
        )
        pedido = PedidoRefeicao(
            numero_pedido="PED-RELATORIO",
            equipe_id=equipe.id,
            restaurante_id=restaurante.id,
            data_pedido=date(2026, 9, 10),
            status="Enviado",
            enviado_whatsapp=True,
            quantidade_envios=1,
        )
        db.session.add_all([item, pedido])
        db.session.flush()
        db.session.add_all([
            ConsumoRefeicao(
                pedido_id=pedido.id,
                colaborador_id=colaborador.id,
                item_cardapio_id=item.id,
                quantidade=1,
                valor_unitario=Decimal("25.00"),
                valor_total=Decimal("25.00"),
            ),
            FretePedidoRefeicao(
                data=date(2026, 9, 10),
                restaurante_id=restaurante.id,
                valor=Decimal("10.00"),
                ativo=True,
            ),
        ])
        db.session.commit()
        self.equipe_id = equipe.id
        self.restaurante_id = restaurante.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_emissao_aceita_ids_textuais_dos_filtros_da_tela(self):
        pedidos = buscar_pedidos_relatorio_refeicoes(
            data_inicial="2026-09-01",
            data_final="2026-09-30",
            equipe_id=str(self.equipe_id),
            restaurante_id=str(self.restaurante_id),
            status="Enviado",
        )
        fretes = buscar_fretes(
            ativos_apenas=True,
            data_inicial="2026-09-01",
            data_final="2026-09-30",
            restaurante_id=str(self.restaurante_id),
        )

        self.assertEqual([pedido.numero_pedido for pedido in pedidos], ["PED-RELATORIO"])
        self.assertEqual(len(fretes), 1)

    def test_ids_invalidos_nao_removem_os_filtros_do_relatorio(self):
        pedidos = buscar_pedidos_relatorio_refeicoes(
            data_inicial="2026-09-01",
            data_final="2026-09-30",
            equipe_id="invalido",
        )
        fretes = buscar_fretes(restaurante_id="invalido")

        self.assertEqual(pedidos, [])
        self.assertEqual(fretes, [])


if __name__ == "__main__":
    unittest.main()
