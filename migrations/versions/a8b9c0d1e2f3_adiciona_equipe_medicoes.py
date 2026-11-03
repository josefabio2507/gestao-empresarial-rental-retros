"""adiciona equipe às medições de contratos

Revision ID: a8b9c0d1e2f3
Revises: z6p7q8r9s0t1
"""

from alembic import op
import sqlalchemy as sa


revision = "a8b9c0d1e2f3"
down_revision = "z6p7q8r9s0t1"
branch_labels = None
depends_on = None


TABELA = "financeiro_contratos_medicoes"
COLUNA = "equipe_id"
INDICE = "ix_fin_medicoes_equipe"
FK = "fk_fin_medicoes_equipe"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA not in inspector.get_table_names():
        return
    if COLUNA not in {coluna["name"] for coluna in inspector.get_columns(TABELA)}:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.add_column(sa.Column(COLUNA, sa.Integer(), nullable=True))
    inspector = sa.inspect(bind)
    if FK not in {fk.get("name") for fk in inspector.get_foreign_keys(TABELA)}:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.create_foreign_key(FK, "equipes", [COLUNA], ["id"])
    if INDICE not in {indice["name"] for indice in sa.inspect(bind).get_indexes(TABELA)}:
        op.create_index(INDICE, TABELA, [COLUNA])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA not in inspector.get_table_names():
        return
    if INDICE in {indice["name"] for indice in inspector.get_indexes(TABELA)}:
        op.drop_index(INDICE, table_name=TABELA)
    if COLUNA in {coluna["name"] for coluna in sa.inspect(bind).get_columns(TABELA)}:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.drop_constraint(FK, type_="foreignkey")
            batch_op.drop_column(COLUNA)
