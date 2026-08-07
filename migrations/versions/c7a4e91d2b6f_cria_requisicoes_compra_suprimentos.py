"""cria requisicoes compra suprimentos

Revision ID: c7a4e91d2b6f
Revises: b4e2c9a7d1f3
Create Date: 2026-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c7a4e91d2b6f"
down_revision = "b4e2c9a7d1f3"
branch_labels = None
depends_on = None


def criar_indice_se_nao_existir(inspector, tabela, nome, colunas):
    indices = {indice["name"] for indice in inspector.get_indexes(tabela)}

    if nome not in indices:
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_requisicoes_compra" not in tabelas:
        op.create_table(
            "suprimentos_requisicoes_compra",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("numero", sa.String(length=30), nullable=False),
            sa.Column("solicitante_usuario_id", sa.Integer(), nullable=False),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("justificativa", sa.Text(), nullable=False),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("enviada_em", sa.DateTime(), nullable=True),
            sa.Column("cancelada_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "status in ('Rascunho', 'Enviada para Analise', 'Cancelada')",
                name="ck_suprimentos_requisicoes_compra_status",
            ),
            sa.ForeignKeyConstraint(
                ["solicitante_usuario_id"],
                ["usuarios.id"],
                name="fk_suprimentos_requisicoes_compra_solicitante_usuario_id",
            ),
            sa.ForeignKeyConstraint(
                ["centro_custo_id"],
                ["centros_custo.id"],
                name="fk_suprimentos_requisicoes_compra_centro_custo_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("numero", name="uq_suprimentos_requisicoes_compra_numero"),
        )

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_requisicao_compra_itens" not in tabelas:
        op.create_table(
            "suprimentos_requisicao_compra_itens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("requisicao_id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("item_codigo_snapshot", sa.String(length=60), nullable=True),
            sa.Column("item_descricao_snapshot", sa.String(length=220), nullable=False),
            sa.Column("unidade_medida_snapshot", sa.String(length=20), nullable=False),
            sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "quantidade > 0",
                name="ck_suprimentos_requisicao_compra_itens_quantidade",
            ),
            sa.ForeignKeyConstraint(
                ["requisicao_id"],
                ["suprimentos_requisicoes_compra.id"],
                name="fk_suprimentos_requisicao_compra_itens_requisicao_id",
            ),
            sa.ForeignKeyConstraint(
                ["item_id"],
                ["suprimentos_itens.id"],
                name="fk_suprimentos_requisicao_compra_itens_item_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "requisicao_id",
                "item_id",
                name="uq_suprimentos_requisicao_compra_item",
            ),
        )

    inspector = sa.inspect(bind)

    for tabela, indices in {
        "suprimentos_requisicoes_compra": [
            ("ix_suprimentos_requisicoes_compra_numero", ["numero"]),
            ("ix_suprimentos_requisicoes_compra_solicitante_usuario_id", ["solicitante_usuario_id"]),
            ("ix_suprimentos_requisicoes_compra_centro_custo_id", ["centro_custo_id"]),
            ("ix_suprimentos_requisicoes_compra_status", ["status"]),
        ],
        "suprimentos_requisicao_compra_itens": [
            ("ix_suprimentos_requisicao_compra_itens_requisicao_id", ["requisicao_id"]),
            ("ix_suprimentos_requisicao_compra_itens_item_id", ["item_id"]),
        ],
    }.items():
        for nome_indice, colunas in indices:
            inspector = sa.inspect(bind)
            criar_indice_se_nao_existir(inspector, tabela, nome_indice, colunas)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    for tabela in [
        "suprimentos_requisicao_compra_itens",
        "suprimentos_requisicoes_compra",
    ]:
        if tabela in tabelas:
            op.drop_table(tabela)
