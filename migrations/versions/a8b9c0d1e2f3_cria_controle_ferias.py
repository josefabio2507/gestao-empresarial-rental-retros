"""Cria controle de ferias por colaborador."""

from alembic import op
import sqlalchemy as sa


revision = "c9d0e1f2a3b4"
down_revision = ("a8b9c0d1e2f3", "z7q8r9s0t1u2")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ferias_colaboradores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("colaborador_id", sa.Integer(), sa.ForeignKey("colaboradores.id"), nullable=False),
        sa.Column("periodo_aquisitivo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_aquisitivo_fim", sa.Date(), nullable=False),
        sa.Column("inicio_ferias", sa.Date(), nullable=False),
        sa.Column("fim_ferias", sa.Date(), nullable=False),
        sa.Column("dias", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("abono_pecuniario", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="programada"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ferias_colaboradores_colaborador_id", "ferias_colaboradores", ["colaborador_id"])
    op.create_index("ix_ferias_colaboradores_status", "ferias_colaboradores", ["status"])


def downgrade():
    op.drop_index("ix_ferias_colaboradores_status", table_name="ferias_colaboradores")
    op.drop_index("ix_ferias_colaboradores_colaborador_id", table_name="ferias_colaboradores")
    op.drop_table("ferias_colaboradores")
