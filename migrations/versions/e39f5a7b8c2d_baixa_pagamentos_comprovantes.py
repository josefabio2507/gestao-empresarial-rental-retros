"""baixa pagamentos comprovantes

Revision ID: e39f5a7b8c2d
Revises: d28e4f6a7b9c
Create Date: 2026-08-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e39f5a7b8c2d"
down_revision = "d28e4f6a7b9c"
branch_labels = None
depends_on = None


def _tabelas(bind):
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _indices(bind, tabela):
    inspector = sa.inspect(bind)
    try:
        return {idx["name"] for idx in inspector.get_indexes(tabela)}
    except Exception:
        return set()


def _criar_indice(bind, nome, tabela, colunas):
    if nome not in _indices(bind, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    tabelas = _tabelas(bind)

    if "financeiro_contas_pagar_baixas" not in tabelas:
        op.create_table(
            "financeiro_contas_pagar_baixas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("titulo_id", sa.Integer(), nullable=False),
            sa.Column("data_pagamento", sa.Date(), nullable=False),
            sa.Column("valor_pago", sa.Numeric(12, 2), nullable=False),
            sa.Column("forma_pagamento", sa.String(length=30), nullable=False),
            sa.Column("conta_pagamento_descricao", sa.String(length=180), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativa"),
            sa.Column("comprovante_nome_original", sa.String(length=255), nullable=True),
            sa.Column("comprovante_nome_armazenado", sa.String(length=255), nullable=True),
            sa.Column("comprovante_path", sa.String(length=500), nullable=True),
            sa.Column("comprovante_drive_file_id", sa.String(length=255), nullable=True),
            sa.Column("comprovante_drive_link", sa.String(length=500), nullable=True),
            sa.Column("comprovante_extensao", sa.String(length=10), nullable=True),
            sa.Column("comprovante_tamanho", sa.Integer(), nullable=True),
            sa.Column("registrado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("valor_pago > 0", name="ck_fin_cp_baixa_valor_pago"),
            sa.CheckConstraint("status in ('Ativa', 'Cancelada', 'Estornada')", name="ck_fin_cp_baixa_status"),
            sa.CheckConstraint(
                "forma_pagamento in ('Boleto', 'Pix', 'Transferencia', 'Deposito', 'Cartao de Credito', 'Outro')",
                name="ck_fin_cp_baixa_forma_pagamento",
            ),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["registrado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["titulo_id"], ["financeiro_contas_pagar_titulos.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    _criar_indice(bind, "ix_fin_cp_baixa_titulo", "financeiro_contas_pagar_baixas", ["titulo_id"])
    _criar_indice(bind, "ix_fin_cp_baixa_data", "financeiro_contas_pagar_baixas", ["data_pagamento"])
    _criar_indice(bind, "ix_fin_cp_baixa_status", "financeiro_contas_pagar_baixas", ["status"])
    _criar_indice(bind, "ix_fin_cp_baixa_forma", "financeiro_contas_pagar_baixas", ["forma_pagamento"])
    _criar_indice(bind, "ix_fin_cp_baixa_reg_user", "financeiro_contas_pagar_baixas", ["registrado_por_usuario_id"])
    _criar_indice(bind, "ix_fin_cp_baixa_can_user", "financeiro_contas_pagar_baixas", ["cancelado_por_usuario_id"])


def downgrade():
    bind = op.get_bind()
    if "financeiro_contas_pagar_baixas" not in _tabelas(bind):
        return

    for nome in [
        "ix_fin_cp_baixa_can_user",
        "ix_fin_cp_baixa_reg_user",
        "ix_fin_cp_baixa_forma",
        "ix_fin_cp_baixa_status",
        "ix_fin_cp_baixa_data",
        "ix_fin_cp_baixa_titulo",
    ]:
        if nome in _indices(bind, "financeiro_contas_pagar_baixas"):
            op.drop_index(nome, table_name="financeiro_contas_pagar_baixas")

    op.drop_table("financeiro_contas_pagar_baixas")
