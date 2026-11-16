"""Cria rascunhos de pedidos Tícket e vincula itens aos colaboradores.

Revision ID: v4w5x6y7z8a9
Revises: u3v4w5x6y7z8
Create Date: 2026-11-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "v4w5x6y7z8a9"
down_revision = "u3v4w5x6y7z8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dp_pedido_ticket_pedidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero_pedido", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="rascunho", nullable=False),
        sa.Column("quantidade_beneficiarios", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valor_total", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_dp_ticket_pedido_usuario"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dp_pedido_ticket_pedidos_numero_pedido", "dp_pedido_ticket_pedidos", ["numero_pedido"], unique=True)
    op.create_index("ix_dp_pedido_ticket_pedidos_status", "dp_pedido_ticket_pedidos", ["status"], unique=False)
    op.add_column("dp_pedido_ticket_beneficiarios", sa.Column("pedido_id", sa.Integer(), nullable=True))
    op.add_column("dp_pedido_ticket_beneficiarios", sa.Column("colaborador_id", sa.Integer(), nullable=True))
    op.create_index("ix_dp_pedido_ticket_beneficiarios_pedido_id", "dp_pedido_ticket_beneficiarios", ["pedido_id"], unique=False)
    op.create_index("ix_dp_pedido_ticket_beneficiarios_colaborador_id", "dp_pedido_ticket_beneficiarios", ["colaborador_id"], unique=False)
    op.create_foreign_key(
        "fk_dp_ticket_beneficiario_pedido", "dp_pedido_ticket_beneficiarios", "dp_pedido_ticket_pedidos",
        ["pedido_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_dp_ticket_beneficiario_colaborador", "dp_pedido_ticket_beneficiarios", "colaboradores",
        ["colaborador_id"], ["id"],
    )


def downgrade():
    op.drop_constraint("fk_dp_ticket_beneficiario_colaborador", "dp_pedido_ticket_beneficiarios", type_="foreignkey")
    op.drop_constraint("fk_dp_ticket_beneficiario_pedido", "dp_pedido_ticket_beneficiarios", type_="foreignkey")
    op.drop_index("ix_dp_pedido_ticket_beneficiarios_colaborador_id", table_name="dp_pedido_ticket_beneficiarios")
    op.drop_index("ix_dp_pedido_ticket_beneficiarios_pedido_id", table_name="dp_pedido_ticket_beneficiarios")
    op.drop_column("dp_pedido_ticket_beneficiarios", "colaborador_id")
    op.drop_column("dp_pedido_ticket_beneficiarios", "pedido_id")
    op.drop_index("ix_dp_pedido_ticket_pedidos_status", table_name="dp_pedido_ticket_pedidos")
    op.drop_index("ix_dp_pedido_ticket_pedidos_numero_pedido", table_name="dp_pedido_ticket_pedidos")
    op.drop_table("dp_pedido_ticket_pedidos")
