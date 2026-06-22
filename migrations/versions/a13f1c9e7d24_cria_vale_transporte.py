"""cria vale transporte

Revision ID: a13f1c9e7d24
Revises: 6e1c9a4b2d7f
Create Date: 2026-06-22 00:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a13f1c9e7d24"
down_revision = "6e1c9a4b2d7f"
branch_labels = None
depends_on = None


MODULO_SLUG = "vale_transporte"


def _criar_modulo(bind, inspector):
    if "departamentos" not in inspector.get_table_names():
        return

    if "modulos" not in inspector.get_table_names():
        return

    departamento = bind.execute(
        sa.text(
            "SELECT id FROM departamentos "
            "WHERE slug = :slug_departamento "
            "LIMIT 1"
        ),
        {"slug_departamento": "departamento_pessoal"},
    ).fetchone()

    if not departamento:
        return

    modulo = bind.execute(
        sa.text(
            "SELECT id FROM modulos "
            "WHERE departamento_id = :departamento_id "
            "AND slug = :slug_modulo "
            "LIMIT 1"
        ),
        {
            "departamento_id": departamento.id,
            "slug_modulo": MODULO_SLUG,
        },
    ).fetchone()

    agora = datetime.utcnow()

    if modulo:
        bind.execute(
            sa.text(
                "UPDATE modulos "
                "SET nome = :nome, descricao = :descricao, ativo = :ativo, "
                "ordem = :ordem, atualizado_em = :atualizado_em "
                "WHERE id = :modulo_id"
            ),
            {
                "nome": "Vale Transporte",
                "descricao": "Cadastro de linhas e vínculos de Vale Transporte.",
                "ativo": True,
                "ordem": 25,
                "atualizado_em": agora,
                "modulo_id": modulo.id,
            },
        )
        return

    bind.execute(
        sa.text(
            "INSERT INTO modulos "
            "(departamento_id, nome, slug, descricao, ativo, ordem, criado_em, atualizado_em) "
            "VALUES "
            "(:departamento_id, :nome, :slug, :descricao, :ativo, :ordem, :criado_em, :atualizado_em)"
        ),
        {
            "departamento_id": departamento.id,
            "nome": "Vale Transporte",
            "slug": MODULO_SLUG,
            "descricao": "Cadastro de linhas e vínculos de Vale Transporte.",
            "ativo": True,
            "ordem": 25,
            "criado_em": agora,
            "atualizado_em": agora,
        },
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "colaboradores" in tabelas:
        colunas_colaboradores = {
            coluna["name"]
            for coluna in inspector.get_columns("colaboradores")
        }

        if "vale_transporte_optante" not in colunas_colaboradores:
            op.add_column(
                "colaboradores",
                sa.Column(
                    "vale_transporte_optante",
                    sa.Boolean(),
                    server_default=sa.false(),
                    nullable=False,
                ),
            )

    if "linhas_onibus" not in tabelas:
        op.create_table(
            "linhas_onibus",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=150), nullable=False),
            sa.Column("codigo", sa.String(length=60), nullable=True),
            sa.Column("empresa_transporte", sa.String(length=150), nullable=False),
            sa.Column("valor_tarifa_dia", sa.Numeric(10, 2), nullable=False),
            sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column(
                "criado_em",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "atualizado_em",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "valor_tarifa_dia > 0",
                name="ck_linhas_onibus_valor_tarifa_dia_positivo",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "vale_transporte_colaborador_linhas" not in tabelas:
        op.create_table(
            "vale_transporte_colaborador_linhas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("colaborador_id", sa.Integer(), nullable=False),
            sa.Column("linha_onibus_id", sa.Integer(), nullable=False),
            sa.Column("tipo_pagamento", sa.String(length=30), nullable=False),
            sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column(
                "criado_em",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "atualizado_em",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "tipo_pagamento in ('dinheiro', 'cartao_transporte')",
                name="ck_vale_transporte_tipo_pagamento",
            ),
            sa.ForeignKeyConstraint(
                ["colaborador_id"],
                ["colaboradores.id"],
                name="fk_vale_transporte_colaborador_linhas_colaborador_id",
            ),
            sa.ForeignKeyConstraint(
                ["linha_onibus_id"],
                ["linhas_onibus.id"],
                name="fk_vale_transporte_colaborador_linhas_linha_onibus_id",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)

    if "vale_transporte_colaborador_linhas" in inspector.get_table_names():
        indices_vinculos = {
            indice["name"]
            for indice in inspector.get_indexes("vale_transporte_colaborador_linhas")
        }

        if "ix_vale_transporte_colaborador_linhas_colaborador_id" not in indices_vinculos:
            op.create_index(
                "ix_vale_transporte_colaborador_linhas_colaborador_id",
                "vale_transporte_colaborador_linhas",
                ["colaborador_id"],
                unique=False,
            )

        if "ix_vale_transporte_colaborador_linhas_linha_onibus_id" not in indices_vinculos:
            op.create_index(
                "ix_vale_transporte_colaborador_linhas_linha_onibus_id",
                "vale_transporte_colaborador_linhas",
                ["linha_onibus_id"],
                unique=False,
            )

    _criar_modulo(bind, sa.inspect(bind))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "modulos" in tabelas:
        bind.execute(
            sa.text("DELETE FROM modulos WHERE slug = :slug_modulo"),
            {"slug_modulo": MODULO_SLUG},
        )

    if "vale_transporte_colaborador_linhas" in tabelas:
        op.drop_table("vale_transporte_colaborador_linhas")

    if "linhas_onibus" in tabelas:
        op.drop_table("linhas_onibus")

    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "colaboradores" in tabelas:
        colunas_colaboradores = {
            coluna["name"]
            for coluna in inspector.get_columns("colaboradores")
        }

        if "vale_transporte_optante" in colunas_colaboradores:
            op.drop_column("colaboradores", "vale_transporte_optante")
