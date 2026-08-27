"""cartoes faturas contas pagar

Revision ID: b17c2d3e4f5a
Revises: a17b1c2d3e4f
Create Date: 2026-08-26 23:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b17c2d3e4f5a"
down_revision = "a17b1c2d3e4f"
branch_labels = None
depends_on = None


T_CARTOES = "financeiro_cartoes_credito"
T_FATURAS = "financeiro_cartoes_faturas"
T_TITULOS = "financeiro_contas_pagar_titulos"


def _tabelas(inspector):
    return inspector.get_table_names()


def _colunas(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def _indices(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _fks(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [fk["name"] for fk in inspector.get_foreign_keys(tabela)]


def _criar_indice(inspector, nome, tabela, colunas, unique=False):
    if tabela in inspector.get_table_names() and nome not in _indices(inspector, tabela):
        op.create_index(nome, tabela, colunas, unique=unique)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = _tabelas(inspector)

    if T_CARTOES not in tabelas:
        op.create_table(
            T_CARTOES,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=120), nullable=False),
            sa.Column("banco", sa.String(length=120), nullable=False),
            sa.Column("bandeira", sa.String(length=60), nullable=True),
            sa.Column("ultimos_4_digitos", sa.String(length=4), nullable=True),
            sa.Column("titular_responsavel", sa.String(length=120), nullable=True),
            sa.Column("dia_fechamento", sa.Integer(), nullable=False),
            sa.Column("dia_vencimento", sa.Integer(), nullable=False),
            sa.Column("limite", sa.Numeric(12, 2), nullable=True),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["centro_custo_id"], ["centros_custo.id"], name="fk_fin_cartao_centro_custo_id"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cartao_criado_por_id"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cartao_atualizado_por_id"),
            sa.CheckConstraint("dia_fechamento between 1 and 31", name="ck_fin_cartao_dia_fechamento"),
            sa.CheckConstraint("dia_vencimento between 1 and 31", name="ck_fin_cartao_dia_vencimento"),
            sa.CheckConstraint("limite is null or limite >= 0", name="ck_fin_cartao_limite"),
            sa.CheckConstraint("ultimos_4_digitos is null or length(ultimos_4_digitos) = 4", name="ck_fin_cartao_ultimos_4"),
        )

    inspector = sa.inspect(bind)
    if T_FATURAS not in inspector.get_table_names():
        op.create_table(
            T_FATURAS,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cartao_credito_id", sa.Integer(), nullable=False),
            sa.Column("competencia", sa.Date(), nullable=False),
            sa.Column("data_fechamento", sa.Date(), nullable=False),
            sa.Column("data_vencimento", sa.Date(), nullable=False),
            sa.Column("valor_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_pago", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("data_pagamento", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Aberta"),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("cartao_credito_id", "competencia", name="uq_fin_cartao_fatura_competencia"),
            sa.ForeignKeyConstraint(["cartao_credito_id"], [f"{T_CARTOES}.id"], name="fk_fin_fatura_cartao_credito_id"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_fatura_criado_por_id"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_fin_fatura_atualizado_por_id"),
            sa.CheckConstraint("valor_total >= 0", name="ck_fin_fatura_valor_total"),
            sa.CheckConstraint("valor_pago >= 0", name="ck_fin_fatura_valor_pago"),
            sa.CheckConstraint("status in ('Aberta', 'Fechada', 'Agendada', 'Paga', 'Vencida', 'Cancelada')", name="ck_fin_fatura_status"),
        )

    inspector = sa.inspect(bind)
    if T_TITULOS in inspector.get_table_names():
        colunas = _colunas(inspector, T_TITULOS)
        novas_colunas = [
            ("fatura_cartao_id", sa.Column("fatura_cartao_id", sa.Integer(), nullable=True)),
            ("data_compra_cartao", sa.Column("data_compra_cartao", sa.Date(), nullable=True)),
            ("competencia_fatura_cartao", sa.Column("competencia_fatura_cartao", sa.Date(), nullable=True)),
        ]
        if bind.dialect.name == "sqlite":
            for nome_coluna, coluna in novas_colunas:
                if nome_coluna not in colunas:
                    op.add_column(T_TITULOS, coluna)
        else:
            with op.batch_alter_table(T_TITULOS) as batch_op:
                for nome_coluna, coluna in novas_colunas:
                    if nome_coluna not in colunas:
                        batch_op.add_column(coluna)

    inspector = sa.inspect(bind)
    if bind.dialect.name != "sqlite" and T_TITULOS in inspector.get_table_names():
        fks = _fks(inspector, T_TITULOS)
        with op.batch_alter_table(T_TITULOS) as batch_op:
            if "fk_financeiro_cp_cartao_credito_id" not in fks:
                batch_op.create_foreign_key(
                    "fk_financeiro_cp_cartao_credito_id",
                    T_CARTOES,
                    ["cartao_credito_id"],
                    ["id"],
                )
            if "fk_financeiro_cp_fatura_cartao_id" not in fks:
                batch_op.create_foreign_key(
                    "fk_financeiro_cp_fatura_cartao_id",
                    T_FATURAS,
                    ["fatura_cartao_id"],
                    ["id"],
                )


    inspector = sa.inspect(bind)
    for nome, tabela, colunas, unique in [
        ("ix_fin_cartao_nome", T_CARTOES, ["nome"], False),
        ("ix_fin_cartao_banco", T_CARTOES, ["banco"], False),
        ("ix_fin_cartao_bandeira", T_CARTOES, ["bandeira"], False),
        ("ix_fin_cartao_ativo", T_CARTOES, ["ativo"], False),
        ("ix_fin_fatura_cartao_credito_id", T_FATURAS, ["cartao_credito_id"], False),
        ("ix_fin_fatura_competencia", T_FATURAS, ["competencia"], False),
        ("ix_fin_fatura_status", T_FATURAS, ["status"], False),
        ("ix_fin_fatura_data_vencimento", T_FATURAS, ["data_vencimento"], False),
        ("ix_fin_fatura_data_fechamento", T_FATURAS, ["data_fechamento"], False),
        ("ix_financeiro_cp_fatura_cartao_id", T_TITULOS, ["fatura_cartao_id"], False),
        ("ix_financeiro_cp_data_compra_cartao", T_TITULOS, ["data_compra_cartao"], False),
        ("ix_financeiro_cp_competencia_fatura_cartao", T_TITULOS, ["competencia_fatura_cartao"], False),
    ]:
        _criar_indice(inspector, nome, tabela, colunas, unique=unique)
        inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if T_TITULOS in inspector.get_table_names():
        indices = _indices(inspector, T_TITULOS)
        for nome in [
            "ix_financeiro_cp_competencia_fatura_cartao",
            "ix_financeiro_cp_data_compra_cartao",
            "ix_financeiro_cp_fatura_cartao_id",
        ]:
            if nome in indices:
                op.drop_index(nome, table_name=T_TITULOS)
        with op.batch_alter_table(T_TITULOS) as batch_op:
            for coluna in ["competencia_fatura_cartao", "data_compra_cartao", "fatura_cartao_id"]:
                if coluna in _colunas(inspector, T_TITULOS):
                    batch_op.drop_column(coluna)

    inspector = sa.inspect(bind)
    for tabela in [T_FATURAS, T_CARTOES]:
        if tabela in inspector.get_table_names():
            for indice in _indices(inspector, tabela):
                if indice.startswith("ix_fin_"):
                    op.drop_index(indice, table_name=tabela)
            op.drop_table(tabela)
