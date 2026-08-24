"""cria multas de transito operacao

Revision ID: c1d2e3f4a5b6
Revises: c0d1e2f3a4b5
Create Date: 2026-08-23 21:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operacao_multas_transito",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("veiculo_id", sa.Integer(), nullable=False),
        sa.Column("motorista_vinculado_id", sa.Integer(), nullable=True),
        sa.Column("motorista_indicado_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("data_infracao", sa.Date(), nullable=False),
        sa.Column("hora_infracao", sa.Time(), nullable=False),
        sa.Column("numero_auto_infracao", sa.String(length=80), nullable=False),
        sa.Column("local_infracao", sa.String(length=255), nullable=False),
        sa.Column("cidade", sa.String(length=80), nullable=False),
        sa.Column("descricao_infracao", sa.Text(), nullable=False),
        sa.Column("valor_multa", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column("gravidade", sa.String(length=40), nullable=False),
        sa.Column("pontuacao", sa.Integer(), nullable=False),
        sa.Column("data_vencimento_segunda_cobranca", sa.Date(), nullable=True),
        sa.Column("valor_segunda_cobranca", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "cidade in ('CUBATAO', 'SANTOS', 'SAO VICENTE', 'GUARUJA', 'PRAIA GRANDE', 'ITANHAEM', 'MONGAGUA', 'SAO PAULO')",
            name="ck_operacao_multas_transito_cidade",
        ),
        sa.CheckConstraint(
            "gravidade in ('Leve', 'Media', 'Grave', 'Gravissima')",
            name="ck_operacao_multas_transito_gravidade",
        ),
        sa.CheckConstraint("valor_multa >= 0", name="ck_operacao_multas_transito_valor"),
        sa.CheckConstraint(
            "valor_segunda_cobranca is null or valor_segunda_cobranca >= 0",
            name="ck_operacao_multas_transito_valor_segunda",
        ),
        sa.CheckConstraint("pontuacao >= 0", name="ck_operacao_multas_transito_pontuacao"),
        sa.ForeignKeyConstraint(["motorista_indicado_id"], ["colaboradores.id"]),
        sa.ForeignKeyConstraint(["motorista_vinculado_id"], ["colaboradores.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["veiculo_id"], ["operacao_veiculos_equipamentos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_auto_infracao", name="uq_operacao_multas_transito_auto"),
    )
    op.create_index("ix_operacao_multas_transito_cidade", "operacao_multas_transito", ["cidade"])
    op.create_index("ix_operacao_multas_transito_data_infracao", "operacao_multas_transito", ["data_infracao"])
    op.create_index("ix_operacao_multas_transito_motorista_indicado_id", "operacao_multas_transito", ["motorista_indicado_id"])
    op.create_index("ix_operacao_multas_transito_motorista_vinculado_id", "operacao_multas_transito", ["motorista_vinculado_id"])
    op.create_index("ix_operacao_multas_transito_numero_auto_infracao", "operacao_multas_transito", ["numero_auto_infracao"])
    op.create_index("ix_operacao_multas_transito_usuario_id", "operacao_multas_transito", ["usuario_id"])
    op.create_index("ix_operacao_multas_transito_veiculo_id", "operacao_multas_transito", ["veiculo_id"])


def downgrade():
    op.drop_index("ix_operacao_multas_transito_veiculo_id", table_name="operacao_multas_transito")
    op.drop_index("ix_operacao_multas_transito_usuario_id", table_name="operacao_multas_transito")
    op.drop_index("ix_operacao_multas_transito_numero_auto_infracao", table_name="operacao_multas_transito")
    op.drop_index("ix_operacao_multas_transito_motorista_vinculado_id", table_name="operacao_multas_transito")
    op.drop_index("ix_operacao_multas_transito_motorista_indicado_id", table_name="operacao_multas_transito")
    op.drop_index("ix_operacao_multas_transito_data_infracao", table_name="operacao_multas_transito")
    op.drop_index("ix_operacao_multas_transito_cidade", table_name="operacao_multas_transito")
    op.drop_table("operacao_multas_transito")
