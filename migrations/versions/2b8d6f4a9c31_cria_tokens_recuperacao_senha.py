"""cria tokens recuperacao senha

Revision ID: 2b8d6f4a9c31
Revises: 1a701f39c288
Create Date: 2026-05-05 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b8d6f4a9c31'
down_revision = '1a701f39c288'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = inspector.get_table_names()

    if "tokens_recuperacao_senha" not in tabelas:
        op.create_table(
            "tokens_recuperacao_senha",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("usuario_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expira_em", sa.DateTime(), nullable=False),
            sa.Column("usado_em", sa.DateTime(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.Column("ip_solicitacao", sa.String(length=80), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    indices = {
        indice["name"]
        for indice in inspector.get_indexes("tokens_recuperacao_senha")
    }

    if "ix_tokens_recuperacao_senha_usuario_id" not in indices:
        op.create_index(
            "ix_tokens_recuperacao_senha_usuario_id",
            "tokens_recuperacao_senha",
            ["usuario_id"],
            unique=False,
        )

    if "ix_tokens_recuperacao_senha_token_hash" not in indices:
        op.create_index(
            "ix_tokens_recuperacao_senha_token_hash",
            "tokens_recuperacao_senha",
            ["token_hash"],
            unique=True,
        )

    if "ix_tokens_recuperacao_senha_expira_em" not in indices:
        op.create_index(
            "ix_tokens_recuperacao_senha_expira_em",
            "tokens_recuperacao_senha",
            ["expira_em"],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "tokens_recuperacao_senha" in inspector.get_table_names():
        op.drop_table("tokens_recuperacao_senha")
