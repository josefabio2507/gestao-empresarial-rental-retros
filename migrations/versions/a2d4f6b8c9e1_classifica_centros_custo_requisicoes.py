"""classifica centros custo requisicoes

Revision ID: a2d4f6b8c9e1
Revises: f15a1c9e0b7d
Create Date: 2026-08-14 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a2d4f6b8c9e1"
down_revision = "f15a1c9e0b7d"
branch_labels = None
depends_on = None


CLASSE_CENTRO_CUSTO = "CENTRO DE CUSTO"
CLASSE_CENTRO_CUSTO_EQUIPES = "CENTRO DE CUSTO EQUIPES"


def _colunas(inspector, tabela):
    return {coluna["name"] for coluna in inspector.get_columns(tabela)}


def _indices(inspector, tabela):
    return {indice["name"] for indice in inspector.get_indexes(tabela)}


def _adicionar_colunas_centros_custo(inspector):
    colunas = _colunas(inspector, "centros_custo")

    with op.batch_alter_table("centros_custo") as batch_op:
        if "classe" not in colunas:
            batch_op.add_column(
                sa.Column(
                    "classe",
                    sa.String(length=40),
                    nullable=False,
                    server_default=CLASSE_CENTRO_CUSTO,
                )
            )

    indices = _indices(sa.inspect(op.get_bind()), "centros_custo")
    if "ix_centros_custo_classe" not in indices:
        op.create_index("ix_centros_custo_classe", "centros_custo", ["classe"])


def _adicionar_colunas_requisicoes(inspector):
    colunas = _colunas(inspector, "suprimentos_requisicoes_compra")

    with op.batch_alter_table("suprimentos_requisicoes_compra") as batch_op:
        if "sub_centro_custo_equipe_id" not in colunas:
            batch_op.add_column(sa.Column("sub_centro_custo_equipe_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_suprimentos_requisicoes_compra_sub_centro_custo_equipe_id",
                "centros_custo",
                ["sub_centro_custo_equipe_id"],
                ["id"],
            )
        if "sub_centro_custo_veiculo_id" not in colunas:
            batch_op.add_column(sa.Column("sub_centro_custo_veiculo_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_suprimentos_requisicoes_compra_sub_centro_custo_veiculo_id",
                "centros_custo",
                ["sub_centro_custo_veiculo_id"],
                ["id"],
            )

    indices = _indices(sa.inspect(op.get_bind()), "suprimentos_requisicoes_compra")
    if "ix_suprimentos_requisicoes_compra_sub_centro_custo_equipe_id" not in indices:
        op.create_index(
            "ix_suprimentos_requisicoes_compra_sub_centro_custo_equipe_id",
            "suprimentos_requisicoes_compra",
            ["sub_centro_custo_equipe_id"],
        )
    if "ix_suprimentos_requisicoes_compra_sub_centro_custo_veiculo_id" not in indices:
        op.create_index(
            "ix_suprimentos_requisicoes_compra_sub_centro_custo_veiculo_id",
            "suprimentos_requisicoes_compra",
            ["sub_centro_custo_veiculo_id"],
        )


def _classificar_centros_custo(conn):
    centros_base = (
        "SETOR-ADMINISTRAÇÃO",
        "SETOR-ADMINISTRACAO",
        "SETOR-OFICINA",
        "SETOR-OPERAÇÃO",
        "SETOR-OPERACAO",
        "SETOR-SEGURANÇA DO TRABALHO",
        "SETOR-SEGURANCA DO TRABALHO",
    )
    parametros = {f"nome_{indice}": nome for indice, nome in enumerate(centros_base)}
    lista_parametros = ", ".join(f":nome_{indice}" for indice in range(len(centros_base)))

    conn.execute(
        sa.text(
            f"""
            UPDATE centros_custo
               SET classe = CASE
                   WHEN upper(trim(nome)) IN ({lista_parametros})
                     OR trim(coalesce(codigo, '')) IN ('08', '09', '10', '11')
                   THEN :classe_centro
                   ELSE :classe_equipes
               END
             WHERE classe IS NULL
                OR classe = ''
                OR classe = :classe_centro
            """
        ),
        {
            **parametros,
            "classe_centro": CLASSE_CENTRO_CUSTO,
            "classe_equipes": CLASSE_CENTRO_CUSTO_EQUIPES,
        },
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "centros_custo" in tabelas:
        _adicionar_colunas_centros_custo(inspector)
        _classificar_centros_custo(bind)

    if "suprimentos_requisicoes_compra" in tabelas and "centros_custo" in tabelas:
        _adicionar_colunas_requisicoes(sa.inspect(bind))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if "suprimentos_requisicoes_compra" in tabelas:
        colunas = _colunas(inspector, "suprimentos_requisicoes_compra")
        indices = _indices(inspector, "suprimentos_requisicoes_compra")

        if "ix_suprimentos_requisicoes_compra_sub_centro_custo_veiculo_id" in indices:
            op.drop_index(
                "ix_suprimentos_requisicoes_compra_sub_centro_custo_veiculo_id",
                table_name="suprimentos_requisicoes_compra",
            )
        if "ix_suprimentos_requisicoes_compra_sub_centro_custo_equipe_id" in indices:
            op.drop_index(
                "ix_suprimentos_requisicoes_compra_sub_centro_custo_equipe_id",
                table_name="suprimentos_requisicoes_compra",
            )

        with op.batch_alter_table("suprimentos_requisicoes_compra") as batch_op:
            if "sub_centro_custo_veiculo_id" in colunas:
                batch_op.drop_constraint(
                    "fk_suprimentos_requisicoes_compra_sub_centro_custo_veiculo_id",
                    type_="foreignkey",
                )
                batch_op.drop_column("sub_centro_custo_veiculo_id")
            if "sub_centro_custo_equipe_id" in colunas:
                batch_op.drop_constraint(
                    "fk_suprimentos_requisicoes_compra_sub_centro_custo_equipe_id",
                    type_="foreignkey",
                )
                batch_op.drop_column("sub_centro_custo_equipe_id")

    if "centros_custo" in tabelas:
        colunas = _colunas(inspector, "centros_custo")
        indices = _indices(inspector, "centros_custo")

        if "ix_centros_custo_classe" in indices:
            op.drop_index("ix_centros_custo_classe", table_name="centros_custo")

        with op.batch_alter_table("centros_custo") as batch_op:
            if "classe" in colunas:
                batch_op.drop_column("classe")
