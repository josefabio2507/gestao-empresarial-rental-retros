import unittest

from app import create_app
from app.extensions import db
from app.models import Colaborador, Equipe, LinhaOnibus
from app.departamento_pessoal.vale_transporte.services import (
    atualizar_pagamento_vinculo,
    salvar_vinculo_colaborador_linha,
)


class ValeTransportePeriodicidadePagamentoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            WTF_CSRF_ENABLED=False,
            AUTO_MIGRATE_ON_START=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

        equipe = Equipe(nome="Operacao", slug="operacao", ativo=True)
        self.colaborador = Colaborador(
            matricula="100",
            nome="Colaborador Teste",
            cpf="12345678901",
            cargo="Operador",
            equipe=equipe,
            vale_transporte_optante=True,
            ativo=True,
        )
        self.linha = LinhaOnibus(
            nome="Centro",
            empresa_transporte="Transporte Teste",
            valor_tarifa_dia=10,
            ativo=True,
        )
        db.session.add_all([equipe, self.colaborador, self.linha])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_salva_periodicidade_semanal_no_vinculo(self):
        sucesso, mensagem = salvar_vinculo_colaborador_linha(
            colaborador=self.colaborador,
            linha_onibus_id=self.linha.id,
            tipo_pagamento="dinheiro",
            periodicidade_pagamento="semanal",
        )

        self.assertTrue(sucesso, mensagem)
        vinculo = self.colaborador.linhas_vale_transporte[0]
        self.assertEqual("semanal", vinculo.periodicidade_pagamento)

    def test_rejeita_periodicidade_invalida(self):
        sucesso, mensagem = salvar_vinculo_colaborador_linha(
            colaborador=self.colaborador,
            linha_onibus_id=self.linha.id,
            tipo_pagamento="dinheiro",
            periodicidade_pagamento="diaria",
        )

        self.assertFalse(sucesso)
        self.assertEqual("Periodicidade do pagamento inválida.", mensagem)

    def test_atualiza_tipo_e_periodicidade_pagamento(self):
        sucesso, mensagem = salvar_vinculo_colaborador_linha(
            colaborador=self.colaborador,
            linha_onibus_id=self.linha.id,
            tipo_pagamento="dinheiro",
            periodicidade_pagamento="mensal",
        )
        self.assertTrue(sucesso, mensagem)
        vinculo = self.colaborador.linhas_vale_transporte[0]

        sucesso, mensagem = atualizar_pagamento_vinculo(
            vinculo,
            tipo_pagamento="cartao_transporte",
            periodicidade_pagamento="semanal",
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual("cartao_transporte", vinculo.tipo_pagamento)
        self.assertEqual("semanal", vinculo.periodicidade_pagamento)


if __name__ == "__main__":
    unittest.main()
