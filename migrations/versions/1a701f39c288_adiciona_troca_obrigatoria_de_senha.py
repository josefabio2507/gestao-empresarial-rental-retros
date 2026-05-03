"""adiciona troca obrigatoria de senha

Revision ID: 1a701f39c288
Revises: ea31abfc7d31
Create Date: 2026-05-02 17:17:18.076753

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a701f39c288'
down_revision = 'ea31abfc7d31'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [coluna["name"] for coluna in inspector.get_columns("usuarios")]

    if "precisa_trocar_senha" not in colunas:
        op.add_column(
            "usuarios",
            sa.Column(
                "precisa_trocar_senha",
                sa.Boolean(),
                nullable=True,
                server_default=sa.true()
            )
        )

    op.execute(
        "UPDATE usuarios SET precisa_trocar_senha = 1 WHERE precisa_trocar_senha IS NULL"
    )

    if bind.dialect.name != "sqlite":
        op.alter_column(
            "usuarios",
            "precisa_trocar_senha",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None
        )

    # ### end Alembic commands ###


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = [coluna["name"] for coluna in inspector.get_columns("usuarios")]

    if "precisa_trocar_senha" in colunas:
        op.drop_column("usuarios", "precisa_trocar_senha")

    # ### end Alembic commands ###
