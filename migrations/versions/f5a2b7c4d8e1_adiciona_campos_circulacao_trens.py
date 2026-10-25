"""Adiciona respostas obrigatórias à circulação de trens.

Revision ID: f5a2b7c4d8e1
Revises: e4f1a6b3c9d5
Create Date: 2026-10-18 22:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f5a2b7c4d8e1"
down_revision = "e4f1a6b3c9d5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("operacao_circulacao_trens") as batch:
        batch.add_column(sa.Column("pedido_corte_composicao", sa.String(length=30), nullable=False))
        batch.add_column(sa.Column("corte_composicao", sa.String(length=30), nullable=False))


def downgrade():
    with op.batch_alter_table("operacao_circulacao_trens") as batch:
        batch.drop_column("corte_composicao")
        batch.drop_column("pedido_corte_composicao")
