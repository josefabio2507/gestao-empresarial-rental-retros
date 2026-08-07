"""cria cotacoes suprimentos

Revision ID: d9f3b7a6c2e1
Revises: c7a4e91d2b6f
Create Date: 2026-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d9f3b7a6c2e1"
down_revision = "c7a4e91d2b6f"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_cotacoes" not in tabelas:
        op.create_table(
            "suprimentos_cotacoes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("numero", sa.String(length=30), nullable=False),
            sa.Column("requisicao_id", sa.Integer(), nullable=False),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("aberta_em", sa.DateTime(), nullable=False),
            sa.Column("encerrada_em", sa.DateTime(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "status in ('Aberta', 'Encerrada', 'Cancelada')",
                name="ck_suprimentos_cotacoes_status",
            ),
            sa.ForeignKeyConstraint(
                ["requisicao_id"],
                ["suprimentos_requisicoes_compra.id"],
                name="fk_suprimentos_cotacoes_requisicao_id",
            ),
            sa.ForeignKeyConstraint(
                ["criado_por_usuario_id"],
                ["usuarios.id"],
                name="fk_suprimentos_cotacoes_criado_por_usuario_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("numero", name="uq_suprimentos_cotacoes_numero"),
        )

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_cotacao_propostas" not in tabelas:
        op.create_table(
            "suprimentos_cotacao_propostas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cotacao_id", sa.Integer(), nullable=False),
            sa.Column("fornecedor_id", sa.Integer(), nullable=False),
            sa.Column("requisicao_item_id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("fornecedor_razao_social_snapshot", sa.String(length=180), nullable=False),
            sa.Column("item_descricao_snapshot", sa.String(length=220), nullable=False),
            sa.Column("unidade_medida_snapshot", sa.String(length=20), nullable=False),
            sa.Column("quantidade_snapshot", sa.Numeric(12, 3), nullable=False),
            sa.Column("preco_unitario", sa.Numeric(12, 2), nullable=False),
            sa.Column("prazo_entrega_dias", sa.Integer(), nullable=True),
            sa.Column("condicao_pagamento", sa.String(length=160), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "preco_unitario >= 0",
                name="ck_suprimentos_cotacao_propostas_preco_unitario",
            ),
            sa.CheckConstraint(
                "prazo_entrega_dias is null or prazo_entrega_dias >= 0",
                name="ck_suprimentos_cotacao_propostas_prazo",
            ),
            sa.ForeignKeyConstraint(
                ["cotacao_id"],
                ["suprimentos_cotacoes.id"],
                name="fk_suprimentos_cotacao_propostas_cotacao_id",
            ),
            sa.ForeignKeyConstraint(
                ["fornecedor_id"],
                ["suprimentos_fornecedores.id"],
                name="fk_suprimentos_cotacao_propostas_fornecedor_id",
            ),
            sa.ForeignKeyConstraint(
                ["requisicao_item_id"],
                ["suprimentos_requisicao_compra_itens.id"],
                name="fk_suprimentos_cotacao_propostas_requisicao_item_id",
            ),
            sa.ForeignKeyConstraint(
                ["item_id"],
                ["suprimentos_itens.id"],
                name="fk_suprimentos_cotacao_propostas_item_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "cotacao_id",
                "fornecedor_id",
                "requisicao_item_id",
                name="uq_suprimentos_cotacao_fornecedor_item",
            ),
        )

    inspector = sa.inspect(bind)
    for tabela, indices in {
        "suprimentos_cotacoes": [
            ("ix_suprimentos_cotacoes_numero", ["numero"]),
            ("ix_suprimentos_cotacoes_requisicao_id", ["requisicao_id"]),
            ("ix_suprimentos_cotacoes_criado_por_usuario_id", ["criado_por_usuario_id"]),
            ("ix_suprimentos_cotacoes_status", ["status"]),
        ],
        "suprimentos_cotacao_propostas": [
            ("ix_suprimentos_cotacao_propostas_cotacao_id", ["cotacao_id"]),
            ("ix_suprimentos_cotacao_propostas_fornecedor_id", ["fornecedor_id"]),
            ("ix_suprimentos_cotacao_propostas_requisicao_item_id", ["requisicao_item_id"]),
            ("ix_suprimentos_cotacao_propostas_item_id", ["item_id"]),
            ("ix_suprimentos_cotacao_propostas_ativo", ["ativo"]),
        ],
    }.items():
        nomes = {indice["name"] for indice in inspector.get_indexes(tabela)}
        for nome, colunas in indices:
            if nome not in nomes:
                op.create_index(nome, tabela, colunas)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    for tabela in ["suprimentos_cotacao_propostas", "suprimentos_cotacoes"]:
        if tabela in tabelas:
            op.drop_table(tabela)
