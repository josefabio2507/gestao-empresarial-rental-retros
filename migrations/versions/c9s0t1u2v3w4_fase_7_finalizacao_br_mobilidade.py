"""fase 7: autorização e finalização BR Mobilidade

Revision ID: c9s0t1u2v3w4
Revises: b8r9s0t1u2v3
"""

import sqlalchemy as sa
from alembic import op


revision = "c9s0t1u2v3w4"
down_revision = "b8r9s0t1u2v3"
branch_labels = None
depends_on = None


ESTADOS_ANTERIORES = (
    "AGUARDANDO_ENVIO",
    "ENVIANDO",
    "AGUARDANDO_STATUS",
    "IMPORTADO",
    "ERRO_IMPORTACAO",
    "ERRO_ENVIO",
    "AGUARDANDO_CRIACAO_MANUAL",
    "CRIADO_MANUAL_SEM_CONFERENCIA",
)

ESTADOS_FASE_7 = ESTADOS_ANTERIORES + (
    "AGUARDANDO_AUTORIZACAO_FINALIZACAO",
    "AUTORIZADO_FINALIZACAO",
    "FINALIZANDO_PORTAL",
    "FINALIZADO_PORTAL",
    "ERRO_FINALIZACAO",
    "FINALIZACAO_INCERTA",
)


def _restricao(estados):
    return "status_interno in ({})".format(
        ", ".join(f"'{estado}'" for estado in estados)
    )


def upgrade():
    with op.batch_alter_table("vale_transporte_integracoes_br_mobilidade") as batch_op:
        batch_op.drop_constraint("ck_vt_br_integracao_status", type_="check")
        batch_op.alter_column(
            "status_interno",
            existing_type=sa.String(length=30),
            type_=sa.String(length=50),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column("taxa_administrativa", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("valor_cartoes", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("valor_total_portal", sa.Numeric(12, 2)))
        batch_op.add_column(sa.Column("data_pedido_portal", sa.Date()))
        batch_op.add_column(sa.Column("autorizado_finalizacao_em", sa.DateTime()))
        batch_op.add_column(sa.Column("autorizado_finalizacao_por_id", sa.Integer()))
        batch_op.add_column(sa.Column("finalizado_portal_em", sa.DateTime()))
        batch_op.create_foreign_key(
            "fk_vt_br_integracao_autorizado_por",
            "usuarios",
            ["autorizado_finalizacao_por_id"],
            ["id"],
        )
        batch_op.create_check_constraint(
            "ck_vt_br_integracao_status",
            _restricao(ESTADOS_FASE_7),
        )


def downgrade():
    with op.batch_alter_table("vale_transporte_integracoes_br_mobilidade") as batch_op:
        batch_op.drop_constraint("ck_vt_br_integracao_status", type_="check")
        batch_op.drop_constraint("fk_vt_br_integracao_autorizado_por", type_="foreignkey")
        batch_op.drop_column("finalizado_portal_em")
        batch_op.drop_column("autorizado_finalizacao_por_id")
        batch_op.drop_column("autorizado_finalizacao_em")
        batch_op.drop_column("valor_total_portal")
        batch_op.drop_column("data_pedido_portal")
        batch_op.drop_column("valor_cartoes")
        batch_op.drop_column("taxa_administrativa")
        batch_op.alter_column(
            "status_interno",
            existing_type=sa.String(length=50),
            type_=sa.String(length=30),
            existing_nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_vt_br_integracao_status",
            _restricao(ESTADOS_ANTERIORES),
        )
