"""Adiciona observações às intervenções adversas."""

from alembic import op
import sqlalchemy as sa


revision = "z7q8r9s0t1u2"
down_revision = "z6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("operacao_intervencoes_adversas", sa.Column("observacoes", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("operacao_intervencoes_adversas", "observacoes")
