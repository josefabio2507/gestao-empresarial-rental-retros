"""torna categoria e descricao de custos extras opcionais

Revision ID: j0f2a3b4c5d6
Revises: i9e1f2a3b4c5
"""
from alembic import op
import sqlalchemy as sa

revision = "j0f2a3b4c5d6"
down_revision = "i9e1f2a3b4c5"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("operacao_abastecimento_custos_extras") as batch_op:
        batch_op.alter_column("categoria", existing_type=sa.String(length=80), nullable=True)
        batch_op.alter_column("descricao", existing_type=sa.String(length=255), nullable=True)

def downgrade():
    with op.batch_alter_table("operacao_abastecimento_custos_extras") as batch_op:
        batch_op.alter_column("categoria", existing_type=sa.String(length=80), nullable=False)
        batch_op.alter_column("descricao", existing_type=sa.String(length=255), nullable=False)
