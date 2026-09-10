"""Importacao de parcelas legadas e saldo pago historico.

Revision ID: m3c4d5e6f7a8
Revises: l2b3c4d5e6f7
"""
from alembic import op
import sqlalchemy as sa

revision = "m3c4d5e6f7a8"
down_revision = "l2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("financeiro_contas_pagar_titulos") as batch:
        batch.add_column(sa.Column("chave_legado_cartao", sa.String(100), nullable=True))
        batch.add_column(sa.Column("valor_pago_legado", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch.create_unique_constraint("uq_fin_titulo_chave_legado_cartao", ["chave_legado_cartao"])
    op.create_table(
        "financeiro_importacoes_cartao",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("arquivo_nome", sa.String(255), nullable=False),
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
    )
    op.create_index("ix_financeiro_importacoes_cartao_usuario_id", "financeiro_importacoes_cartao", ["usuario_id"])


def downgrade():
    op.drop_table("financeiro_importacoes_cartao")
    with op.batch_alter_table("financeiro_contas_pagar_titulos") as batch:
        batch.drop_constraint("uq_fin_titulo_chave_legado_cartao", type_="unique")
        batch.drop_column("valor_pago_legado")
        batch.drop_column("chave_legado_cartao")
