"""cria integracoes BR Mobilidade para pedidos de vale transporte

Revision ID: z6p7q8r9s0t1
Revises: y5o6p7q8r9s0
"""

from alembic import op
import sqlalchemy as sa


revision = "z6p7q8r9s0t1"
down_revision = "y5o6p7q8r9s0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vale_transporte_integracoes_br_mobilidade",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("chave_idempotencia", sa.String(64), nullable=False),
        sa.Column("ambiente", sa.String(20), nullable=False),
        sa.Column("data_liberacao", sa.Date(), nullable=False),
        sa.Column("quantidade_colaboradores", sa.Integer(), nullable=False),
        sa.Column("valor_creditos", sa.Numeric(12, 2), nullable=False),
        sa.Column("nome_arquivo", sa.String(180), nullable=False),
        sa.Column("hash_arquivo", sa.String(64), nullable=False),
        sa.Column("arquivo_conteudo", sa.LargeBinary(), nullable=False),
        sa.Column("status_interno", sa.String(30), nullable=False),
        sa.Column("status_portal", sa.String(100), nullable=True),
        sa.Column("comentario_portal", sa.Text(), nullable=True),
        sa.Column("erros_portal", sa.Text(), nullable=True),
        sa.Column("erro_etapa", sa.String(60), nullable=True),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.Column("enviado_em", sa.DateTime(), nullable=True),
        sa.Column("consultado_em", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["pedido_id"], ["vale_transporte_pedidos.id"]),
        sa.ForeignKeyConstraint(["criado_por_id"], ["usuarios.id"]),
        sa.UniqueConstraint("chave_idempotencia", name="uq_vt_br_integracao_idempotencia"),
        sa.CheckConstraint(
            "status_interno in ('AGUARDANDO_ENVIO', 'ENVIANDO', 'AGUARDANDO_STATUS', "
            "'IMPORTADO', 'ERRO_IMPORTACAO', 'ERRO_ENVIO')",
            name="ck_vt_br_integracao_status",
        ),
        sa.CheckConstraint(
            "ambiente in ('local', 'producao')",
            name="ck_vt_br_integracao_ambiente",
        ),
    )
    op.create_index(
        "ix_vt_br_integracao_pedido_id",
        "vale_transporte_integracoes_br_mobilidade",
        ["pedido_id"],
    )
    op.create_index(
        "ix_vt_br_integracao_status_interno",
        "vale_transporte_integracoes_br_mobilidade",
        ["status_interno"],
    )


def downgrade():
    op.drop_table("vale_transporte_integracoes_br_mobilidade")
