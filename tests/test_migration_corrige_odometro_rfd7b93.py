import unittest
from datetime import date, datetime
from types import SimpleNamespace

import sqlalchemy as sa

from migrations.versions import b1c2d3e4f5a6_corrige_odometro_rfd7b93 as migration


class CorrigeOdometroRfd7b93MigrationTestCase(unittest.TestCase):
    def test_corrige_apenas_o_veiculo_tipo_e_data_informados(self):
        engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        veiculos = sa.Table(
            "operacao_veiculos_equipamentos", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("placa", sa.String),
        )
        vinculos = sa.Table(
            "operacao_veiculos_responsaveis", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("veiculo_id", sa.Integer),
            sa.Column("tipo_leitura", sa.String), sa.Column("iniciado_em", sa.DateTime),
            sa.Column("leitura_inicial", sa.Numeric(12, 2)), sa.Column("leitura_final", sa.Numeric(12, 2)),
        )
        leituras = sa.Table(
            "operacao_leituras_ativos", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("veiculo_id", sa.Integer),
            sa.Column("tipo", sa.String), sa.Column("registrada_em", sa.DateTime),
            sa.Column("leitura", sa.Numeric(12, 2)),
        )
        abastecimentos = sa.Table(
            "operacao_abastecimentos", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("veiculo_id", sa.Integer),
            sa.Column("tipo_leitura", sa.String), sa.Column("data_abastecimento", sa.Date),
            sa.Column("leitura_atual", sa.Numeric(12, 2)),
        )
        metadata.create_all(engine)

        with engine.begin() as bind:
            bind.execute(veiculos.insert(), [
                {"id": 16, "placa": "RFD7B93"}, {"id": 17, "placa": "OUTRA"},
            ])
            bind.execute(vinculos.insert(), [
                {"id": 1, "veiculo_id": 16, "tipo_leitura": "odometro", "iniciado_em": datetime(2026, 10, 2, 7), "leitura_inicial": 1133810, "leitura_final": 1133810},
                {"id": 2, "veiculo_id": 16, "tipo_leitura": "odometro", "iniciado_em": datetime(2026, 10, 1, 7), "leitura_inicial": 1133810, "leitura_final": None},
                {"id": 3, "veiculo_id": 17, "tipo_leitura": "odometro", "iniciado_em": datetime(2026, 10, 2, 7), "leitura_inicial": 1133810, "leitura_final": None},
            ])
            bind.execute(leituras.insert(), [
                {"id": 1, "veiculo_id": 16, "tipo": "odometro", "registrada_em": datetime(2026, 10, 2, 7), "leitura": 1133810},
                {"id": 2, "veiculo_id": 16, "tipo": "odometro", "registrada_em": datetime(2026, 10, 1, 7), "leitura": 1133810},
                {"id": 3, "veiculo_id": 16, "tipo": "horimetro", "registrada_em": datetime(2026, 10, 2, 7), "leitura": 1133810},
            ])
            bind.execute(abastecimentos.insert(), [
                {"id": 1, "veiculo_id": 16, "tipo_leitura": "odometro", "data_abastecimento": date(2026, 10, 2), "leitura_atual": 1133810},
                {"id": 2, "veiculo_id": 16, "tipo_leitura": "odometro", "data_abastecimento": date(2026, 10, 1), "leitura_atual": 1133810},
            ])

            original_op = migration.op
            migration.op = SimpleNamespace(get_bind=lambda: bind)
            try:
                migration.upgrade()
            finally:
                migration.op = original_op

            vinculo_rows = bind.execute(sa.select(vinculos).order_by(vinculos.c.id)).all()
            leitura_rows = bind.execute(sa.select(leituras).order_by(leituras.c.id)).all()
            abastecimento_rows = bind.execute(sa.select(abastecimentos).order_by(abastecimentos.c.id)).all()

        self.assertEqual("113381.00", str(vinculo_rows[0].leitura_inicial))
        self.assertEqual("113381.00", str(vinculo_rows[0].leitura_final))
        self.assertEqual("1133810.00", str(vinculo_rows[1].leitura_inicial))
        self.assertEqual("113381.00", str(leitura_rows[0].leitura))
        self.assertEqual("1133810.00", str(leitura_rows[1].leitura))
        self.assertEqual("1133810.00", str(leitura_rows[2].leitura))
        self.assertEqual("113381.00", str(abastecimento_rows[0].leitura_atual))
        self.assertEqual("1133810.00", str(abastecimento_rows[1].leitura_atual))


if __name__ == "__main__":
    unittest.main()
