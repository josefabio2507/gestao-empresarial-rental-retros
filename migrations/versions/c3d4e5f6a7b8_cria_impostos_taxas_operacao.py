"""cria impostos e taxas operacao

Revision ID: c3d4e5f6a7b8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-23 22:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operacao_impostos_taxas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("veiculo_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo_custo", sa.String(length=30), nullable=False),
        sa.Column("numero_parcela", sa.String(length=20), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("tipo_custo in ('IPVA', 'Licenciamento')", name="ck_operacao_impostos_taxas_tipo_custo"),
        sa.CheckConstraint(
            "numero_parcela in ('Cota Unica', '1a', '2a', '3a', '4a', '5a')",
            name="ck_operacao_impostos_taxas_numero_parcela",
        ),
        sa.CheckConstraint("valor >= 0", name="ck_operacao_impostos_taxas_valor"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["veiculo_id"], ["operacao_veiculos_equipamentos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operacao_impostos_taxas_data_vencimento", "operacao_impostos_taxas", ["data_vencimento"])
    op.create_index("ix_operacao_impostos_taxas_numero_parcela", "operacao_impostos_taxas", ["numero_parcela"])
    op.create_index("ix_operacao_impostos_taxas_tipo_custo", "operacao_impostos_taxas", ["tipo_custo"])
    op.create_index("ix_operacao_impostos_taxas_usuario_id", "operacao_impostos_taxas", ["usuario_id"])
    op.create_index("ix_operacao_impostos_taxas_veiculo_id", "operacao_impostos_taxas", ["veiculo_id"])


def downgrade():
    op.drop_index("ix_operacao_impostos_taxas_veiculo_id", table_name="operacao_impostos_taxas")
    op.drop_index("ix_operacao_impostos_taxas_usuario_id", table_name="operacao_impostos_taxas")
    op.drop_index("ix_operacao_impostos_taxas_tipo_custo", table_name="operacao_impostos_taxas")
    op.drop_index("ix_operacao_impostos_taxas_numero_parcela", table_name="operacao_impostos_taxas")
    op.drop_index("ix_operacao_impostos_taxas_data_vencimento", table_name="operacao_impostos_taxas")
    op.drop_table("operacao_impostos_taxas")
