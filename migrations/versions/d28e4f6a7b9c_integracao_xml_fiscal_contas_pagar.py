"""integracao xml fiscal contas pagar

Revision ID: d28e4f6a7b9c
Revises: c17d3e4f5a6b
Create Date: 2026-08-27 20:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d28e4f6a7b9c"
down_revision = "c17d3e4f5a6b"
branch_labels = None
depends_on = None


T_FISCAL = "fiscal_documentos"
T_TITULOS = "financeiro_contas_pagar_titulos"


def _colunas(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def _indices(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _criar_indice(inspector, nome, tabela, colunas):
    if tabela in inspector.get_table_names() and nome not in _indices(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if T_FISCAL in inspector.get_table_names():
        colunas = _colunas(inspector, T_FISCAL)
        novas_colunas = [
            ("financeiro_status", sa.Column("financeiro_status", sa.String(length=40), nullable=False, server_default="Pendente de geracao")),
            ("financeiro_integrado", sa.Column("financeiro_integrado", sa.Boolean(), nullable=False, server_default=sa.false())),
            ("financeiro_integrado_em", sa.Column("financeiro_integrado_em", sa.DateTime(), nullable=True)),
            ("financeiro_integrado_por_usuario_id", sa.Column("financeiro_integrado_por_usuario_id", sa.Integer(), nullable=True)),
            ("financeiro_ignorado", sa.Column("financeiro_ignorado", sa.Boolean(), nullable=False, server_default=sa.false())),
            ("financeiro_ignorado_em", sa.Column("financeiro_ignorado_em", sa.DateTime(), nullable=True)),
            ("financeiro_ignorado_por_usuario_id", sa.Column("financeiro_ignorado_por_usuario_id", sa.Integer(), nullable=True)),
            ("financeiro_observacoes", sa.Column("financeiro_observacoes", sa.Text(), nullable=True)),
        ]
        if bind.dialect.name == "sqlite":
            for nome, coluna in novas_colunas:
                if nome not in colunas:
                    op.add_column(T_FISCAL, coluna)
        else:
            with op.batch_alter_table(T_FISCAL) as batch_op:
                for nome, coluna in novas_colunas:
                    if nome not in colunas:
                        batch_op.add_column(coluna)

    inspector = sa.inspect(bind)
    for nome, tabela, colunas in [
        ("ix_fd_fin_status", T_FISCAL, ["financeiro_status"]),
        ("ix_fd_fin_integrado", T_FISCAL, ["financeiro_integrado"]),
        ("ix_fd_fin_ignorado", T_FISCAL, ["financeiro_ignorado"]),
        ("ix_fd_fin_int_user", T_FISCAL, ["financeiro_integrado_por_usuario_id"]),
        ("ix_fd_fin_ign_user", T_FISCAL, ["financeiro_ignorado_por_usuario_id"]),
        ("ix_fcp_fiscal_doc_id", T_TITULOS, ["fiscal_documento_id"]),
        ("ix_fcp_chave_nfe", T_TITULOS, ["chave_acesso_nfe"]),
    ]:
        _criar_indice(inspector, nome, tabela, colunas)
        inspector = sa.inspect(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for nome, tabela in [
        ("ix_fcp_chave_nfe", T_TITULOS),
        ("ix_fcp_fiscal_doc_id", T_TITULOS),
        ("ix_fd_fin_ign_user", T_FISCAL),
        ("ix_fd_fin_int_user", T_FISCAL),
        ("ix_fd_fin_ignorado", T_FISCAL),
        ("ix_fd_fin_integrado", T_FISCAL),
        ("ix_fd_fin_status", T_FISCAL),
    ]:
        if tabela in inspector.get_table_names() and nome in _indices(inspector, tabela):
            op.drop_index(nome, table_name=tabela)
            inspector = sa.inspect(bind)

    if T_FISCAL in inspector.get_table_names():
        colunas = _colunas(inspector, T_FISCAL)
        with op.batch_alter_table(T_FISCAL) as batch_op:
            for coluna in [
                "financeiro_observacoes",
                "financeiro_ignorado_por_usuario_id",
                "financeiro_ignorado_em",
                "financeiro_ignorado",
                "financeiro_integrado_por_usuario_id",
                "financeiro_integrado_em",
                "financeiro_integrado",
                "financeiro_status",
            ]:
                if coluna in colunas:
                    batch_op.drop_column(coluna)
