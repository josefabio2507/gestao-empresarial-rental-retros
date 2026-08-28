"""baixa pagamentos em massa

Revision ID: f40a6b8c9d2e
Revises: e39f5a7b8c2d
Create Date: 2026-08-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f40a6b8c9d2e"
down_revision = "e39f5a7b8c2d"
branch_labels = None
depends_on = None


def _inspector(bind):
    return sa.inspect(bind)


def _tabelas(bind):
    return set(_inspector(bind).get_table_names())


def _colunas(bind, tabela):
    try:
        return {col["name"] for col in _inspector(bind).get_columns(tabela)}
    except Exception:
        return set()


def _indices(bind, tabela):
    try:
        return {idx["name"] for idx in _inspector(bind).get_indexes(tabela)}
    except Exception:
        return set()


def _criar_indice(bind, nome, tabela, colunas):
    if nome not in _indices(bind, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    tabelas = _tabelas(bind)

    if "financeiro_contas_pagar_lotes_baixa" not in tabelas:
        op.create_table(
            "financeiro_contas_pagar_lotes_baixa",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("data_pagamento", sa.Date(), nullable=False),
            sa.Column("forma_pagamento", sa.String(length=30), nullable=False),
            sa.Column("conta_pagamento_descricao", sa.String(length=180), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("comprovante_nome_original", sa.String(length=255), nullable=True),
            sa.Column("comprovante_nome_armazenado", sa.String(length=255), nullable=True),
            sa.Column("comprovante_path", sa.String(length=500), nullable=True),
            sa.Column("comprovante_drive_file_id", sa.String(length=255), nullable=True),
            sa.Column("comprovante_drive_link", sa.String(length=500), nullable=True),
            sa.Column("comprovante_extensao", sa.String(length=10), nullable=True),
            sa.Column("comprovante_tamanho", sa.Integer(), nullable=True),
            sa.Column("total_titulos", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valor_total_baixado", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("total_titulos >= 0", name="ck_fin_cp_lote_total_titulos"),
            sa.CheckConstraint("valor_total_baixado >= 0", name="ck_fin_cp_lote_valor_total"),
            sa.CheckConstraint("status in ('Ativo', 'Cancelado', 'Estornado')", name="ck_fin_cp_lote_status"),
            sa.CheckConstraint(
                "forma_pagamento in ('Boleto', 'Pix', 'Transferencia', 'Deposito', 'Cartao de Credito', 'Outro')",
                name="ck_fin_cp_lote_forma_pagamento",
            ),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    _criar_indice(bind, "ix_fin_cp_lote_data", "financeiro_contas_pagar_lotes_baixa", ["data_pagamento"])
    _criar_indice(bind, "ix_fin_cp_lote_forma", "financeiro_contas_pagar_lotes_baixa", ["forma_pagamento"])
    _criar_indice(bind, "ix_fin_cp_lote_status", "financeiro_contas_pagar_lotes_baixa", ["status"])
    _criar_indice(bind, "ix_fin_cp_lote_criado_user", "financeiro_contas_pagar_lotes_baixa", ["criado_por_usuario_id"])
    _criar_indice(bind, "ix_fin_cp_lote_cancel_user", "financeiro_contas_pagar_lotes_baixa", ["cancelado_por_usuario_id"])

    if "financeiro_contas_pagar_baixas" in _tabelas(bind):
        if "lote_baixa_id" not in _colunas(bind, "financeiro_contas_pagar_baixas"):
            with op.batch_alter_table("financeiro_contas_pagar_baixas") as batch_op:
                batch_op.add_column(sa.Column("lote_baixa_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    "fk_fin_cp_baixa_lote",
                    "financeiro_contas_pagar_lotes_baixa",
                    ["lote_baixa_id"],
                    ["id"],
                )
        _criar_indice(bind, "ix_fin_cp_baixa_lote", "financeiro_contas_pagar_baixas", ["lote_baixa_id"])


def downgrade():
    bind = op.get_bind()
    if "financeiro_contas_pagar_baixas" in _tabelas(bind) and "lote_baixa_id" in _colunas(bind, "financeiro_contas_pagar_baixas"):
        if "ix_fin_cp_baixa_lote" in _indices(bind, "financeiro_contas_pagar_baixas"):
            op.drop_index("ix_fin_cp_baixa_lote", table_name="financeiro_contas_pagar_baixas")
        with op.batch_alter_table("financeiro_contas_pagar_baixas") as batch_op:
            batch_op.drop_constraint("fk_fin_cp_baixa_lote", type_="foreignkey")
            batch_op.drop_column("lote_baixa_id")

    if "financeiro_contas_pagar_lotes_baixa" not in _tabelas(bind):
        return
    for nome in [
        "ix_fin_cp_lote_cancel_user",
        "ix_fin_cp_lote_criado_user",
        "ix_fin_cp_lote_status",
        "ix_fin_cp_lote_forma",
        "ix_fin_cp_lote_data",
    ]:
        if nome in _indices(bind, "financeiro_contas_pagar_lotes_baixa"):
            op.drop_index(nome, table_name="financeiro_contas_pagar_lotes_baixa")
    op.drop_table("financeiro_contas_pagar_lotes_baixa")
