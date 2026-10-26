"""Cria tabelas base dos submódulos de Operações.

Revision ID: ad3e4f5a6b7c
Revises: ac2d3e4f5a6b
"""

from alembic import op
import sqlalchemy as sa


revision = "ad3e4f5a6b7c"
down_revision = "ac2d3e4f5a6b"
branch_labels = None
depends_on = None


def _timestamps(table):
    return [
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
    ]


def upgrade():
    op.create_table(
        "operacao_chefes_boletim",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("matricula", sa.String(length=40), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(None),
        sa.UniqueConstraint("matricula", name="uq_operacao_chefes_boletim_matricula"),
    )
    op.create_index("ix_operacao_chefes_boletim_matricula", "operacao_chefes_boletim", ["matricula"])
    op.create_index("ix_operacao_chefes_boletim_ativo", "operacao_chefes_boletim", ["ativo"])

    for table in ("operacao_servicos_catalogo", "operacao_materiais_catalogo"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(length=220), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_timestamps(None),
            sa.UniqueConstraint("nome", name=f"uq_{table}_nome"),
        )
        op.create_index(f"ix_{table}_nome", table, ["nome"])
        op.create_index(f"ix_{table}_ativo", table, ["ativo"])


def downgrade():
    op.drop_table("operacao_materiais_catalogo")
    op.drop_table("operacao_servicos_catalogo")
    op.drop_table("operacao_chefes_boletim")
