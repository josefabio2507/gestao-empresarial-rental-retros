"""corrige subcentros requisicoes producao

Revision ID: b6c8e1f4a9d2
Revises: a2d4f6b8c9e1
Create Date: 2026-08-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b6c8e1f4a9d2"
down_revision = "a2d4f6b8c9e1"
branch_labels = None
depends_on = None


AJUSTES_REQUISICOES = (
    ("RC-2026-0003", "04", None),
    ("RC-2026-0005", "02", "26"),
    ("RC-2026-0012", None, "29"),
    ("RC-2026-0013", "03", "14"),
    ("RC-2026-0014", "06", "35"),
    ("RC-2026-0016", "02", "19"),
    ("RC-2026-0017", None, "29"),
    ("RC-2026-0018", "06", None),
    ("RC-2026-0019", None, "32"),
    ("RC-2026-0022", None, "32"),
    ("RC-2026-0023", "06", None),
    ("RC-2026-0025", "04", None),
)


def _colunas(inspector, tabela):
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def _buscar_centro_id(conn, codigo):
    if not codigo:
        return None

    centro_id = conn.execute(
        sa.text(
            """
            SELECT id
              FROM centros_custo
             WHERE trim(coalesce(codigo, '')) = :codigo
             ORDER BY id
             LIMIT 1
            """
        ),
        {"codigo": codigo},
    ).scalar()

    if centro_id is None:
        raise RuntimeError(f"Centro de custo com codigo {codigo} nao encontrado.")

    return centro_id


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tabelas = set(inspector.get_table_names())

    if "suprimentos_requisicoes_compra" not in tabelas or "centros_custo" not in tabelas:
        return

    colunas = _colunas(inspector, "suprimentos_requisicoes_compra")
    colunas_obrigatorias = {
        "numero",
        "sub_centro_custo_equipe_id",
        "sub_centro_custo_veiculo_id",
    }
    if not colunas_obrigatorias.issubset(colunas):
        return

    limpar_equipe_legada = "equipe_id" in colunas
    limpar_veiculo_legado = "veiculo_placa" in colunas

    for numero, codigo_equipe, codigo_veiculo in AJUSTES_REQUISICOES:
        equipe_id = _buscar_centro_id(conn, codigo_equipe)
        veiculo_id = _buscar_centro_id(conn, codigo_veiculo)

        valores = {
            "numero": numero,
            "equipe_id": equipe_id,
            "veiculo_id": veiculo_id,
        }
        sets = [
            "sub_centro_custo_equipe_id = :equipe_id",
            "sub_centro_custo_veiculo_id = :veiculo_id",
        ]

        if limpar_equipe_legada:
            sets.append("equipe_id = NULL")
        if limpar_veiculo_legado:
            sets.append("veiculo_placa = NULL")

        conn.execute(
            sa.text(
                f"""
                UPDATE suprimentos_requisicoes_compra
                   SET {", ".join(sets)}
                 WHERE numero = :numero
                   AND (
                        coalesce(sub_centro_custo_equipe_id, -1) != coalesce(:equipe_id, -1)
                     OR coalesce(sub_centro_custo_veiculo_id, -1) != coalesce(:veiculo_id, -1)
                     { "OR equipe_id IS NOT NULL" if limpar_equipe_legada else "" }
                     { "OR veiculo_placa IS NOT NULL" if limpar_veiculo_legado else "" }
                   )
                """
            ),
            valores,
        )


def downgrade():
    pass
