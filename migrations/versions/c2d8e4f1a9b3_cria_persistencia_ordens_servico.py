"""Cria persistência relacional do módulo de Ordens de Serviço.

Revision ID: c2d8e4f1a9b3
Revises: a1b2c3d4e5f6
Create Date: 2026-10-18 18:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c2d8e4f1a9b3"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "operacao_ordens_servico",
        sa.Column("id_os_interno", sa.String(length=36), nullable=False),
        sa.Column("codigo_os_rental", sa.String(length=60), nullable=False),
        sa.Column("numero_os_cliente", sa.String(length=80), nullable=True),
        sa.Column("local", sa.String(length=255), nullable=False),
        sa.Column("equipe", sa.String(length=120), nullable=False),
        sa.Column("data_programada_inicial", sa.Date(), nullable=False),
        sa.Column("data_programada_final", sa.Date(), nullable=False),
        sa.Column("data_inicial", sa.Date(), nullable=True),
        sa.Column("data_final", sa.Date(), nullable=True),
        sa.Column("trabalho_previsto", sa.Text(), nullable=True),
        sa.Column("supervisor", sa.String(length=150), nullable=True),
        sa.Column("encarregado", sa.String(length=150), nullable=True),
        sa.Column("status_identificacao", sa.String(length=20), nullable=False),
        sa.Column("status_operacional", sa.String(length=40), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("data_programada_final >= data_programada_inicial", name="ck_operacao_os_periodo_programado"),
        sa.CheckConstraint("status_identificacao in ('Pendente', 'Informado')", name="ck_operacao_os_status_identificacao"),
        sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id_os_interno"),
        sa.UniqueConstraint("codigo_os_rental"),
    )
    op.create_index(op.f("ix_operacao_ordens_servico_codigo_os_rental"), "operacao_ordens_servico", ["codigo_os_rental"], unique=True)
    op.create_index(op.f("ix_operacao_ordens_servico_numero_os_cliente"), "operacao_ordens_servico", ["numero_os_cliente"], unique=False)
    op.create_index(op.f("ix_operacao_ordens_servico_data_programada_inicial"), "operacao_ordens_servico", ["data_programada_inicial"], unique=False)
    op.create_index(op.f("ix_operacao_ordens_servico_data_programada_final"), "operacao_ordens_servico", ["data_programada_final"], unique=False)
    op.create_index(op.f("ix_operacao_ordens_servico_status_identificacao"), "operacao_ordens_servico", ["status_identificacao"], unique=False)
    op.create_index(op.f("ix_operacao_ordens_servico_status_operacional"), "operacao_ordens_servico", ["status_operacional"], unique=False)
    op.create_index(op.f("ix_operacao_ordens_servico_criado_por_usuario_id"), "operacao_ordens_servico", ["criado_por_usuario_id"], unique=False)
    op.create_index(op.f("ix_operacao_ordens_servico_atualizado_por_usuario_id"), "operacao_ordens_servico", ["atualizado_por_usuario_id"], unique=False)

    op.create_table(
        "operacao_apontamentos_diarios",
        sa.Column("id_apontamento_diario", sa.String(length=36), nullable=False),
        sa.Column("id_os_interno", sa.String(length=36), nullable=False),
        sa.Column("data_evento", sa.Date(), nullable=False),
        sa.Column("equipe", sa.String(length=120), nullable=False),
        sa.Column("criado_por_usuario_id", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["id_os_interno"], ["operacao_ordens_servico.id_os_interno"]),
        sa.PrimaryKeyConstraint("id_apontamento_diario"),
    )
    op.create_index(op.f("ix_operacao_apontamentos_diarios_id_os_interno"), "operacao_apontamentos_diarios", ["id_os_interno"], unique=False)
    op.create_index(op.f("ix_operacao_apontamentos_diarios_data_evento"), "operacao_apontamentos_diarios", ["data_evento"], unique=False)
    op.create_index(op.f("ix_operacao_apontamentos_diarios_criado_por_usuario_id"), "operacao_apontamentos_diarios", ["criado_por_usuario_id"], unique=False)

    op.create_table(
        "operacao_diarios_localizacao",
        sa.Column("id_apontamento_diario", sa.String(length=36), nullable=False),
        sa.Column("encarregado", sa.String(length=150), nullable=False),
        sa.Column("chefe_boletim", sa.String(length=180), nullable=False),
        sa.Column("local", sa.String(length=255), nullable=False),
        sa.Column("numero_amv", sa.String(length=80), nullable=True),
        sa.Column("sub", sa.String(length=80), nullable=True),
        sa.Column("km_inicio", sa.String(length=40), nullable=True),
        sa.Column("km_fim", sa.String(length=40), nullable=True),
        sa.Column("intervalo_inicio", sa.Time(), nullable=True),
        sa.Column("intervalo_fim", sa.Time(), nullable=True),
        sa.Column("pedido_liberacao_ccp", sa.Time(), nullable=True),
        sa.Column("liberacao_embandeiramento", sa.Time(), nullable=True),
        sa.Column("termino_embandeiramento", sa.Time(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["id_apontamento_diario"], ["operacao_apontamentos_diarios.id_apontamento_diario"]),
        sa.PrimaryKeyConstraint("id_apontamento_diario"),
    )
    op.create_table(
        "operacao_diarios_servico",
        sa.Column("id_apontamento_diario", sa.String(length=36), nullable=False),
        sa.Column("servico", sa.Text(), nullable=False),
        sa.Column("quantidade", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.CheckConstraint("quantidade > 0", name="ck_operacao_diario_servico_quantidade"),
        sa.ForeignKeyConstraint(["id_apontamento_diario"], ["operacao_apontamentos_diarios.id_apontamento_diario"]),
        sa.PrimaryKeyConstraint("id_apontamento_diario"),
    )
    op.create_table(
        "operacao_diarios_material",
        sa.Column("id_apontamento_diario", sa.String(length=36), nullable=False),
        sa.Column("tipo_material", sa.String(length=20), nullable=False),
        sa.Column("material_aplicado", sa.String(length=255), nullable=False),
        sa.Column("quantidade", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.CheckConstraint("quantidade > 0", name="ck_operacao_diario_material_quantidade"),
        sa.CheckConstraint("tipo_material in ('NOVO', 'RECUPERADO')", name="ck_operacao_diario_material_tipo"),
        sa.ForeignKeyConstraint(["id_apontamento_diario"], ["operacao_apontamentos_diarios.id_apontamento_diario"]),
        sa.PrimaryKeyConstraint("id_apontamento_diario"),
    )
    op.create_table(
        "operacao_circulacao_trens",
        sa.Column("id_apontamento_diario", sa.String(length=36), nullable=False),
        sa.Column("prefixo", sa.String(length=80), nullable=True),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fim", sa.Time(), nullable=True),
        sa.Column("via_linha", sa.String(length=160), nullable=True),
        sa.Column("tempo_interrompido", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["id_apontamento_diario"], ["operacao_apontamentos_diarios.id_apontamento_diario"]),
        sa.PrimaryKeyConstraint("id_apontamento_diario"),
    )
    op.create_table(
        "operacao_intervencoes_adversas",
        sa.Column("id_apontamento_diario", sa.String(length=36), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fim", sa.Time(), nullable=True),
        sa.Column("tempo_total", sa.String(length=40), nullable=True),
        sa.Column("intervencao", sa.Text(), nullable=True),
        sa.Column("categoria", sa.String(length=160), nullable=True),
        sa.ForeignKeyConstraint(["id_apontamento_diario"], ["operacao_apontamentos_diarios.id_apontamento_diario"]),
        sa.PrimaryKeyConstraint("id_apontamento_diario"),
    )


def downgrade():
    op.drop_table("operacao_intervencoes_adversas")
    op.drop_table("operacao_circulacao_trens")
    op.drop_table("operacao_diarios_material")
    op.drop_table("operacao_diarios_servico")
    op.drop_table("operacao_diarios_localizacao")
    op.drop_index(op.f("ix_operacao_apontamentos_diarios_criado_por_usuario_id"), table_name="operacao_apontamentos_diarios")
    op.drop_index(op.f("ix_operacao_apontamentos_diarios_data_evento"), table_name="operacao_apontamentos_diarios")
    op.drop_index(op.f("ix_operacao_apontamentos_diarios_id_os_interno"), table_name="operacao_apontamentos_diarios")
    op.drop_table("operacao_apontamentos_diarios")
    op.drop_index(op.f("ix_operacao_ordens_servico_atualizado_por_usuario_id"), table_name="operacao_ordens_servico")
    op.drop_index(op.f("ix_operacao_ordens_servico_criado_por_usuario_id"), table_name="operacao_ordens_servico")
    op.drop_index(op.f("ix_operacao_ordens_servico_status_operacional"), table_name="operacao_ordens_servico")
    op.drop_index(op.f("ix_operacao_ordens_servico_status_identificacao"), table_name="operacao_ordens_servico")
    op.drop_index(op.f("ix_operacao_ordens_servico_data_programada_final"), table_name="operacao_ordens_servico")
    op.drop_index(op.f("ix_operacao_ordens_servico_data_programada_inicial"), table_name="operacao_ordens_servico")
    op.drop_index(op.f("ix_operacao_ordens_servico_numero_os_cliente"), table_name="operacao_ordens_servico")
    op.drop_index(op.f("ix_operacao_ordens_servico_codigo_os_rental"), table_name="operacao_ordens_servico")
    op.drop_table("operacao_ordens_servico")
