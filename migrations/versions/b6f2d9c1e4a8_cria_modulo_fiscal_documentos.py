"""cria modulo fiscal documentos

Revision ID: b6f2d9c1e4a8
Revises: a2d4f6b8c9e1
Create Date: 2026-08-15 20:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b6f2d9c1e4a8"
down_revision = "a2d4f6b8c9e1"
branch_labels = None
depends_on = None


def _tabelas(inspector):
    return set(inspector.get_table_names())


def _criar_ou_atualizar_departamento_fiscal(conn):
    departamentos = sa.table(
        "departamentos",
        sa.column("id", sa.Integer),
        sa.column("nome", sa.String),
        sa.column("slug", sa.String),
        sa.column("descricao", sa.Text),
        sa.column("icone", sa.String),
        sa.column("ativo", sa.Boolean),
        sa.column("ordem", sa.Integer),
        sa.column("criado_em", sa.DateTime),
        sa.column("atualizado_em", sa.DateTime),
    )
    modulos = sa.table(
        "modulos",
        sa.column("id", sa.Integer),
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

    departamento = conn.execute(
        sa.select(departamentos.c.id).where(departamentos.c.slug == "fiscal")
    ).first()

    if not departamento:
        conn.execute(
            departamentos.insert().values(
                nome="Fiscal",
                slug="fiscal",
                descricao="Central de documentos fiscais, XMLs, DANFEs e integrações com compras.",
                icone="documentos",
                ativo=True,
                ordem=6,
                criado_em=sa.func.now(),
                atualizado_em=sa.func.now(),
            )
        )
        departamento = conn.execute(
            sa.select(departamentos.c.id).where(departamentos.c.slug == "fiscal")
        ).first()
    else:
        conn.execute(
            departamentos.update()
            .where(departamentos.c.id == departamento.id)
            .values(
                nome="Fiscal",
                descricao="Central de documentos fiscais, XMLs, DANFEs e integrações com compras.",
                icone="documentos",
                ativo=True,
                ordem=6,
                atualizado_em=sa.func.now(),
            )
        )

    existe_modulo = conn.execute(
        sa.select(sa.literal(1)).select_from(modulos).where(
            modulos.c.departamento_id == departamento.id,
            modulos.c.slug == "documentos_fiscais",
        )
    ).first()

    if existe_modulo:
        conn.execute(
            modulos.update()
            .where(
                modulos.c.departamento_id == departamento.id,
                modulos.c.slug == "documentos_fiscais",
            )
            .values(
                nome="Documentos Fiscais",
                descricao="Central fiscal para XMLs, DANFEs e vínculo com O.C.",
                ativo=True,
                ordem=1,
                atualizado_em=sa.func.now(),
            )
        )
        return

    conn.execute(
        modulos.insert().values(
            departamento_id=departamento.id,
            nome="Documentos Fiscais",
            slug="documentos_fiscais",
            descricao="Central fiscal para XMLs, DANFEs e vínculo com O.C.",
            icone=None,
            ativo=True,
            ordem=1,
            criado_em=sa.func.now(),
            atualizado_em=sa.func.now(),
        )
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = _tabelas(inspector)

    if "fiscal_certificados_a1" not in tabelas:
        op.create_table(
            "fiscal_certificados_a1",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cnpj_empresa", sa.String(length=14), nullable=False),
            sa.Column("razao_social", sa.String(length=180), nullable=False),
            sa.Column("nome_arquivo_original", sa.String(length=180), nullable=False),
            sa.Column("arquivo_path", sa.String(length=500), nullable=False),
            sa.Column("senha_hash", sa.String(length=255), nullable=False),
            sa.Column("validade", sa.Date(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("cadastrado_por_usuario_id", sa.Integer(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["cadastrado_por_usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_fiscal_certificados_a1_cnpj_empresa", "fiscal_certificados_a1", ["cnpj_empresa"])
        op.create_index("ix_fiscal_certificados_a1_validade", "fiscal_certificados_a1", ["validade"])
        op.create_index("ix_fiscal_certificados_a1_ativo", "fiscal_certificados_a1", ["ativo"])
        op.create_index(
            "ix_fiscal_certificados_a1_cadastrado_por_usuario_id",
            "fiscal_certificados_a1",
            ["cadastrado_por_usuario_id"],
        )

    if "fiscal_controles_nsu" not in tabelas:
        op.create_table(
            "fiscal_controles_nsu",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cnpj_empresa", sa.String(length=14), nullable=False),
            sa.Column("ultimo_nsu", sa.String(length=20), nullable=False, server_default="0"),
            sa.Column("max_nsu", sa.String(length=20), nullable=True),
            sa.Column("consultado_em", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Pendente"),
            sa.Column("mensagem", sa.Text(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("cnpj_empresa", name="uq_fiscal_controles_nsu_cnpj_empresa"),
        )
        op.create_index("ix_fiscal_controles_nsu_cnpj_empresa", "fiscal_controles_nsu", ["cnpj_empresa"])
        op.create_index("ix_fiscal_controles_nsu_status", "fiscal_controles_nsu", ["status"])

    if "fiscal_documentos" not in tabelas:
        op.create_table(
            "fiscal_documentos",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("chave_acesso", sa.String(length=44), nullable=False),
            sa.Column("nsu", sa.String(length=20), nullable=True),
            sa.Column("modelo", sa.String(length=10), nullable=False, server_default="55"),
            sa.Column("serie", sa.String(length=10), nullable=True),
            sa.Column("numero", sa.String(length=20), nullable=False),
            sa.Column("natureza_operacao", sa.String(length=180), nullable=True),
            sa.Column("data_emissao", sa.DateTime(), nullable=True),
            sa.Column("emitente_nome", sa.String(length=180), nullable=False),
            sa.Column("emitente_cnpj", sa.String(length=14), nullable=False),
            sa.Column("destinatario_nome", sa.String(length=180), nullable=True),
            sa.Column("destinatario_cnpj", sa.String(length=14), nullable=False),
            sa.Column("valor_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("xml_path", sa.String(length=500), nullable=False),
            sa.Column("danfe_path", sa.String(length=500), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Disponivel"),
            sa.Column("ordem_compra_id", sa.Integer(), nullable=True),
            sa.Column("vinculado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("vinculado_em", sa.DateTime(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "status in ('Disponivel', 'Vinculado', 'Cancelado')",
                name="ck_fiscal_documentos_status",
            ),
            sa.ForeignKeyConstraint(["ordem_compra_id"], ["suprimentos_ordens_compra.id"]),
            sa.ForeignKeyConstraint(["vinculado_por_usuario_id"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("chave_acesso", name="uq_fiscal_documentos_chave_acesso"),
        )
        for nome, colunas in {
            "ix_fiscal_documentos_chave_acesso": ["chave_acesso"],
            "ix_fiscal_documentos_nsu": ["nsu"],
            "ix_fiscal_documentos_modelo": ["modelo"],
            "ix_fiscal_documentos_numero": ["numero"],
            "ix_fiscal_documentos_data_emissao": ["data_emissao"],
            "ix_fiscal_documentos_emitente_nome": ["emitente_nome"],
            "ix_fiscal_documentos_emitente_cnpj": ["emitente_cnpj"],
            "ix_fiscal_documentos_destinatario_cnpj": ["destinatario_cnpj"],
            "ix_fiscal_documentos_status": ["status"],
            "ix_fiscal_documentos_ordem_compra_id": ["ordem_compra_id"],
            "ix_fiscal_documentos_vinculado_por_usuario_id": ["vinculado_por_usuario_id"],
        }.items():
            op.create_index(nome, "fiscal_documentos", colunas)

    _criar_ou_atualizar_departamento_fiscal(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = _tabelas(inspector)

    if "fiscal_documentos" in tabelas:
        for nome in [
            "ix_fiscal_documentos_vinculado_por_usuario_id",
            "ix_fiscal_documentos_ordem_compra_id",
            "ix_fiscal_documentos_status",
            "ix_fiscal_documentos_destinatario_cnpj",
            "ix_fiscal_documentos_emitente_cnpj",
            "ix_fiscal_documentos_emitente_nome",
            "ix_fiscal_documentos_data_emissao",
            "ix_fiscal_documentos_numero",
            "ix_fiscal_documentos_modelo",
            "ix_fiscal_documentos_nsu",
            "ix_fiscal_documentos_chave_acesso",
        ]:
            op.drop_index(nome, table_name="fiscal_documentos")
        op.drop_table("fiscal_documentos")

    if "fiscal_controles_nsu" in tabelas:
        op.drop_index("ix_fiscal_controles_nsu_status", table_name="fiscal_controles_nsu")
        op.drop_index("ix_fiscal_controles_nsu_cnpj_empresa", table_name="fiscal_controles_nsu")
        op.drop_table("fiscal_controles_nsu")

    if "fiscal_certificados_a1" in tabelas:
        op.drop_index("ix_fiscal_certificados_a1_cadastrado_por_usuario_id", table_name="fiscal_certificados_a1")
        op.drop_index("ix_fiscal_certificados_a1_ativo", table_name="fiscal_certificados_a1")
        op.drop_index("ix_fiscal_certificados_a1_validade", table_name="fiscal_certificados_a1")
        op.drop_index("ix_fiscal_certificados_a1_cnpj_empresa", table_name="fiscal_certificados_a1")
        op.drop_table("fiscal_certificados_a1")
