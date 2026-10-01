from datetime import datetime, timedelta
from decimal import Decimal
import unittest
from uuid import uuid4

from app import create_app
from app.extensions import db
from app.models import Colaborador, Equipe, LinhaOnibus
from app.departamento_pessoal.vale_transporte.services import (
    buscar_historico_vale_transporte_colaborador,
    criar_pedido_vale_transporte,
    listar_colaboradores_ativos_para_historico,
    resolver_colaborador_ativo_para_historico,
    salvar_vinculo_colaborador_linha,
)


class ValeTransporteHistoricoTestCase(unittest.TestCase):
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

        sufixo = uuid4().hex[:8]
        equipe = Equipe(nome="Operação", slug=f"operacao-{sufixo}", ativo=True)
        self.ativo = Colaborador(
            matricula=f"100-{sufixo}",
            nome="Ana Ativa",
            cpf=f"1{sufixo}"[:11],
            equipe=equipe,
            vale_transporte_optante=True,
            ativo=True,
        )
        self.inativo = Colaborador(
            matricula=f"200-{sufixo}",
            nome="Inácio Inativo",
            cpf=f"2{sufixo}"[:11],
            equipe=equipe,
            vale_transporte_optante=True,
            ativo=False,
        )
        linha = LinhaOnibus(
            nome="Centro",
            codigo="001",
            empresa_transporte="Transporte Teste",
            valor_tarifa_dia=Decimal("10.00"),
            ativo=True,
        )
        db.session.add_all([equipe, self.ativo, self.inativo, linha])
        db.session.commit()
        sucesso, mensagem = salvar_vinculo_colaborador_linha(
            self.ativo, linha.id, "dinheiro", "mensal"
        )
        self.assertTrue(sucesso, mensagem)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _criar_pedido(self, competencia, data_inicial, data_final):
        sucesso, mensagem, pedido = criar_pedido_vale_transporte(
            competencia=competencia,
            data_inicial=data_inicial,
            data_final=data_final,
            quantidade_dias="20",
            colaborador=self.ativo.matricula,
            prazo_pagamento="mensal",
        )
        self.assertTrue(sucesso, mensagem)
        return pedido

    def test_pesquisa_historico_considera_somente_colaboradores_ativos(self):
        self.assertEqual([self.ativo], listar_colaboradores_ativos_para_historico())
        self.assertEqual(
            self.ativo,
            resolver_colaborador_ativo_para_historico(colaborador_texto="Ana Ativa"),
        )
        with self.assertRaisesRegex(ValueError, "disponível na lista"):
            resolver_colaborador_ativo_para_historico(
                colaborador_texto=self.inativo.matricula
            )

        with self.assertRaisesRegex(ValueError, "disponível na lista"):
            resolver_colaborador_ativo_para_historico(colaborador_texto="Ana")

    def test_historico_ordena_pela_criacao_do_pedido_decrescente(self):
        antigo = self._criar_pedido("08.2026", "2026-08-01", "2026-08-31")
        recente = self._criar_pedido("09.2026", "2026-09-01", "2026-09-30")
        antigo.criado_em = datetime.now() - timedelta(days=1)
        recente.criado_em = datetime.now()
        db.session.commit()

        itens = buscar_historico_vale_transporte_colaborador(self.ativo.id)

        self.assertEqual([recente.id, antigo.id], [item.pedido_id for item in itens])
        self.assertEqual("Centro - 001", itens[0].linha_transporte_snapshot)
        self.assertEqual(Decimal("10.00"), itens[0].tarifa_diaria)


if __name__ == "__main__":
    unittest.main()
