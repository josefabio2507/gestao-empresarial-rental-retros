"""separa permissoes gestao veiculos operacao

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

SUBMODULOS = [
    ("Veículos e Equipamentos", "veiculos_equipamentos", "Cadastro, consulta, edição e controle de status da frota operacional.", 701),
    ("Pool de Veículos", "pool_veiculos", "Responsabilidade operacional, disponibilidade e histórico de leituras.", 702),
    ("Abastecimento", "abastecimento", "Registro e consulta de abastecimentos dos veículos.", 703),
    ("Multas de Trânsito", "multas_transito", "Cadastro e consulta de multas de trânsito por veículo.", 704),
    ("Impostos e Taxas", "impostos_taxas", "Cadastro e consulta de parcelas de IPVA e licenciamento.", 705),
    ("Central de Custos", "central_custos", "Consulta consolidada de custos por veículo ou equipamento.", 706),
]


def _tabela_existe(conn, tabela):
    return sa.inspect(conn).has_table(tabela)


def _estrutura_permissoes_existe(conn):
    return all(
        _tabela_existe(conn, tabela)
        for tabela in ["departamentos", "modulos", "permissoes_usuario_modulo"]
    )


def _departamento_operacao_id(conn):
    row = conn.execute(sa.text("SELECT id FROM departamentos WHERE slug = 'operacao' LIMIT 1")).first()
    return row[0] if row else None


def _modulo_id(conn, departamento_id, slug):
    row = conn.execute(
        sa.text("SELECT id FROM modulos WHERE departamento_id = :departamento_id AND slug = :slug LIMIT 1"),
        {"departamento_id": departamento_id, "slug": slug},
    ).first()
    return row[0] if row else None


def _garantir_submodulos(conn, departamento_id):
    for nome, slug, descricao, ordem in SUBMODULOS:
        modulo_id = _modulo_id(conn, departamento_id, slug)
        if modulo_id:
            conn.execute(
                sa.text(
                    """
                    UPDATE modulos
                    SET nome = :nome, descricao = :descricao, ativo = :ativo, ordem = :ordem, atualizado_em = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": modulo_id, "nome": nome, "descricao": descricao, "ordem": ordem, "ativo": True},
            )
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO modulos (departamento_id, nome, slug, descricao, icone, ativo, ordem, criado_em, atualizado_em)
                VALUES (:departamento_id, :nome, :slug, :descricao, NULL, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"departamento_id": departamento_id, "nome": nome, "slug": slug, "descricao": descricao, "ordem": ordem, "ativo": True},
        )


def _copiar_permissoes_antigas(conn, departamento_id):
    modulo_antigo_id = _modulo_id(conn, departamento_id, "gestao_veiculos_epgs")
    if not modulo_antigo_id:
        return

    for _, slug, _, _ in SUBMODULOS:
        novo_modulo_id = _modulo_id(conn, departamento_id, slug)
        if not novo_modulo_id:
            continue
        conn.execute(
            sa.text(
                """
                INSERT INTO permissoes_usuario_modulo (
                    usuario_id, modulo_id, pode_visualizar, pode_criar, pode_editar,
                    pode_excluir, pode_aprovar, pode_exportar, ativo, criado_em, atualizado_em
                )
                SELECT
                    p.usuario_id, :novo_modulo_id, p.pode_visualizar, p.pode_criar, p.pode_editar,
                    p.pode_excluir, p.pode_aprovar, p.pode_exportar, p.ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM permissoes_usuario_modulo p
                WHERE p.modulo_id = :modulo_antigo_id
                  AND NOT EXISTS (
                      SELECT 1
                      FROM permissoes_usuario_modulo existente
                      WHERE existente.usuario_id = p.usuario_id
                        AND existente.modulo_id = :novo_modulo_id
                  )
                """
            ),
            {"novo_modulo_id": novo_modulo_id, "modulo_antigo_id": modulo_antigo_id},
        )

    conn.execute(
        sa.text("UPDATE modulos SET ativo = :ativo, atualizado_em = CURRENT_TIMESTAMP WHERE id = :id"),
        {"id": modulo_antigo_id, "ativo": False},
    )


def upgrade():
    conn = op.get_bind()
    if not _estrutura_permissoes_existe(conn):
        return
    if not _estrutura_permissoes_existe(conn):
        return
    departamento_id = _departamento_operacao_id(conn)
    if not departamento_id:
        return
    _garantir_submodulos(conn, departamento_id)
    _copiar_permissoes_antigas(conn, departamento_id)


def downgrade():
    conn = op.get_bind()
    departamento_id = _departamento_operacao_id(conn)
    if not departamento_id:
        return
    conn.execute(
        sa.text("UPDATE modulos SET ativo = :ativo, atualizado_em = CURRENT_TIMESTAMP WHERE departamento_id = :departamento_id AND slug = 'gestao_veiculos_epgs'"),
        {"departamento_id": departamento_id, "ativo": True},
    )
    for _, slug, _, _ in SUBMODULOS:
        conn.execute(
            sa.text("DELETE FROM permissoes_usuario_modulo WHERE modulo_id IN (SELECT id FROM modulos WHERE departamento_id = :departamento_id AND slug = :slug)"),
            {"departamento_id": departamento_id, "slug": slug},
        )
        conn.execute(
            sa.text("DELETE FROM modulos WHERE departamento_id = :departamento_id AND slug = :slug"),
            {"departamento_id": departamento_id, "slug": slug},
        )
