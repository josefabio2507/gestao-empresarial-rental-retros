"""estoque centro custo e edicao epi

Revision ID: b18c2d4e6f8a
Revises: b17c2d3e4f5a
Create Date: 2026-08-27 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b18c2d4e6f8a"
down_revision = "b17c2d3e4f5a"
branch_labels = None
depends_on = None


T_MOVIMENTACOES = "suprimentos_movimentacoes_estoque"
T_ENTREGAS = "seguranca_trabalho_entregas_epi"


def _colunas(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [coluna["name"] for coluna in inspector.get_columns(tabela)]


def _indices(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _fks(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [fk["name"] for fk in inspector.get_foreign_keys(tabela)]


def _checks(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [check["name"] for check in inspector.get_check_constraints(tabela)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if T_MOVIMENTACOES in inspector.get_table_names():
        colunas = _colunas(inspector, T_MOVIMENTACOES)
        with op.batch_alter_table(T_MOVIMENTACOES) as batch_op:
            if "centro_custo_id" not in colunas:
                batch_op.add_column(sa.Column("centro_custo_id", sa.Integer(), nullable=True))

        inspector = sa.inspect(bind)
        if "ix_suprimentos_movimentacoes_estoque_centro_custo_id" not in _indices(inspector, T_MOVIMENTACOES):
            op.create_index(
                "ix_suprimentos_movimentacoes_estoque_centro_custo_id",
                T_MOVIMENTACOES,
                ["centro_custo_id"],
            )
        if "fk_suprimentos_movimentacoes_estoque_centro_custo_id" not in _fks(inspector, T_MOVIMENTACOES):
            with op.batch_alter_table(T_MOVIMENTACOES) as batch_op:
                batch_op.create_foreign_key(
                    "fk_suprimentos_movimentacoes_estoque_centro_custo_id",
                    "centros_custo",
                    ["centro_custo_id"],
                    ["id"],
                )

    inspector = sa.inspect(bind)
    if T_ENTREGAS in inspector.get_table_names():
        colunas = _colunas(inspector, T_ENTREGAS)
        with op.batch_alter_table(T_ENTREGAS) as batch_op:
            if "status" not in colunas:
                batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=False, server_default="Ativa"))
            if "cancelado_em" not in colunas:
                batch_op.add_column(sa.Column("cancelado_em", sa.DateTime(), nullable=True))
            if "cancelado_por_usuario_id" not in colunas:
                batch_op.add_column(sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True))
            if "motivo_cancelamento" not in colunas:
                batch_op.add_column(sa.Column("motivo_cancelamento", sa.Text(), nullable=True))

        inspector = sa.inspect(bind)
        if "ix_seguranca_trabalho_entregas_epi_status" not in _indices(inspector, T_ENTREGAS):
            op.create_index("ix_seguranca_trabalho_entregas_epi_status", T_ENTREGAS, ["status"])
        if "ix_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id" not in _indices(inspector, T_ENTREGAS):
            op.create_index(
                "ix_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id",
                T_ENTREGAS,
                ["cancelado_por_usuario_id"],
            )
        if "fk_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id" not in _fks(inspector, T_ENTREGAS):
            with op.batch_alter_table(T_ENTREGAS) as batch_op:
                batch_op.create_foreign_key(
                    "fk_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id",
                    "usuarios",
                    ["cancelado_por_usuario_id"],
                    ["id"],
                )
        if "ck_seguranca_entregas_epi_status" not in _checks(inspector, T_ENTREGAS):
            with op.batch_alter_table(T_ENTREGAS) as batch_op:
                batch_op.create_check_constraint(
                    "ck_seguranca_entregas_epi_status",
                    "status in ('Ativa', 'Cancelada')",
                )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if T_ENTREGAS in inspector.get_table_names():
        with op.batch_alter_table(T_ENTREGAS) as batch_op:
            if "ck_seguranca_entregas_epi_status" in _checks(inspector, T_ENTREGAS):
                batch_op.drop_constraint("ck_seguranca_entregas_epi_status", type_="check")
            if "fk_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id" in _fks(inspector, T_ENTREGAS):
                batch_op.drop_constraint("fk_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id", type_="foreignkey")
        inspector = sa.inspect(bind)
        if "ix_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id" in _indices(inspector, T_ENTREGAS):
            op.drop_index("ix_seguranca_trabalho_entregas_epi_cancelado_por_usuario_id", table_name=T_ENTREGAS)
        if "ix_seguranca_trabalho_entregas_epi_status" in _indices(inspector, T_ENTREGAS):
            op.drop_index("ix_seguranca_trabalho_entregas_epi_status", table_name=T_ENTREGAS)
        colunas = _colunas(inspector, T_ENTREGAS)
        with op.batch_alter_table(T_ENTREGAS) as batch_op:
            for coluna in ["motivo_cancelamento", "cancelado_por_usuario_id", "cancelado_em", "status"]:
                if coluna in colunas:
                    batch_op.drop_column(coluna)

    inspector = sa.inspect(bind)
    if T_MOVIMENTACOES in inspector.get_table_names():
        with op.batch_alter_table(T_MOVIMENTACOES) as batch_op:
            if "fk_suprimentos_movimentacoes_estoque_centro_custo_id" in _fks(inspector, T_MOVIMENTACOES):
                batch_op.drop_constraint("fk_suprimentos_movimentacoes_estoque_centro_custo_id", type_="foreignkey")
        inspector = sa.inspect(bind)
        if "ix_suprimentos_movimentacoes_estoque_centro_custo_id" in _indices(inspector, T_MOVIMENTACOES):
            op.drop_index("ix_suprimentos_movimentacoes_estoque_centro_custo_id", table_name=T_MOVIMENTACOES)
        if "centro_custo_id" in _colunas(inspector, T_MOVIMENTACOES):
            with op.batch_alter_table(T_MOVIMENTACOES) as batch_op:
                batch_op.drop_column("centro_custo_id")
