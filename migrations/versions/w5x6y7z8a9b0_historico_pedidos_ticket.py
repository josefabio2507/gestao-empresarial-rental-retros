"""Adiciona auditoria e linha do tempo aos pedidos Ticket."""
from alembic import op
import sqlalchemy as sa

revision = "w5x6y7z8a9b0"
down_revision = "v4w5x6y7z8a9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dp_pedido_ticket_eventos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pedido_id", sa.Integer(), nullable=True),
        sa.Column("numero_pedido", sa.String(length=10), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("status_anterior", sa.String(length=20), nullable=True),
        sa.Column("status_novo", sa.String(length=20), nullable=True),
        sa.Column("protocolo", sa.String(length=100), nullable=True),
        sa.Column("arquivo_sha256", sa.String(length=64), nullable=True),
        sa.Column("quantidade_beneficiarios", sa.Integer(), nullable=True),
        sa.Column("valor_total", sa.Numeric(12, 2), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["dp_pedido_ticket_pedidos.id"], name="fk_dp_ticket_evento_pedido", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="fk_dp_ticket_evento_usuario", ondelete="SET NULL"),
    )
    op.create_index("ix_dp_pedido_ticket_eventos_pedido_id", "dp_pedido_ticket_eventos", ["pedido_id"])
    op.create_index("ix_dp_pedido_ticket_eventos_numero_pedido", "dp_pedido_ticket_eventos", ["numero_pedido"])
    op.create_index("ix_dp_pedido_ticket_eventos_criado_em", "dp_pedido_ticket_eventos", ["criado_em"])
    op.create_index("ix_dp_pedido_ticket_eventos_usuario_id", "dp_pedido_ticket_eventos", ["usuario_id"])


def downgrade():
    op.drop_index("ix_dp_pedido_ticket_eventos_usuario_id", table_name="dp_pedido_ticket_eventos")
    op.drop_index("ix_dp_pedido_ticket_eventos_criado_em", table_name="dp_pedido_ticket_eventos")
    op.drop_index("ix_dp_pedido_ticket_eventos_numero_pedido", table_name="dp_pedido_ticket_eventos")
    op.drop_index("ix_dp_pedido_ticket_eventos_pedido_id", table_name="dp_pedido_ticket_eventos")
    op.drop_table("dp_pedido_ticket_eventos")
