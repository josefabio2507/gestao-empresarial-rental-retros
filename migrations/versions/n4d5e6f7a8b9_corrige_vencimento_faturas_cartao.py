"""Corrige vencimento de faturas posterior ao fechamento.

Revision ID: n4d5e6f7a8b9
Revises: m3c4d5e6f7a8
"""
from calendar import monthrange
from datetime import date

from alembic import op
import sqlalchemy as sa


revision = "n4d5e6f7a8b9"
down_revision = "m3c4d5e6f7a8"
branch_labels = None
depends_on = None


def _proximo_mes(ano, mes):
    return (ano + 1, 1) if mes == 12 else (ano, mes + 1)


def upgrade():
    bind = op.get_bind()
    faturas = sa.table(
        "financeiro_cartoes_faturas",
        sa.column("id", sa.Integer),
        sa.column("cartao_credito_id", sa.Integer),
        sa.column("data_fechamento", sa.Date),
        sa.column("data_vencimento", sa.Date),
    )
    cartoes = sa.table(
        "financeiro_cartoes_credito",
        sa.column("id", sa.Integer),
        sa.column("dia_vencimento", sa.Integer),
    )
    consulta = (
        sa.select(faturas.c.id, faturas.c.data_fechamento, cartoes.c.dia_vencimento)
        .select_from(faturas.join(cartoes, cartoes.c.id == faturas.c.cartao_credito_id))
        .where(faturas.c.data_vencimento <= faturas.c.data_fechamento)
    )
    for linha in bind.execute(consulta).mappings():
        ano, mes = _proximo_mes(linha["data_fechamento"].year, linha["data_fechamento"].month)
        vencimento = date(ano, mes, min(linha["dia_vencimento"], monthrange(ano, mes)[1]))
        bind.execute(
            faturas.update().where(faturas.c.id == linha["id"]).values(data_vencimento=vencimento)
        )


def downgrade():
    # Correcao de dados irreversivel: não é seguro recriar datas cronologicamente inválidas.
    pass
