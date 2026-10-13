import unittest
from types import SimpleNamespace

import sqlalchemy as sa

from migrations.versions import a1b2c3d4e5f6_corrige_leituras_ded1g69 as migration


class CorrigeLeiturasDed1g69MigrationTestCase(unittest.TestCase):
    def test_corrige_as_fontes_do_veiculo_sem_alterar_outros_veiculos(self):
        engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        veiculos = sa.Table(
            "operacao_veiculos_equipamentos", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("placa", sa.String),
        )
        vinculos = sa.Table(
            "operacao_veiculos_responsaveis", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("veiculo_id", sa.Integer),
            sa.Column("tipo_leitura", sa.String),
            sa.Column("leitura_inicial", sa.Numeric(12, 2)), sa.Column("leitura_final", sa.Numeric(12, 2)),
        )
        leituras = sa.Table(
            "operacao_leituras_ativos", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("veiculo_id", sa.Integer),
            sa.Column("tipo", sa.String),
            sa.Column("leitura", sa.Numeric(12, 2)),
        )
        abastecimentos = sa.Table(
            "operacao_abastecimentos", metadata,
            sa.Column("id", sa.Integer, primary_key=True), sa.Column("veiculo_id", sa.Integer),
            sa.Column("tipo_leitura", sa.String),
            sa.Column("leitura_atual", sa.Numeric(12, 2)),
        )
        metadata.create_all(engine)

        with engine.begin() as bind:
            bind.execute(veiculos.insert(), [{"id": 14, "placa": "DED1G69"}, {"id": 15, "placa": "OUTRA"}])
            bind.execute(vinculos.insert(), [
                {"id": 1, "veiculo_id": 14, "tipo_leitura": "horimetro", "leitura_inicial": 359100, "leitura_final": 3626100},
                {"id": 2, "veiculo_id": 15, "tipo_leitura": "horimetro", "leitura_inicial": 359100, "leitura_final": None},
                {"id": 3, "veiculo_id": 14, "tipo_leitura": "odometro", "leitura_inicial": 999900, "leitura_final": None},
            ])
            bind.execute(leituras.insert(), [
                {"id": 1, "veiculo_id": 14, "tipo": "horimetro", "leitura": 362000},
                {"id": 2, "veiculo_id": 15, "tipo": "horimetro", "leitura": 362000},
                {"id": 3, "veiculo_id": 14, "tipo": "odometro", "leitura": 888800},
            ])
            bind.execute(abastecimentos.insert(), [
                {"id": 1, "veiculo_id": 14, "tipo_leitura": "horimetro", "leitura_atual": 359400},
                {"id": 2, "veiculo_id": 15, "tipo_leitura": "horimetro", "leitura_atual": 359400},
            ])

            original_op = migration.op
            migration.op = SimpleNamespace(get_bind=lambda: bind)
            try:
                migration.upgrade()
            finally:
                migration.op = original_op

            valores_vinculo = bind.execute(sa.select(vinculos).order_by(vinculos.c.id)).all()
            valores_leitura = bind.execute(sa.select(leituras).order_by(leituras.c.id)).all()
            valores_abastecimento = bind.execute(sa.select(abastecimentos).order_by(abastecimentos.c.id)).all()

        self.assertEqual(("3591.00", "3626.00"), (str(valores_vinculo[0].leitura_inicial), str(valores_vinculo[0].leitura_final)))
        self.assertEqual("3620.00", str(valores_leitura[0].leitura))
        self.assertEqual("3594.00", str(valores_abastecimento[0].leitura_atual))
        self.assertEqual("999900.00", str(valores_vinculo[2].leitura_inicial))
        self.assertEqual("888800.00", str(valores_leitura[2].leitura))
        self.assertEqual("359100.00", str(valores_vinculo[1].leitura_inicial))
        self.assertEqual("362000.00", str(valores_leitura[1].leitura))
        self.assertEqual("359400.00", str(valores_abastecimento[1].leitura_atual))


if __name__ == "__main__":
    unittest.main()
