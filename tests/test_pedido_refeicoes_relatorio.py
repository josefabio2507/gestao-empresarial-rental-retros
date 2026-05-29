from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.departamento_pessoal.pedido_refeicoes.services import (
    calcular_resumo_pedidos_relatorio,
    calcular_resumo_totais_relatorio,
    calcular_total_pedido_relatorio,
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


if __name__ == "__main__":
    unittest.main()
