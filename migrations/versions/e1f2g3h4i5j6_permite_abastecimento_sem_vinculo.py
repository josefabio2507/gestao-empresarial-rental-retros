"""permite abastecimento sem vinculo

Revision ID: e1f2g3h4i5j6
Revises: b8e1c2d3f4a5, d0t1u2v3w4x5
"""

from alembic import op
import sqlalchemy as sa


revision = "e1f2g3h4i5j6"
down_revision = ("b8e1c2d3f4a5", "d0t1u2v3w4x5")
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("operacao_abastecimentos") as batch_op:
        batch_op.alter_column("vinculo_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("colaborador_id", existing_type=sa.Integer(), nullable=True)


def downgrade():
    with op.batch_alter_table("operacao_abastecimentos") as batch_op:
        batch_op.alter_column("colaborador_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("vinculo_id", existing_type=sa.Integer(), nullable=False)
