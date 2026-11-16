"""Adiciona situação às unidades de entrega Ticket.

Revision ID: u3v4w5x6y7z8
Revises: t2u3v4w5x6y7
Create Date: 2026-11-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "u3v4w5x6y7z8"
down_revision = "t2u3v4w5x6y7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dp_pedido_ticket_unidades",
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade():
    op.drop_column("dp_pedido_ticket_unidades", "ativo")
