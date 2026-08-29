"""abastecimento custos extras

Revision ID: a7c9e2f4b6d1
Revises: f40a6b8c9d2e
Create Date: 2026-08-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a7c9e2f4b6d1"
down_revision = "f40a6b8c9d2e"
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


def _adicionar_coluna_abastecimento(bind, nome, coluna):
    if nome not in _colunas(bind, "operacao_abastecimentos"):
        op.add_column("operacao_abastecimentos", coluna)


def upgrade():
    bind = op.get_bind()
    tabelas = _tabelas(bind)

    if "operacao_abastecimentos" in tabelas:
        _adicionar_coluna_abastecimento(bind, "numero_nota_fiscal", sa.Column("numero_nota_fiscal", sa.String(length=80), nullable=True))
        _adicionar_coluna_abastecimento(bind, "chave_acesso_nfe", sa.Column("chave_acesso_nfe", sa.String(length=44), nullable=True))
        _adicionar_coluna_abastecimento(bind, "fiscal_documento_id", sa.Column("fiscal_documento_id", sa.Integer(), nullable=True))
        _adicionar_coluna_abastecimento(bind, "valor_total_nota_fiscal", sa.Column("valor_total_nota_fiscal", sa.Numeric(12, 2), nullable=True))
        _adicionar_coluna_abastecimento(bind, "observacoes_conferencia", sa.Column("observacoes_conferencia", sa.Text(), nullable=True))
        _criar_indice(bind, "ix_operacao_abastecimentos_chave_acesso_nfe", "operacao_abastecimentos", ["chave_acesso_nfe"])
        _criar_indice(bind, "ix_operacao_abastecimentos_fiscal_documento_id", "operacao_abastecimentos", ["fiscal_documento_id"])

    if "operacao_abastecimento_custos_extras" not in tabelas:
        op.create_table(
            "operacao_abastecimento_custos_extras",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("abastecimento_id", sa.Integer(), nullable=False),
            sa.Column("categoria", sa.String(length=80), nullable=False),
            sa.Column("descricao", sa.String(length=255), nullable=False),
            sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
            sa.Column("valor_unitario", sa.Numeric(12, 2), nullable=False),
            sa.Column("valor_total", sa.Numeric(12, 2), nullable=False),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("quantidade > 0", name="ck_operacao_abast_extra_quantidade"),
            sa.CheckConstraint("valor_unitario >= 0", name="ck_operacao_abast_extra_unitario"),
            sa.CheckConstraint("valor_total >= 0", name="ck_operacao_abast_extra_total"),
            sa.CheckConstraint("status in ('Ativo', 'Cancelado')", name="ck_operacao_abast_extra_status"),
            sa.ForeignKeyConstraint(["abastecimento_id"], ["operacao_abastecimentos.id"]),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "operacao_abastecimento_custos_extras" in _tabelas(bind):
        _criar_indice(bind, "ix_operacao_abast_extra_abastecimento", "operacao_abastecimento_custos_extras", ["abastecimento_id"])
        _criar_indice(bind, "ix_operacao_abast_extra_categoria", "operacao_abastecimento_custos_extras", ["categoria"])
        _criar_indice(bind, "ix_operacao_abast_extra_status", "operacao_abastecimento_custos_extras", ["status"])
        _criar_indice(bind, "ix_operacao_abast_extra_criado_em", "operacao_abastecimento_custos_extras", ["criado_em"])


def downgrade():
    bind = op.get_bind()

    if "operacao_abastecimento_custos_extras" in _tabelas(bind):
        for nome in [
            "ix_operacao_abast_extra_criado_em",
            "ix_operacao_abast_extra_status",
            "ix_operacao_abast_extra_categoria",
            "ix_operacao_abast_extra_abastecimento",
        ]:
            if nome in _indices(bind, "operacao_abastecimento_custos_extras"):
                op.drop_index(nome, table_name="operacao_abastecimento_custos_extras")
        op.drop_table("operacao_abastecimento_custos_extras")

    if "operacao_abastecimentos" in _tabelas(bind):
        for nome in [
            "ix_operacao_abastecimentos_fiscal_documento_id",
            "ix_operacao_abastecimentos_chave_acesso_nfe",
        ]:
            if nome in _indices(bind, "operacao_abastecimentos"):
                op.drop_index(nome, table_name="operacao_abastecimentos")
        for coluna in [
            "observacoes_conferencia",
            "valor_total_nota_fiscal",
            "fiscal_documento_id",
            "chave_acesso_nfe",
            "numero_nota_fiscal",
        ]:
            if coluna in _colunas(bind, "operacao_abastecimentos"):
                op.drop_column("operacao_abastecimentos", coluna)