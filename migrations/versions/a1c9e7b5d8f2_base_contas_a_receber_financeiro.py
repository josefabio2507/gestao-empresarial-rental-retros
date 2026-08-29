"""base contas a receber financeiro

Revision ID: a1c9e7b5d8f2
Revises: a7c9e2f4b6d1
Create Date: 2026-08-29 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a1c9e7b5d8f2"
down_revision = "a7c9e2f4b6d1"
branch_labels = None
depends_on = None


STATUS_DEFAULT = "A vencer"
ORIGEM_DEFAULT = "Manual"


def _tabelas(inspector):
    return inspector.get_table_names()


def _indices(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _criar_indice_se_nao_existir(inspector, nome, tabela, colunas):
    if nome not in _indices(inspector, tabela):
        op.create_index(nome, tabela, colunas)


def _garantir_submodulo_contas_receber(bind):
    financeiro = bind.execute(
        sa.text("SELECT id FROM departamentos WHERE slug = :slug"),
        {"slug": "financeiro"},
    ).fetchone()

    if not financeiro:
        return

    modulo = bind.execute(
        sa.text(
            "SELECT id FROM modulos WHERE departamento_id = :departamento_id AND slug = :slug"
        ),
        {"departamento_id": financeiro.id, "slug": "contas_a_receber"},
    ).fetchone()

    if modulo:
        bind.execute(
            sa.text(
                """
                UPDATE modulos
                   SET nome = :nome,
                       descricao = :descricao,
                       ativo = :ativo,
                       atualizado_em = CURRENT_TIMESTAMP
                 WHERE id = :id
                """
            ),
            {
                "id": modulo.id,
                "nome": "Contas a Receber",
                "descricao": "Clientes, títulos a receber e acompanhamento de recebíveis.",
                "ativo": True,
            },
        )
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO modulos
                (departamento_id, nome, slug, descricao, icone, ativo, ordem, criado_em, atualizado_em)
            VALUES
                (:departamento_id, :nome, :slug, :descricao, :icone, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ),
        {
            "departamento_id": financeiro.id,
            "nome": "Contas a Receber",
            "slug": "contas_a_receber",
            "descricao": "Clientes, títulos a receber e acompanhamento de recebíveis.",
            "icone": "receber",
            "ativo": True,
            "ordem": 2,
        },
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = _tabelas(inspector)

    if "financeiro_contas_receber_titulos" not in tabelas:
        op.create_table(
            "financeiro_contas_receber_titulos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cliente_nome_snapshot", sa.String(length=180), nullable=False),
            sa.Column("cliente_cnpj_cpf_snapshot", sa.String(length=20), nullable=True),
            sa.Column("cliente_email_financeiro_snapshot", sa.String(length=150), nullable=True),
            sa.Column("cliente_telefone_snapshot", sa.String(length=20), nullable=True),
            sa.Column("descricao", sa.String(length=255), nullable=False),
            sa.Column("numero_documento", sa.String(length=80), nullable=True),
            sa.Column("numero_nota_fiscal", sa.String(length=80), nullable=True),
            sa.Column("chave_acesso_nfe_nfse", sa.String(length=80), nullable=True),
            sa.Column("contrato_id", sa.Integer(), nullable=True),
            sa.Column("medicao_id", sa.Integer(), nullable=True),
            sa.Column("origem_lancamento", sa.String(length=40), nullable=False, server_default=ORIGEM_DEFAULT),
            sa.Column("competencia", sa.String(length=7), nullable=True),
            sa.Column("data_emissao", sa.Date(), nullable=True),
            sa.Column("data_vencimento", sa.Date(), nullable=False),
            sa.Column("data_recebimento", sa.Date(), nullable=True),
            sa.Column("valor_original", sa.Numeric(12, 2), nullable=False),
            sa.Column("valor_desconto", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_acrescimo", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_juros_multa", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_recebido", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("parcela_numero", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("total_parcelas", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("sub_centro_custo_equipe_id", sa.Integer(), nullable=True),
            sa.Column("sub_centro_custo_veiculo_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default=STATUS_DEFAULT),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("cancelado_em", sa.DateTime(), nullable=True),
            sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["centro_custo_id"], ["centros_custo.id"], name="fk_fin_cr_titulos_centro_custo"),
            sa.ForeignKeyConstraint(["sub_centro_custo_equipe_id"], ["equipes.id"], name="fk_fin_cr_titulos_equipe"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_titulos_criado_por"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_titulos_atualizado_por"),
            sa.ForeignKeyConstraint(["cancelado_por_usuario_id"], ["usuarios.id"], name="fk_fin_cr_titulos_cancelado_por"),
            sa.CheckConstraint("valor_original > 0", name="ck_fin_cr_titulos_valor_original"),
            sa.CheckConstraint("valor_desconto >= 0", name="ck_fin_cr_titulos_valor_desconto"),
            sa.CheckConstraint("valor_acrescimo >= 0", name="ck_fin_cr_titulos_valor_acrescimo"),
            sa.CheckConstraint("valor_juros_multa >= 0", name="ck_fin_cr_titulos_valor_juros"),
            sa.CheckConstraint("valor_recebido >= 0", name="ck_fin_cr_titulos_valor_recebido"),
            sa.CheckConstraint("parcela_numero >= 1", name="ck_fin_cr_titulos_parcela_numero"),
            sa.CheckConstraint("total_parcelas >= 1", name="ck_fin_cr_titulos_total_parcelas"),
            sa.CheckConstraint(
                "status in ('Rascunho', 'Aguardando faturamento', 'Faturado', 'Agendado', 'A vencer', 'Vencido', 'Recebido', 'Recebido parcialmente', 'Cancelado', 'Estornado', 'Inadimplente')",
                name="ck_fin_cr_titulos_status",
            ),
            sa.CheckConstraint(
                "origem_lancamento in ('Manual', 'Nota Fiscal Emitida', 'Medição', 'Contrato', 'Reembolso', 'Outro')",
                name="ck_fin_cr_titulos_origem",
            ),
        )

    inspector = sa.inspect(bind)
    for nome, colunas in [
        ("ix_fin_cr_titulos_cliente_cnpj_cpf", ["cliente_cnpj_cpf_snapshot"]),
        ("ix_fin_cr_titulos_data_vencimento", ["data_vencimento"]),
        ("ix_fin_cr_titulos_data_emissao", ["data_emissao"]),
        ("ix_fin_cr_titulos_status", ["status"]),
        ("ix_fin_cr_titulos_origem", ["origem_lancamento"]),
        ("ix_fin_cr_titulos_competencia", ["competencia"]),
    ]:
        _criar_indice_se_nao_existir(inspector, nome, "financeiro_contas_receber_titulos", colunas)
        inspector = sa.inspect(bind)

    _garantir_submodulo_contas_receber(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "financeiro_contas_receber_titulos" in inspector.get_table_names():
        indices = _indices(inspector, "financeiro_contas_receber_titulos")
        for nome in [
            "ix_fin_cr_titulos_competencia",
            "ix_fin_cr_titulos_origem",
            "ix_fin_cr_titulos_status",
            "ix_fin_cr_titulos_data_emissao",
            "ix_fin_cr_titulos_data_vencimento",
            "ix_fin_cr_titulos_cliente_cnpj_cpf",
        ]:
            if nome in indices:
                op.drop_index(nome, table_name="financeiro_contas_receber_titulos")
        op.drop_table("financeiro_contas_receber_titulos")
