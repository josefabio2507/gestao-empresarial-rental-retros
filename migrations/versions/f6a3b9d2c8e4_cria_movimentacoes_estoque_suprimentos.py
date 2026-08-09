"""cria movimentacoes estoque suprimentos

Revision ID: f6a3b9d2c8e4
Revises: e8b2c4d6f1a9
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f6a3b9d2c8e4"
down_revision = "e8b2c4d6f1a9"
branch_labels = None
depends_on = None


def indice_existe(inspector, tabela, indice):
    return indice in {item["name"] for item in inspector.get_indexes(tabela)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_movimentacoes_estoque" not in tabelas:
        op.create_table(
            "suprimentos_movimentacoes_estoque",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("recebimento_item_id", sa.Integer(), nullable=True),
            sa.Column("ordem_compra_id", sa.Integer(), nullable=True),
            sa.Column("fornecedor_id", sa.Integer(), nullable=True),
            sa.Column("tipo", sa.String(length=20), nullable=False),
            sa.Column("origem", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("documento_tipo", sa.String(length=30), nullable=True),
            sa.Column("documento_numero", sa.String(length=80), nullable=True),
            sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
            sa.Column("valor_unitario", sa.Numeric(12, 2), nullable=True),
            sa.Column("valor_total_snapshot", sa.Numeric(12, 2), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("movimentado_em", sa.DateTime(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "tipo in ('Entrada')",
                name="ck_suprimentos_movimentacoes_estoque_tipo",
            ),
            sa.CheckConstraint(
                "status in ('Registrada', 'Cancelada')",
                name="ck_suprimentos_movimentacoes_estoque_status",
            ),
            sa.CheckConstraint(
                "quantidade > 0",
                name="ck_suprimentos_movimentacoes_estoque_quantidade",
            ),
            sa.ForeignKeyConstraint(
                ["item_id"],
                ["suprimentos_itens.id"],
                name="fk_suprimentos_movimentacoes_estoque_item_id",
            ),
            sa.ForeignKeyConstraint(
                ["recebimento_item_id"],
                ["suprimentos_recebimento_compra_itens.id"],
                name="fk_suprimentos_movimentacoes_estoque_recebimento_item_id",
            ),
            sa.ForeignKeyConstraint(
                ["ordem_compra_id"],
                ["suprimentos_ordens_compra.id"],
                name="fk_suprimentos_movimentacoes_estoque_ordem_compra_id",
            ),
            sa.ForeignKeyConstraint(
                ["fornecedor_id"],
                ["suprimentos_fornecedores.id"],
                name="fk_suprimentos_movimentacoes_estoque_fornecedor_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "recebimento_item_id",
                name="uq_suprimentos_movimentacoes_estoque_recebimento_item",
            ),
        )

    inspector = sa.inspect(bind)
    if "suprimentos_movimentacoes_estoque" not in inspector.get_table_names():
        return

    for nome, colunas in [
        ("ix_suprimentos_movimentacoes_estoque_item_id", ["item_id"]),
        ("ix_suprimentos_movimentacoes_estoque_recebimento_item_id", ["recebimento_item_id"]),
        ("ix_suprimentos_movimentacoes_estoque_ordem_compra_id", ["ordem_compra_id"]),
        ("ix_suprimentos_movimentacoes_estoque_fornecedor_id", ["fornecedor_id"]),
        ("ix_suprimentos_movimentacoes_estoque_status", ["status"]),
    ]:
        inspector = sa.inspect(bind)
        if not indice_existe(inspector, "suprimentos_movimentacoes_estoque", nome):
            op.create_index(nome, "suprimentos_movimentacoes_estoque", colunas)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_movimentacoes_estoque" in inspector.get_table_names():
        op.drop_table("suprimentos_movimentacoes_estoque")
