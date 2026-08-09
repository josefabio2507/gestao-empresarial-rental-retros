"""adiciona indicadores suprimentos

Revision ID: d7a6c3f1b2e9
Revises: c4f2a9b8e1d6
Create Date: 2026-08-09 00:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "d7a6c3f1b2e9"
down_revision = "c4f2a9b8e1d6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "departamentos" not in inspector.get_table_names() or "modulos" not in inspector.get_table_names():
        return

    departamentos = sa.table(
        "departamentos",
        sa.column("id", sa.Integer()),
        sa.column("slug", sa.String()),
    )
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

    departamento = bind.execute(
        sa.select(departamentos.c.id).where(departamentos.c.slug == "suprimentos")
    ).first()

    if not departamento:
        return

    agora = datetime.utcnow()
    existente = bind.execute(
        sa.select(modulos.c.id).where(
            modulos.c.departamento_id == departamento.id,
            modulos.c.slug == "indicadores",
        )
    ).first()

    dados = {
        "nome": "Indicadores",
        "descricao": "Indicadores e relatorios gerenciais de Suprimentos",
        "ativo": True,
        "ordem": 11,
        "atualizado_em": agora,
    }

    if existente:
        bind.execute(
            modulos.update()
            .where(modulos.c.id == existente.id)
            .values(**dados)
        )
        return

    bind.execute(
        modulos.insert().values(
            departamento_id=departamento.id,
            slug="indicadores",
            criado_em=agora,
            **dados,
        )
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "modulos" not in inspector.get_table_names():
        return

    modulos = sa.table(
        "modulos",
        sa.column("slug", sa.String()),
    )
    bind.execute(modulos.delete().where(modulos.c.slug == "indicadores"))
