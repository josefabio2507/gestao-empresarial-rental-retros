"""adiciona email compradores suprimentos

Revision ID: c1e3f5a7b9d2
Revises: b9d2e4f6a8c1
Create Date: 2026-08-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c1e3f5a7b9d2"
down_revision = "b9d2e4f6a8c1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_compradores" not in inspector.get_table_names():
        return

    colunas = [coluna["name"] for coluna in inspector.get_columns("suprimentos_compradores")]
    if "email" not in colunas:
        with op.batch_alter_table("suprimentos_compradores") as batch_op:
            batch_op.add_column(sa.Column("email", sa.String(150), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_compradores" not in inspector.get_table_names():
        return

    colunas = [coluna["name"] for coluna in inspector.get_columns("suprimentos_compradores")]
    if "email" in colunas:
        with op.batch_alter_table("suprimentos_compradores") as batch_op:
            batch_op.drop_column("email")
