import unittest
from datetime import date
from types import SimpleNamespace

from app.departamento_pessoal.pedido_refeicoes.services import (
    DIA_SEMANA_TODOS,
    dia_semana_por_data,
    item_disponivel_para_data,
)


def item(tipo="Refeição", dia_semana=DIA_SEMANA_TODOS):
    return SimpleNamespace(tipo=tipo, dia_semana=dia_semana)


class CardapioDiaSemanaTestCase(unittest.TestCase):
    def test_mapeia_datas_para_dias_da_semana_em_portugues(self):
        self.assertEqual(dia_semana_por_data(date(2026, 5, 11)), "Segunda-Feira")
        self.assertEqual(dia_semana_por_data(date(2026, 5, 12)), "Terça-Feira")
        self.assertEqual(dia_semana_por_data(date(2026, 5, 13)), "Quarta-Feira")
        self.assertEqual(dia_semana_por_data(date(2026, 5, 14)), "Quinta-Feira")
        self.assertEqual(dia_semana_por_data(date(2026, 5, 15)), "Sexta-Feira")
        self.assertEqual(dia_semana_por_data(date(2026, 5, 16)), "Sábado")
        self.assertEqual(dia_semana_por_data(date(2026, 5, 17)), "Domingo")

    def test_refeicao_do_mesmo_dia_fica_disponivel(self):
        self.assertTrue(
            item_disponivel_para_data(
                item(dia_semana="Terça-Feira"),
                date(2026, 5, 12),
            )
        )

    def test_refeicao_de_outro_dia_fica_indisponivel(self):
        self.assertFalse(
            item_disponivel_para_data(
                item(dia_semana="Quarta-Feira"),
                date(2026, 5, 12),
            )
        )

    def test_refeicao_todos_os_dias_fica_disponivel(self):
        self.assertTrue(
            item_disponivel_para_data(
                item(dia_semana=DIA_SEMANA_TODOS),
                date(2026, 5, 12),
            )
        )

    def test_bebida_nao_e_bloqueada_por_dia_da_semana(self):
        self.assertTrue(
            item_disponivel_para_data(
                item(tipo="Bebida", dia_semana="Domingo"),
                date(2026, 5, 12),
            )
        )


if __name__ == "__main__":
    unittest.main()
