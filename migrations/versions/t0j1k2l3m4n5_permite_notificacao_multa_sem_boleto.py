"""Permite cadastrar notificacao de multa antes do boleto.

Revision ID: t0j1k2l3m4n5
Revises: s9i0j1k2l3m4
"""

from alembic import op
import sqlalchemy as sa


revision = "t0j1k2l3m4n5"
down_revision = "s9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("operacao_multas_transito") as batch_op:
        batch_op.alter_column("valor_multa", existing_type=sa.Numeric(12, 2), nullable=True)
        batch_op.alter_column("data_vencimento", existing_type=sa.Date(), nullable=True)


def downgrade():
    op.execute("UPDATE operacao_multas_transito SET valor_multa = 0 WHERE valor_multa IS NULL")
    op.execute("UPDATE operacao_multas_transito SET data_vencimento = data_infracao WHERE data_vencimento IS NULL")
    with op.batch_alter_table("operacao_multas_transito") as batch_op:
        batch_op.alter_column("valor_multa", existing_type=sa.Numeric(12, 2), nullable=False)
        batch_op.alter_column("data_vencimento", existing_type=sa.Date(), nullable=False)
