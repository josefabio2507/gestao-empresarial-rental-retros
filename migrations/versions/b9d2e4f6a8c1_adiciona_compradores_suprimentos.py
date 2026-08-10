"""adiciona compradores suprimentos

Revision ID: b9d2e4f6a8c1
Revises: a8c1d2e3f4b5
Create Date: 2026-08-10 00:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "b9d2e4f6a8c1"
down_revision = "a8c1d2e3f4b5"
branch_labels = None
depends_on = None


def _criar_ou_atualizar_modulo(bind, departamento_id):
    modulos = sa.table(
        "modulos",
        sa.column("id", sa.Integer()),
        sa.column("departamento_id", sa.Integer()),
        sa.column("nome", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("descricao", sa.Text()),
        sa.column("ativo", sa.Boolean()),
        sa.column("ordem", sa.Integer()),
        sa.column("criado_em", sa.DateTime()),
        sa.column("atualizado_em", sa.DateTime()),
    )
    agora = datetime.utcnow()
    existente = bind.execute(
        sa.select(modulos.c.id).where(
            modulos.c.departamento_id == departamento_id,
            modulos.c.slug == "compradores",
        )
    ).first()

    dados = {
        "nome": "Compradores",
        "descricao": "Cadastro de compradores para envio de requisicoes por WhatsApp",
        "ativo": True,
        "ordem": 13,
        "atualizado_em": agora,
    }

    if existente:
        bind.execute(modulos.update().where(modulos.c.id == existente.id).values(**dados))
        return

    bind.execute(
        modulos.insert().values(
            departamento_id=departamento_id,
            slug="compradores",
            criado_em=agora,
            **dados,
        )
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_compradores" not in inspector.get_table_names():
        op.create_table(
            "suprimentos_compradores",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("usuario_comprador_id", sa.Integer(), nullable=True),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("telefone_whatsapp", sa.String(20), nullable=False),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["centro_custo_id"], ["centros_custo.id"]),
            sa.ForeignKeyConstraint(["usuario_comprador_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_suprimentos_compradores_usuario_comprador_id",
            "suprimentos_compradores",
            ["usuario_comprador_id"],
        )
        op.create_index(
            "ix_suprimentos_compradores_centro_custo_id",
            "suprimentos_compradores",
            ["centro_custo_id"],
        )
        op.create_index("ix_suprimentos_compradores_ativo", "suprimentos_compradores", ["ativo"])

    if "departamentos" in inspector.get_table_names() and "modulos" in inspector.get_table_names():
        departamentos = sa.table(
            "departamentos",
            sa.column("id", sa.Integer()),
            sa.column("slug", sa.String()),
        )
        departamento = bind.execute(
            sa.select(departamentos.c.id).where(departamentos.c.slug == "suprimentos")
        ).first()
        if departamento:
            _criar_ou_atualizar_modulo(bind, departamento.id)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "modulos" in inspector.get_table_names():
        modulos = sa.table("modulos", sa.column("slug", sa.String()))
        bind.execute(modulos.delete().where(modulos.c.slug == "compradores"))

    if "suprimentos_compradores" in inspector.get_table_names():
        op.drop_index("ix_suprimentos_compradores_ativo", table_name="suprimentos_compradores")
        op.drop_index("ix_suprimentos_compradores_centro_custo_id", table_name="suprimentos_compradores")
        op.drop_index("ix_suprimentos_compradores_usuario_comprador_id", table_name="suprimentos_compradores")
        op.drop_table("suprimentos_compradores")
