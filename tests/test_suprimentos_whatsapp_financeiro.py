import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.services.suprimentos_service import gerar_mensagem_whatsapp_aprovacao_cotacao


class SuprimentosWhatsAppFinanceiroTestCase(unittest.TestCase):
    def _cotacao_fake(self):
        requisicao = SimpleNamespace(
            numero="REQ-001",
            centro_custo=SimpleNamespace(nome="Administrativo"),
            solicitante=SimpleNamespace(nome="Solicitante Teste"),
            sub_centro_custo_equipe=None,
            sub_centro_custo_veiculo=None,
            equipe=None,
            veiculo_placa="ABC1D23",
        )
        proposta = SimpleNamespace(
            selecionada=True,
            fornecedor_razao_social_snapshot="FORNECEDOR TESTE LTDA",
            item_descricao_snapshot="PECA TESTE",
            quantidade_snapshot=Decimal("2"),
            unidade_medida_snapshot="UN",
            valor_total=Decimal("300.00"),
        )
        return SimpleNamespace(
            id=10,
            numero="COT-001",
            requisicao=requisicao,
            aprovador=SimpleNamespace(nome="Aprovador Teste"),
            propostas=[proposta],
            aprovacao_publica_token_hash=None,
            aprovacao_publica_expira_em=None,
        )

    @patch("app.services.suprimentos_service.link_aprovacao_publica_cotacao", return_value="https://rental.test/aprovar")
    @patch("app.services.suprimentos_service.gerar_token_aprovacao_publica_cotacao", return_value="token-teste")
    @patch("app.services.suprimentos_service._ordem_financeira_cotacao")
    def test_whatsapp_aprovacao_exibe_forma_pix_sem_cartao(self, ordem_mock, *_):
        ordem_mock.return_value = SimpleNamespace(
            tipo_pagamento_financeiro="Faturado",
            forma_pagamento_financeiro="Pix",
            cartao_credito=None,
        )

        mensagem = gerar_mensagem_whatsapp_aprovacao_cotacao(self._cotacao_fake())

        self.assertIn("Tipo de pagamento: Faturado", mensagem)
        self.assertIn("Forma de pagamento: Pix", mensagem)
        self.assertNotIn("Cartao:", mensagem)

    @patch("app.services.suprimentos_service.link_aprovacao_publica_cotacao", return_value="https://rental.test/aprovar")
    @patch("app.services.suprimentos_service.gerar_token_aprovacao_publica_cotacao", return_value="token-teste")
    @patch("app.services.suprimentos_service._ordem_financeira_cotacao")
    def test_whatsapp_aprovacao_exibe_cartao_seguro(self, ordem_mock, *_):
        cartao = SimpleNamespace(identificacao_segura="Cartao Administrativo - Banco Itau - final 1234")
        ordem_mock.return_value = SimpleNamespace(
            tipo_pagamento_financeiro="Cartao de Credito",
            forma_pagamento_financeiro="Cartao de Credito",
            cartao_credito=cartao,
        )

        mensagem = gerar_mensagem_whatsapp_aprovacao_cotacao(self._cotacao_fake())

        self.assertIn("Forma de pagamento: Cartao de Credito", mensagem)
        self.assertIn("Cartao: Cartao Administrativo - Banco Itau - final 1234", mensagem)
        self.assertNotIn("CVV", mensagem.upper())
        self.assertNotIn("senha", mensagem.lower())


if __name__ == "__main__":
    unittest.main()
