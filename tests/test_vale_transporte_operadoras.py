from types import SimpleNamespace
import unittest

from app.departamento_pessoal.vale_transporte.operadoras import (
    BR_MOBILIDADE,
    CITY_TRANSPORTES,
    PEDIDO_MISTO,
    SEM_INTEGRACAO,
    codigo_operadora_por_nome,
    resolver_operadora_pedido,
)


def _pedido(*empresas):
    return SimpleNamespace(
        itens=[
            SimpleNamespace(ativo=True, empresa_transporte_snapshot=empresa)
            for empresa in empresas
        ]
    )


class OperadorasValeTransporteTestCase(unittest.TestCase):
    def test_normaliza_variacoes_das_operadoras_suportadas(self):
        self.assertEqual(BR_MOBILIDADE, codigo_operadora_por_nome("BR MOBILIDADE"))
        self.assertEqual(
            CITY_TRANSPORTES,
            codigo_operadora_por_nome("  City Transportes  "),
        )

    def test_pedido_exclusivo_br_habilita_conector_br(self):
        resultado = resolver_operadora_pedido(_pedido("BR Mobilidade", "BR MOBILIDADE"))
        self.assertEqual(BR_MOBILIDADE, resultado.codigo)

    def test_pedido_exclusivo_city_habilita_conector_city(self):
        resultado = resolver_operadora_pedido(_pedido("City Transportes"))
        self.assertEqual(CITY_TRANSPORTES, resultado.codigo)

    def test_pedido_misto_bloqueia_integracao(self):
        resultado = resolver_operadora_pedido(
            _pedido("BR Mobilidade", "City Transportes")
        )
        self.assertEqual(PEDIDO_MISTO, resultado.codigo)
        self.assertEqual(2, len(resultado.empresas))

    def test_empresa_sem_conector_nao_habilita_integracao(self):
        resultado = resolver_operadora_pedido(_pedido("Outra Empresa"))
        self.assertEqual(SEM_INTEGRACAO, resultado.codigo)

    def test_itens_inativos_nao_definem_operadora(self):
        pedido = _pedido("City Transportes")
        pedido.itens.append(
            SimpleNamespace(
                ativo=False,
                empresa_transporte_snapshot="BR Mobilidade",
            )
        )
        self.assertEqual(CITY_TRANSPORTES, resolver_operadora_pedido(pedido).codigo)


if __name__ == "__main__":
    unittest.main()
