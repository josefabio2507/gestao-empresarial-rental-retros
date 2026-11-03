"""Corrige leituras de abastecimento da RTM9D90.

Revision ID: a0b1c2d3e4f5
Revises: z6p7q8r9s0t1
"""

from datetime import date
from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision = "a0b1c2d3e4f5"
down_revision = "z6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    veiculos = sa.table(
        "operacao_veiculos_equipamentos",
        sa.column("id", sa.Integer),
        sa.column("identificacao", sa.String),
    )
    abastecimentos = sa.table(
        "operacao_abastecimentos",
        sa.column("veiculo_id", sa.Integer),
        sa.column("data_abastecimento", sa.Date),
        sa.column("leitura_atual", sa.Numeric(12, 2)),
    )
    veiculo_rtm9d90 = sa.select(veiculos.c.id).where(veiculos.c.identificacao == "RTM9D90")

    correcoes = (
        (date(2026, 10, 12), Decimal("857890.00"), Decimal("85789.00")),
        (date(2026, 10, 14), Decimal("861720.00"), Decimal("86172.00")),
    )
    for data_abastecimento, leitura_atual, leitura_corrigida in correcoes:
        bind.execute(
            abastecimentos.update()
            .where(
                sa.and_(
                    abastecimentos.c.veiculo_id.in_(veiculo_rtm9d90),
                    abastecimentos.c.data_abastecimento == data_abastecimento,
                    abastecimentos.c.leitura_atual == leitura_atual,
                )
            )
            .values(leitura_atual=leitura_corrigida)
        )


def downgrade():
    # Correção pontual de dados: não reintroduzir as leituras incorretas.
    pass
