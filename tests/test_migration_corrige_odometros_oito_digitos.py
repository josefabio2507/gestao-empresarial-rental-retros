import unittest
from types import SimpleNamespace

import sqlalchemy as sa

from migrations.versions import s9i0j1k2l3m4_corrige_odometros_com_oito_digitos as migration


class CorrigeOdometrosOitoDigitosMigrationTestCase(unittest.TestCase):
    def test_corrige_odometros_em_todas_as_fontes_sem_alterar_horimetros(self):
        engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        abastecimentos = sa.Table(
            "operacao_abastecimentos",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("tipo_leitura", sa.String(20)),
            sa.Column("leitura_atual", sa.Numeric(12, 2)),
        )
        leituras = sa.Table(
            "operacao_leituras_ativos",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("tipo", sa.String(20)),
            sa.Column("leitura", sa.Numeric(12, 2)),
        )
        vinculos = sa.Table(
            "operacao_veiculos_responsaveis",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("tipo_leitura", sa.String(20)),
            sa.Column("leitura_inicial", sa.Numeric(12, 2)),
            sa.Column("leitura_final", sa.Numeric(12, 2)),
        )
        metadata.create_all(engine)

        with engine.begin() as bind:
            bind.execute(abastecimentos.insert(), [
                {"id": 1, "tipo_leitura": "odometro", "leitura_atual": 13107400},
                {"id": 2, "tipo_leitura": "horimetro", "leitura_atual": 35910000},
                {"id": 3, "tipo_leitura": "odometro", "leitura_atual": 9999999},
            ])
            bind.execute(leituras.insert(), [
                {"id": 1, "tipo": "odometro", "leitura": 18723800},
                {"id": 2, "tipo": "horimetro", "leitura": 18723800},
            ])
            bind.execute(vinculos.insert(), [
                {"id": 1, "tipo_leitura": "odometro", "leitura_inicial": 16111200, "leitura_final": 16120000},
                {"id": 2, "tipo_leitura": "horimetro", "leitura_inicial": 16111200, "leitura_final": None},
            ])

            op_original = migration.op
            migration.op = SimpleNamespace(get_bind=lambda: bind)
            try:
                migration.upgrade()
            finally:
                migration.op = op_original

            valores_abastecimentos = bind.execute(sa.select(abastecimentos).order_by(abastecimentos.c.id)).all()
            valores_leituras = bind.execute(sa.select(leituras).order_by(leituras.c.id)).all()
            valores_vinculos = bind.execute(sa.select(vinculos).order_by(vinculos.c.id)).all()

        self.assertEqual(["131074.00", "35910000.00", "9999999.00"], [str(r.leitura_atual) for r in valores_abastecimentos])
        self.assertEqual(["187238.00", "18723800.00"], [str(r.leitura) for r in valores_leituras])
        self.assertEqual("161112.00", str(valores_vinculos[0].leitura_inicial))
        self.assertEqual("161200.00", str(valores_vinculos[0].leitura_final))
        self.assertEqual("16111200.00", str(valores_vinculos[1].leitura_inicial))


if __name__ == "__main__":
    unittest.main()
