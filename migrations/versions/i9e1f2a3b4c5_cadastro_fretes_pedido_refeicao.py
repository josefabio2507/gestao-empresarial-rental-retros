"""cadastro de fretes de pedidos de refeicao

Revision ID: i9e1f2a3b4c5
Revises: h8d0e1f2a3b4
"""
from alembic import op
import sqlalchemy as sa

revision = "i9e1f2a3b4c5"
down_revision = "h8d0e1f2a3b4"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "fretes_pedido_refeicao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("restaurante_id", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["restaurante_id"], ["restaurantes.id"]),
    )
    op.create_index("ix_fretes_pedido_refeicao_data", "fretes_pedido_refeicao", ["data"])
    op.create_index("ix_fretes_pedido_refeicao_restaurante_id", "fretes_pedido_refeicao", ["restaurante_id"])
    op.create_index("ix_fretes_pedido_refeicao_ativo", "fretes_pedido_refeicao", ["ativo"])

def downgrade():
    op.drop_index("ix_fretes_pedido_refeicao_ativo", table_name="fretes_pedido_refeicao")
    op.drop_index("ix_fretes_pedido_refeicao_restaurante_id", table_name="fretes_pedido_refeicao")
    op.drop_index("ix_fretes_pedido_refeicao_data", table_name="fretes_pedido_refeicao")
    op.drop_table("fretes_pedido_refeicao")
