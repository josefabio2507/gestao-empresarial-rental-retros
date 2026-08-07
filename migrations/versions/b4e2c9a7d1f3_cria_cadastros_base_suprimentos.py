"""cria cadastros base suprimentos

Revision ID: b4e2c9a7d1f3
Revises: a9b4c6d8e2f1
Create Date: 2026-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b4e2c9a7d1f3"
down_revision = "a9b4c6d8e2f1"
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

    if "suprimentos_fornecedores" not in tabelas:
        op.create_table(
            "suprimentos_fornecedores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("razao_social", sa.String(length=180), nullable=False),
            sa.Column("nome_fantasia", sa.String(length=180), nullable=True),
            sa.Column("tipo_pessoa", sa.String(length=20), nullable=False),
            sa.Column("cnpj_cpf", sa.String(length=14), nullable=True),
            sa.Column("inscricao_estadual", sa.String(length=40), nullable=True),
            sa.Column("telefone", sa.String(length=30), nullable=True),
            sa.Column("email", sa.String(length=150), nullable=True),
            sa.Column("pessoa_contato", sa.String(length=120), nullable=True),
            sa.Column("endereco", sa.String(length=255), nullable=True),
            sa.Column("cidade", sa.String(length=120), nullable=True),
            sa.Column("uf", sa.String(length=2), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "tipo_pessoa in ('juridica', 'fisica')",
                name="ck_suprimentos_fornecedores_tipo_pessoa",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("cnpj_cpf", name="uq_suprimentos_fornecedores_cnpj_cpf"),
        )

    if "suprimentos_categorias_itens" not in tabelas:
        op.create_table(
            "suprimentos_categorias_itens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=120), nullable=False),
            sa.Column("slug", sa.String(length=120), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug", name="uq_suprimentos_categorias_itens_slug"),
        )

    if "suprimentos_unidades_medida" not in tabelas:
        op.create_table(
            "suprimentos_unidades_medida",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=120), nullable=False),
            sa.Column("sigla", sa.String(length=20), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("sigla", name="uq_suprimentos_unidades_medida_sigla"),
        )

    if "centros_custo" not in tabelas:
        op.create_table(
            "centros_custo",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("codigo", sa.String(length=40), nullable=True),
            sa.Column("nome", sa.String(length=120), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("codigo", name="uq_centros_custo_codigo"),
        )

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_itens" not in tabelas:
        op.create_table(
            "suprimentos_itens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("codigo_interno", sa.String(length=60), nullable=True),
            sa.Column("descricao", sa.String(length=220), nullable=False),
            sa.Column("categoria_id", sa.Integer(), nullable=False),
            sa.Column("unidade_medida_id", sa.Integer(), nullable=False),
            sa.Column("centro_custo_padrao_id", sa.Integer(), nullable=True),
            sa.Column("tipo", sa.String(length=30), nullable=False),
            sa.Column("item_estocavel", sa.Boolean(), nullable=False),
            sa.Column("ncm", sa.String(length=20), nullable=True),
            sa.Column("estoque_minimo", sa.Numeric(12, 3), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "tipo in ('material', 'servico', 'epi', 'ferramenta', 'peca', 'equipamento', 'consumo')",
                name="ck_suprimentos_itens_tipo",
            ),
            sa.CheckConstraint(
                "estoque_minimo is null or estoque_minimo >= 0",
                name="ck_suprimentos_itens_estoque_minimo",
            ),
            sa.ForeignKeyConstraint(
                ["categoria_id"],
                ["suprimentos_categorias_itens.id"],
                name="fk_suprimentos_itens_categoria_id",
            ),
            sa.ForeignKeyConstraint(
                ["unidade_medida_id"],
                ["suprimentos_unidades_medida.id"],
                name="fk_suprimentos_itens_unidade_medida_id",
            ),
            sa.ForeignKeyConstraint(
                ["centro_custo_padrao_id"],
                ["centros_custo.id"],
                name="fk_suprimentos_itens_centro_custo_padrao_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("codigo_interno", name="uq_suprimentos_itens_codigo_interno"),
        )

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_fornecedor_itens" not in tabelas:
        op.create_table(
            "suprimentos_fornecedor_itens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("fornecedor_id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("codigo_item_fornecedor", sa.String(length=80), nullable=True),
            sa.Column("descricao_item_fornecedor", sa.String(length=220), nullable=True),
            sa.Column("preco_referencia", sa.Numeric(12, 2), nullable=True),
            sa.Column("prazo_entrega_dias", sa.Integer(), nullable=True),
            sa.Column("condicao_pagamento", sa.String(length=160), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("fornecedor_preferencial", sa.Boolean(), nullable=False),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "preco_referencia is null or preco_referencia >= 0",
                name="ck_suprimentos_fornecedor_itens_preco",
            ),
            sa.CheckConstraint(
                "prazo_entrega_dias is null or prazo_entrega_dias >= 0",
                name="ck_suprimentos_fornecedor_itens_prazo",
            ),
            sa.ForeignKeyConstraint(
                ["fornecedor_id"],
                ["suprimentos_fornecedores.id"],
                name="fk_suprimentos_fornecedor_itens_fornecedor_id",
            ),
            sa.ForeignKeyConstraint(
                ["item_id"],
                ["suprimentos_itens.id"],
                name="fk_suprimentos_fornecedor_itens_item_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "fornecedor_id",
                "item_id",
                name="uq_suprimentos_fornecedor_item",
            ),
        )

    inspector = sa.inspect(bind)

    for tabela, indices in {
        "suprimentos_fornecedores": [
            ("ix_suprimentos_fornecedores_cnpj_cpf", ["cnpj_cpf"]),
            ("ix_suprimentos_fornecedores_ativo", ["ativo"]),
        ],
        "suprimentos_categorias_itens": [
            ("ix_suprimentos_categorias_itens_slug", ["slug"]),
            ("ix_suprimentos_categorias_itens_ativo", ["ativo"]),
        ],
        "suprimentos_unidades_medida": [
            ("ix_suprimentos_unidades_medida_sigla", ["sigla"]),
            ("ix_suprimentos_unidades_medida_ativo", ["ativo"]),
        ],
        "centros_custo": [
            ("ix_centros_custo_codigo", ["codigo"]),
            ("ix_centros_custo_ativo", ["ativo"]),
        ],
        "suprimentos_itens": [
            ("ix_suprimentos_itens_codigo_interno", ["codigo_interno"]),
            ("ix_suprimentos_itens_categoria_id", ["categoria_id"]),
            ("ix_suprimentos_itens_unidade_medida_id", ["unidade_medida_id"]),
            ("ix_suprimentos_itens_centro_custo_padrao_id", ["centro_custo_padrao_id"]),
            ("ix_suprimentos_itens_ativo", ["ativo"]),
        ],
        "suprimentos_fornecedor_itens": [
            ("ix_suprimentos_fornecedor_itens_fornecedor_id", ["fornecedor_id"]),
            ("ix_suprimentos_fornecedor_itens_item_id", ["item_id"]),
            ("ix_suprimentos_fornecedor_itens_ativo", ["ativo"]),
        ],
    }.items():
        criar_indice_se_nao_existir(inspector, tabela, indices[0][0], indices[0][1])
        for nome_indice, colunas in indices[1:]:
            inspector = sa.inspect(bind)
            criar_indice_se_nao_existir(inspector, tabela, nome_indice, colunas)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    for tabela in [
        "suprimentos_fornecedor_itens",
        "suprimentos_itens",
        "centros_custo",
        "suprimentos_unidades_medida",
        "suprimentos_categorias_itens",
        "suprimentos_fornecedores",
    ]:
        if tabela in tabelas:
            op.drop_table(tabela)
