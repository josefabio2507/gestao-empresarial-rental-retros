"""Corrige todas as leituras históricas de odômetro da placa FJJ3E14."""

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision = "g1h2i3j4k5l6"
down_revision = "f1g2h3i4j5k6"
branch_labels = None
depends_on = None


def _cinco_primeiros_digitos(valor):
    if valor is None:
        return None
    valor = Decimal(valor)
    inteiro = str(abs(valor).quantize(Decimal("1"))).split(".", 1)[0]
    if len(inteiro) <= 5:
        return valor
    corrigido = Decimal(inteiro[:5])
    return -corrigido if valor < 0 else corrigido


def _corrigir_coluna(bind, tabela, coluna, ids):
    for registro_id, valor in bind.execute(
        sa.select(tabela.c.id, coluna).where(tabela.c.id.in_(ids))
    ):
        corrigido = _cinco_primeiros_digitos(valor)
        if corrigido != valor:
            bind.execute(
                tabela.update()
                .where(tabela.c.id == registro_id)
                .values({coluna.name: corrigido})
            )


def upgrade():
    bind = op.get_bind()
    tabelas = set(sa.inspect(bind).get_table_names())
    necessarias = {
        "operacao_veiculos_equipamentos",
        "operacao_veiculos_responsaveis",
        "operacao_leituras_ativos",
        "operacao_abastecimentos",
    }
    if not necessarias.issubset(tabelas):
        return

    veiculos = sa.table(
        "operacao_veiculos_equipamentos",
        sa.column("id", sa.Integer),
        sa.column("placa", sa.String),
    )
    veiculo_id = bind.execute(
        sa.select(veiculos.c.id).where(veiculos.c.placa == "FJJ3E14")
    ).scalar_one_or_none()
    if veiculo_id is None:
        return

    vinculos = sa.table(
        "operacao_veiculos_responsaveis",
        sa.column("id", sa.Integer),
        sa.column("veiculo_id", sa.Integer),
        sa.column("tipo_leitura", sa.String),
        sa.column("leitura_inicial", sa.Numeric(12, 2)),
        sa.column("leitura_final", sa.Numeric(12, 2)),
    )
    ids_vinculos = {
        registro_id
        for (registro_id,) in bind.execute(
            sa.select(vinculos.c.id).where(
                vinculos.c.veiculo_id == veiculo_id,
                vinculos.c.tipo_leitura == "odometro",
            )
        )
    }
    _corrigir_coluna(bind, vinculos, vinculos.c.leitura_inicial, ids_vinculos)
    _corrigir_coluna(bind, vinculos, vinculos.c.leitura_final, ids_vinculos)

    leituras = sa.table(
        "operacao_leituras_ativos",
        sa.column("id", sa.Integer),
        sa.column("veiculo_id", sa.Integer),
        sa.column("tipo", sa.String),
        sa.column("leitura", sa.Numeric(12, 2)),
    )
    ids_leituras = {
        registro_id
        for (registro_id,) in bind.execute(
            sa.select(leituras.c.id).where(
                leituras.c.veiculo_id == veiculo_id,
                leituras.c.tipo == "odometro",
            )
        )
    }
    _corrigir_coluna(bind, leituras, leituras.c.leitura, ids_leituras)

    abastecimentos = sa.table(
        "operacao_abastecimentos",
        sa.column("id", sa.Integer),
        sa.column("veiculo_id", sa.Integer),
        sa.column("tipo_leitura", sa.String),
        sa.column("leitura_atual", sa.Numeric(12, 2)),
    )
    ids_abastecimentos = {
        registro_id
        for (registro_id,) in bind.execute(
            sa.select(abastecimentos.c.id).where(
                abastecimentos.c.veiculo_id == veiculo_id,
                abastecimentos.c.tipo_leitura == "odometro",
            )
        )
    }
    _corrigir_coluna(
        bind, abastecimentos, abastecimentos.c.leitura_atual, ids_abastecimentos
    )


def downgrade():
    # Correção de dados deliberadamente irreversível.
    pass
