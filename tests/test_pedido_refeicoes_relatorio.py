from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.departamento_pessoal.pedido_refeicoes.services import (
    calcular_resumo_totais_relatorio,
    calcular_total_pedido_relatorio,
)


def montar_consumo(tipo, quantidade, valor_total):
    return SimpleNamespace(
        item_cardapio=SimpleNamespace(tipo=tipo, nome=f"Item {tipo}"),
        quantidade=quantidade,
        valor_total=Decimal(valor_total),
    )


def montar_pedido(consumos):
    return SimpleNamespace(consumos=consumos)


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


if __name__ == "__main__":
    unittest.main()
