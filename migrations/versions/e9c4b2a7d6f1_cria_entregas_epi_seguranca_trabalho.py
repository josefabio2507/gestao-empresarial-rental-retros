"""cria entregas epi seguranca trabalho

Revision ID: e9c4b2a7d6f1
Revises: d8f3a7c2b6e1
Create Date: 2026-08-13 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e9c4b2a7d6f1"
down_revision = "d8f3a7c2b6e1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "seguranca_trabalho_entregas_epi" in inspector.get_table_names():
        return

    op.create_table(
        "seguranca_trabalho_entregas_epi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("colaborador_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("movimentacao_estoque_id", sa.Integer(), nullable=True),
        sa.Column("entregue_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo_material", sa.String(length=20), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
        sa.Column("data_entrega", sa.Date(), nullable=False),
        sa.Column("ca_numero", sa.String(length=80), nullable=True),
        sa.Column("tamanho", sa.String(length=40), nullable=True),
        sa.Column("motivo_entrega", sa.String(length=160), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "tipo_material in ('EPI', 'Uniforme')",
            name="ck_seguranca_entregas_epi_tipo_material",
        ),
        sa.CheckConstraint(
            "quantidade > 0",
            name="ck_seguranca_entregas_epi_quantidade",
        ),
        sa.ForeignKeyConstraint(["colaborador_id"], ["colaboradores.id"]),
        sa.ForeignKeyConstraint(["entregue_por_usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["suprimentos_itens.id"]),
        sa.ForeignKeyConstraint(["movimentacao_estoque_id"], ["suprimentos_movimentacoes_estoque.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seguranca_entregas_epi_colaborador_id", "seguranca_trabalho_entregas_epi", ["colaborador_id"])
    op.create_index("ix_seguranca_entregas_epi_data_entrega", "seguranca_trabalho_entregas_epi", ["data_entrega"])
    op.create_index("ix_seguranca_entregas_epi_entregue_por", "seguranca_trabalho_entregas_epi", ["entregue_por_usuario_id"])
    op.create_index("ix_seguranca_entregas_epi_item_id", "seguranca_trabalho_entregas_epi", ["item_id"])
    op.create_index(
        "ix_seguranca_entregas_epi_movimentacao",
        "seguranca_trabalho_entregas_epi",
        ["movimentacao_estoque_id"],
        unique=True,
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "seguranca_trabalho_entregas_epi" not in inspector.get_table_names():
        return

    op.drop_index("ix_seguranca_entregas_epi_movimentacao", table_name="seguranca_trabalho_entregas_epi")
    op.drop_index("ix_seguranca_entregas_epi_item_id", table_name="seguranca_trabalho_entregas_epi")
    op.drop_index("ix_seguranca_entregas_epi_entregue_por", table_name="seguranca_trabalho_entregas_epi")
    op.drop_index("ix_seguranca_entregas_epi_data_entrega", table_name="seguranca_trabalho_entregas_epi")
    op.drop_index("ix_seguranca_entregas_epi_colaborador_id", table_name="seguranca_trabalho_entregas_epi")
    op.drop_table("seguranca_trabalho_entregas_epi")
