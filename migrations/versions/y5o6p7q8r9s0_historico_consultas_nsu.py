"""Adiciona diagnóstico e histórico das consultas de distribuição NSU.

Revision ID: y5o6p7q8r9s0
Revises: x4n5o6p7q8r9
"""

from alembic import op
import sqlalchemy as sa


revision = "y5o6p7q8r9s0"
down_revision = "x4n5o6p7q8r9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("fiscal_controles_nsu") as batch_op:
        batch_op.add_column(sa.Column("proxima_consulta_em", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("ultimo_cstat", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("ultimo_motivo", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("documentos_ultima_consulta", sa.Integer(), nullable=False, server_default="0")
        )

    op.create_table(
        "fiscal_consultas_nsu_historico",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cnpj_empresa", sa.String(length=14), nullable=False),
        sa.Column("origem", sa.String(length=20), nullable=False),
        sa.Column("consultado_em", sa.DateTime(), nullable=False),
        sa.Column("nsu_enviado", sa.String(length=20), nullable=False),
        sa.Column("cstat", sa.String(length=10), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("ultimo_nsu_recebido", sa.String(length=20), nullable=True),
        sa.Column("max_nsu_recebido", sa.String(length=20), nullable=True),
        sa.Column("documentos_quantidade", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("menor_nsu_documento", sa.String(length=20), nullable=True),
        sa.Column("maior_nsu_documento", sa.String(length=20), nullable=True),
        sa.Column("nsu_gravado", sa.String(length=20), nullable=True),
        sa.Column("gravacao_status", sa.String(length=30), nullable=False),
        sa.Column("proxima_consulta_em", sa.DateTime(), nullable=True),
        sa.Column("erro_tecnico", sa.Text(), nullable=True),
        sa.Column("resposta_xml", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fiscal_consultas_nsu_historico_cnpj_empresa",
        "fiscal_consultas_nsu_historico",
        ["cnpj_empresa"],
    )
    op.create_index(
        "ix_fiscal_consultas_nsu_historico_origem",
        "fiscal_consultas_nsu_historico",
        ["origem"],
    )
    op.create_index(
        "ix_fiscal_consultas_nsu_historico_consultado_em",
        "fiscal_consultas_nsu_historico",
        ["consultado_em"],
    )
    op.create_index(
        "ix_fiscal_consultas_nsu_historico_cstat",
        "fiscal_consultas_nsu_historico",
        ["cstat"],
    )


def downgrade():
    op.drop_index("ix_fiscal_consultas_nsu_historico_cstat", table_name="fiscal_consultas_nsu_historico")
    op.drop_index("ix_fiscal_consultas_nsu_historico_consultado_em", table_name="fiscal_consultas_nsu_historico")
    op.drop_index("ix_fiscal_consultas_nsu_historico_origem", table_name="fiscal_consultas_nsu_historico")
    op.drop_index("ix_fiscal_consultas_nsu_historico_cnpj_empresa", table_name="fiscal_consultas_nsu_historico")
    op.drop_table("fiscal_consultas_nsu_historico")

    with op.batch_alter_table("fiscal_controles_nsu") as batch_op:
        batch_op.drop_column("documentos_ultima_consulta")
        batch_op.drop_column("ultimo_motivo")
        batch_op.drop_column("ultimo_cstat")
        batch_op.drop_column("proxima_consulta_em")
