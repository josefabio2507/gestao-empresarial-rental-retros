"""adiciona periodicidade de pagamento ao vale transporte

Revision ID: d4f8a2c7e1b9
Revises: a13f1c9e7d24
Create Date: 2026-06-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d4f8a2c7e1b9"
down_revision = "a13f1c9e7d24"
branch_labels = None
depends_on = None


TABELA = "vale_transporte_colaborador_linhas"
COLUNA = "periodicidade_pagamento"
CONSTRAINT = "ck_vale_transporte_periodicidade_pagamento"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA not in inspector.get_table_names():
        return

    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns(TABELA)
    }

    if COLUNA not in colunas:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.add_column(
                sa.Column(
                    COLUNA,
                    sa.String(length=20),
                    server_default="mensal",
                    nullable=False,
                )
            )

    inspector = sa.inspect(bind)
    constraints = {
        constraint["name"]
        for constraint in inspector.get_check_constraints(TABELA)
    }

    if CONSTRAINT not in constraints:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.create_check_constraint(
                CONSTRAINT,
                f"{COLUNA} in ('mensal', 'semanal')",
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA not in inspector.get_table_names():
        return

    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns(TABELA)
    }

    if COLUNA in colunas:
        with op.batch_alter_table(TABELA) as batch_op:
            batch_op.drop_column(COLUNA)
