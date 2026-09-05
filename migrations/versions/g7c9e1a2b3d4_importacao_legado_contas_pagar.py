"""adiciona rastreio e origem para importacao de contas a pagar legado

Revision ID: g7c9e1a2b3d4
Revises: b8e1c2d3f4a5, f40a6b8c9d2e
"""
from alembic import op
import sqlalchemy as sa

revision = "g7c9e1a2b3d4"
down_revision = ("b8e1c2d3f4a5", "f40a6b8c9d2e")
branch_labels = None
depends_on = None

TABELA = "financeiro_contas_pagar_titulos"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    colunas = {c["name"] for c in inspector.get_columns(TABELA)}
    if "id_legado" not in colunas:
        op.add_column(TABELA, sa.Column("id_legado", sa.String(length=80), nullable=True))
        op.create_index("ix_financeiro_contas_pagar_titulos_id_legado", TABELA, ["id_legado"])
    indices = {i["name"] for i in inspector.get_indexes(TABELA)}
    if "uq_financeiro_cp_origem_id_legado" not in indices:
        op.create_index("uq_financeiro_cp_origem_id_legado", TABELA, ["origem_lancamento", "id_legado"], unique=True)
    # O constraint de origem existente não contempla Legado. O fluxo de importação
    # valida a unicidade do ID legado antes de gravar.
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(TABELA, recreate="always") as batch:
            batch.drop_constraint("ck_financeiro_cp_origem_lancamento", type_="check")
            batch.create_check_constraint("ck_financeiro_cp_origem_lancamento", "origem_lancamento in ('Manual', 'Ordem de Compra', 'XML Fiscal', 'Cartao de Credito', 'Legado')")
    else:
        op.drop_constraint("ck_financeiro_cp_origem_lancamento", TABELA, type_="check")
        op.create_check_constraint("ck_financeiro_cp_origem_lancamento", TABELA, "origem_lancamento in ('Manual', 'Ordem de Compra', 'XML Fiscal', 'Cartao de Credito', 'Legado')")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(TABELA, recreate="always") as batch:
            batch.drop_constraint("ck_financeiro_cp_origem_lancamento", type_="check")
            batch.create_check_constraint("ck_financeiro_cp_origem_lancamento", "origem_lancamento in ('Manual', 'Ordem de Compra', 'XML Fiscal', 'Cartao de Credito')")
    else:
        op.drop_constraint("ck_financeiro_cp_origem_lancamento", TABELA, type_="check")
        op.create_check_constraint("ck_financeiro_cp_origem_lancamento", TABELA, "origem_lancamento in ('Manual', 'Ordem de Compra', 'XML Fiscal', 'Cartao de Credito')")
    inspector = sa.inspect(bind)
    if "id_legado" in {c["name"] for c in inspector.get_columns(TABELA)}:
        op.drop_index("uq_financeiro_cp_origem_id_legado", table_name=TABELA)
        op.drop_index("ix_financeiro_contas_pagar_titulos_id_legado", table_name=TABELA)
        op.drop_column(TABELA, "id_legado")
