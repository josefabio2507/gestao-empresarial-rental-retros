"""manifestacao destinatario fiscal

Revision ID: d6e4f2a9b8c1
Revises: c3a9e5f1b7d2
Create Date: 2026-08-17 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d6e4f2a9b8c1"
down_revision = "c3a9e5f1b7d2"
branch_labels = None
depends_on = None


TABELA_DOCUMENTOS = "fiscal_documentos"
TABELA_MANIFESTACOES = "fiscal_manifestacoes_nfe"


def _tabelas(inspector):
    return set(inspector.get_table_names())


def _colunas(inspector, tabela):
    if tabela not in _tabelas(inspector):
        return set()
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def _indices(inspector, tabela):
    if tabela not in _tabelas(inspector):
        return set()
    return {indice["name"] for indice in inspector.get_indexes(tabela)}


def _adicionar_coluna_se_necessario(inspector, nome, coluna):
    if nome in _colunas(inspector, TABELA_DOCUMENTOS):
        return
    with op.batch_alter_table(TABELA_DOCUMENTOS) as batch_op:
        batch_op.add_column(coluna)


def _criar_indice_se_necessario(inspector, nome, colunas):
    if nome in _indices(inspector, TABELA_DOCUMENTOS):
        return
    op.create_index(nome, TABELA_DOCUMENTOS, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA_DOCUMENTOS not in _tabelas(inspector):
        return

    _adicionar_coluna_se_necessario(
        inspector,
        "tipo_distribuicao",
        sa.Column("tipo_distribuicao", sa.String(length=30), nullable=False, server_default="procNFe"),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "tem_xml_completo",
        sa.Column("tem_xml_completo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "manifestacao_status",
        sa.Column("manifestacao_status", sa.String(length=40), nullable=True),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "manifestacao_evento",
        sa.Column("manifestacao_evento", sa.String(length=40), nullable=True),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "manifestacao_protocolo",
        sa.Column("manifestacao_protocolo", sa.String(length=80), nullable=True),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "manifestacao_em",
        sa.Column("manifestacao_em", sa.DateTime(), nullable=True),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "manifestado_por_usuario_id",
        sa.Column("manifestado_por_usuario_id", sa.Integer(), nullable=True),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "xml_completo_baixado_em",
        sa.Column("xml_completo_baixado_em", sa.DateTime(), nullable=True),
    )
    _adicionar_coluna_se_necessario(
        inspector,
        "ultima_consulta_em",
        sa.Column("ultima_consulta_em", sa.DateTime(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE fiscal_documentos
               SET status = CASE
                   WHEN status = 'Disponivel' THEN 'XML baixado'
                   WHEN status = 'Vinculado' THEN 'Vinculado a OC'
                   ELSE status
               END,
                   tem_xml_completo = CASE
                       WHEN xml_path IS NULL OR trim(xml_path) = '' THEN false
                       ELSE true
                   END,
                   tipo_distribuicao = CASE
                       WHEN xml_path IS NULL OR trim(xml_path) = '' THEN 'resNFe'
                       ELSE 'procNFe'
                   END,
                   xml_completo_baixado_em = CASE
                       WHEN xml_path IS NULL OR trim(xml_path) = '' THEN xml_completo_baixado_em
                       ELSE coalesce(xml_completo_baixado_em, atualizado_em)
                   END
             WHERE status IN ('Disponivel', 'Vinculado')
                OR tipo_distribuicao IS NULL
            """
        )
    )

    with op.batch_alter_table(TABELA_DOCUMENTOS) as batch_op:
        try:
            batch_op.drop_constraint("ck_fiscal_documentos_status", type_="check")
        except ValueError:
            pass
        batch_op.alter_column("xml_path", existing_type=sa.String(length=500), nullable=True)
        batch_op.create_check_constraint(
            "ck_fiscal_documentos_status",
            "status in ('Resumo localizado', 'Aguardando manifestacao', 'Ciencia registrada', 'XML baixado', 'Vinculado a OC', 'Confirmada', 'Desconhecida', 'Operacao nao realizada', 'Cancelada')",
        )
        batch_op.create_foreign_key(
            "fk_fiscal_documentos_manifestado_por_usuario",
            "usuarios",
            ["manifestado_por_usuario_id"],
            ["id"],
        )

    inspector = sa.inspect(bind)
    _criar_indice_se_necessario(inspector, "ix_fiscal_documentos_tipo_distribuicao", ["tipo_distribuicao"])
    _criar_indice_se_necessario(inspector, "ix_fiscal_documentos_tem_xml_completo", ["tem_xml_completo"])
    _criar_indice_se_necessario(inspector, "ix_fiscal_documentos_manifestacao_status", ["manifestacao_status"])
    _criar_indice_se_necessario(inspector, "ix_fiscal_documentos_manifestado_por_usuario_id", ["manifestado_por_usuario_id"])

    if TABELA_MANIFESTACOES not in _tabelas(inspector):
        op.create_table(
            TABELA_MANIFESTACOES,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("documento_id", sa.Integer(), nullable=False),
            sa.Column("chave_acesso", sa.String(length=44), nullable=False),
            sa.Column("evento", sa.String(length=40), nullable=False),
            sa.Column("status_retorno", sa.String(length=20), nullable=True),
            sa.Column("motivo_retorno", sa.Text(), nullable=True),
            sa.Column("protocolo", sa.String(length=80), nullable=True),
            sa.Column("xml_evento_path", sa.String(length=500), nullable=True),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["documento_id"], ["fiscal_documentos.id"]),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_fiscal_manifestacoes_nfe_documento_id", TABELA_MANIFESTACOES, ["documento_id"])
        op.create_index("ix_fiscal_manifestacoes_nfe_chave_acesso", TABELA_MANIFESTACOES, ["chave_acesso"])
        op.create_index("ix_fiscal_manifestacoes_nfe_evento", TABELA_MANIFESTACOES, ["evento"])
        op.create_index("ix_fiscal_manifestacoes_nfe_usuario_id", TABELA_MANIFESTACOES, ["usuario_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA_MANIFESTACOES in _tabelas(inspector):
        for nome in [
            "ix_fiscal_manifestacoes_nfe_usuario_id",
            "ix_fiscal_manifestacoes_nfe_evento",
            "ix_fiscal_manifestacoes_nfe_chave_acesso",
            "ix_fiscal_manifestacoes_nfe_documento_id",
        ]:
            if nome in _indices(inspector, TABELA_MANIFESTACOES):
                op.drop_index(nome, table_name=TABELA_MANIFESTACOES)
        op.drop_table(TABELA_MANIFESTACOES)

    if TABELA_DOCUMENTOS not in _tabelas(inspector):
        return

    for nome in [
        "ix_fiscal_documentos_manifestado_por_usuario_id",
        "ix_fiscal_documentos_manifestacao_status",
        "ix_fiscal_documentos_tem_xml_completo",
        "ix_fiscal_documentos_tipo_distribuicao",
    ]:
        if nome in _indices(inspector, TABELA_DOCUMENTOS):
            op.drop_index(nome, table_name=TABELA_DOCUMENTOS)

    with op.batch_alter_table(TABELA_DOCUMENTOS) as batch_op:
        try:
            batch_op.drop_constraint("fk_fiscal_documentos_manifestado_por_usuario", type_="foreignkey")
        except ValueError:
            pass
        try:
            batch_op.drop_constraint("ck_fiscal_documentos_status", type_="check")
        except ValueError:
            pass
        batch_op.create_check_constraint(
            "ck_fiscal_documentos_status",
            "status in ('Disponivel', 'Vinculado', 'Cancelado')",
        )
        for nome in [
            "ultima_consulta_em",
            "xml_completo_baixado_em",
            "manifestado_por_usuario_id",
            "manifestacao_em",
            "manifestacao_protocolo",
            "manifestacao_evento",
            "manifestacao_status",
            "tem_xml_completo",
            "tipo_distribuicao",
        ]:
            if nome in _colunas(inspector, TABELA_DOCUMENTOS):
                batch_op.drop_column(nome)
