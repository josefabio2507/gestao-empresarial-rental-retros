import unittest
from types import SimpleNamespace

import sqlalchemy as sa

from migrations.versions import q7g8h9i0j1k2_corrige_leituras_multiplicadas_por_cem as migration


class CorrecaoLeiturasQxn5f52MigrationTestCase(unittest.TestCase):
    def test_corrige_somente_os_dois_valores_da_placa_qxn5f52(self):
        engine = sa.create_engine("sqlite:///:memory:")
        metadata = sa.MetaData()
        veiculos = sa.Table(
            "operacao_veiculos_equipamentos",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("identificacao", sa.String),
            sa.Column("placa", sa.String),
        )
        vinculos = sa.Table(
            "operacao_veiculos_responsaveis",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("veiculo_id", sa.Integer),
            sa.Column("leitura_inicial", sa.Numeric(12, 2)),
            sa.Column("leitura_final", sa.Numeric(12, 2)),
        )
        leituras = sa.Table(
            "operacao_leituras_ativos",
            metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("veiculo_id", sa.Integer),
            sa.Column("vinculo_id", sa.Integer),
            sa.Column("leitura", sa.Numeric(12, 2)),
        )
        metadata.create_all(engine)

        with engine.begin() as bind:
            bind.execute(veiculos.insert(), [
                {"id": 18, "identificacao": "QXN5F52", "placa": "QXN5F52"},
                {"id": 19, "identificacao": "OUTRO", "placa": "OUTRO"},
            ])
            bind.execute(vinculos.insert(), [
                {"id": 1, "veiculo_id": 18, "leitura_inicial": 15624700, "leitura_final": None},
                {"id": 2, "veiculo_id": 18, "leitura_inicial": 156121, "leitura_final": 15619800},
                {"id": 3, "veiculo_id": 19, "leitura_inicial": 15624700, "leitura_final": None},
            ])
            bind.execute(leituras.insert(), [
                {"id": 1, "veiculo_id": 18, "vinculo_id": 1, "leitura": 15624700},
                {"id": 2, "veiculo_id": 18, "vinculo_id": 2, "leitura": 15619800},
                {"id": 3, "veiculo_id": 18, "vinculo_id": 2, "leitura": 15593200},
                {"id": 4, "veiculo_id": 19, "vinculo_id": 3, "leitura": 15624700},
            ])

            op_original = migration.op
            migration.op = SimpleNamespace(get_bind=lambda: bind)
            try:
                migration.upgrade()
            finally:
                migration.op = op_original

            valores_vinculos = bind.execute(
                sa.select(vinculos.c.id, vinculos.c.leitura_inicial, vinculos.c.leitura_final).order_by(vinculos.c.id)
            ).all()
            valores_leituras = bind.execute(
                sa.select(leituras.c.id, leituras.c.leitura).order_by(leituras.c.id)
            ).all()

        self.assertEqual("156247.00", str(valores_vinculos[0].leitura_inicial))
        self.assertEqual("156198.00", str(valores_vinculos[1].leitura_final))
        self.assertEqual("15624700.00", str(valores_vinculos[2].leitura_inicial))
        self.assertEqual(
            ["156247.00", "156198.00", "15593200.00", "15624700.00"],
            [str(registro.leitura) for registro in valores_leituras],
        )


if __name__ == "__main__":
    unittest.main()
