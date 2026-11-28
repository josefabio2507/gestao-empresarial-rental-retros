"""Adiciona regras e composição de valores ao Pedido Tícket."""

from alembic import op
import sqlalchemy as sa


revision = "y7z8a9b0c1d2"
down_revision = "x6y7z8a9b0c1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dp_pedido_ticket_tabelas_valores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("numero_contrato", sa.String(length=10), nullable=False),
        sa.Column("tipo_beneficio", sa.String(length=3), nullable=False),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        sa.Column("valor_diaria", sa.Numeric(12, 2), nullable=False),
        sa.Column("valor_cesta", sa.Numeric(12, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "tipo_beneficio in ('TAE', 'TRE', 'TKE', 'TFE')",
            name="ck_dp_ticket_valor_tipo_beneficio",
        ),
        sa.CheckConstraint(
            "valor_diaria >= 0 AND valor_cesta >= 0 AND (valor_diaria > 0 OR valor_cesta > 0)",
            name="ck_dp_ticket_valor_componentes_positivos",
        ),
        sa.CheckConstraint(
            "data_fim is null or data_fim >= data_inicio",
            name="ck_dp_ticket_valor_vigencia",
        ),
        sa.ForeignKeyConstraint(
            ["criado_por_usuario_id"], ["usuarios.id"],
            name="fk_dp_ticket_valor_usuario", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dp_pedido_ticket_tabelas_valores"),
        sa.UniqueConstraint(
            "cnpj", "numero_contrato", "tipo_beneficio", "data_inicio",
            name="uq_dp_ticket_valor_vigencia",
        ),
    )
    op.create_index(
        "ix_dp_pedido_ticket_tabelas_valores_cnpj",
        "dp_pedido_ticket_tabelas_valores",
        ["cnpj"],
    )

    op.add_column(
        "dp_pedido_ticket_cadastros_beneficiarios",
        sa.Column("tipo_calculo", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "dp_pedido_ticket_cadastros_beneficiarios",
        sa.Column("valor_fixo_mensal", sa.Numeric(12, 2), nullable=True),
    )

    op.add_column(
        "dp_pedido_ticket_beneficiarios",
        sa.Column("tipo_calculo", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "dp_pedido_ticket_beneficiarios",
        sa.Column("quantidade_diarias", sa.Integer(), nullable=True),
    )
    op.add_column(
        "dp_pedido_ticket_beneficiarios",
        sa.Column("valor_diaria", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "dp_pedido_ticket_beneficiarios",
        sa.Column("valor_cesta", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "dp_pedido_ticket_beneficiarios",
        sa.Column("valor_fixo_mensal_aplicado", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "dp_pedido_ticket_beneficiarios",
        sa.Column(
            "tabela_valor_id",
            sa.Integer(),
            sa.ForeignKey(
                "dp_pedido_ticket_tabelas_valores.id",
                name="fk_dp_ticket_beneficiario_tabela_valor",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_dp_pedido_ticket_beneficiarios_tabela_valor_id",
        "dp_pedido_ticket_beneficiarios",
        ["tabela_valor_id"],
    )


def downgrade():
    op.drop_index(
        "ix_dp_pedido_ticket_beneficiarios_tabela_valor_id",
        table_name="dp_pedido_ticket_beneficiarios",
    )
    op.drop_column("dp_pedido_ticket_beneficiarios", "tabela_valor_id")
    op.drop_column("dp_pedido_ticket_beneficiarios", "valor_fixo_mensal_aplicado")
    op.drop_column("dp_pedido_ticket_beneficiarios", "valor_cesta")
    op.drop_column("dp_pedido_ticket_beneficiarios", "valor_diaria")
    op.drop_column("dp_pedido_ticket_beneficiarios", "quantidade_diarias")
    op.drop_column("dp_pedido_ticket_beneficiarios", "tipo_calculo")
    op.drop_column("dp_pedido_ticket_cadastros_beneficiarios", "valor_fixo_mensal")
    op.drop_column("dp_pedido_ticket_cadastros_beneficiarios", "tipo_calculo")
    op.drop_index(
        "ix_dp_pedido_ticket_tabelas_valores_cnpj",
        table_name="dp_pedido_ticket_tabelas_valores",
    )
    op.drop_table("dp_pedido_ticket_tabelas_valores")
