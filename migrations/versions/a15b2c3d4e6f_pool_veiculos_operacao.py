"""pool de veiculos operacao

Revision ID: a15b2c3d4e6f
Revises: d6e4f2a9b8c1
Create Date: 2026-08-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a15b2c3d4e6f"
down_revision = "d6e4f2a9b8c1"
branch_labels = None
depends_on = None

TABELA_VEICULOS = "operacao_veiculos_equipamentos"


def _table_exists(inspector, table_name):
    return table_name in set(inspector.get_table_names())


def _column_exists(inspector, table_name, column_name):
    if not _table_exists(inspector, table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(inspector, table_name, index_name):
    if not _table_exists(inspector, table_name):
        return False
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _add_index_if_missing(inspector, index_name, table_name, columns):
    if not _index_exists(inspector, table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _garantir_colunas_pool_veiculos(inspector):
    if not _table_exists(inspector, TABELA_VEICULOS):
        return

    with op.batch_alter_table(TABELA_VEICULOS) as batch_op:
        if not _column_exists(inspector, TABELA_VEICULOS, "centro_custo_id"):
            batch_op.add_column(sa.Column("centro_custo_id", sa.Integer(), nullable=True))
        if not _column_exists(inspector, TABELA_VEICULOS, "status_operacional"):
            batch_op.add_column(
                sa.Column(
                    "status_operacional",
                    sa.String(length=30),
                    nullable=False,
                    server_default="Disponivel",
                )
            )
        if not _column_exists(inspector, TABELA_VEICULOS, "motivo_indisponibilidade"):
            batch_op.add_column(sa.Column("motivo_indisponibilidade", sa.Text(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    _add_index_if_missing(inspector, "ix_operacao_veiculos_centro_custo_id", TABELA_VEICULOS, ["centro_custo_id"])
    _add_index_if_missing(inspector, "ix_operacao_veiculos_status_operacional", TABELA_VEICULOS, ["status_operacional"])


def _garantir_modulo_operacao(conn):
    departamentos = sa.table("departamentos", sa.column("id", sa.Integer), sa.column("slug", sa.String))
    modulos = sa.table(
        "modulos",
        sa.column("departamento_id", sa.Integer),
        sa.column("nome", sa.String),
        sa.column("slug", sa.String),
        sa.column("descricao", sa.Text),
        sa.column("icone", sa.String),
        sa.column("ativo", sa.Boolean),
        sa.column("ordem", sa.Integer),
        sa.column("criado_em", sa.DateTime),
        sa.column("atualizado_em", sa.DateTime),
    )
    departamento = conn.execute(sa.select(departamentos.c.id).where(departamentos.c.slug == "operacao")).first()
    if not departamento:
        return
    existe = conn.execute(
        sa.select(sa.literal(1)).select_from(modulos).where(
            modulos.c.departamento_id == departamento.id,
            modulos.c.slug == "gestao_veiculos_epgs",
        )
    ).first()
    if existe:
        return
    conn.execute(
        modulos.insert().values(
            departamento_id=departamento.id,
            nome="Gestao de Veiculos e EPGs",
            slug="gestao_veiculos_epgs",
            descricao="Pool operacional de veiculos, equipamentos e EPGs.",
            icone=None,
            ativo=True,
            ordem=7,
            criado_em=sa.func.now(),
            atualizado_em=sa.func.now(),
        )
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    _garantir_modulo_operacao(bind)
    _garantir_colunas_pool_veiculos(inspector)
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "operacao_veiculos_responsaveis"):
        op.create_table(
            "operacao_veiculos_responsaveis",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("veiculo_id", sa.Integer(), nullable=False),
            sa.Column("colaborador_id", sa.Integer(), nullable=False),
            sa.Column("equipe_id", sa.Integer(), nullable=True),
            sa.Column("usuario_responsavel_id", sa.Integer(), nullable=True),
            sa.Column("iniciado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("encerrado_em", sa.DateTime(), nullable=True),
            sa.Column("leitura_inicial", sa.Numeric(12, 2), nullable=True),
            sa.Column("leitura_final", sa.Numeric(12, 2), nullable=True),
            sa.Column("tipo_leitura", sa.String(length=20), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Ativo"),
            sa.Column("motivo_correcao", sa.Text(), nullable=True),
            sa.Column("corrigido_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("corrigido_em", sa.DateTime(), nullable=True),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("status in ('Ativo', 'Encerrado', 'Corrigido', 'Cancelado', 'Retificado')", name="ck_operacao_vinculos_status"),
            sa.CheckConstraint("tipo_leitura is null or tipo_leitura in ('odometro', 'horimetro')", name="ck_operacao_vinculos_tipo_leitura"),
            sa.ForeignKeyConstraint(["veiculo_id"], ["operacao_veiculos_equipamentos.id"]),
            sa.ForeignKeyConstraint(["colaborador_id"], ["colaboradores.id"]),
            sa.ForeignKeyConstraint(["equipe_id"], ["equipes.id"]),
            sa.ForeignKeyConstraint(["usuario_responsavel_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["corrigido_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for coluna in ["veiculo_id", "colaborador_id", "equipe_id", "usuario_responsavel_id", "iniciado_em", "encerrado_em", "status", "corrigido_por_usuario_id", "criado_por_usuario_id"]:
            op.create_index(f"ix_operacao_vinculos_{coluna}", "operacao_veiculos_responsaveis", [coluna])

    if not _table_exists(inspector, "operacao_leituras_ativos"):
        op.create_table(
            "operacao_leituras_ativos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("veiculo_id", sa.Integer(), nullable=False),
            sa.Column("vinculo_id", sa.Integer(), nullable=True),
            sa.Column("tipo", sa.String(length=20), nullable=False),
            sa.Column("leitura", sa.Numeric(12, 2), nullable=False),
            sa.Column("origem", sa.String(length=30), nullable=False),
            sa.Column("registrada_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("valida", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("motivo_correcao", sa.Text(), nullable=True),
            sa.Column("registrado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("tipo in ('odometro', 'horimetro')", name="ck_operacao_leituras_tipo"),
            sa.CheckConstraint("origem in ('pool', 'abastecimento', 'manutencao', 'correcao')", name="ck_operacao_leituras_origem"),
            sa.CheckConstraint("leitura >= 0", name="ck_operacao_leituras_valor"),
            sa.ForeignKeyConstraint(["veiculo_id"], ["operacao_veiculos_equipamentos.id"]),
            sa.ForeignKeyConstraint(["vinculo_id"], ["operacao_veiculos_responsaveis.id"]),
            sa.ForeignKeyConstraint(["registrado_por_usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for coluna in ["veiculo_id", "vinculo_id", "tipo", "origem", "registrada_em", "valida", "registrado_por_usuario_id"]:
            op.create_index(f"ix_operacao_leituras_{coluna}", "operacao_leituras_ativos", [coluna])

    if not _table_exists(inspector, "operacao_planos_manutencao_preventiva"):
        op.create_table(
            "operacao_planos_manutencao_preventiva",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("veiculo_id", sa.Integer(), nullable=False),
            sa.Column("descricao", sa.String(length=220), nullable=False),
            sa.Column("periodicidade_km", sa.Integer(), nullable=True),
            sa.Column("periodicidade_horimetro", sa.Integer(), nullable=True),
            sa.Column("periodicidade_dias", sa.Integer(), nullable=True),
            sa.Column("antecedencia_km", sa.Integer(), nullable=True),
            sa.Column("antecedencia_horimetro", sa.Integer(), nullable=True),
            sa.Column("antecedencia_dias", sa.Integer(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["veiculo_id"], ["operacao_veiculos_equipamentos.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_operacao_planos_veiculo_id", "operacao_planos_manutencao_preventiva", ["veiculo_id"])
        op.create_index("ix_operacao_planos_ativo", "operacao_planos_manutencao_preventiva", ["ativo"])

    if not _table_exists(inspector, "operacao_historico_manutencao"):
        op.create_table(
            "operacao_historico_manutencao",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("veiculo_id", sa.Integer(), nullable=False),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("requisicao_compra_id", sa.Integer(), nullable=True),
            sa.Column("ordem_compra_id", sa.Integer(), nullable=True),
            sa.Column("origem_financeira", sa.String(length=30), nullable=False, server_default="Suprimentos"),
            sa.Column("descricao", sa.String(length=220), nullable=False),
            sa.Column("realizada_em", sa.DateTime(), nullable=True),
            sa.Column("leitura_odometro", sa.Numeric(12, 2), nullable=True),
            sa.Column("leitura_horimetro", sa.Numeric(12, 2), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("origem_financeira = 'Suprimentos'", name="ck_operacao_historico_manutencao_origem_financeira"),
            sa.ForeignKeyConstraint(["veiculo_id"], ["operacao_veiculos_equipamentos.id"]),
            sa.ForeignKeyConstraint(["centro_custo_id"], ["centros_custo.id"]),
            sa.ForeignKeyConstraint(["requisicao_compra_id"], ["suprimentos_requisicoes_compra.id"]),
            sa.ForeignKeyConstraint(["ordem_compra_id"], ["suprimentos_ordens_compra.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for coluna in ["veiculo_id", "centro_custo_id", "requisicao_compra_id", "ordem_compra_id", "realizada_em"]:
            op.create_index(f"ix_operacao_historico_manutencao_{coluna}", "operacao_historico_manutencao", [coluna])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in [
        "operacao_historico_manutencao",
        "operacao_planos_manutencao_preventiva",
        "operacao_leituras_ativos",
        "operacao_veiculos_responsaveis",
    ]:
        if _table_exists(inspector, table_name):
            op.drop_table(table_name)

    if _table_exists(inspector, TABELA_VEICULOS):
        with op.batch_alter_table(TABELA_VEICULOS) as batch_op:
            for column_name in ["motivo_indisponibilidade", "status_operacional", "centro_custo_id"]:
                if _column_exists(inspector, TABELA_VEICULOS, column_name):
                    batch_op.drop_column(column_name)