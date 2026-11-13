"""Adiciona observações às intervenções adversas."""

from alembic import op
import sqlalchemy as sa


revision = "z7q8r9s0t1u2"
down_revision = "z6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "operacao_intervencoes_adversas" not in inspector.get_table_names():
        return
    colunas = {coluna["name"] for coluna in inspector.get_columns("operacao_intervencoes_adversas")}
    if "observacoes" not in colunas:
        op.add_column("operacao_intervencoes_adversas", sa.Column("observacoes", sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "operacao_intervencoes_adversas" not in inspector.get_table_names():
        return
    colunas = {coluna["name"] for coluna in inspector.get_columns("operacao_intervencoes_adversas")}
    if "observacoes" in colunas:
        op.drop_column("operacao_intervencoes_adversas", "observacoes")
