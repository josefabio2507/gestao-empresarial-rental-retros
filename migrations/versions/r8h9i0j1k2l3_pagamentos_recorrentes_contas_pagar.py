"""Adiciona rastreio de pagamentos recorrentes em contas a pagar.

Revision ID: r8h9i0j1k2l3
Revises: q7g8h9i0j1k2
"""

from alembic import op
import sqlalchemy as sa


revision = "r8h9i0j1k2l3"
down_revision = "q7g8h9i0j1k2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("financeiro_contas_pagar_titulos") as batch_op:
        batch_op.add_column(sa.Column("recorrencia_grupo_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("recorrencia_periodicidade", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("recorrencia_sequencia", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("recorrencia_total", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("recorrencia_descricao", sa.String(length=120), nullable=True))
        batch_op.create_index("ix_financeiro_contas_pagar_titulos_recorrencia_grupo_id", ["recorrencia_grupo_id"])
        batch_op.create_check_constraint(
            "ck_financeiro_cp_recorrencia_periodicidade",
            "recorrencia_periodicidade is null or recorrencia_periodicidade in ('Mensal', 'Quinzenal', 'Semanal', 'Anual')",
        )
        batch_op.create_check_constraint(
            "ck_financeiro_cp_recorrencia_total",
            "recorrencia_total is null or (recorrencia_total >= 1 and recorrencia_total <= 60)",
        )
        batch_op.create_check_constraint(
            "ck_financeiro_cp_recorrencia_sequencia",
            "recorrencia_sequencia is null or recorrencia_sequencia >= 1",
        )
        batch_op.create_unique_constraint(
            "uq_financeiro_cp_recorrencia_grupo_sequencia",
            ["recorrencia_grupo_id", "recorrencia_sequencia"],
        )


def downgrade():
    with op.batch_alter_table("financeiro_contas_pagar_titulos") as batch_op:
        batch_op.drop_constraint("uq_financeiro_cp_recorrencia_grupo_sequencia", type_="unique")
        batch_op.drop_constraint("ck_financeiro_cp_recorrencia_sequencia", type_="check")
        batch_op.drop_constraint("ck_financeiro_cp_recorrencia_total", type_="check")
        batch_op.drop_constraint("ck_financeiro_cp_recorrencia_periodicidade", type_="check")
        batch_op.drop_index("ix_financeiro_contas_pagar_titulos_recorrencia_grupo_id")
        batch_op.drop_column("recorrencia_descricao")
        batch_op.drop_column("recorrencia_total")
        batch_op.drop_column("recorrencia_sequencia")
        batch_op.drop_column("recorrencia_periodicidade")
        batch_op.drop_column("recorrencia_grupo_id")
