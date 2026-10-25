"""Adiciona status ativo às Ordens de Serviço."""

from alembic import op
import sqlalchemy as sa


revision = "a9b0c1d2e3f4"
down_revision = "z6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "operacao_ordens_servico",
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        op.f("ix_operacao_ordens_servico_ativo"),
        "operacao_ordens_servico",
        ["ativo"],
        unique=False,
    )
    op.alter_column("operacao_ordens_servico", "ativo", server_default=None)


def downgrade():
    op.drop_index(op.f("ix_operacao_ordens_servico_ativo"), table_name="operacao_ordens_servico")
    op.drop_column("operacao_ordens_servico", "ativo")
