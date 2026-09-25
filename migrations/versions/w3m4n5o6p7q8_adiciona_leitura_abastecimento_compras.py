"""Adiciona leitura de abastecimento nas requisicoes e ordens de compra.

Revision ID: w3m4n5o6p7q8
Revises: v2l3m4n5o6p7
"""

from alembic import op
import sqlalchemy as sa


revision = "w3m4n5o6p7q8"
down_revision = "v2l3m4n5o6p7"
branch_labels = None
depends_on = None


def _adicionar_colunas(tabela, prefixo):
    with op.batch_alter_table(tabela) as batch_op:
        batch_op.add_column(sa.Column("tipo_leitura_abastecimento", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("leitura_abastecimento", sa.Numeric(8, 2), nullable=True))
        batch_op.create_check_constraint(
            f"ck_{prefixo}_tipo_leitura_abastecimento",
            "tipo_leitura_abastecimento IS NULL OR tipo_leitura_abastecimento IN ('odometro', 'horimetro')",
        )
        batch_op.create_check_constraint(
            f"ck_{prefixo}_leitura_abastecimento",
            "leitura_abastecimento IS NULL OR leitura_abastecimento >= 0",
        )


def upgrade():
    _adicionar_colunas("suprimentos_requisicoes_compra", "suprimentos_requisicoes_compra")
    _adicionar_colunas("suprimentos_ordens_compra", "suprimentos_ordens_compra")


def downgrade():
    for tabela, prefixo in (
        ("suprimentos_ordens_compra", "suprimentos_ordens_compra"),
        ("suprimentos_requisicoes_compra", "suprimentos_requisicoes_compra"),
    ):
        with op.batch_alter_table(tabela) as batch_op:
            batch_op.drop_constraint(f"ck_{prefixo}_leitura_abastecimento", type_="check")
            batch_op.drop_constraint(f"ck_{prefixo}_tipo_leitura_abastecimento", type_="check")
            batch_op.drop_column("leitura_abastecimento")
            batch_op.drop_column("tipo_leitura_abastecimento")
