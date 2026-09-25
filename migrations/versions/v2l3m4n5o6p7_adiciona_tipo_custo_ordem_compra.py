"""Adiciona tipo de custo nas ordens de compra.

Revision ID: v2l3m4n5o6p7
Revises: u1k2l3m4n5o6
"""

from alembic import op
import sqlalchemy as sa


revision = "v2l3m4n5o6p7"
down_revision = "u1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("suprimentos_ordens_compra") as batch_op:
        batch_op.add_column(sa.Column("tipo_custo", sa.String(length=20), nullable=True))
        batch_op.create_check_constraint(
            "ck_suprimentos_ordens_compra_tipo_custo",
            "tipo_custo IS NULL OR tipo_custo IN ('Abastecimento', 'Diversos', 'Manutenção')",
        )

    op.execute(
        """
        UPDATE suprimentos_ordens_compra
           SET tipo_custo = (
               SELECT requisicao.tipo_custo
                 FROM suprimentos_requisicoes_compra AS requisicao
                WHERE requisicao.id = suprimentos_ordens_compra.requisicao_id
                  AND requisicao.sub_centro_custo_veiculo_id IS NOT NULL
           )
         WHERE EXISTS (
               SELECT 1
                 FROM suprimentos_requisicoes_compra AS requisicao
                WHERE requisicao.id = suprimentos_ordens_compra.requisicao_id
                  AND requisicao.sub_centro_custo_veiculo_id IS NOT NULL
                  AND requisicao.tipo_custo IS NOT NULL
           )
        """
    )


def downgrade():
    with op.batch_alter_table("suprimentos_ordens_compra") as batch_op:
        batch_op.drop_constraint("ck_suprimentos_ordens_compra_tipo_custo", type_="check")
        batch_op.drop_column("tipo_custo")
