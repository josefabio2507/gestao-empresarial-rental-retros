"""adiciona dia semana itens cardapio

Revision ID: b8f6a1d3c4e2
Revises: 7f2b9d1c4a6e
Create Date: 2026-05-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b8f6a1d3c4e2"
down_revision = "7f2b9d1c4a6e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "itens_cardapio" not in inspector.get_table_names():
        return

    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns("itens_cardapio")
    }

    if "dia_semana" not in colunas:
        op.add_column(
            "itens_cardapio",
            sa.Column(
                "dia_semana",
                sa.String(length=30),
                nullable=False,
                server_default="Todos os Dias",
            ),
        )

    op.execute(
        "UPDATE itens_cardapio "
        "SET dia_semana = 'Todos os Dias' "
        "WHERE dia_semana IS NULL OR trim(dia_semana) = ''"
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "itens_cardapio" not in inspector.get_table_names():
        return

    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns("itens_cardapio")
    }

    if "dia_semana" in colunas:
        op.drop_column("itens_cardapio", "dia_semana")
