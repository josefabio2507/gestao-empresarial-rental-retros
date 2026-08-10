"""adiciona alcadas e alertas suprimentos

Revision ID: a8c1d2e3f4b5
Revises: d7a6c3f1b2e9
Create Date: 2026-08-10 00:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "a8c1d2e3f4b5"
down_revision = "d7a6c3f1b2e9"
branch_labels = None
depends_on = None


def _criar_ou_atualizar_modulo(bind, departamento_id, slug, nome, descricao, ordem):
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
            modulos.c.slug == slug,
        )
    ).first()

    dados = {
        "nome": nome,
        "descricao": descricao,
        "ativo": True,
        "ordem": ordem,
        "atualizado_em": agora,
    }

    if existente:
        bind.execute(modulos.update().where(modulos.c.id == existente.id).values(**dados))
        return

    bind.execute(
        modulos.insert().values(
            departamento_id=departamento_id,
            slug=slug,
            criado_em=agora,
            **dados,
        )
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_alcadas_aprovacao" not in inspector.get_table_names():
        op.create_table(
            "suprimentos_alcadas_aprovacao",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("usuario_aprovador_id", sa.Integer(), nullable=False),
            sa.Column("centro_custo_id", sa.Integer(), nullable=True),
            sa.Column("categoria_id", sa.Integer(), nullable=True),
            sa.Column("valor_minimo", sa.Numeric(12, 2), nullable=False),
            sa.Column("valor_maximo", sa.Numeric(12, 2), nullable=True),
            sa.Column("telefone_whatsapp", sa.String(20), nullable=True),
            sa.Column("observacoes", sa.Text(), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["categoria_id"], ["suprimentos_categorias_itens.id"]),
            sa.ForeignKeyConstraint(["centro_custo_id"], ["centros_custo.id"]),
            sa.ForeignKeyConstraint(["usuario_aprovador_id"], ["usuarios.id"]),
            sa.CheckConstraint("valor_minimo >= 0", name="ck_suprimentos_alcadas_valor_minimo"),
            sa.CheckConstraint(
                "valor_maximo is null or valor_maximo >= valor_minimo",
                name="ck_suprimentos_alcadas_valor_maximo",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_suprimentos_alcadas_aprovacao_usuario_aprovador_id",
            "suprimentos_alcadas_aprovacao",
            ["usuario_aprovador_id"],
        )
        op.create_index(
            "ix_suprimentos_alcadas_aprovacao_centro_custo_id",
            "suprimentos_alcadas_aprovacao",
            ["centro_custo_id"],
        )
        op.create_index(
            "ix_suprimentos_alcadas_aprovacao_categoria_id",
            "suprimentos_alcadas_aprovacao",
            ["categoria_id"],
        )
        op.create_index(
            "ix_suprimentos_alcadas_aprovacao_ativo",
            "suprimentos_alcadas_aprovacao",
            ["ativo"],
        )
    else:
        alcadas_colunas = [
            coluna["name"]
            for coluna in inspector.get_columns("suprimentos_alcadas_aprovacao")
        ]
        if "telefone_whatsapp" not in alcadas_colunas:
            with op.batch_alter_table("suprimentos_alcadas_aprovacao") as batch_op:
                batch_op.add_column(sa.Column("telefone_whatsapp", sa.String(20), nullable=True))

    cotacoes_colunas = [coluna["name"] for coluna in inspector.get_columns("suprimentos_cotacoes")]
    with op.batch_alter_table("suprimentos_cotacoes") as batch_op:
        if "aprovador_usuario_id" not in cotacoes_colunas:
            batch_op.add_column(sa.Column("aprovador_usuario_id", sa.Integer(), nullable=True))
            batch_op.create_index("ix_suprimentos_cotacoes_aprovador_usuario_id", ["aprovador_usuario_id"])
            batch_op.create_foreign_key(
                "fk_suprimentos_cotacoes_aprovador_usuario_id",
                "usuarios",
                ["aprovador_usuario_id"],
                ["id"],
            )
        if "alcada_aprovacao_id" not in cotacoes_colunas:
            batch_op.add_column(sa.Column("alcada_aprovacao_id", sa.Integer(), nullable=True))
            batch_op.create_index("ix_suprimentos_cotacoes_alcada_aprovacao_id", ["alcada_aprovacao_id"])
            batch_op.create_foreign_key(
                "fk_suprimentos_cotacoes_alcada_aprovacao_id",
                "suprimentos_alcadas_aprovacao",
                ["alcada_aprovacao_id"],
                ["id"],
            )

    inspector = sa.inspect(bind)
    if "suprimentos_alertas" not in inspector.get_table_names():
        op.create_table(
            "suprimentos_alertas",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("usuario_destinatario_id", sa.Integer(), nullable=False),
            sa.Column("criado_por_usuario_id", sa.Integer(), nullable=True),
            sa.Column("requisicao_id", sa.Integer(), nullable=True),
            sa.Column("cotacao_id", sa.Integer(), nullable=True),
            sa.Column("tipo", sa.String(40), nullable=False),
            sa.Column("titulo", sa.String(160), nullable=False),
            sa.Column("mensagem", sa.Text(), nullable=False),
            sa.Column("link_destino", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="Nao lido"),
            sa.Column("lido_em", sa.DateTime(), nullable=True),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["cotacao_id"], ["suprimentos_cotacoes.id"]),
            sa.ForeignKeyConstraint(["criado_por_usuario_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["requisicao_id"], ["suprimentos_requisicoes_compra.id"]),
            sa.ForeignKeyConstraint(["usuario_destinatario_id"], ["usuarios.id"]),
            sa.CheckConstraint("status in ('Nao lido', 'Lido')", name="ck_suprimentos_alertas_status"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_suprimentos_alertas_usuario_destinatario_id", "suprimentos_alertas", ["usuario_destinatario_id"])
        op.create_index("ix_suprimentos_alertas_criado_por_usuario_id", "suprimentos_alertas", ["criado_por_usuario_id"])
        op.create_index("ix_suprimentos_alertas_requisicao_id", "suprimentos_alertas", ["requisicao_id"])
        op.create_index("ix_suprimentos_alertas_cotacao_id", "suprimentos_alertas", ["cotacao_id"])
        op.create_index("ix_suprimentos_alertas_tipo", "suprimentos_alertas", ["tipo"])
        op.create_index("ix_suprimentos_alertas_status", "suprimentos_alertas", ["status"])

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
            _criar_ou_atualizar_modulo(
                bind,
                departamento.id,
                "alcadas_aprovacao",
                "Alcadas de Aprovacao",
                "Cadastro de aprovadores por valor de proposta",
                12,
            )
            _criar_ou_atualizar_modulo(
                bind,
                departamento.id,
                "alertas",
                "Alertas",
                "Central de alertas internos de Suprimentos",
                13,
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "modulos" in inspector.get_table_names():
        modulos = sa.table("modulos", sa.column("slug", sa.String()))
        bind.execute(modulos.delete().where(modulos.c.slug.in_(["alcadas_aprovacao", "alertas"])))

    if "suprimentos_alertas" in inspector.get_table_names():
        op.drop_index("ix_suprimentos_alertas_status", table_name="suprimentos_alertas")
        op.drop_index("ix_suprimentos_alertas_tipo", table_name="suprimentos_alertas")
        op.drop_index("ix_suprimentos_alertas_cotacao_id", table_name="suprimentos_alertas")
        op.drop_index("ix_suprimentos_alertas_requisicao_id", table_name="suprimentos_alertas")
        op.drop_index("ix_suprimentos_alertas_criado_por_usuario_id", table_name="suprimentos_alertas")
        op.drop_index("ix_suprimentos_alertas_usuario_destinatario_id", table_name="suprimentos_alertas")
        op.drop_table("suprimentos_alertas")

    cotacoes_colunas = [coluna["name"] for coluna in inspector.get_columns("suprimentos_cotacoes")]
    with op.batch_alter_table("suprimentos_cotacoes") as batch_op:
        if "alcada_aprovacao_id" in cotacoes_colunas:
            batch_op.drop_constraint("fk_suprimentos_cotacoes_alcada_aprovacao_id", type_="foreignkey")
            batch_op.drop_index("ix_suprimentos_cotacoes_alcada_aprovacao_id")
            batch_op.drop_column("alcada_aprovacao_id")
        if "aprovador_usuario_id" in cotacoes_colunas:
            batch_op.drop_constraint("fk_suprimentos_cotacoes_aprovador_usuario_id", type_="foreignkey")
            batch_op.drop_index("ix_suprimentos_cotacoes_aprovador_usuario_id")
            batch_op.drop_column("aprovador_usuario_id")

    if "suprimentos_alcadas_aprovacao" in inspector.get_table_names():
        op.drop_index("ix_suprimentos_alcadas_aprovacao_ativo", table_name="suprimentos_alcadas_aprovacao")
        op.drop_index("ix_suprimentos_alcadas_aprovacao_categoria_id", table_name="suprimentos_alcadas_aprovacao")
        op.drop_index("ix_suprimentos_alcadas_aprovacao_centro_custo_id", table_name="suprimentos_alcadas_aprovacao")
        op.drop_index("ix_suprimentos_alcadas_aprovacao_usuario_aprovador_id", table_name="suprimentos_alcadas_aprovacao")
        op.drop_table("suprimentos_alcadas_aprovacao")
