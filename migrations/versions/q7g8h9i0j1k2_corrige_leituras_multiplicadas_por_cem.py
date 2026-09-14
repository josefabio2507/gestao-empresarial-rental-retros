"""Corrige leituras operacionais multiplicadas por cem.

Revision ID: q7g8h9i0j1k2
Revises: p6f7a8b9c0d1
"""

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision = "q7g8h9i0j1k2"
down_revision = "p6f7a8b9c0d1"
branch_labels = None
depends_on = None


veiculos = sa.table(
    "operacao_veiculos_equipamentos",
    sa.column("id", sa.Integer),
    sa.column("identificacao", sa.String),
    sa.column("placa", sa.String),
)
vinculos = sa.table(
    "operacao_veiculos_responsaveis",
    sa.column("id", sa.Integer),
    sa.column("veiculo_id", sa.Integer),
    sa.column("leitura_inicial", sa.Numeric(12, 2)),
    sa.column("leitura_final", sa.Numeric(12, 2)),
)
leituras = sa.table(
    "operacao_leituras_ativos",
    sa.column("id", sa.Integer),
    sa.column("veiculo_id", sa.Integer),
    sa.column("vinculo_id", sa.Integer),
    sa.column("leitura", sa.Numeric(12, 2)),
)
def upgrade():
    bind = op.get_bind()
    tabelas = set(sa.inspect(bind).get_table_names())
    necessarias = {
        "operacao_veiculos_responsaveis",
        "operacao_leituras_ativos",
        "operacao_veiculos_equipamentos",
    }
    if not necessarias.issubset(tabelas):
        return

    veiculo_id = bind.execute(
        sa.select(veiculos.c.id).where(
            sa.or_(veiculos.c.placa == "QXN5F52", veiculos.c.identificacao == "QXN5F52")
        )
    ).scalar_one_or_none()
    if veiculo_id is None:
        return

    bind.execute(
        vinculos.update()
        .where(vinculos.c.veiculo_id == veiculo_id)
        .where(vinculos.c.leitura_inicial == Decimal("15624700.00"))
        .values(leitura_inicial=Decimal("156247.00"))
    )
    bind.execute(
        vinculos.update()
        .where(vinculos.c.veiculo_id == veiculo_id)
        .where(vinculos.c.leitura_final == Decimal("15619800.00"))
        .values(leitura_final=Decimal("156198.00"))
    )
    bind.execute(
        leituras.update()
        .where(leituras.c.veiculo_id == veiculo_id)
        .where(leituras.c.leitura == Decimal("15624700.00"))
        .values(leitura=Decimal("156247.00"))
    )
    bind.execute(
        leituras.update()
        .where(leituras.c.veiculo_id == veiculo_id)
        .where(leituras.c.leitura == Decimal("15619800.00"))
        .values(leitura=Decimal("156198.00"))
    )


def downgrade():
    # Correcao de dados deliberadamente irreversivel: o valor anterior era invalido.
    pass
