"""adiciona colaborador ao pedido de vale transporte

Revision ID: a9b4c6d8e2f1
Revises: f2a7c9d8e3b1
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a9b4c6d8e2f1"
down_revision = "f2a7c9d8e3b1"
branch_labels = None
depends_on = None


TABELA = "vale_transporte_pedidos"
COLUNA = "colaborador_id"
INDICE = "ix_vale_transporte_pedidos_colaborador_id"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns(TABELA)}

    if COLUNA not in colunas:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.add_column(sa.Column(COLUNA, sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_vale_transporte_pedidos_colaborador_id",
                "colaboradores",
                [COLUNA],
                ["id"],
            )

    inspector = sa.inspect(bind)
    indices = {indice["name"] for indice in inspector.get_indexes(TABELA)}

    if INDICE not in indices:
        op.create_index(INDICE, TABELA, [COLUNA])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns(TABELA)}

    if COLUNA in colunas:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.drop_column(COLUNA)
