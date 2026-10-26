"""Adiciona idempotência e versão aos apontamentos diários.

Revision ID: e4f1a6b3c9d5
Revises: d3e9f5a2b8c4
Create Date: 2026-10-18 19:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e4f1a6b3c9d5"
down_revision = "d3e9f5a2b8c4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("operacao_apontamentos_diarios") as batch:
        batch.add_column(sa.Column("chave_idempotencia", sa.String(length=36), nullable=False))
        batch.add_column(sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("versao", sa.Integer(), nullable=False, server_default="1"))
        batch.create_foreign_key(
            "fk_operacao_apontamentos_atualizado_por",
            "usuarios",
            ["atualizado_por_usuario_id"],
            ["id"],
        )
        batch.create_index(
            op.f("ix_operacao_apontamentos_diarios_chave_idempotencia"),
            ["chave_idempotencia"],
            unique=True,
        )
        batch.create_index(
            op.f("ix_operacao_apontamentos_diarios_atualizado_por_usuario_id"),
            ["atualizado_por_usuario_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("operacao_apontamentos_diarios") as batch:
        batch.drop_index(op.f("ix_operacao_apontamentos_diarios_atualizado_por_usuario_id"))
        batch.drop_index(op.f("ix_operacao_apontamentos_diarios_chave_idempotencia"))
        batch.drop_constraint("fk_operacao_apontamentos_atualizado_por", type_="foreignkey")
        batch.drop_column("versao")
        batch.drop_column("atualizado_por_usuario_id")
        batch.drop_column("chave_idempotencia")
