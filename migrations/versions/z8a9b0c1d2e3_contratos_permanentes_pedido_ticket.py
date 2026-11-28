"""Separa o cadastro permanente de contratos dos pedidos Tícket."""

from alembic import op
import sqlalchemy as sa


revision = "z8a9b0c1d2e3"
down_revision = "y7z8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dp_pedido_ticket_contratos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cnpj", sa.String(length=14), nullable=False),
        sa.Column("nome_empresa", sa.String(length=26), nullable=False),
        sa.Column("numero_contrato", sa.String(length=10), nullable=False),
        sa.Column("produto", sa.String(length=3), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "produto in ('TAE', 'TRE', 'TKE', 'TFE')",
            name="ck_dp_ticket_contrato_produto",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dp_pedido_ticket_contratos"),
        sa.UniqueConstraint(
            "cnpj", "numero_contrato", "produto",
            name="uq_dp_ticket_contrato_identidade",
        ),
    )
    op.create_index(
        "ix_dp_pedido_ticket_contratos_cnpj",
        "dp_pedido_ticket_contratos",
        ["cnpj"],
    )

    contratos = sa.table(
        "dp_pedido_ticket_contratos",
        sa.column("id", sa.Integer()),
        sa.column("cnpj", sa.String()),
        sa.column("nome_empresa", sa.String()),
        sa.column("numero_contrato", sa.String()),
        sa.column("produto", sa.String()),
        sa.column("ativo", sa.Boolean()),
    )
    pedidos_empresa = sa.table(
        "dp_pedido_ticket_empresas",
        sa.column("id", sa.Integer()),
        sa.column("cnpj", sa.String()),
        sa.column("nome_empresa", sa.String()),
        sa.column("numero_contrato", sa.String()),
        sa.column("produto", sa.String()),
        sa.column("ativo", sa.Boolean()),
        sa.column("contrato_id", sa.Integer()),
    )

    with op.batch_alter_table("dp_pedido_ticket_empresas") as batch_op:
        batch_op.add_column(sa.Column("contrato_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_dp_ticket_pedido_contrato",
            "dp_pedido_ticket_contratos",
            ["contrato_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(
            "ix_dp_pedido_ticket_empresas_contrato_id",
            ["contrato_id"],
        )

    bind = op.get_bind()
    linhas = bind.execute(
        sa.select(
            pedidos_empresa.c.id,
            pedidos_empresa.c.cnpj,
            pedidos_empresa.c.nome_empresa,
            pedidos_empresa.c.numero_contrato,
            pedidos_empresa.c.produto,
            pedidos_empresa.c.ativo,
        ).order_by(pedidos_empresa.c.id)
    )
    ids_por_identidade = {}
    for linha in linhas:
        identidade = (linha.cnpj, linha.numero_contrato, linha.produto)
        contrato_id = ids_por_identidade.get(identidade)
        if contrato_id is None:
            result = bind.execute(
                contratos.insert().values(
                    cnpj=linha.cnpj,
                    nome_empresa=linha.nome_empresa,
                    numero_contrato=linha.numero_contrato,
                    produto=linha.produto,
                    ativo=bool(linha.ativo),
                )
            )
            contrato_id = result.inserted_primary_key[0]
            ids_por_identidade[identidade] = contrato_id
        elif linha.ativo:
            bind.execute(
                contratos.update()
                .where(contratos.c.id == contrato_id)
                .values(ativo=True)
            )
        bind.execute(
            pedidos_empresa.update()
            .where(pedidos_empresa.c.id == linha.id)
            .values(contrato_id=contrato_id)
        )


def downgrade():
    with op.batch_alter_table("dp_pedido_ticket_empresas") as batch_op:
        batch_op.drop_index("ix_dp_pedido_ticket_empresas_contrato_id")
        batch_op.drop_constraint("fk_dp_ticket_pedido_contrato", type_="foreignkey")
        batch_op.drop_column("contrato_id")
    op.drop_index(
        "ix_dp_pedido_ticket_contratos_cnpj",
        table_name="dp_pedido_ticket_contratos",
    )
    op.drop_table("dp_pedido_ticket_contratos")
