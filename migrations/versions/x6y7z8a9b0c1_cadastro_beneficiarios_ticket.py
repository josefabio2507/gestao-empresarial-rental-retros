"""Adiciona data de nascimento e cadastro de beneficiários Ticket."""
from alembic import op
import sqlalchemy as sa

revision = "x6y7z8a9b0c1"
down_revision = "w5x6y7z8a9b0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("colaboradores", sa.Column("data_nascimento", sa.Date(), nullable=True))
    op.create_table(
        "dp_pedido_ticket_cadastros_beneficiarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("colaborador_id", sa.Integer(), nullable=False),
        sa.Column("tipo_beneficio", sa.String(length=3), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["colaborador_id"], ["colaboradores.id"], name="fk_dp_ticket_cadastro_beneficiario_colaborador"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("colaborador_id", "tipo_beneficio", name="uq_dp_ticket_cadastro_colaborador_beneficio"),
    )
    op.create_index(
        "ix_dp_pedido_ticket_cadastros_beneficiarios_colaborador_id",
        "dp_pedido_ticket_cadastros_beneficiarios",
        ["colaborador_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_dp_pedido_ticket_cadastros_beneficiarios_colaborador_id", table_name="dp_pedido_ticket_cadastros_beneficiarios")
    op.drop_table("dp_pedido_ticket_cadastros_beneficiarios")
    op.drop_column("colaboradores", "data_nascimento")
