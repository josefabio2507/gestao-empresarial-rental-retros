"""Cria cadastros do submódulo Pedido Tícket.

Revision ID: p1q2r3s4t5u6
Revises: e7f8a9b0c1d2, i0j1k2l3m4n5
Create Date: 2026-11-15 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "p1q2r3s4t5u6"
down_revision = ("e7f8a9b0c1d2", "i0j1k2l3m4n5")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dp_pedido_ticket_empresas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero_pedido", sa.String(length=10), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("nome_empresa", sa.String(length=26), nullable=False),
        sa.Column("numero_contrato", sa.String(length=10), nullable=False),
        sa.Column("produto", sa.String(length=3), nullable=False),
        sa.Column("data_credito", sa.Date(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("numero_pedido", "numero_contrato", "produto", name="uq_dp_ticket_pedido_contrato_produto"),
    )
    op.create_index("ix_dp_pedido_ticket_empresas_numero_pedido", "dp_pedido_ticket_empresas", ["numero_pedido"])
    op.create_index("ix_dp_pedido_ticket_empresas_cnpj", "dp_pedido_ticket_empresas", ["cnpj"])

    op.create_table(
        "dp_pedido_ticket_unidades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("codigo_unidade", sa.String(length=6), nullable=False),
        sa.Column("nome_unidade", sa.String(length=26), nullable=False),
        sa.Column("tipo_logradouro", sa.String(length=4), nullable=False),
        sa.Column("logradouro", sa.String(length=50), nullable=False),
        sa.Column("numero", sa.String(length=6), nullable=False),
        sa.Column("complemento", sa.String(length=10), nullable=True),
        sa.Column("bairro", sa.String(length=15), nullable=False),
        sa.Column("estado", sa.String(length=2), nullable=False),
        sa.Column("cidade", sa.String(length=25), nullable=False),
        sa.Column("cep", sa.String(length=8), nullable=False),
        sa.Column("interlocutor", sa.String(length=50), nullable=False),
        sa.Column("cpf_interlocutor", sa.String(length=11), nullable=True),
        sa.Column("rg_interlocutor", sa.String(length=10), nullable=True),
        sa.Column("ddd", sa.String(length=3), nullable=True),
        sa.Column("telefone", sa.String(length=9), nullable=True),
        sa.Column("ramal", sa.String(length=5), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("cnpj", "codigo_unidade", name="uq_dp_ticket_unidade_empresa_codigo"),
    )
    op.create_index("ix_dp_pedido_ticket_unidades_cnpj", "dp_pedido_ticket_unidades", ["cnpj"])

    op.create_table(
        "dp_pedido_ticket_beneficiarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero_pedido", sa.String(length=10), nullable=False),
        sa.Column("matricula", sa.String(length=12), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("nome", sa.String(length=60), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=False),
        sa.Column("departamento", sa.String(length=50), nullable=True),
        sa.Column("unidade_entrega", sa.String(length=40), nullable=False),
        sa.Column("valor_mensal", sa.Numeric(12, 2), nullable=False),
        sa.Column("contrato_produto", sa.String(length=30), nullable=False),
        sa.Column("numero_parcelas", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("numero_pedido", "cpf", name="uq_dp_ticket_beneficiario_pedido_cpf"),
    )
    op.create_index("ix_dp_pedido_ticket_beneficiarios_numero_pedido", "dp_pedido_ticket_beneficiarios", ["numero_pedido"])
    op.create_index("ix_dp_pedido_ticket_beneficiarios_matricula", "dp_pedido_ticket_beneficiarios", ["matricula"])
    op.create_index("ix_dp_pedido_ticket_beneficiarios_cpf", "dp_pedido_ticket_beneficiarios", ["cpf"])


def downgrade():
    op.drop_index("ix_dp_pedido_ticket_beneficiarios_cpf", table_name="dp_pedido_ticket_beneficiarios")
    op.drop_index("ix_dp_pedido_ticket_beneficiarios_matricula", table_name="dp_pedido_ticket_beneficiarios")
    op.drop_index("ix_dp_pedido_ticket_beneficiarios_numero_pedido", table_name="dp_pedido_ticket_beneficiarios")
    op.drop_table("dp_pedido_ticket_beneficiarios")
    op.drop_index("ix_dp_pedido_ticket_unidades_cnpj", table_name="dp_pedido_ticket_unidades")
    op.drop_table("dp_pedido_ticket_unidades")
    op.drop_index("ix_dp_pedido_ticket_empresas_cnpj", table_name="dp_pedido_ticket_empresas")
    op.drop_index("ix_dp_pedido_ticket_empresas_numero_pedido", table_name="dp_pedido_ticket_empresas")
    op.drop_table("dp_pedido_ticket_empresas")
