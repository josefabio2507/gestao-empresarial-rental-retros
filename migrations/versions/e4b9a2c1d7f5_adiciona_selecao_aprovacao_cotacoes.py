"""adiciona selecao aprovacao cotacoes

Revision ID: e4b9a2c1d7f5
Revises: d9f3b7a6c2e1
Create Date: 2026-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e4b9a2c1d7f5"
down_revision = "d9f3b7a6c2e1"
branch_labels = None
depends_on = None


STATUS_COTACAO_CHECK = (
    "status in ('Aberta', 'Em Aprovacao', 'Aprovada', "
    "'Reprovada', 'Encerrada', 'Cancelada')"
)


def coluna_existe(inspector, tabela, coluna):
    return coluna in {item["name"] for item in inspector.get_columns(tabela)}


def indice_existe(inspector, tabela, indice):
    return indice in {item["name"] for item in inspector.get_indexes(tabela)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_cotacoes" in inspector.get_table_names():
        colunas = {item["name"] for item in inspector.get_columns("suprimentos_cotacoes")}

        with op.batch_alter_table("suprimentos_cotacoes", recreate="always") as batch_op:
            if "enviada_aprovacao_em" not in colunas:
                batch_op.add_column(sa.Column("enviada_aprovacao_em", sa.DateTime(), nullable=True))
            if "aprovada_em" not in colunas:
                batch_op.add_column(sa.Column("aprovada_em", sa.DateTime(), nullable=True))
            if "aprovada_por_usuario_id" not in colunas:
                batch_op.add_column(sa.Column("aprovada_por_usuario_id", sa.Integer(), nullable=True))
            if "reprovada_em" not in colunas:
                batch_op.add_column(sa.Column("reprovada_em", sa.DateTime(), nullable=True))
            if "reprovada_por_usuario_id" not in colunas:
                batch_op.add_column(sa.Column("reprovada_por_usuario_id", sa.Integer(), nullable=True))
            if "observacoes_aprovacao" not in colunas:
                batch_op.add_column(sa.Column("observacoes_aprovacao", sa.Text(), nullable=True))

            batch_op.drop_constraint("ck_suprimentos_cotacoes_status", type_="check")
            batch_op.create_check_constraint("ck_suprimentos_cotacoes_status", STATUS_COTACAO_CHECK)

            batch_op.create_foreign_key(
                "fk_suprimentos_cotacoes_aprovada_por_usuario_id",
                "usuarios",
                ["aprovada_por_usuario_id"],
                ["id"],
            )
            batch_op.create_foreign_key(
                "fk_suprimentos_cotacoes_reprovada_por_usuario_id",
                "usuarios",
                ["reprovada_por_usuario_id"],
                ["id"],
            )

    inspector = sa.inspect(bind)

    if "suprimentos_cotacao_propostas" in inspector.get_table_names():
        colunas = {item["name"] for item in inspector.get_columns("suprimentos_cotacao_propostas")}

        with op.batch_alter_table("suprimentos_cotacao_propostas", recreate="always") as batch_op:
            if "selecionada" not in colunas:
                batch_op.add_column(
                    sa.Column("selecionada", sa.Boolean(), nullable=False, server_default=sa.false())
                )
            if "justificativa_selecao" not in colunas:
                batch_op.add_column(sa.Column("justificativa_selecao", sa.Text(), nullable=True))
            if "selecionada_por_usuario_id" not in colunas:
                batch_op.add_column(sa.Column("selecionada_por_usuario_id", sa.Integer(), nullable=True))
            if "selecionada_em" not in colunas:
                batch_op.add_column(sa.Column("selecionada_em", sa.DateTime(), nullable=True))

            batch_op.create_foreign_key(
                "fk_suprimentos_cotacao_propostas_selecionada_por_usuario_id",
                "usuarios",
                ["selecionada_por_usuario_id"],
                ["id"],
            )

    inspector = sa.inspect(bind)

    for tabela, indices in {
        "suprimentos_cotacoes": [
            ("ix_suprimentos_cotacoes_aprovada_por_usuario_id", ["aprovada_por_usuario_id"]),
            ("ix_suprimentos_cotacoes_reprovada_por_usuario_id", ["reprovada_por_usuario_id"]),
        ],
        "suprimentos_cotacao_propostas": [
            ("ix_suprimentos_cotacao_propostas_selecionada", ["selecionada"]),
            ("ix_suprimentos_cotacao_propostas_selecionada_por_usuario_id", ["selecionada_por_usuario_id"]),
        ],
    }.items():
        if tabela not in inspector.get_table_names():
            continue

        for nome, colunas in indices:
            inspector = sa.inspect(bind)
            if not indice_existe(inspector, tabela, nome):
                op.create_index(nome, tabela, colunas)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "suprimentos_cotacao_propostas" in inspector.get_table_names():
        with op.batch_alter_table("suprimentos_cotacao_propostas", recreate="always") as batch_op:
            for nome in [
                "ix_suprimentos_cotacao_propostas_selecionada_por_usuario_id",
                "ix_suprimentos_cotacao_propostas_selecionada",
            ]:
                if indice_existe(inspector, "suprimentos_cotacao_propostas", nome):
                    batch_op.drop_index(nome)

            batch_op.drop_constraint(
                "fk_suprimentos_cotacao_propostas_selecionada_por_usuario_id",
                type_="foreignkey",
            )
            for coluna in [
                "selecionada_em",
                "selecionada_por_usuario_id",
                "justificativa_selecao",
                "selecionada",
            ]:
                if coluna_existe(inspector, "suprimentos_cotacao_propostas", coluna):
                    batch_op.drop_column(coluna)

    inspector = sa.inspect(bind)

    if "suprimentos_cotacoes" in inspector.get_table_names():
        with op.batch_alter_table("suprimentos_cotacoes", recreate="always") as batch_op:
            for nome in [
                "ix_suprimentos_cotacoes_reprovada_por_usuario_id",
                "ix_suprimentos_cotacoes_aprovada_por_usuario_id",
            ]:
                if indice_existe(inspector, "suprimentos_cotacoes", nome):
                    batch_op.drop_index(nome)

            batch_op.drop_constraint("fk_suprimentos_cotacoes_reprovada_por_usuario_id", type_="foreignkey")
            batch_op.drop_constraint("fk_suprimentos_cotacoes_aprovada_por_usuario_id", type_="foreignkey")
            batch_op.drop_constraint("ck_suprimentos_cotacoes_status", type_="check")
            batch_op.create_check_constraint(
                "ck_suprimentos_cotacoes_status",
                "status in ('Aberta', 'Encerrada', 'Cancelada')",
            )
            for coluna in [
                "observacoes_aprovacao",
                "reprovada_por_usuario_id",
                "reprovada_em",
                "aprovada_por_usuario_id",
                "aprovada_em",
                "enviada_aprovacao_em",
            ]:
                if coluna_existe(inspector, "suprimentos_cotacoes", coluna):
                    batch_op.drop_column(coluna)
