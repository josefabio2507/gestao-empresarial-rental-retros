"""Impede números duplicados de Ordem de Serviço do cliente.

Revision ID: f7a8b9c0d1e2
Revises: z6p7q8r9s0t1
Create Date: 2026-11-03 00:00:00.000000
"""

from alembic import op


revision = "f7a8b9c0d1e2"
down_revision = "z6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_operacao_ordens_servico_numero_os_cliente",
        "operacao_ordens_servico",
        ["numero_os_cliente"],
    )


def downgrade():
    op.drop_constraint(
        "uq_operacao_ordens_servico_numero_os_cliente",
        "operacao_ordens_servico",
        type_="unique",
    )
