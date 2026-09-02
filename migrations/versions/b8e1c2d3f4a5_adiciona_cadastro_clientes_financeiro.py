"""adiciona cadastro de clientes financeiro

Revision ID: b8e1c2d3f4a5
Revises: a7c9d2e4f6b8
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa

revision = "b8e1c2d3f4a5"
down_revision = "b9c1d2e3f4a5"
branch_labels = None
depends_on = None


def _has_table(bind, table):
    return sa.inspect(bind).has_table(table)


def _has_column(bind, table, column):
    if not _has_table(bind, table):
        return False
    return column in {col["name"] for col in sa.inspect(bind).get_columns(table)}


def _ensure_index(bind, table, index_name, columns):
    if not _has_table(bind, table):
        return
    indexes = {idx["name"] for idx in sa.inspect(bind).get_indexes(table)}
    if index_name not in indexes:
        op.create_index(index_name, table, columns)


def _ensure_modulo_clientes(bind):
    financeiro = bind.execute(sa.text("select id from departamentos where slug = :slug"), {"slug": "financeiro"}).first()
    if not financeiro:
        bind.execute(sa.text("insert into departamentos (nome, slug, descricao, icone, ativo, ordem, criado_em, atualizado_em) values (:nome, :slug, :descricao, :icone, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"nome": "Financeiro", "slug": "financeiro", "descricao": "Controle financeiro, contas, fluxo de caixa e relatorios.", "icone": "grafico", "ativo": True, "ordem": 1})
        financeiro = bind.execute(sa.text("select id from departamentos where slug = :slug"), {"slug": "financeiro"}).first()
    modulo = bind.execute(sa.text("select id from modulos where departamento_id = :departamento_id and slug = :slug"), {"departamento_id": financeiro.id, "slug": "clientes"}).first()
    if not modulo:
        bind.execute(sa.text("insert into modulos (departamento_id, nome, slug, descricao, ativo, ordem, criado_em, atualizado_em) values (:departamento_id, :nome, :slug, :descricao, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"departamento_id": financeiro.id, "nome": "Clientes", "slug": "clientes", "descricao": "Cadastro central de clientes financeiros", "ativo": True, "ordem": 2})


def upgrade():
    bind = op.get_bind()
    if not _has_table(bind, "financeiro_clientes"):
        op.create_table(
            "financeiro_clientes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tipo_pessoa", sa.String(length=20), nullable=False, server_default="juridica"),
            sa.Column("cnpj_cpf", sa.String(length=20), nullable=False),
            sa.Column("cnpj_cpf_normalizado", sa.String(length=14), nullable=False),
            sa.Column("razao_social", sa.String(length=180), nullable=False),
            sa.Column("nome_fantasia", sa.String(length=180), nullable=True),
            sa.Column("inscricao_estadual", sa.String(length=40), nullable=True),
            sa.Column("inscricao_municipal", sa.String(length=40), nullable=True),
            sa.Column("email_financeiro", sa.String(length=150), nullable=True),
            sa.Column("email_alternativo", sa.String(length=150), nullable=True),
            sa.Column("telefone_principal", sa.String(length=30), nullable=True),
            sa.Column("telefone_alternativo", sa.String(length=30), nullable=True),
            sa.Column("contato_responsavel", sa.String(length=120), nullable=True),
            sa.Column("cargo_contato", sa.String(length=120), nullable=True),
            sa.Column("endereco", sa.String(length=255), nullable=True),
            sa.Column("numero", sa.String(length=30), nullable=True),
            sa.Column("complemento", sa.String(length=120), nullable=True),
            sa.Column("bairro", sa.String(length=120), nullable=True),
            sa.Column("cidade", sa.String(length=120), nullable=True),
            sa.Column("uf", sa.String(length=2), nullable=True),
            sa.Column("cep", sa.String(length=20), nullable=True),
            sa.Column("condicao_recebimento_padrao", sa.String(length=120), nullable=True),
            sa.Column("prazo_vencimento_padrao", sa.Integer(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("inativado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("inativado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_inativacao", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.CheckConstraint("tipo_pessoa in ('juridica', 'fisica')", name="ck_fin_clientes_tipo_pessoa"),
            sa.CheckConstraint("prazo_vencimento_padrao is null or prazo_vencimento_padrao >= 0", name="ck_fin_clientes_prazo_vencimento"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["inativado_por_usuario_id"], ["usuarios.id"]),
            sa.UniqueConstraint("cnpj_cpf_normalizado", name="uq_fin_clientes_documento"),
        )
    for name, cols in [
        ("ix_fin_clientes_documento", ["cnpj_cpf_normalizado"]),
        ("ix_fin_clientes_razao", ["razao_social"]),
        ("ix_fin_clientes_fantasia", ["nome_fantasia"]),
        ("ix_fin_clientes_cidade", ["cidade"]),
        ("ix_fin_clientes_uf", ["uf"]),
        ("ix_fin_clientes_ativo", ["ativo"]),
    ]:
        _ensure_index(bind, "financeiro_clientes", name, cols)

    for table, index_name in [
        ("financeiro_contas_receber_titulos", "ix_fin_cr_titulos_cliente_id"),
        ("financeiro_notas_fiscais_emitidas", "ix_fin_notas_emitidas_cliente_id"),
        ("financeiro_contratos_clientes", "ix_fin_contratos_cliente_id"),
    ]:
        if _has_table(bind, table) and not _has_column(bind, table, "cliente_id"):
            op.add_column(table, sa.Column("cliente_id", sa.Integer(), nullable=True))
        _ensure_index(bind, table, index_name, ["cliente_id"])

    _ensure_modulo_clientes(bind)


def downgrade():
    bind = op.get_bind()
    for table, index_name in [
        ("financeiro_contas_receber_titulos", "ix_fin_cr_titulos_cliente_id"),
        ("financeiro_notas_fiscais_emitidas", "ix_fin_notas_emitidas_cliente_id"),
        ("financeiro_contratos_clientes", "ix_fin_contratos_cliente_id"),
    ]:
        if _has_table(bind, table):
            indexes = {idx["name"] for idx in sa.inspect(bind).get_indexes(table)}
            if index_name in indexes:
                op.drop_index(index_name, table_name=table)
            if _has_column(bind, table, "cliente_id"):
                op.drop_column(table, "cliente_id")
    if _has_table(bind, "financeiro_clientes"):
        op.drop_table("financeiro_clientes")

