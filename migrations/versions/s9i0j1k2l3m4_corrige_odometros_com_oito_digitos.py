"""Corrige odometros com dois zeros excedentes antes da virgula.

Revision ID: s9i0j1k2l3m4
Revises: r8h9i0j1k2l3
"""

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision = "s9i0j1k2l3m4"
down_revision = "r8h9i0j1k2l3"
branch_labels = None
depends_on = None


LIMITE_INFERIOR = Decimal("10000000.00")
LIMITE_SUPERIOR = Decimal("100000000.00")
DIVISOR = Decimal("100.00")


def _corrigir_coluna(bind, tabela, coluna, filtro_tipo=None):
    condicoes = [
        coluna >= LIMITE_INFERIOR,
        coluna < LIMITE_SUPERIOR,
    ]
    if filtro_tipo is not None:
        condicoes.append(filtro_tipo == "odometro")
    bind.execute(
        tabela.update()
        .where(sa.and_(*condicoes))
        .values({coluna.name: coluna / DIVISOR})
    )


def upgrade():
    bind = op.get_bind()
    tabelas_existentes = set(sa.inspect(bind).get_table_names())

    if "operacao_abastecimentos" in tabelas_existentes:
        abastecimentos = sa.table(
            "operacao_abastecimentos",
            sa.column("leitura_atual", sa.Numeric(12, 2)),
            sa.column("tipo_leitura", sa.String(20)),
        )
        _corrigir_coluna(
            bind,
            abastecimentos,
            abastecimentos.c.leitura_atual,
            abastecimentos.c.tipo_leitura,
        )

    if "operacao_leituras_ativos" in tabelas_existentes:
        leituras = sa.table(
            "operacao_leituras_ativos",
            sa.column("leitura", sa.Numeric(12, 2)),
            sa.column("tipo", sa.String(20)),
        )
        _corrigir_coluna(bind, leituras, leituras.c.leitura, leituras.c.tipo)

    if "operacao_veiculos_responsaveis" in tabelas_existentes:
        vinculos = sa.table(
            "operacao_veiculos_responsaveis",
            sa.column("leitura_inicial", sa.Numeric(12, 2)),
            sa.column("leitura_final", sa.Numeric(12, 2)),
            sa.column("tipo_leitura", sa.String(20)),
        )
        _corrigir_coluna(
            bind,
            vinculos,
            vinculos.c.leitura_inicial,
            vinculos.c.tipo_leitura,
        )
        _corrigir_coluna(
            bind,
            vinculos,
            vinculos.c.leitura_final,
            vinculos.c.tipo_leitura,
        )


def downgrade():
    # Correcao de dados irreversivel: os valores anteriores eram invalidos.
    pass
