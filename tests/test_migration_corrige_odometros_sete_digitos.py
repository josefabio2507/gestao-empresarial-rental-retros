import unittest
from types import SimpleNamespace

import sqlalchemy as sa

from migrations.versions import a7b8c9d0e1f2_corrige_odometros_sete_digitos as migration


class CorrigeOdometrosSeteDigitosMigrationTestCase(unittest.TestCase):
    def test_corrige_odometros_em_todas_as_fontes_sem_alterar_horimetros(self):
        engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        abastecimentos = sa.Table("operacao_abastecimentos", metadata, sa.Column("id", sa.Integer, primary_key=True), sa.Column("tipo_leitura", sa.String(20)), sa.Column("leitura_atual", sa.Numeric(12, 2)))
        leituras = sa.Table("operacao_leituras_ativos", metadata, sa.Column("id", sa.Integer, primary_key=True), sa.Column("tipo", sa.String(20)), sa.Column("leitura", sa.Numeric(12, 2)))
        vinculos = sa.Table("operacao_veiculos_responsaveis", metadata, sa.Column("id", sa.Integer, primary_key=True), sa.Column("tipo_leitura", sa.String(20)), sa.Column("leitura_inicial", sa.Numeric(12, 2)), sa.Column("leitura_final", sa.Numeric(12, 2)))
        metadata.create_all(engine)

        with engine.begin() as bind:
            bind.execute(abastecimentos.insert(), [{"id": 1, "tipo_leitura": "odometro", "leitura_atual": 3760900}, {"id": 2, "tipo_leitura": "horimetro", "leitura_atual": 3760900}])
            bind.execute(leituras.insert(), [{"id": 1, "tipo": "odometro", "leitura": 3756800}, {"id": 2, "tipo": "horimetro", "leitura": 3756800}])
            bind.execute(vinculos.insert(), [{"id": 1, "tipo_leitura": "odometro", "leitura_inicial": 1831145, "leitura_final": 1833246}, {"id": 2, "tipo_leitura": "horimetro", "leitura_inicial": 1831145, "leitura_final": None}])
            original_op = migration.op
            migration.op = SimpleNamespace(get_bind=lambda: bind)
            try:
                migration.upgrade()
            finally:
                migration.op = original_op
            valores_abastecimentos = bind.execute(sa.select(abastecimentos).order_by(abastecimentos.c.id)).all()
            valores_leituras = bind.execute(sa.select(leituras).order_by(leituras.c.id)).all()
            valores_vinculos = bind.execute(sa.select(vinculos).order_by(vinculos.c.id)).all()

        self.assertEqual(["37609.00", "3760900.00"], [str(r.leitura_atual) for r in valores_abastecimentos])
        self.assertEqual(["37568.00", "3756800.00"], [str(r.leitura) for r in valores_leituras])
        self.assertEqual(("18311.45", "18332.46"), (str(valores_vinculos[0].leitura_inicial), str(valores_vinculos[0].leitura_final)))
        self.assertEqual("1831145.00", str(valores_vinculos[1].leitura_inicial))


if __name__ == "__main__":
    unittest.main()
