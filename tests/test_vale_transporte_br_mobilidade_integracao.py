from datetime import date, datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    Colaborador,
    Equipe,
    LinhaOnibus,
    NivelAcesso,
    Usuario,
    ValeTransportePedido,
    ValeTransportePedidoItem,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_integracao import (
    buscar_integracoes_pendentes,
    preparar_integracao_br_mobilidade,
    registrar_criacao_manual_br_mobilidade,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_conferencia import (
    ResumoPedidoPortal,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_finalizacao import (
    autorizar_finalizacao,
    iniciar_finalizacao,
    preparar_conferencia_finalizacao,
    registrar_falha_finalizacao,
    registrar_finalizacao_sucesso,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_documentos import (
    capturar_documentos_para_download,
)
from app.departamento_pessoal.vale_transporte.br_mobilidade_portal import (
    ResultadoDocumentosBRMobilidade,
)


class IntegracaoBRMobilidadeTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "AUTO_MIGRATE_ON_START": False,
            "BR_MOBILIDADE_INTEGRACAO_ATIVA": True,
            "BR_MOBILIDADE_AMBIENTE": "local",
        })
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

        equipe = Equipe(nome="Equipe Teste", slug="equipe-teste", ativo=True)
        colaborador = Colaborador(
            matricula="BR-001",
            nome="Usuário Teste",
            cpf="52998224725",
            cargo="Teste",
            equipe=equipe,
            vale_transporte_optante=True,
            ativo=True,
        )
        linha = LinhaOnibus(
            nome="Linha Teste",
            codigo="BR01",
            empresa_transporte="BR Mobilidade",
            valor_tarifa_dia=Decimal("10.00"),
            ativo=True,
        )
        pedido = ValeTransportePedido(
            competencia="10.2026",
            data_inicial=date(2026, 10, 1),
            data_final=date(2026, 10, 31),
            quantidade_dias_padrao=22,
            prazo_pagamento="mensal",
            status="Gerado",
        )
        nivel = NivelAcesso(nome="Administrador", slug="admin-teste", ativo=True)
        usuario = Usuario(
            nome="Autorizador",
            email="autorizador@teste.com",
            senha_hash="teste",
            nivel_acesso=nivel,
            ativo=True,
        )
        db.session.add_all([equipe, colaborador, linha, pedido, nivel, usuario])
        db.session.flush()
        db.session.add(
            ValeTransportePedidoItem(
                pedido_id=pedido.id,
                colaborador_id=colaborador.id,
                linha_onibus_id=linha.id,
                matricula_snapshot=colaborador.matricula,
                nome_colaborador_snapshot=colaborador.nome,
                empresa_transporte_snapshot="BR Mobilidade",
                linha_transporte_snapshot="Linha Teste",
                forma_pagamento="cartao_transporte",
                tarifa_diaria=Decimal("10.00"),
                quantidade_dias=22,
                valor_base=Decimal("220.00"),
                valor_acrescimo=Decimal("0.00"),
                valor_desconto=Decimal("0.00"),
                valor_total=Decimal("220.00"),
                ativo=True,
            )
        )
        db.session.commit()
        self.pedido = pedido
        self.usuario = usuario

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def test_prepara_execucao_persistente_com_nome_e_hash_unicos(self):
        integracao = preparar_integracao_br_mobilidade(
            self.pedido,
            data_liberacao=date(2026, 10, 5),
        )

        self.assertEqual("AGUARDANDO_ENVIO", integracao.status_interno)
        self.assertIn(f"_P{self.pedido.id}_", integracao.nome_arquivo)
        self.assertEqual(64, len(integracao.hash_arquivo))
        self.assertTrue(integracao.arquivo_conteudo.startswith(b"0200\r\n"))

        with self.assertRaisesRegex(ValueError, "integração em andamento"):
            preparar_integracao_br_mobilidade(
                self.pedido,
                data_liberacao=date(2026, 10, 5),
            )

    def test_preparacao_manual_nao_entra_na_fila_de_envio(self):
        integracao = preparar_integracao_br_mobilidade(
            self.pedido,
            data_liberacao=date(2026, 10, 5),
            modo_manual=True,
        )

        self.assertEqual("AGUARDANDO_CRIACAO_MANUAL", integracao.status_interno)
        self.assertEqual(date(2026, 10, 5), integracao.data_liberacao)
        self.assertNotIn(integracao.id, [item.id for item in buscar_integracoes_pendentes()])
        with self.assertRaisesRegex(ValueError, "integração em andamento"):
            preparar_integracao_br_mobilidade(
                self.pedido,
                data_liberacao=date(2026, 10, 5),
                modo_manual=True,
            )

    def test_registra_criacao_manual_apos_conferencia(self):
        integracao = preparar_integracao_br_mobilidade(
            self.pedido,
            data_liberacao=date(2026, 10, 6),
            modo_manual=True,
        )
        resumo = ResumoPedidoPortal(
            numero="2970860",
            data_pedido=date(2026, 10, 2),
            data_liberacao=date(2026, 10, 6),
            status="Novo",
            valor_creditos=Decimal("220.00"),
            taxa_administrativa=Decimal("6.60"),
            valor_cartoes=Decimal("0.00"),
            valor_total=Decimal("226.60"),
            quantidade_usuarios=1,
        )

        integracao, conferencia = registrar_criacao_manual_br_mobilidade(
            integracao.id, resumo
        )

        self.assertTrue(conferencia.aprovado)
        self.assertEqual("2970860", integracao.numero_pedido_portal)
        self.assertEqual("FINALIZADO_PORTAL", integracao.status_interno)
        self.assertEqual("Novo", integracao.status_portal)
        self.assertEqual(Decimal("6.60"), integracao.taxa_administrativa)
        self.assertIsNotNone(integracao.finalizado_portal_em)

    def test_fase_7_exige_autorizacao_e_finaliza_uma_unica_vez(self):
        integracao = preparar_integracao_br_mobilidade(
            self.pedido,
            data_liberacao=date(2026, 10, 6),
            modo_manual=True,
        )
        resumo = ResumoPedidoPortal(
            numero="",
            data_pedido=date(2026, 10, 2),
            data_liberacao=date(2026, 10, 6),
            status="Novo",
            valor_creditos=Decimal("220.00"),
            taxa_administrativa=Decimal("6.60"),
            valor_cartoes=Decimal("0.00"),
            valor_total=Decimal("226.60"),
            quantidade_usuarios=1,
        )

        integracao, conferencia = preparar_conferencia_finalizacao(
            integracao.id, resumo
        )
        self.assertTrue(conferencia.aprovado)
        self.assertEqual(
            "AGUARDANDO_AUTORIZACAO_FINALIZACAO", integracao.status_interno
        )
        self.assertEqual(date(2026, 10, 2), integracao.data_pedido_portal)

        integracao = autorizar_finalizacao(integracao.id, self.usuario.id)
        self.assertEqual("AUTORIZADO_FINALIZACAO", integracao.status_interno)
        with self.assertRaisesRegex(ValueError, "já foi autorizada"):
            autorizar_finalizacao(integracao.id, self.usuario.id)

        integracao = iniciar_finalizacao(integracao.id)
        self.assertEqual("FINALIZANDO_PORTAL", integracao.status_interno)
        with self.assertRaisesRegex(ValueError, "já foi iniciada"):
            iniciar_finalizacao(integracao.id)

        integracao = registrar_finalizacao_sucesso(
            integracao.id,
            numero_pedido_portal="2970861",
            status_portal="Novo",
        )
        self.assertEqual("FINALIZADO_PORTAL", integracao.status_interno)
        self.assertEqual("2970861", integracao.numero_pedido_portal)

    def test_fase_7_marca_resultado_incerto_sem_permitir_repeticao(self):
        integracao = preparar_integracao_br_mobilidade(
            self.pedido,
            data_liberacao=date(2026, 10, 6),
            modo_manual=True,
        )
        integracao.status_interno = "FINALIZANDO_PORTAL"
        db.session.commit()

        integracao = registrar_falha_finalizacao(
            integracao.id,
            "Pedido não localizado após o clique.",
            resultado_incerto=True,
        )

        self.assertEqual("FINALIZACAO_INCERTA", integracao.status_interno)
        with self.assertRaisesRegex(ValueError, "já foi iniciada"):
            iniciar_finalizacao(integracao.id)

    def test_fase_8_entrega_boleto_relatorio_sem_armazenar_arquivos(self):
        integracao = preparar_integracao_br_mobilidade(
            self.pedido,
            data_liberacao=date(2026, 10, 6),
            modo_manual=True,
        )
        resumo = ResumoPedidoPortal(
            numero="2972189",
            data_pedido=date(2026, 10, 2),
            data_liberacao=date(2026, 10, 6),
            status="Novo",
            valor_creditos=Decimal("220.00"),
            taxa_administrativa=Decimal("0.00"),
            valor_cartoes=Decimal("0.00"),
            valor_total=Decimal("220.00"),
            quantidade_usuarios=1,
        )
        integracao, _ = registrar_criacao_manual_br_mobilidade(
            integracao.id, resumo
        )
        retorno = ResultadoDocumentosBRMobilidade(
            numero_pedido="2972189",
            status="Novo",
            valor_historico=Decimal("226.60"),
            boleto_pdf=b"%PDF-boleto",
            relatorio_pdf=b"%PDF-relatorio",
            relatorio_texto="Número do pedido 2972189 Total de registros 1",
            capturado_em=datetime(2026, 10, 3, 9, 0),
        )

        with patch(
            "app.departamento_pessoal.vale_transporte.br_mobilidade_documentos."
            "capturar_documentos_br_mobilidade_com_config",
            return_value=retorno,
        ):
            integracao, documentos = capturar_documentos_para_download(
                integracao.id, {}
            )

        self.assertEqual("FINALIZADO_PORTAL", integracao.status_interno)
        self.assertEqual(Decimal("6.60"), integracao.taxa_administrativa)
        self.assertEqual(Decimal("226.60"), integracao.valor_total_portal)
        self.assertEqual(b"%PDF-boleto", documentos.boleto_pdf)
        self.assertEqual(b"%PDF-relatorio", documentos.relatorio_pdf)
        self.assertFalse(hasattr(integracao, "boleto_conteudo"))
        self.assertFalse(hasattr(integracao, "relatorio_conteudo"))


if __name__ == "__main__":
    unittest.main()
