"""cria modulo historico refeicoes colaborador

Revision ID: 9c3d2a1b4e5f
Revises: b8f6a1d3c4e2
Create Date: 2026-05-29 00:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c3d2a1b4e5f"
down_revision = "b8f6a1d3c4e2"
branch_labels = None
depends_on = None


MODULO_SLUG = "pedido-refeicoes-historico-colaborador"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "departamentos" not in inspector.get_table_names():
        return

    if "modulos" not in inspector.get_table_names():
        return

    departamento = bind.execute(
        sa.text(
            "SELECT id FROM departamentos "
            "WHERE slug = :slug_departamento "
            "LIMIT 1"
        ),
        {"slug_departamento": "departamento_pessoal"},
    ).fetchone()

    if not departamento:
        return

    modulo_existente = bind.execute(
        sa.text(
            "SELECT id FROM modulos "
            "WHERE departamento_id = :departamento_id "
            "AND slug = :slug_modulo "
            "LIMIT 1"
        ),
        {
            "departamento_id": departamento.id,
            "slug_modulo": MODULO_SLUG,
        },
    ).fetchone()

    if modulo_existente:
        bind.execute(
            sa.text(
                "UPDATE modulos "
                "SET nome = :nome, descricao = :descricao, ativo = :ativo, "
                "ordem = :ordem, atualizado_em = :atualizado_em "
                "WHERE id = :modulo_id"
            ),
            {
                "nome": "Pedido de Refeições - Histórico por Colaborador",
                "descricao": "Consulta do histórico de refeições e bebidas por colaborador ativo.",
                "ativo": True,
                "ordem": 24,
                "atualizado_em": datetime.utcnow(),
                "modulo_id": modulo_existente.id,
            },
        )
        return

    agora = datetime.utcnow()
    bind.execute(
        sa.text(
            "INSERT INTO modulos "
            "(departamento_id, nome, slug, descricao, ativo, ordem, criado_em, atualizado_em) "
            "VALUES "
            "(:departamento_id, :nome, :slug, :descricao, :ativo, :ordem, :criado_em, :atualizado_em)"
        ),
        {
            "departamento_id": departamento.id,
            "nome": "Pedido de Refeições - Histórico por Colaborador",
            "slug": MODULO_SLUG,
            "descricao": "Consulta do histórico de refeições e bebidas por colaborador ativo.",
            "ativo": True,
            "ordem": 24,
            "criado_em": agora,
            "atualizado_em": agora,
        },
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "modulos" not in inspector.get_table_names():
        return

    bind.execute(
        sa.text("DELETE FROM modulos WHERE slug = :slug_modulo"),
        {"slug_modulo": MODULO_SLUG},
    )
