"""Adiciona aprova��o ao controle de f�rias."""

from alembic import op
import sqlalchemy as sa


revision = "e7f8a9b0c1d2"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existentes = {col["name"] for col in sa.inspect(bind).get_columns("ferias_colaboradores")}
    if "aprovacao_status" not in existentes:
        op.add_column("ferias_colaboradores", sa.Column("aprovacao_status", sa.String(length=20), nullable=False, server_default="pendente"))
    if "aprovado_por_usuario_id" not in existentes:
        op.add_column("ferias_colaboradores", sa.Column("aprovado_por_usuario_id", sa.Integer(), nullable=True))
    if "aprovado_em" not in existentes:
        op.add_column("ferias_colaboradores", sa.Column("aprovado_em", sa.DateTime(), nullable=True))
    if "motivo_reprovacao" not in existentes:
        op.add_column("ferias_colaboradores", sa.Column("motivo_reprovacao", sa.Text(), nullable=True))
    op.create_index("ix_ferias_colaboradores_aprovacao_status", "ferias_colaboradores", ["aprovacao_status"])


def downgrade():
    op.drop_index("ix_ferias_colaboradores_aprovacao_status", table_name="ferias_colaboradores")
    with op.batch_alter_table("ferias_colaboradores") as batch_op:
        batch_op.drop_column("motivo_reprovacao")
        batch_op.drop_column("aprovado_em")
        batch_op.drop_column("aprovado_por_usuario_id")
        batch_op.drop_column("aprovacao_status")
