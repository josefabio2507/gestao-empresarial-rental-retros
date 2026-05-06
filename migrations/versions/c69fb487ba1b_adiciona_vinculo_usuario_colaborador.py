"""adiciona vinculo usuario colaborador

Revision ID: c69fb487ba1b
Revises: 2b8d6f4a9c31
Create Date: 2026-05-06 20:18:29.004840

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c69fb487ba1b'
down_revision = '2b8d6f4a9c31'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    colunas_usuarios = {
        coluna['name']
        for coluna in inspector.get_columns('usuarios')
    }
    indices_usuarios = {
        indice['name']
        for indice in inspector.get_indexes('usuarios')
    }
    fks_usuarios = {
        fk['name']
        for fk in inspector.get_foreign_keys('usuarios')
    }

    if 'colaborador_id' not in colunas_usuarios:
        op.add_column(
            'usuarios',
            sa.Column('colaborador_id', sa.Integer(), nullable=True),
        )

    if bind.dialect.name != 'sqlite':
        nome_fk = 'fk_usuarios_colaborador_id_colaboradores'

        if nome_fk not in fks_usuarios:
            op.create_foreign_key(
                nome_fk,
                'usuarios',
                'colaboradores',
                ['colaborador_id'],
                ['id'],
            )

    nome_indice = op.f('ix_usuarios_colaborador_id')

    if nome_indice not in indices_usuarios:
        op.create_index(
            nome_indice,
            'usuarios',
            ['colaborador_id'],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    colunas_usuarios = {
        coluna['name']
        for coluna in inspector.get_columns('usuarios')
    }
    indices_usuarios = {
        indice['name']
        for indice in inspector.get_indexes('usuarios')
    }
    fks_usuarios = {
        fk['name']
        for fk in inspector.get_foreign_keys('usuarios')
    }
    nome_indice = op.f('ix_usuarios_colaborador_id')

    if nome_indice in indices_usuarios:
        op.drop_index(nome_indice, table_name='usuarios')

    if bind.dialect.name != 'sqlite':
        nome_fk = 'fk_usuarios_colaborador_id_colaboradores'

        if nome_fk in fks_usuarios:
            op.drop_constraint(
                nome_fk,
                'usuarios',
                type_='foreignkey',
            )

    if 'colaborador_id' in colunas_usuarios:
        op.drop_column('usuarios', 'colaborador_id')
