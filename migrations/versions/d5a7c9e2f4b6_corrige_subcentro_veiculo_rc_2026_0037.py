"""corrige subcentro veiculo rc 2026 0037

Revision ID: d5a7c9e2f4b6
Revises: d4e5f6a7b8c9
Create Date: 2026-08-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d5a7c9e2f4b6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


REQUISICAO_NUMERO = "RC-2026-0037"
CENTRO_CUSTO_VEICULO_CODIGO = "19"
CENTRO_CUSTO_VEICULO_NOME = "SWO7D00-CASE - 580N SERIE 2"


def _tabela_existe(inspector, tabela):
    return tabela in set(inspector.get_table_names())


def _colunas(inspector, tabela):
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def _buscar_centro_veiculo_id(conn):
    centro_id = conn.execute(
        sa.text(
            """
            SELECT id
              FROM centros_custo
             WHERE trim(coalesce(codigo, '')) = :codigo
               AND upper(trim(coalesce(nome, ''))) = upper(:nome)
             ORDER BY id
             LIMIT 1
            """
        ),
        {"codigo": CENTRO_CUSTO_VEICULO_CODIGO, "nome": CENTRO_CUSTO_VEICULO_NOME},
    ).scalar()

    if centro_id is None:
        raise RuntimeError(
            "Centro de custo de veiculo nao encontrado: "
            f"{CENTRO_CUSTO_VEICULO_CODIGO} - {CENTRO_CUSTO_VEICULO_NOME}."
        )

    return centro_id


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not _tabela_existe(inspector, "suprimentos_requisicoes_compra"):
        return
    if not _tabela_existe(inspector, "centros_custo"):
        return

    colunas = _colunas(inspector, "suprimentos_requisicoes_compra")
    if not {"numero", "sub_centro_custo_veiculo_id"}.issubset(colunas):
        return

    veiculo_id = _buscar_centro_veiculo_id(conn)

    conn.execute(
        sa.text(
            """
            UPDATE suprimentos_requisicoes_compra
               SET sub_centro_custo_veiculo_id = :veiculo_id
             WHERE numero = :numero
               AND coalesce(sub_centro_custo_veiculo_id, -1) != :veiculo_id
            """
        ),
        {"numero": REQUISICAO_NUMERO, "veiculo_id": veiculo_id},
    )


def downgrade():
    pass