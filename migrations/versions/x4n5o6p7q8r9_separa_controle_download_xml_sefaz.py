"""Separa o controle de download XML da consulta sequencial por NSU.

Revision ID: x4n5o6p7q8r9
Revises: w3m4n5o6p7q8
"""

from alembic import op
import sqlalchemy as sa


revision = "x4n5o6p7q8r9"
down_revision = "w3m4n5o6p7q8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("fiscal_controles_nsu") as batch_op:
        batch_op.add_column(sa.Column("ultimo_download_xml_em", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("download_xml_bloqueado_ate", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("download_xml_status", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("download_xml_mensagem", sa.Text(), nullable=True))

    with op.batch_alter_table("fiscal_documentos") as batch_op:
        batch_op.add_column(sa.Column("xml_consultado_em", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("fiscal_documentos") as batch_op:
        batch_op.drop_column("xml_consultado_em")

    with op.batch_alter_table("fiscal_controles_nsu") as batch_op:
        batch_op.drop_column("download_xml_mensagem")
        batch_op.drop_column("download_xml_status")
        batch_op.drop_column("download_xml_bloqueado_ate")
        batch_op.drop_column("ultimo_download_xml_em")
