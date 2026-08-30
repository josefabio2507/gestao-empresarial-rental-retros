"""integra notas emitidas contas receber

Revision ID: d4f1a8c9e2b6
Revises: c3e8f2a7d9b1
Create Date: 2026-08-29 20:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d4f1a8c9e2b6"
down_revision = "c3e8f2a7d9b1"
branch_labels = None
depends_on = None


TABELA_NOTAS = "financeiro_notas_fiscais_emitidas"
TABELA_TITULOS = "financeiro_contas_receber_titulos"


def _tabela_existe(inspector, tabela):
    return tabela in inspector.get_table_names()


def _colunas(inspector, tabela):
    if not _tabela_existe(inspector, tabela):
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def _indices(inspector, tabela):
    if not _tabela_existe(inspector, tabela):
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _fks(inspector, tabela):
    if not _tabela_existe(inspector, tabela):
        return []
    return [fk["name"] for fk in inspector.get_foreign_keys(tabela)]


def _criar_indice_se_nao_existir(inspector, nome, tabela, colunas):
    if _tabela_existe(inspector, tabela) and nome not in _indices(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _tabela_existe(inspector, TABELA_NOTAS):
        op.create_table(
            TABELA_NOTAS,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("tipo_nota", sa.String(length=30), nullable=False),
            sa.Column("numero_nota", sa.String(length=80), nullable=False),
            sa.Column("serie", sa.String(length=30), nullable=True),
            sa.Column("chave_acesso", sa.String(length=80), nullable=True),
            sa.Column("codigo_verificacao_nfse", sa.String(length=80), nullable=True),
            sa.Column("cliente_nome_snapshot", sa.String(length=180), nullable=False),
            sa.Column("cliente_cnpj_cpf_snapshot", sa.String(length=20), nullable=False),
            sa.Column("cliente_email_financeiro_snapshot", sa.String(length=150), nullable=True),
            sa.Column("cliente_telefone_snapshot", sa.String(length=20), nullable=True),
            sa.Column("data_emissao", sa.Date(), nullable=False),
            sa.Column("competencia", sa.String(length=7), nullable=True),
            sa.Column("descricao", sa.Text(), nullable=True),
            sa.Column("valor_bruto", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_desconto", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_impostos_retidos", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_liquido", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_total", sa.Numeric(12, 2), nullable=False),
            sa.Column("data_vencimento_padrao", sa.Date(), nullable=True),
            sa.Column("numero_parcelas", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("condicao_recebimento", sa.String(length=120), nullable=True),
            sa.Column("status_fiscal", sa.String(length=30), nullable=False, server_default="Emitida"),
            sa.Column("status_financeiro", sa.String(length=40), nullable=False, server_default="Não integrado"),
            sa.Column("arquivo_pdf_nome_original", sa.String(length=255), nullable=True),
            sa.Column("arquivo_pdf_nome_armazenado", sa.String(length=255), nullable=True),
            sa.Column("arquivo_pdf_path", sa.String(length=500), nullable=True),
            sa.Column("arquivo_pdf_drive_file_id", sa.String(length=255), nullable=True),
            sa.Column("arquivo_pdf_drive_link", sa.String(length=500), nullable=True),
            sa.Column("arquivo_xml_nome_original", sa.String(length=255), nullable=True),
            sa.Column("arquivo_xml_nome_armazenado", sa.String(length=255), nullable=True),
            sa.Column("arquivo_xml_path", sa.String(length=500), nullable=True),
            sa.Column("arquivo_xml_drive_file_id", sa.String(length=255), nullable=True),
            sa.Column("arquivo_xml_drive_link", sa.String(length=500), nullable=True),
            sa.Column("observacoes_fiscais", sa.Text(), nullable=True),
            sa.Column("observacoes_financeiras", sa.Text(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_notas_emitidas_criado_por"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_fin_notas_emitidas_atualizado_por"),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"], name="fk_fin_notas_emitidas_cancelado_por"),
            sa.CheckConstraint("valor_bruto >= 0", name="ck_fin_notas_emitidas_valor_bruto"),
            sa.CheckConstraint("valor_desconto >= 0", name="ck_fin_notas_emitidas_valor_desconto"),
            sa.CheckConstraint("valor_impostos_retidos >= 0", name="ck_fin_notas_emitidas_valor_impostos"),
            sa.CheckConstraint("valor_liquido >= 0", name="ck_fin_notas_emitidas_valor_liquido"),
            sa.CheckConstraint("valor_total > 0", name="ck_fin_notas_emitidas_valor_total"),
            sa.CheckConstraint("numero_parcelas >= 1", name="ck_fin_notas_emitidas_parcelas"),
            sa.CheckConstraint("tipo_nota in ('NFS-e', 'NF-e', 'Recibo', 'Fatura', 'Outro')", name="ck_fin_notas_emitidas_tipo"),
            sa.CheckConstraint("status_fiscal in ('Rascunho', 'Emitida', 'Enviada ao cliente', 'Cancelada', 'Substituída')", name="ck_fin_notas_emitidas_status_fiscal"),
            sa.CheckConstraint("status_financeiro in ('Não integrado', 'Pendente de geração', 'Título gerado', 'Parcialmente vinculado', 'Vinculado a título existente', 'Cancelado')", name="ck_fin_notas_emitidas_status_financeiro"),
        )

    inspector = sa.inspect(bind)
    if _tabela_existe(inspector, TABELA_TITULOS):
        colunas = _colunas(inspector, TABELA_TITULOS)
        with op.batch_alter_table(TABELA_TITULOS) as batch_op:
            if "nota_emitida_id" not in colunas:
                batch_op.add_column(sa.Column("nota_emitida_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key("fk_fin_cr_titulos_nota_emitida", TABELA_NOTAS, ["nota_emitida_id"], ["id"])
            if "tipo_nota_emitida" not in colunas:
                batch_op.add_column(sa.Column("tipo_nota_emitida", sa.String(length=30), nullable=True))
            if "codigo_verificacao_nfse" not in colunas:
                batch_op.add_column(sa.Column("codigo_verificacao_nfse", sa.String(length=80), nullable=True))

    inspector = sa.inspect(bind)
    for nome, tabela, colunas in [
        ("ix_fin_notas_emitidas_numero", TABELA_NOTAS, ["numero_nota"]),
        ("ix_fin_notas_emitidas_chave", TABELA_NOTAS, ["chave_acesso"]),
        ("ix_fin_notas_emitidas_cliente_cnpj", TABELA_NOTAS, ["cliente_cnpj_cpf_snapshot"]),
        ("ix_fin_notas_emitidas_data", TABELA_NOTAS, ["data_emissao"]),
        ("ix_fin_notas_emitidas_competencia", TABELA_NOTAS, ["competencia"]),
        ("ix_fin_notas_emitidas_status_fiscal", TABELA_NOTAS, ["status_fiscal"]),
        ("ix_fin_notas_emitidas_status_fin", TABELA_NOTAS, ["status_financeiro"]),
        ("ix_fin_cr_titulos_nota_emitida", TABELA_TITULOS, ["nota_emitida_id"]),
    ]:
        _criar_indice_se_nao_existir(inspector, nome, tabela, colunas)
        inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _tabela_existe(inspector, TABELA_TITULOS):
        colunas = _colunas(inspector, TABELA_TITULOS)
        indices = _indices(inspector, TABELA_TITULOS)
        if "ix_fin_cr_titulos_nota_emitida" in indices:
            op.drop_index("ix_fin_cr_titulos_nota_emitida", table_name=TABELA_TITULOS)
        with op.batch_alter_table(TABELA_TITULOS) as batch_op:
            if "fk_fin_cr_titulos_nota_emitida" in _fks(inspector, TABELA_TITULOS):
                batch_op.drop_constraint("fk_fin_cr_titulos_nota_emitida", type_="foreignkey")
            if "codigo_verificacao_nfse" in colunas:
                batch_op.drop_column("codigo_verificacao_nfse")
            if "tipo_nota_emitida" in colunas:
                batch_op.drop_column("tipo_nota_emitida")
            if "nota_emitida_id" in colunas:
                batch_op.drop_column("nota_emitida_id")

    inspector = sa.inspect(bind)
    if _tabela_existe(inspector, TABELA_NOTAS):
        indices = _indices(inspector, TABELA_NOTAS)
        for nome in [
            "ix_fin_notas_emitidas_status_fin",
            "ix_fin_notas_emitidas_status_fiscal",
            "ix_fin_notas_emitidas_competencia",
            "ix_fin_notas_emitidas_data",
            "ix_fin_notas_emitidas_cliente_cnpj",
            "ix_fin_notas_emitidas_chave",
            "ix_fin_notas_emitidas_numero",
        ]:
            if nome in indices:
                op.drop_index(nome, table_name=TABELA_NOTAS)
        op.drop_table(TABELA_NOTAS)
