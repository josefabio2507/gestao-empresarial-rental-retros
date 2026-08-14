"""cria gestao de veiculos e epgs operacao

Revision ID: b2e6f8a9c4d1
Revises: e9c4b2a7d6f1
Create Date: 2026-08-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b2e6f8a9c4d1"
down_revision = "e9c4b2a7d6f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operacao_veiculos_equipamentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identificacao", sa.String(length=80), nullable=False),
        sa.Column("placa", sa.String(length=20), nullable=True),
        sa.Column("descricao", sa.String(length=180), nullable=False),
        sa.Column("chassi", sa.String(length=80), nullable=True),
        sa.Column("renavam", sa.String(length=40), nullable=True),
        sa.Column("centro_custo", sa.String(length=260), nullable=False),
        sa.Column("situacao_aquisicao", sa.String(length=30), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "situacao_aquisicao in ('Quitado', 'Financiado')",
            name="ck_operacao_veiculos_situacao_aquisicao",
        ),
        sa.CheckConstraint(
            "tipo in ('Veiculo leve', 'Caminhao', 'Maquina', 'Equipamento', 'EPG', 'Outro')",
            name="ck_operacao_veiculos_tipo",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chassi", name="uq_operacao_veiculos_chassi"),
        sa.UniqueConstraint("identificacao", name="uq_operacao_veiculos_identificacao"),
    )
    op.create_index(
        "ix_operacao_veiculos_equipamentos_ativo",
        "operacao_veiculos_equipamentos",
        ["ativo"],
    )
    op.create_index(
        "ix_operacao_veiculos_equipamentos_centro_custo",
        "operacao_veiculos_equipamentos",
        ["centro_custo"],
    )
    op.create_index(
        "ix_operacao_veiculos_equipamentos_chassi",
        "operacao_veiculos_equipamentos",
        ["chassi"],
    )
    op.create_index(
        "ix_operacao_veiculos_equipamentos_identificacao",
        "operacao_veiculos_equipamentos",
        ["identificacao"],
    )
    op.create_index(
        "ix_operacao_veiculos_equipamentos_placa",
        "operacao_veiculos_equipamentos",
        ["placa"],
    )


def downgrade():
    op.drop_index(
        "ix_operacao_veiculos_equipamentos_placa",
        table_name="operacao_veiculos_equipamentos",
    )
    op.drop_index(
        "ix_operacao_veiculos_equipamentos_identificacao",
        table_name="operacao_veiculos_equipamentos",
    )
    op.drop_index(
        "ix_operacao_veiculos_equipamentos_chassi",
        table_name="operacao_veiculos_equipamentos",
    )
    op.drop_index(
        "ix_operacao_veiculos_equipamentos_centro_custo",
        table_name="operacao_veiculos_equipamentos",
    )
    op.drop_index(
        "ix_operacao_veiculos_equipamentos_ativo",
        table_name="operacao_veiculos_equipamentos",
    )
    op.drop_table("operacao_veiculos_equipamentos")
