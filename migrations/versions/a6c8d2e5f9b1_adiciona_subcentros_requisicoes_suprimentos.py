"""adiciona subcentros requisicoes suprimentos

Revision ID: a6c8d2e5f9b1
Revises: e4b9a2c1d7f5
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a6c8d2e5f9b1"
down_revision = "e4b9a2c1d7f5"
branch_labels = None
depends_on = None


def coluna_existe(inspector, tabela, coluna):
    return coluna in {item["name"] for item in inspector.get_columns(tabela)}


def indice_existe(inspector, tabela, indice):
    return indice in {item["name"] for item in inspector.get_indexes(tabela)}


def modo_recriacao(bind):
    return "always" if bind.dialect.name == "sqlite" else "auto"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_requisicoes_compra" not in inspector.get_table_names():
        return

    colunas = {item["name"] for item in inspector.get_columns("suprimentos_requisicoes_compra")}

    with op.batch_alter_table("suprimentos_requisicoes_compra", recreate=modo_recriacao(bind)) as batch_op:
        if "equipe_id" not in colunas:
            batch_op.add_column(sa.Column("equipe_id", sa.Integer(), nullable=True))
        if "veiculo_placa" not in colunas:
            batch_op.add_column(sa.Column("veiculo_placa", sa.String(length=20), nullable=True))

        if "equipe_id" not in colunas:
            batch_op.create_foreign_key(
                "fk_suprimentos_requisicoes_compra_equipe_id",
                "equipes",
                ["equipe_id"],
                ["id"],
            )

    inspector = sa.inspect(bind)
    if not indice_existe(inspector, "suprimentos_requisicoes_compra", "ix_suprimentos_requisicoes_compra_equipe_id"):
        op.create_index(
            "ix_suprimentos_requisicoes_compra_equipe_id",
            "suprimentos_requisicoes_compra",
            ["equipe_id"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_requisicoes_compra" not in inspector.get_table_names():
        return

    if indice_existe(inspector, "suprimentos_requisicoes_compra", "ix_suprimentos_requisicoes_compra_equipe_id"):
        op.drop_index(
            "ix_suprimentos_requisicoes_compra_equipe_id",
            table_name="suprimentos_requisicoes_compra",
        )

    colunas = {item["name"] for item in inspector.get_columns("suprimentos_requisicoes_compra")}

    with op.batch_alter_table("suprimentos_requisicoes_compra", recreate=modo_recriacao(bind)) as batch_op:
        if "equipe_id" in colunas:
            batch_op.drop_constraint("fk_suprimentos_requisicoes_compra_equipe_id", type_="foreignkey")
            batch_op.drop_column("equipe_id")
        if "veiculo_placa" in colunas:
            batch_op.drop_column("veiculo_placa")
