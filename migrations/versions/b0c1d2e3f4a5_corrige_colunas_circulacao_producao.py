"""Completa as colunas de circulação já utilizadas pelo monitoramento.

Revision ID: b0c1d2e3f4a5
Revises: af5a6b7c8d9e
Create Date: 2026-10-26 14:22:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b0c1d2e3f4a5"
down_revision = "af5a6b7c8d9e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    colunas = {coluna["name"] for coluna in sa.inspect(bind).get_columns("operacao_circulacao_trens")}
    if "motivo_paralisacao" not in colunas:
        op.add_column("operacao_circulacao_trens", sa.Column("motivo_paralisacao", sa.String(length=40), nullable=True))
    if "operador_ccp_maquinista" not in colunas:
        op.add_column("operacao_circulacao_trens", sa.Column("operador_ccp_maquinista", sa.String(length=160), nullable=True))


def downgrade():
    bind = op.get_bind()
    colunas = {coluna["name"] for coluna in sa.inspect(bind).get_columns("operacao_circulacao_trens")}
    if "operador_ccp_maquinista" in colunas:
        op.drop_column("operacao_circulacao_trens", "operador_ccp_maquinista")
    if "motivo_paralisacao" in colunas:
        op.drop_column("operacao_circulacao_trens", "motivo_paralisacao")
