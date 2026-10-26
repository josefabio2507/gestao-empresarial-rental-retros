"""Cria a persistência dos controles de liberação das Ordens de Serviço.

Revision ID: ae4f5a6b7c8d
Revises: ad3e4f5a6b7c
Create Date: 2026-10-26 14:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "ae4f5a6b7c8d"
down_revision = "ad3e4f5a6b7c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operacao_controles_liberacao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("id_os_interno", sa.String(length=36), nullable=False),
        sa.Column("data_evento", sa.Date(), nullable=False),
        sa.Column("pedido_liberacao_ccp", sa.Time(), nullable=True),
        sa.Column("liberacao_embandeiramento", sa.Time(), nullable=True),
        sa.Column("termino_embandeiramento", sa.Time(), nullable=True),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["id_os_interno"], ["operacao_ordens_servico.id_os_interno"]),
        sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
    )
    op.create_index(
        "ix_operacao_controles_liberacao_id_os_interno",
        "operacao_controles_liberacao",
        ["id_os_interno"],
    )
    op.create_index(
        "ix_operacao_controles_liberacao_data_evento",
        "operacao_controles_liberacao",
        ["data_evento"],
    )


def downgrade():
    op.drop_index(
        "ix_operacao_controles_liberacao_data_evento",
        table_name="operacao_controles_liberacao",
    )
    op.drop_index(
        "ix_operacao_controles_liberacao_id_os_interno",
        table_name="operacao_controles_liberacao",
    )
    op.drop_table("operacao_controles_liberacao")
