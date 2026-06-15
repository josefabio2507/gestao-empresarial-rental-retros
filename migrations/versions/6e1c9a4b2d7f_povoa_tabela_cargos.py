"""povoa tabela cargos

Revision ID: 6e1c9a4b2d7f
Revises: 4d8a2f6c1b7e
Create Date: 2026-06-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6e1c9a4b2d7f"
down_revision = "4d8a2f6c1b7e"
branch_labels = None
depends_on = None


CARGOS = (
    "ALMOXARIFE",
    "AUXILIAR ADMINISTRATIVO",
    "AUXILIAR GERAL",
    "ENCARREGADO DE VIAS",
    "GERENTE ADMINIST.",
    "MECANICO",
    "OPERADOR DE MAQUINAS",
    "OPERADOR DE MAQUINAS LEVES",
    "SUPERVISOR",
    "TECNICO SEGURANCA DO TRABALHO",
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "cargos" not in inspector.get_table_names():
        op.create_table(
            "cargos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=120), nullable=False),
            sa.Column(
                "ativo",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            ),
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
            sa.PrimaryKeyConstraint("id"),
        )

    buscar_cargo = sa.text(
        "SELECT id FROM cargos "
        "WHERE lower(trim(nome)) = lower(:nome) "
        "LIMIT 1"
    )
    inserir_cargo = sa.text(
        "INSERT INTO cargos (nome, ativo) "
        "VALUES (:nome, :ativo)"
    )

    for nome in CARGOS:
        cargo_existente = bind.execute(
            buscar_cargo,
            {"nome": nome},
        ).fetchone()

        if not cargo_existente:
            bind.execute(
                inserir_cargo,
                {
                    "nome": nome,
                    "ativo": True,
                },
            )


def downgrade():
    # Cargos são dados administrativos e não devem ser excluídos fisicamente.
    pass
