"""preparacao financeira ordens compra

Revision ID: d2f4a6c8e9b1
Revises: c1e3f5a7b9d2
Create Date: 2026-08-10 19:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d2f4a6c8e9b1"
down_revision = "c1e3f5a7b9d2"
branch_labels = None
depends_on = None


STATUS_FINANCEIRO_PENDENTE = "Pendente de Financeiro"
STATUS_FINANCEIRO_CANCELADO = "Cancelado"


def _colunas(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def _indices(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "suprimentos_ordens_compra" in tabelas:
        colunas = _colunas(inspector, "suprimentos_ordens_compra")
        with op.batch_alter_table("suprimentos_ordens_compra") as batch_op:
            if "status_financeiro" not in colunas:
                batch_op.add_column(
                    sa.Column(
                        "status_financeiro",
                        sa.String(length=30),
                        nullable=False,
                        server_default=STATUS_FINANCEIRO_PENDENTE,
                    )
                )
            if "previsao_vencimento" not in colunas:
                batch_op.add_column(sa.Column("previsao_vencimento", sa.Date(), nullable=True))
            if "quantidade_parcelas" not in colunas:
                batch_op.add_column(
                    sa.Column("quantidade_parcelas", sa.Integer(), nullable=False, server_default="1")
                )
            if "observacoes_financeiras" not in colunas:
                batch_op.add_column(sa.Column("observacoes_financeiras", sa.Text(), nullable=True))
            if "preparado_financeiro_em" not in colunas:
                batch_op.add_column(sa.Column("preparado_financeiro_em", sa.DateTime(), nullable=True))
            if "provisionado_financeiro_em" not in colunas:
                batch_op.add_column(sa.Column("provisionado_financeiro_em", sa.DateTime(), nullable=True))

        indices = _indices(sa.inspect(bind), "suprimentos_ordens_compra")
        if "ix_suprimentos_ordens_compra_status_financeiro" not in indices:
            op.create_index(
                "ix_suprimentos_ordens_compra_status_financeiro",
                "suprimentos_ordens_compra",
                ["status_financeiro"],
            )
        if "ix_suprimentos_ordens_compra_previsao_vencimento" not in indices:
            op.create_index(
                "ix_suprimentos_ordens_compra_previsao_vencimento",
                "suprimentos_ordens_compra",
                ["previsao_vencimento"],
            )

        bind.execute(
            sa.text(
                """
                UPDATE suprimentos_ordens_compra
                   SET status_financeiro = CASE
                       WHEN status = 'Cancelada' THEN :cancelado
                       ELSE :pendente
                   END
                 WHERE status_financeiro IS NULL
                    OR status_financeiro = ''
                """
            ),
            {"cancelado": STATUS_FINANCEIRO_CANCELADO, "pendente": STATUS_FINANCEIRO_PENDENTE},
        )
        bind.execute(
            sa.text(
                """
                UPDATE suprimentos_ordens_compra
                   SET quantidade_parcelas = 1
                 WHERE quantidade_parcelas IS NULL
                    OR quantidade_parcelas < 1
                """
            )
        )

    inspector = sa.inspect(bind)
    if "suprimentos_ordem_compra_parcelas" not in inspector.get_table_names():
        op.create_table(
            "suprimentos_ordem_compra_parcelas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ordem_compra_id", sa.Integer(), nullable=False),
            sa.Column("numero_parcela", sa.Integer(), nullable=False),
            sa.Column("valor_previsto", sa.Numeric(12, 2), nullable=False),
            sa.Column("data_vencimento", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Prevista"),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["ordem_compra_id"],
                ["suprimentos_ordens_compra.id"],
                name="fk_suprimentos_oc_parcelas_ordem_compra_id",
            ),
            sa.UniqueConstraint(
                "ordem_compra_id",
                "numero_parcela",
                name="uq_suprimentos_oc_parcelas_ordem_numero",
            ),
            sa.CheckConstraint("numero_parcela >= 1", name="ck_suprimentos_oc_parcelas_numero"),
            sa.CheckConstraint("valor_previsto >= 0", name="ck_suprimentos_oc_parcelas_valor"),
            sa.CheckConstraint("status in ('Prevista', 'Cancelada')", name="ck_suprimentos_oc_parcelas_status"),
        )
        op.create_index(
            "ix_suprimentos_ordem_compra_parcelas_ordem_compra_id",
            "suprimentos_ordem_compra_parcelas",
            ["ordem_compra_id"],
        )
        op.create_index(
            "ix_suprimentos_ordem_compra_parcelas_data_vencimento",
            "suprimentos_ordem_compra_parcelas",
            ["data_vencimento"],
        )
        op.create_index(
            "ix_suprimentos_ordem_compra_parcelas_status",
            "suprimentos_ordem_compra_parcelas",
            ["status"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_ordem_compra_parcelas" in inspector.get_table_names():
        indices = _indices(inspector, "suprimentos_ordem_compra_parcelas")
        if "ix_suprimentos_ordem_compra_parcelas_status" in indices:
            op.drop_index("ix_suprimentos_ordem_compra_parcelas_status", table_name="suprimentos_ordem_compra_parcelas")
        if "ix_suprimentos_ordem_compra_parcelas_data_vencimento" in indices:
            op.drop_index(
                "ix_suprimentos_ordem_compra_parcelas_data_vencimento",
                table_name="suprimentos_ordem_compra_parcelas",
            )
        if "ix_suprimentos_ordem_compra_parcelas_ordem_compra_id" in indices:
            op.drop_index(
                "ix_suprimentos_ordem_compra_parcelas_ordem_compra_id",
                table_name="suprimentos_ordem_compra_parcelas",
            )
        op.drop_table("suprimentos_ordem_compra_parcelas")

    inspector = sa.inspect(bind)
    if "suprimentos_ordens_compra" in inspector.get_table_names():
        indices = _indices(inspector, "suprimentos_ordens_compra")
        if "ix_suprimentos_ordens_compra_previsao_vencimento" in indices:
            op.drop_index("ix_suprimentos_ordens_compra_previsao_vencimento", table_name="suprimentos_ordens_compra")
        if "ix_suprimentos_ordens_compra_status_financeiro" in indices:
            op.drop_index("ix_suprimentos_ordens_compra_status_financeiro", table_name="suprimentos_ordens_compra")

        colunas = _colunas(sa.inspect(bind), "suprimentos_ordens_compra")
        with op.batch_alter_table("suprimentos_ordens_compra") as batch_op:
            for nome_coluna in (
                "provisionado_financeiro_em",
                "preparado_financeiro_em",
                "observacoes_financeiras",
                "quantidade_parcelas",
                "previsao_vencimento",
                "status_financeiro",
            ):
                if nome_coluna in colunas:
                    batch_op.drop_column(nome_coluna)
