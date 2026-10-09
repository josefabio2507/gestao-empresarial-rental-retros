from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.departamento_pessoal.vale_transporte.br_mobilidade_arquivo import (
    cpf_valido,
    gerar_arquivo_br_mobilidade,
    nome_arquivo_br_mobilidade,
    validar_pedido_br_mobilidade,
)


def item_br(
    cpf="52998224725",
    nome="José da Silva",
    tarifa="10.00",
    dias=22,
    empresa="BR Mobilidade",
    forma="cartao_transporte",
    acrescimo="0.00",
    desconto="0.00",
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
        valor_acrescimo=Decimal(acrescimo),
        valor_desconto=Decimal(desconto),
        valor_total=(tarifa_decimal * dias + Decimal(acrescimo) - Decimal(desconto)),
    )


def pedido(*itens, competencia="10.2026", status="Gerado"):
    return SimpleNamespace(
        id=42,
        competencia=competencia,
        status=status,
        itens=list(itens),
    )


class ArquivoBRMobilidadeTestCase(unittest.TestCase):
    def test_gera_layout_0200_em_centavos_com_crlf(self):
        conteudo, resultado = gerar_arquivo_br_mobilidade(pedido(item_br()))

        self.assertEqual(
            b"0200\r\n52998224725|22|1000|JOS\xc9 DA SILVA\r\n",
            conteudo,
        )
        self.assertEqual(1, resultado.quantidade_colaboradores)
        self.assertEqual(Decimal("220.00"), resultado.valor_total_creditos)

    def test_consolida_linhas_do_mesmo_cpf_sem_duplicar_registro(self):
        primeiro = item_br(tarifa="10.00")
        segundo = item_br(tarifa="8.50")
        segundo.id = 2

        conteudo, resultado = gerar_arquivo_br_mobilidade(pedido(primeiro, segundo))

        self.assertEqual(1, resultado.quantidade_colaboradores)
        self.assertIn(b"52998224725|22|1850|", conteudo)
        self.assertEqual(Decimal("407.00"), resultado.valor_total_creditos)

    def test_bloqueia_linhas_do_mesmo_cpf_com_dias_diferentes(self):
        primeiro = item_br(dias=22)
        segundo = item_br(dias=20)
        segundo.id = 2

        resultado = validar_pedido_br_mobilidade(pedido(primeiro, segundo))

        self.assertFalse(resultado.valido)
        self.assertTrue(any("quantidades de dias diferentes" in erro for erro in resultado.erros))

    def test_bloqueia_cpf_invalido(self):
        resultado = validar_pedido_br_mobilidade(pedido(item_br(cpf="12345678901")))

        self.assertFalse(resultado.valido)
        self.assertTrue(any("CPF inválido" in erro for erro in resultado.erros))

    def test_bloqueia_acrescimo_que_layout_nao_representa(self):
        resultado = validar_pedido_br_mobilidade(
            pedido(item_br(acrescimo="1.00"))
        )

        self.assertFalse(resultado.valido)
        self.assertTrue(any("acréscimos ou descontos" in erro for erro in resultado.erros))

    def test_bloqueia_pedido_com_outras_operadoras(self):
        dinheiro = item_br(forma="dinheiro")
        outra_empresa = item_br(empresa="Outra Empresa")
        valido = item_br()

        resultado = validar_pedido_br_mobilidade(
            pedido(dinheiro, outra_empresa, valido)
        )

        self.assertFalse(resultado.valido)
        self.assertTrue(any("mais de uma empresa" in erro for erro in resultado.erros))

    def test_arquivo_0200_ignora_colaborador_com_total_zero(self):
        com_credito = item_br()
        sem_credito = item_br(
            cpf="11144477735",
            nome="Colaborador sem crédito",
            tarifa="13.70",
            dias=3,
        )
        sem_credito.id = 2
        sem_credito.valor_total = Decimal("0.00")

        conteudo, resultado = gerar_arquivo_br_mobilidade(
            pedido(com_credito, sem_credito)
        )

        self.assertTrue(resultado.valido)
        self.assertEqual(1, resultado.quantidade_colaboradores)
        self.assertEqual(1, resultado.itens_ignorados)
        self.assertEqual(Decimal("220.00"), resultado.valor_total_creditos)
        self.assertIn(b"52998224725|22|1000|", conteudo)
        self.assertNotIn(b"11144477735", conteudo)

    def test_bloqueia_arquivo_quando_todos_os_colaboradores_tem_total_zero(self):
        sem_credito = item_br()
        sem_credito.valor_total = Decimal("0.00")

        resultado = validar_pedido_br_mobilidade(pedido(sem_credito))

        self.assertFalse(resultado.valido)
        self.assertEqual(0, resultado.itens_ignorados)
        self.assertTrue(any("não pertence exclusivamente" in erro for erro in resultado.erros))

    def test_bloqueia_valor_a_receber_negativo(self):
        negativo = item_br()
        negativo.valor_total = Decimal("-1.00")

        resultado = validar_pedido_br_mobilidade(pedido(item_br(), negativo))

        self.assertFalse(resultado.valido)
        self.assertTrue(any("não pode ser negativo" in erro for erro in resultado.erros))

    def test_bloqueia_pedido_cancelado(self):
        resultado = validar_pedido_br_mobilidade(
            pedido(item_br(), status="Cancelado")
        )

        self.assertFalse(resultado.valido)
        self.assertIn("Pedido cancelado", resultado.erros[0])

    def test_respeita_limite_maximo_de_registros(self):
        segundo = item_br(cpf="11144477735", nome="Maria")
        segundo.id = 2
        with patch(
            "app.departamento_pessoal.vale_transporte.br_mobilidade_arquivo.LIMITE_REGISTROS",
            1,
        ):
            resultado = validar_pedido_br_mobilidade(pedido(item_br(), segundo))

        self.assertFalse(resultado.valido)
        self.assertTrue(any("limite de 1 registros" in erro for erro in resultado.erros))

    def test_informa_erro_quando_nome_nao_cabe_na_codificacao(self):
        with self.assertRaisesRegex(ValueError, "codificação configurada"):
            gerar_arquivo_br_mobilidade(
                pedido(item_br(nome="Usuário 🚍")),
                encoding="cp1252",
            )

    def test_nome_do_arquivo_usa_competencia_ano_mes(self):
        self.assertEqual(
            "PEDIDO_VT_BR_MOBILIDADE_2026_10.txt",
            nome_arquivo_br_mobilidade(pedido(item_br())),
        )

    def test_validador_de_cpf_rejeita_repeticoes_e_aceita_cpf_valido(self):
        self.assertTrue(cpf_valido("529.982.247-25"))
        self.assertFalse(cpf_valido("11111111111"))


if __name__ == "__main__":
    unittest.main()
