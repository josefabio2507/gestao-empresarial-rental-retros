"""adiciona forma de pagamento na proposta de cotacao

Revision ID: l2b3c4d5e6f7
Revises: k1a2b3c4d5e6
Create Date: 2026-09-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "l2b3c4d5e6f7"
down_revision = "k1a2b3c4d5e6"
branch_labels = None
depends_on = None


TABLE = "suprimentos_cotacao_propostas"
FORMA_COLUMN = "forma_pagamento"
CARTAO_COLUMN = "cartao_credito_id"
FORMA_INDEX = "ix_suprimentos_cotacao_propostas_forma_pagamento"
CARTAO_INDEX = "ix_suprimentos_cotacao_propostas_cartao_credito_id"
CARTAO_FK = "fk_suprimentos_cotacao_propostas_cartao_credito_id"


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
        if FORMA_COLUMN not in colunas:
            batch_op.add_column(sa.Column(FORMA_COLUMN, sa.String(length=30), nullable=True))
        if CARTAO_COLUMN not in colunas:
            batch_op.add_column(sa.Column(CARTAO_COLUMN, sa.Integer(), nullable=True))
        if not any(
            fk.get("name") == CARTAO_FK
            for fk in inspector.get_foreign_keys(TABLE)
        ):
            batch_op.create_foreign_key(
                CARTAO_FK,
                "financeiro_cartoes_credito",
                [CARTAO_COLUMN],
                ["id"],
            )

    if FORMA_INDEX not in indices:
        op.create_index(FORMA_INDEX, TABLE, [FORMA_COLUMN])
    if CARTAO_INDEX not in indices:
        op.create_index(CARTAO_INDEX, TABLE, [CARTAO_COLUMN])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if TABLE not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns(TABLE)}
    indices = {indice["name"] for indice in inspector.get_indexes(TABLE)}
    with op.batch_alter_table(TABLE, recreate=_modo_recriacao(bind)) as batch_op:
        if any(
            fk.get("name") == CARTAO_FK
            for fk in inspector.get_foreign_keys(TABLE)
        ):
            batch_op.drop_constraint(CARTAO_FK, type_="foreignkey")
        if CARTAO_COLUMN in colunas:
            batch_op.drop_column(CARTAO_COLUMN)
        if FORMA_COLUMN in colunas:
            batch_op.drop_column(FORMA_COLUMN)

    if FORMA_INDEX in indices:
        op.drop_index(FORMA_INDEX, table_name=TABLE)
    if CARTAO_INDEX in indices:
        op.drop_index(CARTAO_INDEX, table_name=TABLE)
