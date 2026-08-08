"""adiciona status aprovada requisicoes suprimentos

Revision ID: e8b2c4d6f1a9
Revises: d4a8f6c2b9e1
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e8b2c4d6f1a9"
down_revision = "d4a8f6c2b9e1"
branch_labels = None
depends_on = None


CHECK_NOVO = "status in ('Rascunho', 'Enviada para Analise', 'Aprovada', 'Cancelada')"
CHECK_ANTERIOR = "status in ('Rascunho', 'Enviada para Analise', 'Cancelada')"
NOME_CHECK = "ck_suprimentos_requisicoes_compra_status"


def atualizar_check_status_requisicao(novo_check):
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_requisicoes_compra" not in inspector.get_table_names():
        return

    with op.batch_alter_table("suprimentos_requisicoes_compra", recreate="auto") as batch_op:
        batch_op.drop_constraint(NOME_CHECK, type_="check")
        batch_op.create_check_constraint(NOME_CHECK, novo_check)


def upgrade():
    atualizar_check_status_requisicao(CHECK_NOVO)


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            update suprimentos_requisicoes_compra
               set status = 'Enviada para Analise'
             where status = 'Aprovada'
            """
        )
    )
    atualizar_check_status_requisicao(CHECK_ANTERIOR)
