"""Adiciona horários de jornada ao diário de localização.

Revision ID: a7b8c9d0e1f2
Revises: z6p7q8r9s0t1
"""

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f5a2b7c4d8e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("operacao_diarios_localizacao", sa.Column("hora_inicial", sa.Time(), nullable=True))
    op.add_column("operacao_diarios_localizacao", sa.Column("intervalo_jornada", sa.Time(), nullable=True))
    op.add_column("operacao_diarios_localizacao", sa.Column("hora_final", sa.Time(), nullable=True))


def downgrade():
    op.drop_column("operacao_diarios_localizacao", "hora_final")
    op.drop_column("operacao_diarios_localizacao", "intervalo_jornada")
    op.drop_column("operacao_diarios_localizacao", "hora_inicial")
