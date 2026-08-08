"""cria ordens compra suprimentos

Revision ID: f2a7c9d4e8b6
Revises: a6c8d2e5f9b1
Create Date: 2026-08-08 00:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "f2a7c9d4e8b6"
down_revision = "a6c8d2e5f9b1"
branch_labels = None
depends_on = None


def indice_existe(inspector, tabela, indice):
    return indice in {item["name"] for item in inspector.get_indexes(tabela)}


def criar_ou_atualizar_modulo_ordens_compra(bind):
    departamentos = sa.table(
        "departamentos",
        sa.column("id", sa.Integer()),
        sa.column("slug", sa.String()),
    )
    modulos = sa.table(
        "modulos",
        sa.column("id", sa.Integer()),
        sa.column("departamento_id", sa.Integer()),
        sa.column("nome", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("descricao", sa.Text()),
        sa.column("ativo", sa.Boolean()),
        sa.column("ordem", sa.Integer()),
        sa.column("criado_em", sa.DateTime()),
        sa.column("atualizado_em", sa.DateTime()),
    )

    departamento = bind.execute(
        sa.select(departamentos.c.id).where(departamentos.c.slug == "suprimentos")
    ).first()

    if not departamento:
        return

    agora = datetime.utcnow()
    existente = bind.execute(
        sa.select(modulos.c.id).where(
            modulos.c.departamento_id == departamento.id,
            modulos.c.slug == "ordens_compra",
        )
    ).first()

    dados = {
        "nome": "Ordens de Compra",
        "descricao": "Geracao e consulta de ordens de compra aprovadas",
        "ativo": True,
        "ordem": 9,
        "atualizado_em": agora,
    }

    if existente:
        bind.execute(
            modulos.update()
            .where(modulos.c.id == existente.id)
            .values(**dados)
        )
        return

    bind.execute(
        modulos.insert().values(
            departamento_id=departamento.id,
            slug="ordens_compra",
            criado_em=agora,
            **dados,
        )
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_ordens_compra" not in tabelas:
        op.create_table(
            "suprimentos_ordens_compra",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("numero", sa.String(length=30), nullable=False),
            sa.Column("cotacao_id", sa.Integer(), nullable=False),
            sa.Column("requisicao_id", sa.Integer(), nullable=False),
            sa.Column("fornecedor_id", sa.Integer(), nullable=False),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
            sa.Column("fornecedor_razao_social_snapshot", sa.String(length=180), nullable=False),
            sa.Column("fornecedor_cnpj_cpf_snapshot", sa.String(length=20), nullable=True),
            sa.Column("condicao_pagamento_snapshot", sa.String(length=160), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("gerada_em", sa.DateTime(), nullable=False),
            sa.Column("cancelada_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "status in ('Gerada', 'Cancelada')",
                name="ck_suprimentos_ordens_compra_status",
            ),
            sa.ForeignKeyConstraint(["cotacao_id"], ["suprimentos_cotacoes.id"], name="fk_suprimentos_oc_cotacao_id"),
            sa.ForeignKeyConstraint(["requisicao_id"], ["suprimentos_requisicoes_compra.id"], name="fk_suprimentos_oc_requisicao_id"),
            sa.ForeignKeyConstraint(["fornecedor_id"], ["suprimentos_fornecedores.id"], name="fk_suprimentos_oc_fornecedor_id"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_suprimentos_oc_criado_por_usuario_id"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("numero", name="uq_suprimentos_ordens_compra_numero"),
            sa.UniqueConstraint("cotacao_id", "fornecedor_id", name="uq_suprimentos_ordens_compra_cotacao_fornecedor"),
        )

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_ordem_compra_itens" not in tabelas:
        op.create_table(
            "suprimentos_ordem_compra_itens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ordem_compra_id", sa.Integer(), nullable=False),
            sa.Column("cotacao_proposta_id", sa.Integer(), nullable=False),
            sa.Column("requisicao_item_id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("item_codigo_snapshot", sa.String(length=60), nullable=True),
            sa.Column("item_descricao_snapshot", sa.String(length=220), nullable=False),
            sa.Column("unidade_medida_snapshot", sa.String(length=20), nullable=False),
            sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
            sa.Column("preco_unitario", sa.Numeric(12, 2), nullable=False),
            sa.Column("prazo_entrega_dias", sa.Integer(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.CheckConstraint("quantidade > 0", name="ck_suprimentos_oc_itens_quantidade"),
            sa.CheckConstraint("preco_unitario >= 0", name="ck_suprimentos_oc_itens_preco_unitario"),
            sa.CheckConstraint("prazo_entrega_dias is null or prazo_entrega_dias >= 0", name="ck_suprimentos_oc_itens_prazo"),
            sa.ForeignKeyConstraint(["ordem_compra_id"], ["suprimentos_ordens_compra.id"], name="fk_suprimentos_oc_itens_ordem_compra_id"),
            sa.ForeignKeyConstraint(["cotacao_proposta_id"], ["suprimentos_cotacao_propostas.id"], name="fk_suprimentos_oc_itens_cotacao_proposta_id"),
            sa.ForeignKeyConstraint(["requisicao_item_id"], ["suprimentos_requisicao_compra_itens.id"], name="fk_suprimentos_oc_itens_requisicao_item_id"),
            sa.ForeignKeyConstraint(["item_id"], ["suprimentos_itens.id"], name="fk_suprimentos_oc_itens_item_id"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ordem_compra_id", "cotacao_proposta_id", name="uq_suprimentos_oc_item_proposta"),
        )

    inspector = sa.inspect(bind)
    for tabela, indices in {
        "suprimentos_ordens_compra": [
            ("ix_suprimentos_ordens_compra_numero", ["numero"]),
            ("ix_suprimentos_ordens_compra_cotacao_id", ["cotacao_id"]),
            ("ix_suprimentos_ordens_compra_requisicao_id", ["requisicao_id"]),
            ("ix_suprimentos_ordens_compra_fornecedor_id", ["fornecedor_id"]),
            ("ix_suprimentos_ordens_compra_criado_por_usuario_id", ["criado_por_usuario_id"]),
            ("ix_suprimentos_ordens_compra_status", ["status"]),
        ],
        "suprimentos_ordem_compra_itens": [
            ("ix_suprimentos_ordem_compra_itens_ordem_compra_id", ["ordem_compra_id"]),
            ("ix_suprimentos_ordem_compra_itens_cotacao_proposta_id", ["cotacao_proposta_id"]),
            ("ix_suprimentos_ordem_compra_itens_requisicao_item_id", ["requisicao_item_id"]),
            ("ix_suprimentos_ordem_compra_itens_item_id", ["item_id"]),
        ],
    }.items():
        nomes = {indice["name"] for indice in inspector.get_indexes(tabela)}
        for nome, colunas in indices:
            if nome not in nomes:
                op.create_index(nome, tabela, colunas)

    criar_ou_atualizar_modulo_ordens_compra(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    for tabela in ["suprimentos_ordem_compra_itens", "suprimentos_ordens_compra"]:
        if tabela in tabelas:
            op.drop_table(tabela)
