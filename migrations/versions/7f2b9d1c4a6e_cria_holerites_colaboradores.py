"""cria holerites colaboradores

Revision ID: 7f2b9d1c4a6e
Revises: c69fb487ba1b
Create Date: 2026-05-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7f2b9d1c4a6e"
down_revision = "c69fb487ba1b"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "holerites_colaboradores" not in tabelas:
        op.create_table(
            "holerites_colaboradores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("colaborador_id", sa.Integer(), nullable=False),
            sa.Column("competencia", sa.String(length=7), nullable=False),
            sa.Column("tipo", sa.String(length=80), nullable=False),
            sa.Column("nome_arquivo", sa.String(length=255), nullable=False),
            sa.Column("origem_arquivo", sa.String(length=50), nullable=True),
            sa.Column("google_drive_file_id", sa.String(length=255), nullable=True),
            sa.Column("google_drive_url", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ["colaborador_id"],
                ["colaboradores.id"],
                name="fk_holerites_colaboradores_colaborador_id",
            ),
            sa.ForeignKeyConstraint(
                ["criado_por_usuario_id"],
                ["usuarios.id"],
                name="fk_holerites_colaboradores_criado_por_usuario_id",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    indices = {
        indice["name"]
        for indice in inspector.get_indexes("holerites_colaboradores")
    }

    indices_necessarios = [
        (
            "ix_holerites_colaboradores_colaborador_id",
            ["colaborador_id"],
        ),
        (
            "ix_holerites_colaboradores_competencia",
            ["competencia"],
        ),
        (
            "ix_holerites_colaboradores_ativo",
            ["ativo"],
        ),
        (
            "ix_holerites_colaboradores_criado_por_usuario_id",
            ["criado_por_usuario_id"],
        ),
    ]

    for nome_indice, colunas in indices_necessarios:
        if nome_indice not in indices:
            op.create_index(
                nome_indice,
                "holerites_colaboradores",
                colunas,
                unique=False,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "holerites_colaboradores" in inspector.get_table_names():
        op.drop_table("holerites_colaboradores")
