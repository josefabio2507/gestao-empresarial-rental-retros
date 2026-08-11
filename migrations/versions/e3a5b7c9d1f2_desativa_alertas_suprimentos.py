"""desativa alertas suprimentos

Revision ID: e3a5b7c9d1f2
Revises: d2f4a6c8e9b1
Create Date: 2026-08-10 20:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e3a5b7c9d1f2"
down_revision = "d2f4a6c8e9b1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "modulos" not in inspector.get_table_names():
        return

    modulos = sa.table(
        "modulos",
        sa.column("slug", sa.String),
        sa.column("ativo", sa.Boolean),
    )
    bind.execute(
        modulos.update()
        .where(modulos.c.slug == "alertas")
        .values(ativo=False)
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "modulos" not in inspector.get_table_names():
        return

    modulos = sa.table(
        "modulos",
        sa.column("slug", sa.String),
        sa.column("ativo", sa.Boolean),
    )
    bind.execute(
        modulos.update()
        .where(modulos.c.slug == "alertas")
        .values(ativo=True)
    )
