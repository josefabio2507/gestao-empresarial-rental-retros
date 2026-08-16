"""prepara pynfe certificado fiscal

Revision ID: c3a9e5f1b7d2
Revises: b6f2d9c1e4a8
Create Date: 2026-08-15 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3a9e5f1b7d2"
down_revision = "b6f2d9c1e4a8"
branch_labels = None
depends_on = None


def _colunas(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "fiscal_certificados_a1" not in inspector.get_table_names():
        return

    colunas = _colunas(inspector, "fiscal_certificados_a1")
    if "senha_criptografada" not in colunas:
        with op.batch_alter_table("fiscal_certificados_a1") as batch_op:
            batch_op.add_column(sa.Column("senha_criptografada", sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "fiscal_certificados_a1" not in inspector.get_table_names():
        return

    colunas = _colunas(inspector, "fiscal_certificados_a1")
    if "senha_criptografada" in colunas:
        with op.batch_alter_table("fiscal_certificados_a1") as batch_op:
            batch_op.drop_column("senha_criptografada")
