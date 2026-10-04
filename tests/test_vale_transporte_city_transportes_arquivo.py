from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.departamento_pessoal.vale_transporte.city_transportes_arquivo import (
    gerar_arquivo_city_transportes,
    nome_arquivo_city_transportes,
    validar_pedido_city_transportes,
)


def item_city(
    cpf="52998224725",
    nome="José da Silva",
    tarifa="10.50",
    dias=22,
    empresa="City Transportes",
    forma="cartao_transporte",
    design="04",
    aplicacao="400",
    linha="",
    total=None,
):
    tarifa_decimal = Decimal(tarifa)
    return SimpleNamespace(
        id=1,
        ativo=True,
        forma_pagamento=forma,
        empresa_transporte_snapshot=empresa,
        nome_colaborador_snapshot=nome,
        colaborador=SimpleNamespace(cpf=cpf),
        quantidade_dias=dias,
        tarifa_diaria=tarifa_decimal,
        valor_acrescimo=Decimal("0.00"),
        valor_desconto=Decimal("0.00"),
        valor_total=Decimal(total) if total is not None else tarifa_decimal * dias,
        city_design_cartao_snapshot=design,
        city_aplicacao_snapshot=aplicacao,
        linha_transporte_snapshot=linha,
    )


def pedido(*itens, status="Gerado"):
    return SimpleNamespace(id=7, competencia="10.2026", status=status, itens=list(itens))


class ArquivoCityTransportesTestCase(unittest.TestCase):
    def test_gera_layout_0800_com_campos_oficiais(self):
        conteudo, resultado = gerar_arquivo_city_transportes(pedido(item_city()))
        self.assertEqual(
            b"0800\r\n52998224725|22|1050|JOS\xc9 DA SILVA|04|400\r\n",
            conteudo,
        )
        self.assertEqual(1, resultado.quantidade_colaboradores)
        self.assertEqual(Decimal("231.00"), resultado.valor_total_creditos)

    def test_ignora_colaborador_com_valor_zero(self):
        zero = item_city(cpf="11144477735", nome="Sem crédito", total="0.00")
        zero.id = 2
        conteudo, resultado = gerar_arquivo_city_transportes(pedido(item_city(), zero))
        self.assertEqual(1, resultado.itens_ignorados)
        self.assertNotIn(b"11144477735", conteudo)

    def test_inclui_city_e_ignora_outra_operadora_em_dinheiro_sem_duplicar(self):
        city = item_city(
            tarifa="10.60",
            dias=3,
            total="31.80",
            aplicacao="",
            linha="LINHA MUNICIPAL GUARUJÁ - 2",
        )
        dinheiro = item_city(
            empresa="TRANSPORTE MARÍTIMO",
            forma="dinheiro",
            tarifa="6.00",
            dias=3,
            total="0.00",
        )
        dinheiro.id = 2

        conteudo, resultado = gerar_arquivo_city_transportes(
            pedido(city, dinheiro)
        )

        self.assertEqual(1, resultado.quantidade_colaboradores)
        self.assertEqual(1, resultado.itens_ignorados)
        self.assertEqual(Decimal("31.80"), resultado.valor_total_creditos)
        self.assertEqual(1, conteudo.count(b"52998224725"))
        self.assertIn(b"|3|1060|JOS\xc9 DA SILVA|04|400", conteudo)

    def test_exige_design_e_aplicacao(self):
        resultado = validar_pedido_city_transportes(
            pedido(item_city(design="", aplicacao=""))
        )
        self.assertFalse(resultado.valido)
        self.assertTrue(any("design" in erro for erro in resultado.erros))

    def test_bloqueia_pedido_de_outra_operadora(self):
        resultado = validar_pedido_city_transportes(
            pedido(item_city(empresa="BR Mobilidade"))
        )
        self.assertFalse(resultado.valido)
        self.assertTrue(any("não pertence exclusivamente" in erro for erro in resultado.erros))

    def test_consolida_tarifas_do_mesmo_cpf(self):
        segundo = item_city(tarifa="2.50")
        segundo.id = 2
        conteudo, resultado = gerar_arquivo_city_transportes(
            pedido(item_city(), segundo)
        )
        self.assertEqual(1, resultado.quantidade_colaboradores)
        self.assertIn(b"|22|1300|", conteudo)

    def test_bloqueia_metadados_divergentes_para_mesmo_cpf(self):
        segundo = item_city(aplicacao="410")
        segundo.id = 2
        resultado = validar_pedido_city_transportes(pedido(item_city(), segundo))
        self.assertFalse(resultado.valido)
        self.assertTrue(any("divergentes" in erro for erro in resultado.erros))

    def test_nome_do_arquivo(self):
        self.assertEqual(
            "PEDIDO_VT_CITY_TRANSPORTES_2026_10.txt",
            nome_arquivo_city_transportes(pedido(item_city())),
        )


if __name__ == "__main__":
    unittest.main()
