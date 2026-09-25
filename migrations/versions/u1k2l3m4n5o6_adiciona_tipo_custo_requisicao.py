"""Adiciona tipo de custo nas requisicoes com veiculo.

Revision ID: u1k2l3m4n5o6
Revises: t0j1k2l3m4n5
"""

from alembic import op
import sqlalchemy as sa


revision = "u1k2l3m4n5o6"
down_revision = "t0j1k2l3m4n5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("suprimentos_requisicoes_compra") as batch_op:
        batch_op.add_column(sa.Column("tipo_custo", sa.String(length=20), nullable=True))
        batch_op.create_check_constraint(
            "ck_suprimentos_requisicoes_compra_tipo_custo",
            "tipo_custo IS NULL OR tipo_custo IN ('Abastecimento', 'Diversos', 'Manutenção')",
        )


def downgrade():
    with op.batch_alter_table("suprimentos_requisicoes_compra") as batch_op:
        batch_op.drop_constraint("ck_suprimentos_requisicoes_compra_tipo_custo", type_="check")
        batch_op.drop_column("tipo_custo")
