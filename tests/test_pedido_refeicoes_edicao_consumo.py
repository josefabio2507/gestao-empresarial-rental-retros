from types import SimpleNamespace
import unittest

from app.departamento_pessoal.pedido_refeicoes.services import (
    STATUS_PEDIDO_ABERTO,
    STATUS_PEDIDO_CANCELADO,
    STATUS_PEDIDO_ENVIADO,
    STATUS_PEDIDO_FECHADO,
    pedido_pode_ser_editado,
    pedido_pode_ser_cancelado,
)


def montar_pedido(status, quantidade_envios=0):
    return SimpleNamespace(status=status, quantidade_envios=quantidade_envios)


class PedidoRefeicoesEdicaoConsumoTestCase(unittest.TestCase):
    def test_pedido_aberto_permite_edicao_de_consumo(self):
        self.assertTrue(pedido_pode_ser_editado(montar_pedido(STATUS_PEDIDO_ABERTO)))

    def test_pedido_fechado_permite_edicao_de_consumo(self):
        self.assertTrue(pedido_pode_ser_editado(montar_pedido(STATUS_PEDIDO_FECHADO)))

    def test_pedido_enviado_uma_vez_permite_edicao_de_consumo(self):
        self.assertTrue(
            pedido_pode_ser_editado(
                montar_pedido(STATUS_PEDIDO_ENVIADO, quantidade_envios=1)
            )
        )

    def test_pedido_enviado_duas_vezes_bloqueia_edicao_de_consumo(self):
        self.assertFalse(
            pedido_pode_ser_editado(
                montar_pedido(STATUS_PEDIDO_ENVIADO, quantidade_envios=2)
            )
        )

    def test_pedido_cancelado_bloqueia_edicao_de_consumo(self):
        self.assertFalse(pedido_pode_ser_editado(montar_pedido(STATUS_PEDIDO_CANCELADO)))

    def test_pedido_aberto_pode_ser_cancelado(self):
        self.assertTrue(pedido_pode_ser_cancelado(montar_pedido(STATUS_PEDIDO_ABERTO)))

    def test_pedido_fechado_pode_ser_cancelado(self):
        self.assertTrue(pedido_pode_ser_cancelado(montar_pedido(STATUS_PEDIDO_FECHADO)))

    def test_pedido_enviado_uma_vez_pode_ser_cancelado(self):
        self.assertTrue(
            pedido_pode_ser_cancelado(
                montar_pedido(STATUS_PEDIDO_ENVIADO, quantidade_envios=1)
            )
        )

    def test_pedido_enviado_duas_vezes_pode_ser_cancelado(self):
        self.assertTrue(
            pedido_pode_ser_cancelado(
                montar_pedido(STATUS_PEDIDO_ENVIADO, quantidade_envios=2)
            )
        )

    def test_pedido_cancelado_nao_pode_ser_cancelado_novamente(self):
        self.assertFalse(pedido_pode_ser_cancelado(montar_pedido(STATUS_PEDIDO_CANCELADO)))


if __name__ == "__main__":
    unittest.main()
