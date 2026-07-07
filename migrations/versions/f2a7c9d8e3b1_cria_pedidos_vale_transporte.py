"""cria pedidos de vale transporte

Revision ID: f2a7c9d8e3b1
Revises: d4f8a2c7e1b9
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f2a7c9d8e3b1"
down_revision = "d4f8a2c7e1b9"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "vale_transporte_pedidos" not in tabelas:
        op.create_table(
            "vale_transporte_pedidos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("competencia", sa.String(length=7), nullable=False),
            sa.Column("data_inicial", sa.Date(), nullable=False),
            sa.Column("data_final", sa.Date(), nullable=False),
            sa.Column("quantidade_dias_padrao", sa.Integer(), nullable=False),
            sa.Column("equipe_id", sa.Integer(), nullable=True),
            sa.Column("forma_pagamento_filtro", sa.String(length=30), nullable=True),
            sa.Column("empresa_transporte_filtro", sa.String(length=150), nullable=True),
            sa.Column("prazo_pagamento", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Gerado"),
            sa.Column("criado_por_id", sa.Integer(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["equipe_id"], ["equipes.id"]),
            sa.CheckConstraint(
                "status in ('Rascunho', 'Gerado', 'Cancelado')",
                name="ck_vale_transporte_pedidos_status",
            ),
            sa.CheckConstraint(
                "prazo_pagamento in ('mensal', 'semanal')",
                name="ck_vale_transporte_pedidos_prazo_pagamento",
            ),
            sa.CheckConstraint(
                "quantidade_dias_padrao > 0",
                name="ck_vale_transporte_pedidos_quantidade_dias",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if "vale_transporte_pedido_itens" not in tabelas:
        op.create_table(
            "vale_transporte_pedido_itens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pedido_id", sa.Integer(), nullable=False),
            sa.Column("colaborador_id", sa.Integer(), nullable=False),
            sa.Column("linha_onibus_id", sa.Integer(), nullable=False),
            sa.Column("matricula_snapshot", sa.String(length=40), nullable=False),
            sa.Column("nome_colaborador_snapshot", sa.String(length=150), nullable=False),
            sa.Column("equipe_snapshot", sa.String(length=120), nullable=True),
            sa.Column("empresa_transporte_snapshot", sa.String(length=150), nullable=False),
            sa.Column("linha_transporte_snapshot", sa.String(length=220), nullable=False),
            sa.Column("forma_pagamento", sa.String(length=30), nullable=False),
            sa.Column("tarifa_diaria", sa.Numeric(10, 2), nullable=False),
            sa.Column("quantidade_dias", sa.Integer(), nullable=False),
            sa.Column("valor_base", sa.Numeric(10, 2), nullable=False),
            sa.Column("valor_acrescimo", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("valor_desconto", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["colaborador_id"], ["colaboradores.id"]),
            sa.ForeignKeyConstraint(["linha_onibus_id"], ["linhas_onibus.id"]),
            sa.ForeignKeyConstraint(["pedido_id"], ["vale_transporte_pedidos.id"]),
            sa.UniqueConstraint(
                "pedido_id",
                "colaborador_id",
                "linha_onibus_id",
                name="uq_vale_transporte_pedido_item_colaborador_linha",
            ),
            sa.CheckConstraint(
                "forma_pagamento in ('dinheiro', 'cartao_transporte')",
                name="ck_vale_transporte_pedido_itens_forma_pagamento",
            ),
            sa.CheckConstraint(
                "quantidade_dias > 0",
                name="ck_vale_transporte_pedido_itens_quantidade_dias",
            ),
            sa.CheckConstraint(
                "valor_acrescimo >= 0",
                name="ck_vale_transporte_pedido_itens_acrescimo",
            ),
            sa.CheckConstraint(
                "valor_desconto >= 0",
                name="ck_vale_transporte_pedido_itens_desconto",
            ),
            sa.CheckConstraint(
                "valor_total >= 0",
                name="ck_vale_transporte_pedido_itens_total",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    indices = {
        tabela: {indice["name"] for indice in inspector.get_indexes(tabela)}
        for tabela in inspector.get_table_names()
        if tabela in {"vale_transporte_pedidos", "vale_transporte_pedido_itens"}
    }

    indices_pedidos = indices.get("vale_transporte_pedidos", set())
    if "ix_vale_transporte_pedidos_competencia" not in indices_pedidos:
        op.create_index(
            "ix_vale_transporte_pedidos_competencia",
            "vale_transporte_pedidos",
            ["competencia"],
        )
    if "ix_vale_transporte_pedidos_equipe_id" not in indices_pedidos:
        op.create_index(
            "ix_vale_transporte_pedidos_equipe_id",
            "vale_transporte_pedidos",
            ["equipe_id"],
        )
    if "ix_vale_transporte_pedidos_status" not in indices_pedidos:
        op.create_index(
            "ix_vale_transporte_pedidos_status",
            "vale_transporte_pedidos",
            ["status"],
        )
    if "ix_vale_transporte_pedidos_criado_por_id" not in indices_pedidos:
        op.create_index(
            "ix_vale_transporte_pedidos_criado_por_id",
            "vale_transporte_pedidos",
            ["criado_por_id"],
        )

    indices_itens = indices.get("vale_transporte_pedido_itens", set())
    for nome_indice, coluna in (
        ("ix_vale_transporte_pedido_itens_pedido_id", "pedido_id"),
        ("ix_vale_transporte_pedido_itens_colaborador_id", "colaborador_id"),
        ("ix_vale_transporte_pedido_itens_linha_onibus_id", "linha_onibus_id"),
        ("ix_vale_transporte_pedido_itens_ativo", "ativo"),
    ):
        if nome_indice not in indices_itens:
            op.create_index(nome_indice, "vale_transporte_pedido_itens", [coluna])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "vale_transporte_pedido_itens" in tabelas:
        op.drop_table("vale_transporte_pedido_itens")

    if "vale_transporte_pedidos" in tabelas:
        op.drop_table("vale_transporte_pedidos")
