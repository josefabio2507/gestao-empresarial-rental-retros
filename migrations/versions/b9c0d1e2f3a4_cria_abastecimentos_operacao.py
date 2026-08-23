"""cria abastecimentos operacao

Revision ID: b9c0d1e2f3a4
Revises: b8c9d0e1f2a3
Create Date: 2026-08-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b9c0d1e2f3a4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operacao_abastecimentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("veiculo_id", sa.Integer(), nullable=False),
        sa.Column("vinculo_id", sa.Integer(), nullable=False),
        sa.Column("colaborador_id", sa.Integer(), nullable=False),
        sa.Column("equipe_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("data_abastecimento", sa.Date(), nullable=False),
        sa.Column("tipo_combustivel", sa.String(length=40), nullable=False),
        sa.Column("qtd_litros", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("preco", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cupom_drive_file_id", sa.String(length=255), nullable=True),
        sa.Column("cupom_nome_arquivo", sa.String(length=255), nullable=True),
        sa.Column("cupom_link", sa.String(length=500), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "tipo_combustivel in ('Diesel', 'Diesel S10', 'Gasolina', 'Etanol', 'Arla 32', 'Outro')",
            name="ck_operacao_abastecimentos_tipo_combustivel",
        ),
        sa.CheckConstraint("qtd_litros > 0", name="ck_operacao_abastecimentos_qtd_litros"),
        sa.CheckConstraint("preco >= 0", name="ck_operacao_abastecimentos_preco"),
        sa.ForeignKeyConstraint(["colaborador_id"], ["colaboradores.id"]),
        sa.ForeignKeyConstraint(["equipe_id"], ["equipes.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["veiculo_id"], ["operacao_veiculos_equipamentos.id"]),
        sa.ForeignKeyConstraint(["vinculo_id"], ["operacao_veiculos_responsaveis.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operacao_abastecimentos_colaborador_id", "operacao_abastecimentos", ["colaborador_id"])
    op.create_index("ix_operacao_abastecimentos_data_abastecimento", "operacao_abastecimentos", ["data_abastecimento"])
    op.create_index("ix_operacao_abastecimentos_equipe_id", "operacao_abastecimentos", ["equipe_id"])
    op.create_index("ix_operacao_abastecimentos_tipo_combustivel", "operacao_abastecimentos", ["tipo_combustivel"])
    op.create_index("ix_operacao_abastecimentos_usuario_id", "operacao_abastecimentos", ["usuario_id"])
    op.create_index("ix_operacao_abastecimentos_veiculo_id", "operacao_abastecimentos", ["veiculo_id"])
    op.create_index("ix_operacao_abastecimentos_vinculo_id", "operacao_abastecimentos", ["vinculo_id"])


def downgrade():
    op.drop_index("ix_operacao_abastecimentos_vinculo_id", table_name="operacao_abastecimentos")
    op.drop_index("ix_operacao_abastecimentos_veiculo_id", table_name="operacao_abastecimentos")
    op.drop_index("ix_operacao_abastecimentos_usuario_id", table_name="operacao_abastecimentos")
    op.drop_index("ix_operacao_abastecimentos_tipo_combustivel", table_name="operacao_abastecimentos")
    op.drop_index("ix_operacao_abastecimentos_equipe_id", table_name="operacao_abastecimentos")
    op.drop_index("ix_operacao_abastecimentos_data_abastecimento", table_name="operacao_abastecimentos")
    op.drop_index("ix_operacao_abastecimentos_colaborador_id", table_name="operacao_abastecimentos")
    op.drop_table("operacao_abastecimentos")
