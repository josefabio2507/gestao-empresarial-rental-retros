from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.departamento_pessoal.vale_transporte.br_mobilidade_conferencia import (
    ResumoPedidoPortal,
    conferir_resumo_pedido,
)


def test_conferencia_aceita_creditos_usuarios_liberacao_e_total_coerentes():
    integracao = SimpleNamespace(
        numero_pedido_portal="2969715",
        quantidade_colaboradores=1,
        valor_creditos=Decimal("13.70"),
        data_liberacao=date(2026, 10, 5),
    )
    resumo = ResumoPedidoPortal(
        numero="2969715",
        data_pedido=date(2026, 10, 1),
        data_liberacao=date(2026, 10, 5),
        status="Novo",
        valor_creditos=Decimal("13.70"),
        taxa_administrativa=Decimal("0.00"),
        valor_cartoes=Decimal("0.00"),
        valor_total=Decimal("13.70"),
        quantidade_usuarios=1,
    )

    assert conferir_resumo_pedido(integracao, resumo).aprovado


def test_conferencia_bloqueia_divergencia_de_quantidade_e_valor():
    integracao = SimpleNamespace(
        numero_pedido_portal="2969715",
        quantidade_colaboradores=1,
        valor_creditos=Decimal("13.70"),
        data_liberacao=date(2026, 10, 5),
    )
    resumo = ResumoPedidoPortal(
        numero="2969715",
        data_pedido=date(2026, 10, 1),
        data_liberacao=date(2026, 10, 5),
        status="Novo",
        valor_creditos=Decimal("27.40"),
        taxa_administrativa=Decimal("0.00"),
        valor_cartoes=Decimal("0.00"),
        valor_total=Decimal("27.40"),
        quantidade_usuarios=2,
    )

    resultado = conferir_resumo_pedido(integracao, resumo)
    assert not resultado.aprovado
    assert "Quantidade de colaboradores divergente." in resultado.divergencias
    assert "Valor dos créditos divergente." in resultado.divergencias


def test_conferencia_bloqueia_divergencias_observadas_no_portal():
    integracao = SimpleNamespace(
        numero_pedido_portal="2969715",
        quantidade_colaboradores=1,
        valor_creditos=Decimal("13.70"),
        data_liberacao=date(2026, 10, 5),
    )
    resumo = ResumoPedidoPortal(
        numero="2969715",
        data_pedido=date(2026, 10, 1),
        data_liberacao=date(2026, 10, 1),
        status="Novo",
        valor_creditos=Decimal("13.70"),
        taxa_administrativa=Decimal("0.00"),
        valor_cartoes=Decimal("0.00"),
        valor_total=Decimal("13.70"),
        quantidade_usuarios=1,
        valor_historico=Decimal("14.11"),
        acrescimo_historico_confirmado=True,
    )

    resultado = conferir_resumo_pedido(integracao, resumo)
    assert not resultado.aprovado
    assert "Data de liberação divergente." in resultado.divergencias
    assert resultado.acrescimo_historico == Decimal("0.41")
    assert len(resultado.divergencias) == 1


def test_conferencia_exige_confirmacao_de_acrescimo_nao_identificado():
    integracao = SimpleNamespace(
        numero_pedido_portal="2969715",
        quantidade_colaboradores=1,
        valor_creditos=Decimal("13.70"),
        data_liberacao=date(2026, 10, 1),
    )
    resumo = ResumoPedidoPortal(
        numero="2969715",
        data_pedido=date(2026, 10, 1),
        data_liberacao=date(2026, 10, 1),
        status="Novo",
        valor_creditos=Decimal("13.70"),
        taxa_administrativa=Decimal("0.00"),
        valor_cartoes=Decimal("0.00"),
        valor_total=Decimal("13.70"),
        quantidade_usuarios=1,
        valor_historico=Decimal("14.11"),
    )

    resultado = conferir_resumo_pedido(integracao, resumo)
    assert not resultado.aprovado
    assert "Acréscimo do histórico requer confirmação da taxa da empresa." in resultado.divergencias


def test_conferencia_pre_finalizacao_aceita_numero_ainda_nao_gerado():
    integracao = SimpleNamespace(
        numero_pedido_portal=None,
        quantidade_colaboradores=1,
        valor_creditos=Decimal("27.40"),
        data_liberacao=date(2026, 10, 6),
    )
    resumo = ResumoPedidoPortal(
        numero="",
        data_pedido=date(2026, 10, 2),
        data_liberacao=date(2026, 10, 6),
        status="Novo",
        valor_creditos=Decimal("27.40"),
        taxa_administrativa=Decimal("0.82"),
        valor_cartoes=Decimal("0.00"),
        valor_total=Decimal("28.22"),
        quantidade_usuarios=1,
    )

    assert conferir_resumo_pedido(integracao, resumo).aprovado
