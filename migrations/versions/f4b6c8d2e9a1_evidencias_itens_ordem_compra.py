"""evidencias itens ordem compra

Revision ID: f4b6c8d2e9a1
Revises: e3a5b7c9d1f2
Create Date: 2026-08-10 21:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f4b6c8d2e9a1"
down_revision = "e3a5b7c9d1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "suprimentos_oc_item_evidencias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ordem_compra_id", sa.Integer(), nullable=False),
        sa.Column("ordem_compra_item_id", sa.Integer(), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column("numero_oc_snapshot", sa.String(length=30), nullable=False),
        sa.Column("numero_item_snapshot", sa.String(length=20), nullable=False),
        sa.Column("descricao_item_snapshot", sa.String(length=220), nullable=False),
        sa.Column("unidade_medida_snapshot", sa.String(length=20), nullable=False),
        sa.Column("quantidade_snapshot", sa.Numeric(12, 3), nullable=False),
        sa.Column("destino_real", sa.Text(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("data_evidencia", sa.Date(), nullable=False),
        sa.Column("foto_1_drive_file_id", sa.String(length=120), nullable=False),
        sa.Column("foto_1_nome_arquivo", sa.String(length=180), nullable=False),
        sa.Column("foto_1_link", sa.String(length=500), nullable=True),
        sa.Column("foto_2_drive_file_id", sa.String(length=120), nullable=True),
        sa.Column("foto_2_nome_arquivo", sa.String(length=180), nullable=True),
        sa.Column("foto_2_link", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status in ('Pendente', 'Evidenciado', 'Cancelado')",
            name="ck_suprimentos_oc_item_evidencias_status",
        ),
        sa.ForeignKeyConstraint(
            ["criado_por_usuario_id"],
            ["usuarios.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ordem_compra_id"],
            ["suprimentos_ordens_compra.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ordem_compra_item_id"],
            ["suprimentos_ordem_compra_itens.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ordem_compra_item_id",
            name="uq_suprimentos_oc_item_evidencia_item",
        ),
    )
    op.create_index(
        op.f("ix_suprimentos_oc_item_evidencias_criado_por_usuario_id"),
        "suprimentos_oc_item_evidencias",
        ["criado_por_usuario_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_suprimentos_oc_item_evidencias_data_evidencia"),
        "suprimentos_oc_item_evidencias",
        ["data_evidencia"],
        unique=False,
    )
    op.create_index(
        op.f("ix_suprimentos_oc_item_evidencias_ordem_compra_id"),
        "suprimentos_oc_item_evidencias",
        ["ordem_compra_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_suprimentos_oc_item_evidencias_ordem_compra_item_id"),
        "suprimentos_oc_item_evidencias",
        ["ordem_compra_item_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_suprimentos_oc_item_evidencias_status"),
        "suprimentos_oc_item_evidencias",
        ["status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_suprimentos_oc_item_evidencias_status"),
        table_name="suprimentos_oc_item_evidencias",
    )
    op.drop_index(
        op.f("ix_suprimentos_oc_item_evidencias_ordem_compra_item_id"),
        table_name="suprimentos_oc_item_evidencias",
    )
    op.drop_index(
        op.f("ix_suprimentos_oc_item_evidencias_ordem_compra_id"),
        table_name="suprimentos_oc_item_evidencias",
    )
    op.drop_index(
        op.f("ix_suprimentos_oc_item_evidencias_data_evidencia"),
        table_name="suprimentos_oc_item_evidencias",
    )
    op.drop_index(
        op.f("ix_suprimentos_oc_item_evidencias_criado_por_usuario_id"),
        table_name="suprimentos_oc_item_evidencias",
    )
    op.drop_table("suprimentos_oc_item_evidencias")
