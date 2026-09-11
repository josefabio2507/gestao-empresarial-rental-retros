"""Remove estrutura temporaria da importacao de cartao legado.

Revision ID: p6f7a8b9c0d1
Revises: o5e6f7a8b9c0
"""
from alembic import op
import sqlalchemy as sa


revision = "p6f7a8b9c0d1"
down_revision = "o5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index(
        "ix_financeiro_importacoes_cartao_usuario_id",
        table_name="financeiro_importacoes_cartao",
    )
    op.drop_table("financeiro_importacoes_cartao")


def downgrade():
    op.create_table(
        "financeiro_importacoes_cartao",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("arquivo_nome", sa.String(length=255), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=False),
        sa.Column("mapeamento", sa.JSON(), nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False),
        sa.Column("importados", sa.Integer(), nullable=False),
        sa.Column("ignorados", sa.Integer(), nullable=False),
        sa.Column("pendentes", sa.Integer(), nullable=False),
        sa.Column("iniciado", sa.Boolean(), nullable=False),
        sa.Column("concluido", sa.Boolean(), nullable=False),
        sa.Column("proximo_lote_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_financeiro_importacoes_cartao_usuario_id",
        "financeiro_importacoes_cartao",
        ["usuario_id"],
        unique=False,
    )
