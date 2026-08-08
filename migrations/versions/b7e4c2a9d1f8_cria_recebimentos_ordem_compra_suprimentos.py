"""cria recebimentos ordem compra suprimentos

Revision ID: b7e4c2a9d1f8
Revises: f2a7c9d4e8b6
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b7e4c2a9d1f8"
down_revision = "f2a7c9d4e8b6"
branch_labels = None
depends_on = None


STATUS_ORDEM_CHECK = "status in ('Gerada', 'Parcialmente Recebida', 'Recebida', 'Cancelada')"
STATUS_ORDEM_CHECK_ANTERIOR = "status in ('Gerada', 'Cancelada')"


def indice_existe(inspector, tabela, indice):
    return indice in {item["name"] for item in inspector.get_indexes(tabela)}


def modo_recriacao(bind):
    return "always" if bind.dialect.name == "sqlite" else "auto"


def atualizar_check_status_ordem(bind, novo_check):
    inspector = sa.inspect(bind)

    if "suprimentos_ordens_compra" not in inspector.get_table_names():
        return

    with op.batch_alter_table("suprimentos_ordens_compra", recreate=modo_recriacao(bind)) as batch_op:
        batch_op.drop_constraint("ck_suprimentos_ordens_compra_status", type_="check")
        batch_op.create_check_constraint("ck_suprimentos_ordens_compra_status", novo_check)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    atualizar_check_status_ordem(bind, STATUS_ORDEM_CHECK)

    if "suprimentos_recebimentos_compra" not in tabelas:
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
            sa.ForeignKeyConstraint(["ordem_compra_id"], ["suprimentos_ordens_compra.id"], name="fk_suprimentos_recebimentos_oc_id"),
            sa.ForeignKeyConstraint(["recebido_por_usuario_id"], ["usuarios.id"], name="fk_suprimentos_recebimentos_usuario_id"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("numero", name="uq_suprimentos_recebimentos_compra_numero"),
        )

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_recebimento_compra_itens" not in tabelas:
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
            sa.ForeignKeyConstraint(["recebimento_id"], ["suprimentos_recebimentos_compra.id"], name="fk_suprimentos_recebimento_itens_recebimento_id"),
            sa.ForeignKeyConstraint(["ordem_compra_item_id"], ["suprimentos_ordem_compra_itens.id"], name="fk_suprimentos_recebimento_itens_oc_item_id"),
            sa.ForeignKeyConstraint(["item_id"], ["suprimentos_itens.id"], name="fk_suprimentos_recebimento_itens_item_id"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    for tabela, indices in {
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
    }.items():
        if tabela not in inspector.get_table_names():
            continue

        nomes = {indice["name"] for indice in inspector.get_indexes(tabela)}
        for nome, colunas in indices:
            if nome not in nomes:
                op.create_index(nome, tabela, colunas)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    for tabela in ["suprimentos_recebimento_compra_itens", "suprimentos_recebimentos_compra"]:
        if tabela in tabelas:
            op.drop_table(tabela)

    atualizar_check_status_ordem(bind, STATUS_ORDEM_CHECK_ANTERIOR)
