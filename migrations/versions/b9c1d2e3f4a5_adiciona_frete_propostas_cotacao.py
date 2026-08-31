"""adiciona frete propostas cotacao

Revision ID: b9c1d2e3f4a5
Revises: a7c9d2e4f6b8
Create Date: 2026-08-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "b9c1d2e3f4a5"
down_revision = "a7c9d2e4f6b8"
branch_labels = None
depends_on = None


T_PROPOSTAS = "suprimentos_cotacao_propostas"
T_OC_ITENS = "suprimentos_ordem_compra_itens"
CK_PROPOSTAS_FRETE = "ck_suprimentos_cotacao_propostas_valor_frete"
CK_OC_ITENS_FRETE = "ck_suprimentos_oc_itens_valor_frete"


def _colunas(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return set()
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def _constraints_check(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return set()
    return {constraint["name"] for constraint in inspector.get_check_constraints(tabela)}


def _modo_recriacao(bind):
    return "always" if bind.dialect.name == "sqlite" else "auto"


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tabelas = set(inspector.get_table_names())

    if T_PROPOSTAS in tabelas:
        colunas = _colunas(inspector, T_PROPOSTAS)
        constraints = _constraints_check(inspector, T_PROPOSTAS)
        with op.batch_alter_table(T_PROPOSTAS, recreate=_modo_recriacao(bind)) as batch_op:
            if "valor_frete" not in colunas:
                batch_op.add_column(
                    sa.Column(
                        "valor_frete",
                        sa.Numeric(12, 2),
                        nullable=False,
                        server_default="0",
                    )
                )
            if CK_PROPOSTAS_FRETE not in constraints:
                batch_op.create_check_constraint(CK_PROPOSTAS_FRETE, "valor_frete >= 0")

    inspector = inspect(bind)
    if T_OC_ITENS in tabelas:
        colunas = _colunas(inspector, T_OC_ITENS)
        constraints = _constraints_check(inspector, T_OC_ITENS)
        with op.batch_alter_table(T_OC_ITENS, recreate=_modo_recriacao(bind)) as batch_op:
            if "valor_frete" not in colunas:
                batch_op.add_column(
                    sa.Column(
                        "valor_frete",
                        sa.Numeric(12, 2),
                        nullable=False,
                        server_default="0",
                    )
                )
            if CK_OC_ITENS_FRETE not in constraints:
                batch_op.create_check_constraint(CK_OC_ITENS_FRETE, "valor_frete >= 0")


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tabelas = set(inspector.get_table_names())

    if T_OC_ITENS in tabelas and "valor_frete" in _colunas(inspector, T_OC_ITENS):
        constraints = _constraints_check(inspector, T_OC_ITENS)
        with op.batch_alter_table(T_OC_ITENS, recreate=_modo_recriacao(bind)) as batch_op:
            if CK_OC_ITENS_FRETE in constraints:
                batch_op.drop_constraint(CK_OC_ITENS_FRETE, type_="check")
            batch_op.drop_column("valor_frete")

    inspector = inspect(bind)
    if T_PROPOSTAS in tabelas and "valor_frete" in _colunas(inspector, T_PROPOSTAS):
        constraints = _constraints_check(inspector, T_PROPOSTAS)
        with op.batch_alter_table(T_PROPOSTAS, recreate=_modo_recriacao(bind)) as batch_op:
            if CK_PROPOSTAS_FRETE in constraints:
                batch_op.drop_constraint(CK_PROPOSTAS_FRETE, type_="check")
            batch_op.drop_column("valor_frete")
