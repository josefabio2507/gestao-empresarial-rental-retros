"""adiciona leitura abastecimento

Revision ID: o5e6f7a8b9c0
Revises: n4d5e6f7a8b9
Create Date: 2026-09-10 21:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "o5e6f7a8b9c0"
down_revision = "n4d5e6f7a8b9"
branch_labels = None
depends_on = None


TABELA = "operacao_abastecimentos"


def _colunas(bind):
    return {coluna["name"] for coluna in sa.inspect(bind).get_columns(TABELA)}


def upgrade():
    bind = op.get_bind()
    if TABELA not in sa.inspect(bind).get_table_names():
        return

    colunas = _colunas(bind)
    if "tipo_leitura" not in colunas:
        op.add_column(
            TABELA,
            sa.Column("tipo_leitura", sa.String(length=20), nullable=False, server_default="odometro"),
        )
    if "leitura_atual" not in colunas:
        op.add_column(
            TABELA,
            sa.Column("leitura_atual", sa.Numeric(12, 2), nullable=False, server_default="0"),
        )

    with op.batch_alter_table(TABELA) as batch_op:
        batch_op.create_check_constraint(
            "ck_operacao_abastecimentos_tipo_leitura",
            "tipo_leitura in ('odometro', 'horimetro')",
        )
        batch_op.create_check_constraint(
            "ck_operacao_abastecimentos_leitura_atual",
            "leitura_atual >= 0",
        )


def downgrade():
    bind = op.get_bind()
    if TABELA not in sa.inspect(bind).get_table_names():
        return

    with op.batch_alter_table(TABELA) as batch_op:
        batch_op.drop_constraint("ck_operacao_abastecimentos_leitura_atual", type_="check")
        batch_op.drop_constraint("ck_operacao_abastecimentos_tipo_leitura", type_="check")

    colunas = _colunas(bind)
    if "leitura_atual" in colunas:
        op.drop_column(TABELA, "leitura_atual")
    if "tipo_leitura" in colunas:
        op.drop_column(TABELA, "tipo_leitura")
