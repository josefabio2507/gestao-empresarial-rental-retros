"""permite formas individuais em lotes de baixa

Revision ID: h8d0e1f2a3b4
Revises: g7c9e1a2b3d4
"""

from alembic import op


revision = "h8d0e1f2a3b4"
down_revision = "g7c9e1a2b3d4"
branch_labels = None
depends_on = None


TABELA = "financeiro_contas_pagar_lotes_baixa"
CONSTRAINT = "ck_fin_cp_lote_forma_pagamento"
FORMAS = "('Boleto', 'Pix', 'Transferencia', 'Deposito', 'Cartao de Credito', 'Outro', 'Diversas')"


def upgrade():
    with op.batch_alter_table(TABELA) as batch_op:
        batch_op.drop_constraint(CONSTRAINT, type_="check")
        batch_op.create_check_constraint(CONSTRAINT, f"forma_pagamento in {FORMAS}")


def downgrade():
    with op.batch_alter_table(TABELA) as batch_op:
        batch_op.drop_constraint(CONSTRAINT, type_="check")
        batch_op.create_check_constraint(CONSTRAINT, "forma_pagamento in ('Boleto', 'Pix', 'Transferencia', 'Deposito', 'Cartao de Credito', 'Outro')")
