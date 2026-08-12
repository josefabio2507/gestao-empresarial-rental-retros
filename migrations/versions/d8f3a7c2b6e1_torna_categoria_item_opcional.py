"""torna categoria item opcional

Revision ID: d8f3a7c2b6e1
Revises: c8f2e4a6b9d1
Create Date: 2026-08-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d8f3a7c2b6e1"
down_revision = "c8f2e4a6b9d1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_itens" not in inspector.get_table_names():
        return

    colunas = {
        coluna["name"]: coluna
        for coluna in inspector.get_columns("suprimentos_itens")
    }

    if "categoria_id" in colunas and not colunas["categoria_id"]["nullable"]:
        with op.batch_alter_table("suprimentos_itens") as batch_op:
            batch_op.alter_column(
                "categoria_id",
                existing_type=sa.Integer(),
                nullable=True,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_itens" not in inspector.get_table_names():
        return

    categoria = None
    if "suprimentos_categorias_itens" in inspector.get_table_names():
        categorias = sa.table(
            "suprimentos_categorias_itens",
            sa.column("id", sa.Integer),
        )
        categoria = bind.execute(
            sa.select(categorias.c.id).order_by(categorias.c.id.asc())
        ).first()

    if not categoria:
        return

    bind.execute(
        sa.text("UPDATE suprimentos_itens SET categoria_id = :categoria_id WHERE categoria_id IS NULL"),
        {"categoria_id": categoria.id},
    )

    with op.batch_alter_table("suprimentos_itens") as batch_op:
        batch_op.alter_column(
            "categoria_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
