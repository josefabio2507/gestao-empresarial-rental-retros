"""corrige epg para egp em textos e valores

Revision ID: b8c9d0e1f2a3
Revises: a15b2c3d4e6f
Create Date: 2026-08-23 15:40:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "b8c9d0e1f2a3"
down_revision = "a15b2c3d4e6f"
branch_labels = None
depends_on = None


TIPOS_VEICULO_EGP = "tipo in ('Veiculo leve', 'Caminhao', 'Maquina', 'Equipamento', 'EGP', 'Outro')"
TIPOS_VEICULO_EPG = "tipo in ('Veiculo leve', 'Caminhao', 'Maquina', 'Equipamento', 'EPG', 'Outro')"


def upgrade():
    with op.batch_alter_table("operacao_veiculos_equipamentos") as batch_op:
        batch_op.drop_constraint("ck_operacao_veiculos_tipo", type_="check")

    op.execute("UPDATE operacao_veiculos_equipamentos SET tipo = 'EGP' WHERE tipo = 'EPG'")
    op.execute("UPDATE centros_custo SET classe = 'CENTRO DE EGP VEÍCULOS' WHERE classe = 'CENTRO DE EPG VEÍCULOS'")
    op.execute(
        "UPDATE modulos SET nome = REPLACE(nome, 'EPGs', 'EGPs'), "
        "descricao = REPLACE(descricao, 'EPGs', 'EGPs') "
        "WHERE slug = 'gestao_veiculos_epgs'"
    )

    with op.batch_alter_table("operacao_veiculos_equipamentos") as batch_op:
        batch_op.create_check_constraint("ck_operacao_veiculos_tipo", TIPOS_VEICULO_EGP)


def downgrade():
    with op.batch_alter_table("operacao_veiculos_equipamentos") as batch_op:
        batch_op.drop_constraint("ck_operacao_veiculos_tipo", type_="check")

    op.execute("UPDATE operacao_veiculos_equipamentos SET tipo = 'EPG' WHERE tipo = 'EGP'")
    op.execute("UPDATE centros_custo SET classe = 'CENTRO DE EPG VEÍCULOS' WHERE classe = 'CENTRO DE EGP VEÍCULOS'")
    op.execute(
        "UPDATE modulos SET nome = REPLACE(nome, 'EGPs', 'EPGs'), "
        "descricao = REPLACE(descricao, 'EGPs', 'EPGs') "
        "WHERE slug = 'gestao_veiculos_epgs'"
    )

    with op.batch_alter_table("operacao_veiculos_equipamentos") as batch_op:
        batch_op.create_check_constraint("ck_operacao_veiculos_tipo", TIPOS_VEICULO_EPG)