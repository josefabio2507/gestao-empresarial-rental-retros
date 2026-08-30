"""Relatorios e inadimplencia do contas a receber.

Revision ID: f6b8d1c2e3a4
Revises: e5a7c2d9f1b4
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa


revision = "f6b8d1c2e3a4"
down_revision = "e5a7c2d9f1b4"
branch_labels = None
depends_on = None

TABELA_COBRANCAS = "financeiro_contas_receber_cobrancas"


def _table_names(inspector):
    return set(inspector.get_table_names())


def _indexes(inspector, tabela):
    if tabela not in _table_names(inspector):
        return set()
    return {indice["name"] for indice in inspector.get_indexes(tabela)}


def _create_index_if_missing(inspector, nome, tabela, colunas):
    if tabela in _table_names(inspector) and nome not in _indexes(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA_COBRANCAS not in _table_names(inspector):
        op.create_table(
            TABELA_COBRANCAS,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("titulo_id", sa.Integer(), nullable=False),
            sa.Column("data_contato", sa.Date(), nullable=False),
            sa.Column("tipo_contato", sa.String(length=30), nullable=False),
            sa.Column("responsavel_usuario_id", sa.Integer(), nullable=True),
            sa.Column("status_cobranca", sa.String(length=40), nullable=False, server_default="A cobrar"),
            sa.Column("previsao_pagamento", sa.Date(), nullable=True),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column("proxima_acao", sa.String(length=180), nullable=True),
            sa.Column("data_proxima_acao", sa.Date(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativo"),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["titulo_id"], ["financeiro_contas_receber_titulos.id"], name="fk_fin_cr_cobrancas_titulo"),
            sa.ForeignKeyConstraint(["responsavel_usuario_id"], ["usuarios.id"], name="fk_fin_cr_cobrancas_responsavel"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_cobrancas_criado_por"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_cobrancas_atualizado_por"),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_cobrancas_cancelado_por"),
            sa.CheckConstraint("tipo_contato in ('Telefone', 'WhatsApp', 'E-mail', 'Reunião', 'Presencial', 'Outro')", name="ck_fin_cr_cobrancas_tipo_contato"),
            sa.CheckConstraint("status_cobranca in ('Sem cobrança', 'A cobrar', 'Cobrança enviada', 'Em negociação', 'Promessa de pagamento', 'Aguardando retorno', 'Recebido parcialmente', 'Resolvido', 'Suspenso', 'Inadimplência encerrada')", name="ck_fin_cr_cobrancas_status_cobranca"),
            sa.CheckConstraint("status in ('Ativo', 'Cancelado')", name="ck_fin_cr_cobrancas_status"),
        )

    inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, "ix_fin_cr_cobrancas_titulo", TABELA_COBRANCAS, ["titulo_id"])
    _create_index_if_missing(inspector, "ix_fin_cr_cobrancas_data", TABELA_COBRANCAS, ["data_contato"])
    _create_index_if_missing(inspector, "ix_fin_cr_cobrancas_status_cobranca", TABELA_COBRANCAS, ["status_cobranca"])
    _create_index_if_missing(inspector, "ix_fin_cr_cobrancas_responsavel", TABELA_COBRANCAS, ["responsavel_usuario_id"])
    _create_index_if_missing(inspector, "ix_fin_cr_cobrancas_proxima_acao", TABELA_COBRANCAS, ["data_proxima_acao"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA_COBRANCAS in _table_names(inspector):
        for nome in [
            "ix_fin_cr_cobrancas_proxima_acao",
            "ix_fin_cr_cobrancas_responsavel",
            "ix_fin_cr_cobrancas_status_cobranca",
            "ix_fin_cr_cobrancas_data",
            "ix_fin_cr_cobrancas_titulo",
        ]:
            if nome in _indexes(inspector, TABELA_COBRANCAS):
                op.drop_index(nome, table_name=TABELA_COBRANCAS)
        op.drop_table(TABELA_COBRANCAS)
