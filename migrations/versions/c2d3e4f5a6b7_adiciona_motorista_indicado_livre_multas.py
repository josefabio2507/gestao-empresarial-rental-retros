"""adiciona motorista indicado livre em multas

Revision ID: c2d3e4f5a6b7
Revises: c1d2e3f4a5b6
Create Date: 2026-08-23 22:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c2d3e4f5a6b7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("operacao_multas_transito", sa.Column("motorista_indicado_nome", sa.String(length=160), nullable=True))


def downgrade():
    op.drop_column("operacao_multas_transito", "motorista_indicado_nome")
