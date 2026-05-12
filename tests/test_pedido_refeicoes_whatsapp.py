import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.departamento_pessoal.pedido_refeicoes.services import gerar_mensagem_whatsapp


def montar_pedido(observacao=None):
    return SimpleNamespace(
        numero_pedido="PED-000021",
        data_pedido=date(2026, 5, 11),
        equipe=SimpleNamespace(nome="TMC - SANTOS"),
        restaurante=SimpleNamespace(nome="CASA DO SOL"),
        observacao=observacao,
    )


def montar_consumo(colaborador, tipo, item_nome, quantidade, observacao=None):
    return SimpleNamespace(
        colaborador=colaborador,
        item_cardapio=SimpleNamespace(tipo=tipo, nome=item_nome),
        quantidade=quantidade,
        observacao=observacao,
    )


class PedidoRefeicoesWhatsappTestCase(unittest.TestCase):
    def gerar_mensagem(self, pedido, consumos):
        resumo = {
            "Bebida": {
                "SUCO": {
                    "quantidade": 1,
                    "valor_total": Decimal("5.00"),
                },
            },
            "Refeição": {
                "PRATO": {
                    "quantidade": 1,
                    "valor_total": Decimal("20.00"),
                },
            },
        }

        with patch(
            "app.departamento_pessoal.pedido_refeicoes.services.buscar_consumos_do_pedido",
            return_value=consumos,
        ), patch(
            "app.departamento_pessoal.pedido_refeicoes.services.calcular_resumo_pedido",
            return_value=(resumo, Decimal("25.00")),
        ):
            return gerar_mensagem_whatsapp(pedido)

    def test_observacao_geral_do_pedido_aparece_no_cabecalho(self):
        colaborador = SimpleNamespace(id=1, nome="COLABORADOR")
        mensagem = self.gerar_mensagem(
            montar_pedido(observacao=" Entregar sem atraso "),
            [montar_consumo(colaborador, "Refeição", "PRATO", 1)],
        )

        self.assertIn("Obs. do pedido: Entregar sem atraso", mensagem)
        self.assertLess(
            mensagem.index("Restaurante: CASA DO SOL"),
            mensagem.index("Obs. do pedido: Entregar sem atraso"),
        )

    def test_observacao_geral_vazia_nao_gera_linha(self):
        colaborador = SimpleNamespace(id=1, nome="COLABORADOR")
        mensagem = self.gerar_mensagem(
            montar_pedido(observacao="   "),
            [montar_consumo(colaborador, "Refeição", "PRATO", 1)],
        )

        self.assertNotIn("Obs. do pedido:", mensagem)

    def test_observacao_de_consumo_nao_duplica_para_refeicao_e_bebida(self):
        colaborador = SimpleNamespace(id=1, nome="COLABORADOR")
        mensagem = self.gerar_mensagem(
            montar_pedido(),
            [
                montar_consumo(colaborador, "Bebida", "SUCO", 1, "Salada"),
                montar_consumo(colaborador, "Refeição", "PRATO", 1, "Salada"),
            ],
        )

        self.assertEqual(mensagem.count("💬 Obs: Salada"), 1)
        self.assertIn("🥤 SUCO | Qtd: 1", mensagem)
        self.assertIn("🍽️ PRATO | Qtd: 1", mensagem)

    def test_consumo_sem_observacao_nao_gera_linha(self):
        colaborador = SimpleNamespace(id=1, nome="COLABORADOR")
        mensagem = self.gerar_mensagem(
            montar_pedido(),
            [montar_consumo(colaborador, "Refeição", "PRATO", 1, "   ")],
        )

        self.assertNotIn("💬 Obs:", mensagem)

    def test_valores_por_item_continuam_ocultos_e_total_geral_permanece(self):
        colaborador = SimpleNamespace(id=1, nome="COLABORADOR")
        mensagem = self.gerar_mensagem(
            montar_pedido(),
            [montar_consumo(colaborador, "Refeição", "PRATO", 1)],
        )

        self.assertIn("- PRATO | Qtd: 1", mensagem)
        self.assertIn("💰 *Total geral:* R$ 25,00", mensagem)
        self.assertNotIn("R$ 20,00", mensagem)
        self.assertNotIn("R$ 5,00", mensagem)


if __name__ == "__main__":
    unittest.main()
