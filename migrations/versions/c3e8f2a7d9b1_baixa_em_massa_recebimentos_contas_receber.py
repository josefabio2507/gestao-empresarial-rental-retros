"""baixa em massa recebimentos contas receber

Revision ID: c3e8f2a7d9b1
Revises: b2d7f1a9c3e4
Create Date: 2026-08-29 17:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3e8f2a7d9b1"
down_revision = "b2d7f1a9c3e4"
branch_labels = None
depends_on = None


TABELA_LOTES = "financeiro_contas_receber_lotes_baixa"
TABELA_BAIXAS = "financeiro_contas_receber_baixas"


def _tabelas(inspector):
    return inspector.get_table_names()


def _tabela_existe(inspector, tabela):
    return tabela in _tabelas(inspector)


def _colunas(inspector, tabela):
    if not _tabela_existe(inspector, tabela):
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def _indices(inspector, tabela):
    if not _tabela_existe(inspector, tabela):
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _fks(inspector, tabela):
    if not _tabela_existe(inspector, tabela):
        return []
    return [fk["name"] for fk in inspector.get_foreign_keys(tabela)]


def _criar_indice_se_nao_existir(inspector, nome, tabela, colunas):
    if nome not in _indices(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _tabela_existe(inspector, TABELA_LOTES):
        op.create_table(
            TABELA_LOTES,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("data_recebimento", sa.Date(), nullable=False),
            sa.Column("forma_recebimento", sa.String(length=30), nullable=False),
            sa.Column("conta_recebimento_descricao", sa.String(length=180), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("comprovante_nome_original", sa.String(length=255), nullable=True),
            sa.Column("comprovante_nome_armazenado", sa.String(length=255), nullable=True),
            sa.Column("comprovante_path", sa.String(length=500), nullable=True),
            sa.Column("comprovante_drive_file_id", sa.String(length=255), nullable=True),
            sa.Column("comprovante_drive_link", sa.String(length=500), nullable=True),
            sa.Column("comprovante_extensao", sa.String(length=10), nullable=True),
            sa.Column("comprovante_tamanho", sa.Integer(), nullable=True),
            sa.Column("total_titulos", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valor_total_recebido", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_lote_criado_por"),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_lote_cancelado_por"),
            sa.CheckConstraint("total_titulos >= 0", name="ck_fin_cr_lote_total_titulos"),
            sa.CheckConstraint("valor_total_recebido >= 0", name="ck_fin_cr_lote_valor_total"),
            sa.CheckConstraint("status in ('Ativo', 'Cancelado', 'Estornado')", name="ck_fin_cr_lote_status"),
            sa.CheckConstraint(
                "forma_recebimento in ('Pix', 'Transferência', 'Depósito', 'Boleto', 'Dinheiro', 'Cartão', 'Outro')",
                name="ck_fin_cr_lote_forma_recebimento",
            ),
        )

    inspector = sa.inspect(bind)
    if _tabela_existe(inspector, TABELA_BAIXAS) and "lote_baixa_id" not in _colunas(inspector, TABELA_BAIXAS):
        with op.batch_alter_table(TABELA_BAIXAS) as batch_op:
            batch_op.add_column(sa.Column("lote_baixa_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_fin_cr_baixas_lote",
                TABELA_LOTES,
                ["lote_baixa_id"],
                ["id"],
            )

    inspector = sa.inspect(bind)
    for nome, tabela, colunas in [
        ("ix_fin_cr_lote_data_recebimento", TABELA_LOTES, ["data_recebimento"]),
        ("ix_fin_cr_lote_status", TABELA_LOTES, ["status"]),
        ("ix_fin_cr_lote_criado_por", TABELA_LOTES, ["criado_por_usuario_id"]),
        ("ix_fin_cr_lote_forma", TABELA_LOTES, ["forma_recebimento"]),
        ("ix_fin_cr_baixas_lote_id", TABELA_BAIXAS, ["lote_baixa_id"]),
    ]:
        if _tabela_existe(inspector, tabela):
            _criar_indice_se_nao_existir(inspector, nome, tabela, colunas)
            inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _tabela_existe(inspector, TABELA_BAIXAS) and "lote_baixa_id" in _colunas(inspector, TABELA_BAIXAS):
        indices = _indices(inspector, TABELA_BAIXAS)
        if "ix_fin_cr_baixas_lote_id" in indices:
            op.drop_index("ix_fin_cr_baixas_lote_id", table_name=TABELA_BAIXAS)
        with op.batch_alter_table(TABELA_BAIXAS) as batch_op:
            if "fk_fin_cr_baixas_lote" in _fks(inspector, TABELA_BAIXAS):
                batch_op.drop_constraint("fk_fin_cr_baixas_lote", type_="foreignkey")
            batch_op.drop_column("lote_baixa_id")

    inspector = sa.inspect(bind)
    if _tabela_existe(inspector, TABELA_LOTES):
        indices = _indices(inspector, TABELA_LOTES)
        for nome in [
            "ix_fin_cr_lote_forma",
            "ix_fin_cr_lote_criado_por",
            "ix_fin_cr_lote_status",
            "ix_fin_cr_lote_data_recebimento",
        ]:
            if nome in indices:
                op.drop_index(nome, table_name=TABELA_LOTES)
        op.drop_table(TABELA_LOTES)