"""cria contas pagar financeiro

Revision ID: a17b1c2d3e4f
Revises: d5a7c9e2f4b6
Create Date: 2026-08-26 19:50:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a17b1c2d3e4f"
down_revision = "d5a7c9e2f4b6"
branch_labels = None
depends_on = None


TABELA = "financeiro_contas_pagar_titulos"


def _tabelas(inspector):
    return inspector.get_table_names()


def _indices(inspector, tabela):
    if tabela not in inspector.get_table_names():
        return []
    return [indice["name"] for indice in inspector.get_indexes(tabela)]


def _garantir_modulo_contas_pagar(bind):
    agora = sa.func.now()
    departamento = bind.execute(
        sa.text("SELECT id FROM departamentos WHERE slug = :slug"),
        {"slug": "financeiro"},
    ).fetchone()

    if not departamento:
        bind.execute(
            sa.text(
                """
                INSERT INTO departamentos (nome, slug, descricao, icone, ativo, ordem, criado_em, atualizado_em)
                VALUES (:nome, :slug, :descricao, :icone, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "nome": "Financeiro",
                "slug": "financeiro",
                "descricao": "Controle financeiro, contas, fluxo de caixa e relatorios.",
                "icone": "grafico",
                "ativo": True,
                "ordem": 1,
            },
        )
        departamento = bind.execute(
            sa.text("SELECT id FROM departamentos WHERE slug = :slug"),
            {"slug": "financeiro"},
        ).fetchone()

    modulo = bind.execute(
        sa.text(
            """
            SELECT id FROM modulos
             WHERE departamento_id = :departamento_id
               AND slug = :slug
            """
        ),
        {"departamento_id": departamento.id, "slug": "contas_a_pagar"},
    ).fetchone()

    if not modulo:
        bind.execute(
            sa.text(
                """
                INSERT INTO modulos (departamento_id, nome, slug, descricao, icone, ativo, ordem, criado_em, atualizado_em)
                VALUES (:departamento_id, :nome, :slug, :descricao, :icone, :ativo, :ordem, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "departamento_id": departamento.id,
                "nome": "Contas a Pagar",
                "slug": "contas_a_pagar",
                "descricao": "Vencimentos e aprovacoes",
                "icone": None,
                "ativo": True,
                "ordem": 1,
            },
        )
    else:
        bind.execute(
            sa.text(
                """
                UPDATE modulos
                   SET nome = :nome,
                       descricao = :descricao,
                       ativo = :ativo,
                       ordem = CASE WHEN ordem IS NULL OR ordem = 0 THEN :ordem ELSE ordem END,
                       atualizado_em = CURRENT_TIMESTAMP
                 WHERE id = :id
                """
            ),
            {
                "id": modulo.id,
                "nome": "Contas a Pagar",
                "descricao": "Vencimentos e aprovacoes",
                "ativo": True,
                "ordem": 1,
            },
        )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = _tabelas(inspector)

    if "departamentos" in tabelas and "modulos" in tabelas:
        _garantir_modulo_contas_pagar(bind)

    if TABELA not in tabelas:
        op.create_table(
            TABELA,
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("fornecedor_id", sa.Integer(), nullable=True),
            sa.Column("fornecedor_nome_snapshot", sa.String(length=180), nullable=False),
            sa.Column("fornecedor_cnpj_cpf_snapshot", sa.String(length=14), nullable=True),
            sa.Column("descricao", sa.String(length=220), nullable=False),
            sa.Column("numero_documento", sa.String(length=80), nullable=True),
            sa.Column("numero_nfe", sa.String(length=20), nullable=True),
            sa.Column("chave_acesso_nfe", sa.String(length=44), nullable=True),
            sa.Column("ordem_compra_id", sa.Integer(), nullable=True),
            sa.Column("fiscal_documento_id", sa.Integer(), nullable=True),
            sa.Column("cartao_credito_id", sa.Integer(), nullable=True),
            sa.Column("origem_lancamento", sa.String(length=30), nullable=False),
            sa.Column("tipo_pagamento", sa.String(length=30), nullable=False),
            sa.Column("forma_pagamento", sa.String(length=30), nullable=False),
            sa.Column("competencia", sa.Date(), nullable=True),
            sa.Column("data_emissao", sa.Date(), nullable=True),
            sa.Column("data_vencimento", sa.Date(), nullable=False),
            sa.Column("data_pagamento", sa.Date(), nullable=True),
            sa.Column("valor_original", sa.Numeric(12, 2), nullable=False),
            sa.Column("valor_desconto", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_acrescimo", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_juros_multa", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("valor_pago", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("parcela_numero", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("total_parcelas", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("sub_centro_custo_equipe_id", sa.Integer(), nullable=True),
            sa.Column("sub_centro_custo_veiculo_id", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Agendado"),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("atualizado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["fornecedor_id"], ["suprimentos_fornecedores.id"], name="fk_financeiro_cp_fornecedor_id"),
            sa.ForeignKeyConstraint(["ordem_compra_id"], ["suprimentos_ordens_compra.id"], name="fk_financeiro_cp_ordem_compra_id"),
            sa.ForeignKeyConstraint(["fiscal_documento_id"], ["fiscal_documentos.id"], name="fk_financeiro_cp_fiscal_documento_id"),
            sa.ForeignKeyConstraint(["centro_custo_id"], ["centros_custo.id"], name="fk_financeiro_cp_centro_custo_id"),
            sa.ForeignKeyConstraint(["sub_centro_custo_equipe_id"], ["equipes.id"], name="fk_financeiro_cp_sub_centro_equipe_id"),
            sa.ForeignKeyConstraint(["sub_centro_custo_veiculo_id"], ["operacao_veiculos_equipamentos.id"], name="fk_financeiro_cp_sub_centro_veiculo_id"),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"], name="fk_financeiro_cp_criado_por_id"),
            sa.ForeignKeyConstraint(["atualizado_por_usuario_id"], ["usuarios.id"], name="fk_financeiro_cp_atualizado_por_id"),
            sa.CheckConstraint("origem_lancamento in ('Manual', 'Ordem de Compra', 'XML Fiscal', 'Cartao de Credito')", name="ck_financeiro_cp_origem_lancamento"),
            sa.CheckConstraint("tipo_pagamento in ('Faturado', 'Cartao de Credito')", name="ck_financeiro_cp_tipo_pagamento"),
            sa.CheckConstraint("forma_pagamento in ('Boleto', 'Pix', 'Transferencia', 'Deposito', 'Cartao de Credito', 'Outro')", name="ck_financeiro_cp_forma_pagamento"),
            sa.CheckConstraint("status in ('Rascunho', 'Aguardando conferencia', 'Agendado', 'A vencer', 'Vencido', 'Pago', 'Pago parcialmente', 'Cancelado', 'Estornado')", name="ck_financeiro_cp_status"),
            sa.CheckConstraint("valor_original > 0", name="ck_financeiro_cp_valor_original"),
            sa.CheckConstraint("valor_desconto >= 0", name="ck_financeiro_cp_valor_desconto"),
            sa.CheckConstraint("valor_acrescimo >= 0", name="ck_financeiro_cp_valor_acrescimo"),
            sa.CheckConstraint("valor_juros_multa >= 0", name="ck_financeiro_cp_valor_juros_multa"),
            sa.CheckConstraint("valor_pago >= 0", name="ck_financeiro_cp_valor_pago"),
            sa.CheckConstraint("parcela_numero >= 1", name="ck_financeiro_cp_parcela_numero"),
            sa.CheckConstraint("total_parcelas >= 1", name="ck_financeiro_cp_total_parcelas"),
            sa.CheckConstraint("parcela_numero <= total_parcelas", name="ck_financeiro_cp_parcela_total"),
        )

    inspector = sa.inspect(bind)
    indices = _indices(inspector, TABELA)
    for nome, colunas in {
        "ix_financeiro_cp_fornecedor_nome": ["fornecedor_nome_snapshot"],
        "ix_financeiro_cp_fornecedor_documento": ["fornecedor_cnpj_cpf_snapshot"],
        "ix_financeiro_cp_data_vencimento": ["data_vencimento"],
        "ix_financeiro_cp_status": ["status"],
        "ix_financeiro_cp_origem_lancamento": ["origem_lancamento"],
        "ix_financeiro_cp_tipo_pagamento": ["tipo_pagamento"],
        "ix_financeiro_cp_forma_pagamento": ["forma_pagamento"],
        "ix_financeiro_cp_centro_custo_id": ["centro_custo_id"],
        "ix_financeiro_cp_ordem_compra_id": ["ordem_compra_id"],
        "ix_financeiro_cp_fiscal_documento_id": ["fiscal_documento_id"],
        "ix_financeiro_cp_cartao_credito_id": ["cartao_credito_id"],
    }.items():
        if nome not in indices:
            op.create_index(nome, TABELA, colunas)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABELA in inspector.get_table_names():
        for nome in reversed(_indices(inspector, TABELA)):
            if nome.startswith("ix_financeiro_cp_"):
                op.drop_index(nome, table_name=TABELA)
        op.drop_table(TABELA)
