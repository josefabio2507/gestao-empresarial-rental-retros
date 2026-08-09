"""ajustes saidas inventario estoque

Revision ID: c4f2a9b8e1d6
Revises: b9e7c4a1d3f2
Create Date: 2026-08-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c4f2a9b8e1d6"
down_revision = "b9e7c4a1d3f2"
branch_labels = None
depends_on = None


TABELA = "suprimentos_movimentacoes_estoque"


def nomes_colunas(inspector):
    return {coluna["name"] for coluna in inspector.get_columns(TABELA)}


def nomes_checks(inspector):
    return {check["name"] for check in inspector.get_check_constraints(TABELA)}


def nomes_fks(inspector):
    return {fk["name"] for fk in inspector.get_foreign_keys(TABELA)}


def indice_existe(inspector, indice):
    return indice in {item["name"] for item in inspector.get_indexes(TABELA)}


def modo_recriacao(bind):
    return "always" if bind.dialect.name == "sqlite" else "auto"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA not in inspector.get_table_names():
        return

    colunas = nomes_colunas(inspector)
    checks = nomes_checks(inspector)
    fks = nomes_fks(inspector)

    with op.batch_alter_table(TABELA, recreate=modo_recriacao(bind)) as batch_op:
        if "responsavel_usuario_id" not in colunas:
            batch_op.add_column(sa.Column("responsavel_usuario_id", sa.Integer(), nullable=True))

        if "ck_suprimentos_movimentacoes_estoque_tipo" in checks:
            batch_op.drop_constraint("ck_suprimentos_movimentacoes_estoque_tipo", type_="check")
        batch_op.create_check_constraint(
            "ck_suprimentos_movimentacoes_estoque_tipo",
            "tipo in ('Entrada', 'Saida')",
        )

        if "ck_suprimentos_movimentacoes_estoque_quantidade" in checks:
            batch_op.drop_constraint("ck_suprimentos_movimentacoes_estoque_quantidade", type_="check")
        batch_op.create_check_constraint(
            "ck_suprimentos_movimentacoes_estoque_quantidade",
            "quantidade <> 0",
        )

        if "fk_suprimentos_movimentacoes_estoque_responsavel_usuario_id" not in fks:
            batch_op.create_foreign_key(
                "fk_suprimentos_movimentacoes_estoque_responsavel_usuario_id",
                "usuarios",
                ["responsavel_usuario_id"],
                ["id"],
            )

    inspector = sa.inspect(bind)
    if not indice_existe(inspector, "ix_suprimentos_movimentacoes_estoque_responsavel_usuario_id"):
        op.create_index(
            "ix_suprimentos_movimentacoes_estoque_responsavel_usuario_id",
            TABELA,
            ["responsavel_usuario_id"],
        )


def downgrade():
    pass
