"""baixas recebimentos contas receber

Revision ID: b2d7f1a9c3e4
Revises: a1c9e7b5d8f2
Create Date: 2026-08-29 16:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2d7f1a9c3e4"
down_revision = "a1c9e7b5d8f2"
branch_labels = None
depends_on = None


TABELA_BAIXAS = "financeiro_contas_receber_baixas"


def _tabela_existe(inspector, tabela):
    return tabela in inspector.get_table_names()


def _indices(inspector, tabela):
    if not _tabela_existe(inspector, tabela):
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _criar_indice_se_nao_existir(inspector, nome, tabela, colunas):
    if nome not in _indices(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _tabela_existe(inspector, TABELA_BAIXAS):
        op.create_table(
            TABELA_BAIXAS,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("titulo_id", sa.Integer(), nullable=False),
            sa.Column("data_recebimento", sa.Date(), nullable=False),
            sa.Column("valor_recebido", sa.Numeric(12, 2), nullable=False),
            sa.Column("forma_recebimento", sa.String(length=30), nullable=False),
            sa.Column("conta_recebimento_descricao", sa.String(length=180), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["titulo_id"], ["financeiro_contas_receber_titulos.id"], name="fk_fin_cr_baixas_titulo"),
            sa.ForeignKeyConstraint(["registrado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_baixas_registrado_por"),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_baixas_cancelado_por"),
            sa.CheckConstraint("valor_recebido > 0", name="ck_fin_cr_baixa_valor_recebido"),
            sa.CheckConstraint("status in ('Ativa', 'Cancelada', 'Estornada')", name="ck_fin_cr_baixa_status"),
            sa.CheckConstraint(
                "forma_recebimento in ('Pix', 'Transferência', 'Depósito', 'Boleto', 'Dinheiro', 'Cartão', 'Outro')",
                name="ck_fin_cr_baixa_forma_recebimento",
            ),
        )

    inspector = sa.inspect(bind)
    for nome, colunas in [
        ("ix_fin_cr_baixas_titulo_id", ["titulo_id"]),
        ("ix_fin_cr_baixas_data_recebimento", ["data_recebimento"]),
        ("ix_fin_cr_baixas_status", ["status"]),
        ("ix_fin_cr_baixas_registrado_por", ["registrado_por_usuario_id"]),
        ("ix_fin_cr_baixas_forma", ["forma_recebimento"]),
    ]:
        _criar_indice_se_nao_existir(inspector, nome, TABELA_BAIXAS, colunas)
        inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _tabela_existe(inspector, TABELA_BAIXAS):
        indices = _indices(inspector, TABELA_BAIXAS)
        for nome in [
            "ix_fin_cr_baixas_forma",
            "ix_fin_cr_baixas_registrado_por",
            "ix_fin_cr_baixas_status",
            "ix_fin_cr_baixas_data_recebimento",
            "ix_fin_cr_baixas_titulo_id",
        ]:
            if nome in indices:
                op.drop_index(nome, table_name=TABELA_BAIXAS)
        op.drop_table(TABELA_BAIXAS)
