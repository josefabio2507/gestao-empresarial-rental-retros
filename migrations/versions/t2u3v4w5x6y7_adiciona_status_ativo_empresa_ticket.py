"""Adiciona situação ativa ao cadastro de empresas e contratos Tícket.

Revision ID: t2u3v4w5x6y7
Revises: p1q2r3s4t5u6
Create Date: 2026-11-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "t2u3v4w5x6y7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dp_pedido_ticket_empresas",
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade():
    op.drop_column("dp_pedido_ticket_empresas", "ativo")
