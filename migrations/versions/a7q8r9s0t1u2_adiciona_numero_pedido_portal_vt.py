"""adiciona numero do pedido BR Mobilidade

Revision ID: a7q8r9s0t1u2
Revises: z6p7q8r9s0t1
"""

from alembic import op
import sqlalchemy as sa


revision = "a7q8r9s0t1u2"
down_revision = "z6p7q8r9s0t1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("vale_transporte_integracoes_br_mobilidade") as batch_op:
        batch_op.add_column(sa.Column("numero_pedido_portal", sa.String(30), nullable=True))
        batch_op.create_unique_constraint(
            "uq_vt_br_integracao_numero_pedido_portal",
            ["numero_pedido_portal"],
        )
        batch_op.create_index(
            "ix_vt_br_integracao_numero_pedido_portal",
            ["numero_pedido_portal"],
        )


def downgrade():
    with op.batch_alter_table("vale_transporte_integracoes_br_mobilidade") as batch_op:
        batch_op.drop_index("ix_vt_br_integracao_numero_pedido_portal")
        batch_op.drop_constraint(
            "uq_vt_br_integracao_numero_pedido_portal",
            type_="unique",
        )
        batch_op.drop_column("numero_pedido_portal")
