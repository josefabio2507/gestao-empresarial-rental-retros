"""adiciona metadados do layout City Transportes

Revision ID: d0t1u2v3w4x5
Revises: c9s0t1u2v3w4
"""

import sqlalchemy as sa
from alembic import op


revision = "d0t1u2v3w4x5"
down_revision = "c9s0t1u2v3w4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("linhas_onibus") as batch_op:
        batch_op.add_column(sa.Column("city_aplicacao", sa.String(length=3)))
    with op.batch_alter_table("vale_transporte_colaborador_linhas") as batch_op:
        batch_op.add_column(sa.Column("city_design_cartao", sa.String(length=2)))
    with op.batch_alter_table("vale_transporte_pedido_itens") as batch_op:
        batch_op.add_column(sa.Column("city_aplicacao_snapshot", sa.String(length=3)))
        batch_op.add_column(sa.Column("city_design_cartao_snapshot", sa.String(length=2)))


def downgrade():
    with op.batch_alter_table("vale_transporte_pedido_itens") as batch_op:
        batch_op.drop_column("city_design_cartao_snapshot")
        batch_op.drop_column("city_aplicacao_snapshot")
    with op.batch_alter_table("vale_transporte_colaborador_linhas") as batch_op:
        batch_op.drop_column("city_design_cartao")
    with op.batch_alter_table("linhas_onibus") as batch_op:
        batch_op.drop_column("city_aplicacao")
