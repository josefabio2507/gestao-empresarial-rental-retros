"""garante modulo fluxo de caixa financeiro

Revision ID: a7c9d2e4f6b8
Revises: f6b8d1c2e3a4
Create Date: 2026-08-30 18:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a7c9d2e4f6b8"
down_revision = "f6b8d1c2e3a4"
branch_labels = None
depends_on = None


def _tabela_existe(bind, nome):
    return sa.inspect(bind).has_table(nome)


def upgrade():
    bind = op.get_bind()
    if not _tabela_existe(bind, "departamentos") or not _tabela_existe(bind, "modulos"):
        return
    financeiro = bind.execute(sa.text("select id from departamentos where slug = :slug"), {"slug": "financeiro"}).first()
    if not financeiro:
        bind.execute(sa.text("insert into departamentos (nome, slug, descricao, icone, ativo, ordem, criado_em, atualizado_em) values (:nome, :slug, :descricao, :icone, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"nome": "Financeiro", "slug": "financeiro", "descricao": "Controle financeiro, contas, fluxo de caixa e relatorios.", "icone": "grafico", "ativo": True, "ordem": 1})
        financeiro = bind.execute(sa.text("select id from departamentos where slug = :slug"), {"slug": "financeiro"}).first()
    modulo = bind.execute(sa.text("select id from modulos where departamento_id = :departamento_id and slug = :slug"), {"departamento_id": financeiro.id, "slug": "fluxo_de_caixa"}).first()
    if not modulo:
        bind.execute(sa.text("insert into modulos (departamento_id, nome, slug, descricao, ativo, ordem, criado_em, atualizado_em) values (:departamento_id, :nome, :slug, :descricao, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"departamento_id": financeiro.id, "nome": "Fluxo de Caixa", "slug": "fluxo_de_caixa", "descricao": "Entradas e saidas", "ativo": True, "ordem": 3})
    else:
        bind.execute(sa.text("update modulos set nome = :nome, descricao = :descricao, ativo = :ativo, ordem = case when ordem is null or ordem = 0 then :ordem else ordem end, atualizado_em = CURRENT_TIMESTAMP where id = :id"), {"id": modulo.id, "nome": "Fluxo de Caixa", "descricao": "Entradas e saidas", "ativo": True, "ordem": 3})


def downgrade():
    pass
