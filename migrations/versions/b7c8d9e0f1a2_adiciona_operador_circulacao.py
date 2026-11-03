"""Adiciona o operador CCP ou maquinista à circulação de trens."""

from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "ad3e4f5a6b7c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("operacao_circulacao_trens") as batch:
        batch.add_column(sa.Column("operador_ccp_maquinista", sa.String(length=160), nullable=True))


def downgrade():
    with op.batch_alter_table("operacao_circulacao_trens") as batch:
        batch.drop_column("operador_ccp_maquinista")
