"""cria gestao veiculos epgs operacao

Revision ID: f15a1c9e0b7d
Revises: e9c4b2a7d6f1
Create Date: 2026-08-14 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f15a1c9e0b7d"
down_revision = "b2e6f8a9c4d1"
branch_labels = None
depends_on = None


TABELA = "operacao_veiculos_equipamentos"

REGISTROS_INICIAIS = [
    ("STG7D96", "CITROEN JUMPY", "9V7VBYHVERA007070", "Quitado", "Veiculo leve"),
    ("RMJ4E07", "M BENZ - ACCELO 1016", "9BM979078LB191211", "Quitado", "Caminhao"),
    ("QNH0H80", "M BENZ - ACCELO 1016", "9BM979026JB075295", "Quitado", "Caminhao"),
    ("FUV6F90", "FORD - CARGO 816", "9BFVEADS1EBS69487", "Quitado", "Caminhao"),
    ("IWQ7F41", "FORD - CARGO 1319", "9BFXEB1B1FBS73432", "Quitado", "Caminhao"),
    ("SWLC90", "VOLKS - EXPRESS", "95355FTEXPR042128", "Quitado", "Caminhao"),
    ("SUD8D27", "CASE - 580N SERIE 2", "HBZN580NPRAH34224", "Quitado", "Maquina"),
    ("SWO7D00", "CASE - 580N SERIE 2", "HBZN580NJPAH31968", "Quitado", "Maquina"),
    ("FDE3E21", "CASE - 580N TC", "HBZN580NHNAH30415", "Quitado", "Maquina"),
    ("FKC0H21", "CASE - 580N TC", "HBZN580NKNAH30413", "Quitado", "Maquina"),
    ("FCT4A64", "JOHN DEERE - 310L", "1BZ310LAKJD001386", "Quitado", "Maquina"),
    ("EXR7I36", "JOHN DEERE - 310L", "1BZ310LAJKD002105", "Quitado", "Maquina"),
    ("TKG7G47", "NEW HOLLAND - B95C", "HBZNB95CTRAH34101", "Quitado", "Maquina"),
    ("DED1G69", "NEW HOLLAND - B95B", "HBZNB95BLGAH15935", "Quitado", "Maquina"),
    ("RVP9D49", "FIAT MOBI LIKE", "9BD341ACZPY851075", "Quitado", "Veiculo leve"),
    ("RFD7B93", "FIAT MOBI LIKE", "9BD341A5XLY680113", "Quitado", "Veiculo leve"),
    ("RFD1D62", "FIAT MOBI LIKE", "9BD341A5XLY680509", "Quitado", "Veiculo leve"),
    ("QXN5F52", "FIAT MOBI LIKE", "9BD341A5XLY669544", "Quitado", "Veiculo leve"),
    ("SDS7F82", "VOLKS VOYAGE", "9BWDG45U1PT055300", "Quitado", "Veiculo leve"),
    ("GAG9B93", "VOLKS SAVEIRO", "9BWKB45U5KP017849", "Quitado", "Veiculo leve"),
    ("TKS5F97", "CITROEN BASALT", "935CPFCA7SB556035", "Quitado", "Veiculo leve"),
    ("ESC HIDRÁULICA", "JOHN DEERE - 200G", "1F9200GXPND020551", "Financiado", "Maquina"),
    ("TJF7D14", "VW/EXPRESS DRF 4X2", "95355FTE9SR015706", "Financiado", "Caminhao"),
    ("SWU3F73", "VOLKS - DELIVERY 11.180", "9535E6TB4PR054099", "Financiado", "Caminhao"),
    ("FJJ3E14", "VOLKS - CONSTELATION 31320", "9536C8TL9SR002684", "Financiado", "Caminhao"),
]


def _table_names(inspector):
    return set(inspector.get_table_names())


def _criar_tabela(inspector):
    if TABELA in _table_names(inspector):
        return False

    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identificacao", sa.String(length=120), nullable=False),
        sa.Column("placa", sa.String(length=20), nullable=True),
        sa.Column("descricao", sa.String(length=220), nullable=False),
        sa.Column("chassi", sa.String(length=80), nullable=True),
        sa.Column("renavam", sa.String(length=40), nullable=True),
        sa.Column("centro_custo", sa.String(length=360), nullable=False),
        sa.Column("situacao_aquisicao", sa.String(length=30), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "situacao_aquisicao in ('Quitado', 'Financiado')",
            name="ck_operacao_veiculos_situacao_aquisicao",
        ),
        sa.CheckConstraint(
            "tipo in ('Veiculo leve', 'Caminhao', 'Maquina', 'Equipamento', 'EPG', 'Outro')",
            name="ck_operacao_veiculos_tipo",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chassi", name="uq_operacao_veiculos_equipamentos_chassi"),
        sa.UniqueConstraint("identificacao", name="uq_operacao_veiculos_equipamentos_identificacao"),
    )
    op.create_index("ix_operacao_veiculos_identificacao", TABELA, ["identificacao"])
    op.create_index("ix_operacao_veiculos_placa", TABELA, ["placa"])
    op.create_index("ix_operacao_veiculos_chassi", TABELA, ["chassi"])
    op.create_index("ix_operacao_veiculos_centro_custo", TABELA, ["centro_custo"])
    op.create_index("ix_operacao_veiculos_ativo", TABELA, ["ativo"])
    return True


def _garantir_modulo_operacao(conn):
    departamentos = sa.table(
        "departamentos",
        sa.column("id", sa.Integer),
        sa.column("slug", sa.String),
    )
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

    departamento = conn.execute(
        sa.select(departamentos.c.id).where(departamentos.c.slug == "operacao")
    ).first()

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
            nome="Gestão de Veículos e EPGs",
            slug="gestao_veiculos_epgs",
            descricao="Cadastro e consulta de veículos, máquinas e equipamentos operacionais",
            icone=None,
            ativo=True,
            ordem=7,
            criado_em=sa.func.now(),
            atualizado_em=sa.func.now(),
        )
    )


def _carga_inicial(conn):
    veiculos = sa.table(
        TABELA,
        sa.column("identificacao", sa.String),
        sa.column("placa", sa.String),
        sa.column("descricao", sa.String),
        sa.column("chassi", sa.String),
        sa.column("renavam", sa.String),
        sa.column("centro_custo", sa.String),
        sa.column("situacao_aquisicao", sa.String),
        sa.column("tipo", sa.String),
        sa.column("ativo", sa.Boolean),
    )

    for identificacao, descricao, chassi, situacao, tipo in REGISTROS_INICIAIS:
        existente = conn.execute(
            sa.select(sa.literal(1)).select_from(veiculos).where(
                sa.or_(
                    veiculos.c.chassi == chassi,
                    veiculos.c.identificacao == identificacao,
                )
            )
        ).first()

        if existente:
            continue

        conn.execute(
            veiculos.insert().values(
                identificacao=identificacao,
                placa=identificacao if identificacao != "ESC HIDRÁULICA" else None,
                descricao=descricao,
                chassi=chassi,
                renavam=None,
                centro_custo=f"{identificacao}-{descricao}",
                situacao_aquisicao=situacao,
                tipo=tipo,
                ativo=True,
            )
        )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tabela_criada = _criar_tabela(inspector)
    _garantir_modulo_operacao(bind)
    if tabela_criada:
        _carga_inicial(bind)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if TABELA not in _table_names(inspector):
        return

    op.drop_index("ix_operacao_veiculos_ativo", table_name=TABELA)
    op.drop_index("ix_operacao_veiculos_centro_custo", table_name=TABELA)
    op.drop_index("ix_operacao_veiculos_chassi", table_name=TABELA)
    op.drop_index("ix_operacao_veiculos_placa", table_name=TABELA)
    op.drop_index("ix_operacao_veiculos_identificacao", table_name=TABELA)
    op.drop_table(TABELA)
