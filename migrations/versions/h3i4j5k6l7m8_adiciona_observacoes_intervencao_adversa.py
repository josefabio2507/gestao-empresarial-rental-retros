"""Adiciona observações às intervenções adversas."""

from alembic import op
import sqlalchemy as sa


revision = "h3i4j5k6l7m8"
down_revision = "g2h3i4j5k6l7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("operacao_intervencoes_adversas", sa.Column("observacoes", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("operacao_intervencoes_adversas", "observacoes")
