"""Adiciona controle idempotente ao cadastro de Ordens de Serviço.

Revision ID: d3e9f5a2b8c4
Revises: c2d8e4f1a9b3
Create Date: 2026-10-18 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d3e9f5a2b8c4"
down_revision = "c2d8e4f1a9b3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "operacao_ordens_servico",
        sa.Column("chave_idempotencia", sa.String(length=36), nullable=False),
    )
    op.create_index(
        op.f("ix_operacao_ordens_servico_chave_idempotencia"),
        "operacao_ordens_servico",
        ["chave_idempotencia"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        op.f("ix_operacao_ordens_servico_chave_idempotencia"),
        table_name="operacao_ordens_servico",
    )
    op.drop_column("operacao_ordens_servico", "chave_idempotencia")
