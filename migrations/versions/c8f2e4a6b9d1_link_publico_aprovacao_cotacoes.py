"""link publico aprovacao cotacoes

Revision ID: c8f2e4a6b9d1
Revises: f4b6c8d2e9a1
Create Date: 2026-08-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f2e4a6b9d1"
down_revision = "f4b6c8d2e9a1"
branch_labels = None
depends_on = None


def _indice_existe(inspector, tabela, nome):
    return nome in {indice["name"] for indice in inspector.get_indexes(tabela)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_cotacoes" not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns("suprimentos_cotacoes")}

    with op.batch_alter_table("suprimentos_cotacoes") as batch_op:
        if "aprovacao_publica_token_hash" not in colunas:
            batch_op.add_column(sa.Column("aprovacao_publica_token_hash", sa.String(64), nullable=True))
        if "aprovacao_publica_expira_em" not in colunas:
            batch_op.add_column(sa.Column("aprovacao_publica_expira_em", sa.DateTime(), nullable=True))
        if "aprovacao_publica_usado_em" not in colunas:
            batch_op.add_column(sa.Column("aprovacao_publica_usado_em", sa.DateTime(), nullable=True))

    inspector = sa.inspect(bind)
    if not _indice_existe(inspector, "suprimentos_cotacoes", "ix_suprimentos_cotacoes_aprovacao_publica_token_hash"):
        op.create_index(
            "ix_suprimentos_cotacoes_aprovacao_publica_token_hash",
            "suprimentos_cotacoes",
            ["aprovacao_publica_token_hash"],
            unique=True,
        )
    if not _indice_existe(inspector, "suprimentos_cotacoes", "ix_suprimentos_cotacoes_aprovacao_publica_expira_em"):
        op.create_index(
            "ix_suprimentos_cotacoes_aprovacao_publica_expira_em",
            "suprimentos_cotacoes",
            ["aprovacao_publica_expira_em"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_cotacoes" not in inspector.get_table_names():
        return

    colunas = {coluna["name"] for coluna in inspector.get_columns("suprimentos_cotacoes")}
    indices = {indice["name"] for indice in inspector.get_indexes("suprimentos_cotacoes")}

    if "ix_suprimentos_cotacoes_aprovacao_publica_expira_em" in indices:
        op.drop_index("ix_suprimentos_cotacoes_aprovacao_publica_expira_em", table_name="suprimentos_cotacoes")
    if "ix_suprimentos_cotacoes_aprovacao_publica_token_hash" in indices:
        op.drop_index("ix_suprimentos_cotacoes_aprovacao_publica_token_hash", table_name="suprimentos_cotacoes")

    with op.batch_alter_table("suprimentos_cotacoes") as batch_op:
        if "aprovacao_publica_usado_em" in colunas:
            batch_op.drop_column("aprovacao_publica_usado_em")
        if "aprovacao_publica_expira_em" in colunas:
            batch_op.drop_column("aprovacao_publica_expira_em")
        if "aprovacao_publica_token_hash" in colunas:
            batch_op.drop_column("aprovacao_publica_token_hash")
