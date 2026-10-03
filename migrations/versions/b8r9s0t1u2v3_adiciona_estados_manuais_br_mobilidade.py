"""adiciona estados de criação manual BR Mobilidade

Revision ID: b8r9s0t1u2v3
Revises: a7q8r9s0t1u2
"""

from alembic import op


revision = "b8r9s0t1u2v3"
down_revision = "a7q8r9s0t1u2"
branch_labels = None
depends_on = None


def _trocar_restricao(estados):
    valores = ", ".join(f"'{estado}'" for estado in estados)
    with op.batch_alter_table("vale_transporte_integracoes_br_mobilidade") as batch_op:
        batch_op.drop_constraint("ck_vt_br_integracao_status", type_="check")
        batch_op.create_check_constraint(
            "ck_vt_br_integracao_status",
            f"status_interno in ({valores})",
        )


def upgrade():
    _trocar_restricao(
        (
            "AGUARDANDO_ENVIO",
            "ENVIANDO",
            "AGUARDANDO_STATUS",
            "IMPORTADO",
            "ERRO_IMPORTACAO",
            "ERRO_ENVIO",
            "AGUARDANDO_CRIACAO_MANUAL",
            "CRIADO_MANUAL_SEM_CONFERENCIA",
        )
    )


def downgrade():
    _trocar_restricao(
        (
            "AGUARDANDO_ENVIO",
            "ENVIANDO",
            "AGUARDANDO_STATUS",
            "IMPORTADO",
            "ERRO_IMPORTACAO",
            "ERRO_ENVIO",
        )
    )
