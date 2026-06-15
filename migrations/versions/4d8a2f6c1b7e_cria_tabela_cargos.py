"""cria tabela cargos

Revision ID: 4d8a2f6c1b7e
Revises: 9c3d2a1b4e5f
Create Date: 2026-06-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4d8a2f6c1b7e"
down_revision = "9c3d2a1b4e5f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cargos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column(
            "ativo",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("cargos")
