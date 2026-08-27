"""integracao oc contas pagar

Revision ID: c17d3e4f5a6b
Revises: b18c2d4e6f8a
Create Date: 2026-08-27 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c17d3e4f5a6b"
down_revision = "b18c2d4e6f8a"
branch_labels = None
depends_on = None


T_OC = "suprimentos_ordens_compra"
T_TITULOS = "financeiro_contas_pagar_titulos"


def _colunas(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def _indices(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _criar_indice(inspector, nome, tabela, colunas):
    if tabela in inspector.get_table_names() and nome not in _indices(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if T_OC in inspector.get_table_names():
        colunas = _colunas(inspector, T_OC)
        novas_colunas = [
            ("tipo_pagamento_financeiro", sa.Column("tipo_pagamento_financeiro", sa.String(length=30), nullable=True)),
            ("forma_pagamento_financeiro", sa.Column("forma_pagamento_financeiro", sa.String(length=30), nullable=True)),
            ("condicao_pagamento_financeiro", sa.Column("condicao_pagamento_financeiro", sa.String(length=60), nullable=True)),
            ("numero_parcelas_financeiro", sa.Column("numero_parcelas_financeiro", sa.Integer(), nullable=False, server_default="1")),
            ("data_primeiro_vencimento_financeiro", sa.Column("data_primeiro_vencimento_financeiro", sa.Date(), nullable=True)),
            ("cartao_credito_id", sa.Column("cartao_credito_id", sa.Integer(), nullable=True)),
            ("financeiro_integrado", sa.Column("financeiro_integrado", sa.Boolean(), nullable=False, server_default=sa.false())),
            ("financeiro_integrado_em", sa.Column("financeiro_integrado_em", sa.DateTime(), nullable=True)),
            ("financeiro_integrado_por_usuario_id", sa.Column("financeiro_integrado_por_usuario_id", sa.Integer(), nullable=True)),
        ]
        if bind.dialect.name == "sqlite":
            for nome, coluna in novas_colunas:
                if nome not in colunas:
                    op.add_column(T_OC, coluna)
        else:
            with op.batch_alter_table(T_OC) as batch_op:
                for nome, coluna in novas_colunas:
                    if nome not in colunas:
                        batch_op.add_column(coluna)

        bind.execute(
            sa.text(
                """
                UPDATE suprimentos_ordens_compra
                   SET numero_parcelas_financeiro = quantidade_parcelas
                 WHERE numero_parcelas_financeiro IS NULL
                    OR numero_parcelas_financeiro < 1
                """
            )
        )
        bind.execute(
            sa.text(
                """
                UPDATE suprimentos_ordens_compra
                   SET data_primeiro_vencimento_financeiro = previsao_vencimento
                 WHERE data_primeiro_vencimento_financeiro IS NULL
                   AND previsao_vencimento IS NOT NULL
                """
            )
        )

    inspector = sa.inspect(bind)
    for nome, tabela, colunas in [
        ("ix_suprimentos_ordens_compra_tipo_pagamento_financeiro", T_OC, ["tipo_pagamento_financeiro"]),
        ("ix_suprimentos_ordens_compra_forma_pagamento_financeiro", T_OC, ["forma_pagamento_financeiro"]),
        ("ix_suprimentos_ordens_compra_data_primeiro_vencimento_financeiro", T_OC, ["data_primeiro_vencimento_financeiro"]),
        ("ix_suprimentos_ordens_compra_cartao_credito_id", T_OC, ["cartao_credito_id"]),
        ("ix_suprimentos_ordens_compra_financeiro_integrado", T_OC, ["financeiro_integrado"]),
        ("ix_suprimentos_ordens_compra_financeiro_integrado_por_usuario_id", T_OC, ["financeiro_integrado_por_usuario_id"]),
        ("ix_financeiro_cp_ordem_compra_id", T_TITULOS, ["ordem_compra_id"]),
        ("ix_financeiro_cp_origem_lancamento", T_TITULOS, ["origem_lancamento"]),
        ("ix_financeiro_cp_status", T_TITULOS, ["status"]),
        ("ix_financeiro_cp_data_vencimento", T_TITULOS, ["data_vencimento"]),
    ]:
        _criar_indice(inspector, nome, tabela, colunas)
        inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for nome, tabela in [
        ("ix_financeiro_cp_data_vencimento", T_TITULOS),
        ("ix_financeiro_cp_status", T_TITULOS),
        ("ix_financeiro_cp_origem_lancamento", T_TITULOS),
        ("ix_financeiro_cp_ordem_compra_id", T_TITULOS),
        ("ix_suprimentos_ordens_compra_financeiro_integrado_por_usuario_id", T_OC),
        ("ix_suprimentos_ordens_compra_financeiro_integrado", T_OC),
        ("ix_suprimentos_ordens_compra_cartao_credito_id", T_OC),
        ("ix_suprimentos_ordens_compra_data_primeiro_vencimento_financeiro", T_OC),
        ("ix_suprimentos_ordens_compra_forma_pagamento_financeiro", T_OC),
        ("ix_suprimentos_ordens_compra_tipo_pagamento_financeiro", T_OC),
    ]:
        if tabela in inspector.get_table_names() and nome in _indices(inspector, tabela):
            op.drop_index(nome, table_name=tabela)
            inspector = sa.inspect(bind)

    if T_OC in inspector.get_table_names():
        colunas = _colunas(inspector, T_OC)
        with op.batch_alter_table(T_OC) as batch_op:
            for coluna in [
                "financeiro_integrado_por_usuario_id",
                "financeiro_integrado_em",
                "financeiro_integrado",
                "cartao_credito_id",
                "data_primeiro_vencimento_financeiro",
                "numero_parcelas_financeiro",
                "condicao_pagamento_financeiro",
                "forma_pagamento_financeiro",
                "tipo_pagamento_financeiro",
            ]:
                if coluna in colunas:
                    batch_op.drop_column(coluna)
