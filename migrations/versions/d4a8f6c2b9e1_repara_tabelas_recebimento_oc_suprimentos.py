"""repara tabelas recebimento oc suprimentos

Revision ID: d4a8f6c2b9e1
Revises: c9f1e8a4b2d7
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d4a8f6c2b9e1"
down_revision = "c9f1e8a4b2d7"
branch_labels = None
depends_on = None


def indice_existe(inspector, tabela, indice):
    return indice in {item["name"] for item in inspector.get_indexes(tabela)}


def criar_tabela_recebimentos():
    op.create_table(
        "suprimentos_recebimentos_compra",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(length=30), nullable=False),
        sa.Column("ordem_compra_id", sa.Integer(), nullable=False),
        sa.Column("recebido_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("tipo_documento", sa.String(length=30), nullable=False),
        sa.Column("numero_documento", sa.String(length=80), nullable=False),
        sa.Column("data_documento", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("recebido_em", sa.DateTime(), nullable=False),
        sa.Column("cancelado_em", sa.DateTime(), nullable=True),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status in ('Registrado', 'Cancelado')",
            name="ck_suprimentos_recebimentos_compra_status",
        ),
        sa.CheckConstraint(
            "tipo_documento in ('Nota Fiscal', 'Cupom Fiscal', 'Romaneio', 'Outro')",
            name="ck_suprimentos_recebimentos_tipo_documento",
        ),
        sa.ForeignKeyConstraint(
            ["ordem_compra_id"],
            ["suprimentos_ordens_compra.id"],
            name="fk_suprimentos_recebimentos_oc_id",
        ),
        sa.ForeignKeyConstraint(
            ["recebido_por_usuario_id"],
            ["usuarios.id"],
            name="fk_suprimentos_recebimentos_usuario_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero", name="uq_suprimentos_recebimentos_compra_numero"),
    )


def criar_tabela_recebimento_itens():
    op.create_table(
        "suprimentos_recebimento_compra_itens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recebimento_id", sa.Integer(), nullable=False),
        sa.Column("ordem_compra_item_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("item_codigo_snapshot", sa.String(length=60), nullable=True),
        sa.Column("item_descricao_snapshot", sa.String(length=220), nullable=False),
        sa.Column("unidade_medida_snapshot", sa.String(length=20), nullable=False),
        sa.Column("quantidade_recebida", sa.Numeric(12, 3), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "quantidade_recebida > 0",
            name="ck_suprimentos_recebimento_itens_quantidade",
        ),
        sa.ForeignKeyConstraint(
            ["recebimento_id"],
            ["suprimentos_recebimentos_compra.id"],
            name="fk_suprimentos_recebimento_itens_recebimento_id",
        ),
        sa.ForeignKeyConstraint(
            ["ordem_compra_item_id"],
            ["suprimentos_ordem_compra_itens.id"],
            name="fk_suprimentos_recebimento_itens_oc_item_id",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["suprimentos_itens.id"],
            name="fk_suprimentos_recebimento_itens_item_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def criar_indices_faltantes(inspector):
    indices = {
        "suprimentos_recebimentos_compra": [
            ("ix_suprimentos_recebimentos_compra_numero", ["numero"]),
            ("ix_suprimentos_recebimentos_compra_ordem_compra_id", ["ordem_compra_id"]),
            ("ix_suprimentos_recebimentos_compra_recebido_por_usuario_id", ["recebido_por_usuario_id"]),
            ("ix_suprimentos_recebimentos_compra_status", ["status"]),
        ],
        "suprimentos_recebimento_compra_itens": [
            ("ix_suprimentos_recebimento_compra_itens_recebimento_id", ["recebimento_id"]),
            ("ix_suprimentos_recebimento_compra_itens_ordem_compra_item_id", ["ordem_compra_item_id"]),
            ("ix_suprimentos_recebimento_compra_itens_item_id", ["item_id"]),
        ],
    }

    for tabela, itens in indices.items():
        inspector = sa.inspect(op.get_bind())
        if tabela not in inspector.get_table_names():
            continue

        for nome, colunas in itens:
            if not indice_existe(inspector, tabela, nome):
                op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_recebimentos_compra" not in tabelas:
        criar_tabela_recebimentos()

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_recebimento_compra_itens" not in tabelas:
        criar_tabela_recebimento_itens()

    criar_indices_faltantes(sa.inspect(bind))


def downgrade():
    pass
