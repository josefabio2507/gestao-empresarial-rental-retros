"""atualiza combustiveis abastecimentos

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-08-23 00:00:00.000000
"""

from alembic import op


revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_operacao_abastecimentos_tipo_combustivel"
COMBUSTIVEIS_ATUAIS = "tipo_combustivel in ('Diesel S10', 'Etanol', 'Etanol aditivado', 'Gasolina comum', 'Gasolina aditivada', 'Gasolina Premium')"
COMBUSTIVEIS_ANTERIORES = "tipo_combustivel in ('Diesel', 'Diesel S10', 'Gasolina', 'Etanol', 'Arla 32', 'Outro')"


def _trocar_constraint(condicao):
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("operacao_abastecimentos", recreate="always") as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
            batch_op.create_check_constraint(CONSTRAINT_NAME, condicao)
        return

    op.drop_constraint(CONSTRAINT_NAME, "operacao_abastecimentos", type_="check")
    op.create_check_constraint(CONSTRAINT_NAME, "operacao_abastecimentos", condicao)


def upgrade():
    _trocar_constraint(COMBUSTIVEIS_ATUAIS)


def downgrade():
    _trocar_constraint(COMBUSTIVEIS_ANTERIORES)
