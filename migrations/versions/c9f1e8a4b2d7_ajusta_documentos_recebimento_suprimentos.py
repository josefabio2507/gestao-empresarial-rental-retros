"""ajusta documentos recebimento suprimentos

Revision ID: c9f1e8a4b2d7
Revises: b7e4c2a9d1f8
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c9f1e8a4b2d7"
down_revision = "b7e4c2a9d1f8"
branch_labels = None
depends_on = None


def coluna_existe(inspector, tabela, coluna):
    return coluna in {item["name"] for item in inspector.get_columns(tabela)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabela = "suprimentos_recebimentos_compra"

    if tabela not in inspector.get_table_names():
        return

    colunas = {item["name"] for item in inspector.get_columns(tabela)}

    with op.batch_alter_table(tabela, recreate="auto") as batch_op:
        if "tipo_documento" not in colunas:
            batch_op.add_column(
                sa.Column("tipo_documento", sa.String(length=30), nullable=True, server_default="Outro")
            )
        if "numero_documento" not in colunas:
            batch_op.add_column(
                sa.Column("numero_documento", sa.String(length=80), nullable=True, server_default="SEM DOCUMENTO")
            )
        if "data_documento" not in colunas:
            batch_op.add_column(sa.Column("data_documento", sa.Date(), nullable=True))

    inspector = sa.inspect(bind)
    colunas = {item["name"] for item in inspector.get_columns(tabela)}

    if "documento_referencia" in colunas and "numero_documento" in colunas:
        bind.execute(
            sa.text(
                """
                update suprimentos_recebimentos_compra
                   set tipo_documento = coalesce(tipo_documento, 'Outro'),
                       numero_documento = coalesce(nullif(documento_referencia, ''), numero_documento, 'SEM DOCUMENTO')
                 where numero_documento is null
                    or numero_documento = 'SEM DOCUMENTO'
                """
            )
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabela = "suprimentos_recebimentos_compra"

    if tabela not in inspector.get_table_names():
        return

    with op.batch_alter_table(tabela, recreate="auto") as batch_op:
        for coluna in ["data_documento", "numero_documento", "tipo_documento"]:
            if coluna_existe(inspector, tabela, coluna):
                batch_op.drop_column(coluna)
