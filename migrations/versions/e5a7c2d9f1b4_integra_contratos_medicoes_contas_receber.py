"""Integra contratos e medicoes ao contas a receber.

Revision ID: e5a7c2d9f1b4
Revises: d4f1a8c9e2b6
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa


revision = "e5a7c2d9f1b4"
down_revision = "d4f1a8c9e2b6"
branch_labels = None
depends_on = None

TABELA_CONTRATOS = "financeiro_contratos_clientes"
TABELA_MEDICOES = "financeiro_contratos_medicoes"
TABELA_TITULOS = "financeiro_contas_receber_titulos"
TABELA_NOTAS = "financeiro_notas_fiscais_emitidas"


def _table_names(inspector):
    return set(inspector.get_table_names())


def _columns(inspector, tabela):
    if tabela not in _table_names(inspector):
        return set()
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def _indexes(inspector, tabela):
    if tabela not in _table_names(inspector):
        return set()
    return {indice["name"] for indice in inspector.get_indexes(tabela)}


def _fks(inspector, tabela):
    if tabela not in _table_names(inspector):
        return set()
    return {fk["name"] for fk in inspector.get_foreign_keys(tabela) if fk.get("name")}


def _create_index_if_missing(inspector, nome, tabela, colunas):
    if nome not in _indexes(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = _table_names(inspector)

    if TABELA_CONTRATOS not in tabelas:
        op.create_table(
            TABELA_CONTRATOS,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("numero_contrato", sa.String(length=80), nullable=False),
            sa.Column("cliente_nome_snapshot", sa.String(length=180), nullable=False),
            sa.Column("cliente_cnpj_cpf_snapshot", sa.String(length=20), nullable=False),
            sa.Column("cliente_email_financeiro_snapshot", sa.String(length=150), nullable=True),
            sa.Column("cliente_telefone_snapshot", sa.String(length=20), nullable=True),
            sa.Column("descricao_objeto", sa.Text(), nullable=True),
            sa.Column("data_inicio", sa.Date(), nullable=False),
            sa.Column("data_fim", sa.Date(), nullable=True),
            sa.Column("valor_contratual", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("tipo_cobranca", sa.String(length=40), nullable=False, server_default="Medição variável"),
            sa.Column("periodicidade_medicao", sa.String(length=30), nullable=False, server_default="Mensal"),
            sa.Column("dia_padrao_vencimento", sa.Integer(), nullable=True),
            sa.Column("condicao_recebimento", sa.String(length=120), nullable=True),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("sub_centro_custo_equipe_id", sa.Integer(), nullable=True),
            sa.Column("responsavel_interno_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Ativo"),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["centro_custo_id"], ["centros_custo.id"], name="fk_fin_contratos_centro_custo"),
            sa.ForeignKeyConstraint(["sub_centro_custo_equipe_id"], ["equipes.id"], name="fk_fin_contratos_equipe"),
            sa.ForeignKeyConstraint(["responsavel_interno_id"], ["usuarios.id"], name="fk_fin_contratos_responsavel"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_contratos_criado_por"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_fin_contratos_atualizado_por"),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"], name="fk_fin_contratos_cancelado_por"),
            sa.UniqueConstraint("numero_contrato", "cliente_cnpj_cpf_snapshot", name="uq_fin_contratos_numero_cliente"),
            sa.CheckConstraint("valor_contratual >= 0", name="ck_fin_contratos_valor"),
            sa.CheckConstraint("status in ('Rascunho', 'Ativo', 'Suspenso', 'Encerrado', 'Cancelado')", name="ck_fin_contratos_status"),
            sa.CheckConstraint("tipo_cobranca in ('Medição variável', 'Valor fixo mensal', 'Por evento', 'Por ordem de serviço', 'Reembolso', 'Outro')", name="ck_fin_contratos_tipo_cobranca"),
            sa.CheckConstraint("periodicidade_medicao in ('Mensal', 'Quinzenal', 'Semanal', 'Por demanda', 'Única', 'Outra')", name="ck_fin_contratos_periodicidade"),
        )

    inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, "ix_fin_contratos_numero", TABELA_CONTRATOS, ["numero_contrato"])
    _create_index_if_missing(inspector, "ix_fin_contratos_cliente", TABELA_CONTRATOS, ["cliente_nome_snapshot"])
    _create_index_if_missing(inspector, "ix_fin_contratos_cnpj", TABELA_CONTRATOS, ["cliente_cnpj_cpf_snapshot"])
    _create_index_if_missing(inspector, "ix_fin_contratos_status", TABELA_CONTRATOS, ["status"])
    _create_index_if_missing(inspector, "ix_fin_contratos_inicio", TABELA_CONTRATOS, ["data_inicio"])

    inspector = sa.inspect(bind)
    tabelas = _table_names(inspector)
    if TABELA_MEDICOES not in tabelas:
        op.create_table(
            TABELA_MEDICOES,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("contrato_id", sa.Integer(), nullable=False),
            sa.Column("nota_emitida_id", sa.Integer(), nullable=True),
            sa.Column("numero_medicao", sa.String(length=80), nullable=False),
            sa.Column("competencia", sa.String(length=7), nullable=False),
            sa.Column("data_medicao", sa.Date(), nullable=False),
            sa.Column("periodo_inicio", sa.Date(), nullable=False),
            sa.Column("periodo_fim", sa.Date(), nullable=False),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("valor_bruto_medido", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_desconto", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_acrescimo", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_retencoes", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_liquido_medido", sa.Numeric(12, 2), nullable=False),
            sa.Column("data_prevista_faturamento", sa.Date(), nullable=True),
            sa.Column("data_prevista_vencimento", sa.Date(), nullable=True),
            sa.Column("status_medicao", sa.String(length=40), nullable=False, server_default="Medida"),
            sa.Column("status_financeiro", sa.String(length=40), nullable=False, server_default="Não integrado"),
            sa.Column("anexo_nome_original", sa.String(length=255), nullable=True),
            sa.Column("anexo_nome_armazenado", sa.String(length=255), nullable=True),
            sa.Column("anexo_path", sa.String(length=500), nullable=True),
            sa.Column("anexo_drive_file_id", sa.String(length=255), nullable=True),
            sa.Column("anexo_drive_link", sa.String(length=500), nullable=True),
            sa.Column("observacoes_tecnicas", sa.Text(), nullable=True),
            sa.Column("observacoes_financeiras", sa.Text(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["contrato_id"], [f"{TABELA_CONTRATOS}.id"], name="fk_fin_medicoes_contrato"),
            sa.ForeignKeyConstraint(["nota_emitida_id"], [f"{TABELA_NOTAS}.id"], name="fk_fin_medicoes_nota"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_medicoes_criado_por"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_fin_medicoes_atualizado_por"),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"], name="fk_fin_medicoes_cancelado_por"),
            sa.UniqueConstraint("contrato_id", "numero_medicao", name="uq_fin_medicoes_contrato_numero"),
            sa.CheckConstraint("valor_bruto_medido >= 0", name="ck_fin_medicoes_valor_bruto"),
            sa.CheckConstraint("valor_desconto >= 0", name="ck_fin_medicoes_desconto"),
            sa.CheckConstraint("valor_acrescimo >= 0", name="ck_fin_medicoes_acrescimo"),
            sa.CheckConstraint("valor_retencoes >= 0", name="ck_fin_medicoes_retencoes"),
            sa.CheckConstraint("valor_liquido_medido > 0", name="ck_fin_medicoes_valor_liquido"),
            sa.CheckConstraint("periodo_fim >= periodo_inicio", name="ck_fin_medicoes_periodo"),
            sa.CheckConstraint("status_medicao in ('Rascunho', 'Medida', 'Aguardando aprovação', 'Aprovada', 'Faturada', 'Gerada no Contas a Receber', 'Cancelada')", name="ck_fin_medicoes_status"),
            sa.CheckConstraint("status_financeiro in ('Não integrado', 'Pendente de geração', 'Título gerado', 'Vinculado a título existente', 'Vinculado à nota emitida', 'Cancelado')", name="ck_fin_medicoes_status_financeiro"),
        )

    inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, "ix_fin_medicoes_contrato", TABELA_MEDICOES, ["contrato_id"])
    _create_index_if_missing(inspector, "ix_fin_medicoes_nota", TABELA_MEDICOES, ["nota_emitida_id"])
    _create_index_if_missing(inspector, "ix_fin_medicoes_numero", TABELA_MEDICOES, ["numero_medicao"])
    _create_index_if_missing(inspector, "ix_fin_medicoes_competencia", TABELA_MEDICOES, ["competencia"])
    _create_index_if_missing(inspector, "ix_fin_medicoes_data", TABELA_MEDICOES, ["data_medicao"])
    _create_index_if_missing(inspector, "ix_fin_medicoes_status", TABELA_MEDICOES, ["status_medicao"])
    _create_index_if_missing(inspector, "ix_fin_medicoes_status_financeiro", TABELA_MEDICOES, ["status_financeiro"])

    inspector = sa.inspect(bind)
    colunas_notas = _columns(inspector, TABELA_NOTAS)
    with op.batch_alter_table(TABELA_NOTAS) as batch_op:
        if "contrato_id" not in colunas_notas:
            batch_op.add_column(sa.Column("contrato_id", sa.Integer(), nullable=True))
        if "medicao_id" not in colunas_notas:
            batch_op.add_column(sa.Column("medicao_id", sa.Integer(), nullable=True))
    inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, "ix_fin_notas_emitidas_contrato", TABELA_NOTAS, ["contrato_id"])
    _create_index_if_missing(inspector, "ix_fin_notas_emitidas_medicao", TABELA_NOTAS, ["medicao_id"])

    inspector = sa.inspect(bind)
    _create_index_if_missing(inspector, "ix_fin_cr_titulos_contrato", TABELA_TITULOS, ["contrato_id"])
    _create_index_if_missing(inspector, "ix_fin_cr_titulos_medicao", TABELA_TITULOS, ["medicao_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA_TITULOS in _table_names(inspector):
        for nome in ["ix_fin_cr_titulos_medicao", "ix_fin_cr_titulos_contrato"]:
            if nome in _indexes(inspector, TABELA_TITULOS):
                op.drop_index(nome, table_name=TABELA_TITULOS)
    inspector = sa.inspect(bind)
    if TABELA_NOTAS in _table_names(inspector):
        for nome in ["ix_fin_notas_emitidas_medicao", "ix_fin_notas_emitidas_contrato"]:
            if nome in _indexes(inspector, TABELA_NOTAS):
                op.drop_index(nome, table_name=TABELA_NOTAS)
        colunas_notas = _columns(inspector, TABELA_NOTAS)
        with op.batch_alter_table(TABELA_NOTAS) as batch_op:
            if "medicao_id" in colunas_notas:
                batch_op.drop_column("medicao_id")
            if "contrato_id" in colunas_notas:
                batch_op.drop_column("contrato_id")
    inspector = sa.inspect(bind)
    if TABELA_MEDICOES in _table_names(inspector):
        op.drop_table(TABELA_MEDICOES)
    inspector = sa.inspect(bind)
    if TABELA_CONTRATOS in _table_names(inspector):
        op.drop_table(TABELA_CONTRATOS)
