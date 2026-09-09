"""adiciona selecao de frete na cotacao

Revision ID: k1a2b3c4d5e6
Revises: j0f2a3b4c5d6
Create Date: 2026-09-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "k1a2b3c4d5e6"
down_revision = "j0f2a3b4c5d6"
branch_labels = None
depends_on = None


TABLE = "suprimentos_cotacoes"
COLUMN = "frete_fornecedor_id"
INDEX = "ix_suprimentos_cotacoes_frete_fornecedor_id"
FK = "fk_suprimentos_cotacoes_frete_fornecedor_id"


def _modo_recriacao(bind):
    return "always" if bind.dialect.name == "sqlite" else "auto"


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns(TABLE)}
    indices = {indice["name"] for indice in inspector.get_indexes(TABLE)}
    with op.batch_alter_table(TABLE, recreate=_modo_recriacao(bind)) as batch_op:
        if COLUMN not in colunas:
            batch_op.add_column(sa.Column(COLUMN, sa.Integer(), nullable=True))
        if not any(
            fk.get("name") == FK
            for fk in inspector.get_foreign_keys(TABLE)
        ):
            batch_op.create_foreign_key(FK, "suprimentos_fornecedores", [COLUMN], ["id"])

    if INDEX not in indices:
        op.create_index(INDEX, TABLE, [COLUMN])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns(TABLE)}
    indices = {indice["name"] for indice in inspector.get_indexes(TABLE)}
    with op.batch_alter_table(TABLE, recreate=_modo_recriacao(bind)) as batch_op:
        if any(
            fk.get("name") == FK
            for fk in inspector.get_foreign_keys(TABLE)
        ):
            batch_op.drop_constraint(FK, type_="foreignkey")
        if COLUMN in colunas:
            batch_op.drop_column(COLUMN)

    if INDEX in indices:
        op.drop_index(INDEX, table_name=TABLE)
