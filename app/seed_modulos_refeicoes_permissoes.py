from app import create_app
from app.extensions import db
from app.models import Departamento, Modulo, PermissaoUsuarioModulo


DEPARTAMENTO_SLUG = "departamento_pessoal"
MODULO_ANTIGO_SLUGS = ["pedido_refeicoes", "pedido-refeicoes"]
MODULO_ANTIGO_NOME = "Pedido de Refeições"

NOVOS_MODULOS = [
    {
        "nome": "Pedido de Refeições - Restaurantes",
        "slug": "pedido-refeicoes-restaurantes",
        "descricao": "Cadastro e gestão de restaurantes utilizados nos pedidos de refeições.",
        "ordem": 20,
    },
    {
        "nome": "Pedido de Refeições - Cardápio",
        "slug": "pedido-refeicoes-cardapio",
        "descricao": "Cadastro e gestão de pratos, bebidas e itens de cardápio por restaurante.",
        "ordem": 21,
    },
    {
        "nome": "Pedido de Refeições - Pedidos",
        "slug": "pedido-refeicoes-pedidos",
        "descricao": "Criação, edição, fechamento e envio de pedidos de refeição.",
        "ordem": 22,
    },
    {
        "nome": "Pedido de Refeições - Relatórios",
        "slug": "pedido-refeicoes-relatorios",
        "descricao": "Consulta, análise e exportação dos relatórios de refeições.",
        "ordem": 23,
    },
]

ACOES = [
    "pode_visualizar",
    "pode_criar",
    "pode_editar",
    "pode_excluir",
    "pode_aprovar",
    "pode_exportar",
]


def buscar_modulo(departamento_id, slug):
    return Modulo.query.filter_by(
        departamento_id=departamento_id,
        slug=slug,
    ).first()


def criar_ou_atualizar_modulos(departamento):
    criados = 0
    atualizados = 0
    modulos_novos = []

    for dados in NOVOS_MODULOS:
        modulo = buscar_modulo(departamento.id, dados["slug"])

        if modulo:
            modulo.nome = dados["nome"]
            modulo.descricao = dados["descricao"]
            modulo.ordem = dados["ordem"]
            modulo.ativo = True
            atualizados += 1
        else:
            modulo = Modulo(
                departamento_id=departamento.id,
                nome=dados["nome"],
                slug=dados["slug"],
                descricao=dados["descricao"],
                ativo=True,
                ordem=dados["ordem"],
            )
            db.session.add(modulo)
            criados += 1

        modulos_novos.append(modulo)

    db.session.flush()
    return modulos_novos, criados, atualizados


def copiar_permissoes_antigas(departamento, modulos_novos):
    modulo_antigo = None

    for slug in MODULO_ANTIGO_SLUGS:
        modulo_antigo = buscar_modulo(departamento.id, slug)

        if modulo_antigo:
            break

    if not modulo_antigo:
        modulo_antigo = Modulo.query.filter_by(
            departamento_id=departamento.id,
            nome=MODULO_ANTIGO_NOME,
        ).first()

    if not modulo_antigo:
        return 0, 0, 0

    permissoes_antigas = PermissaoUsuarioModulo.query.filter_by(
        modulo_id=modulo_antigo.id,
        ativo=True,
    ).all()

    permissoes_criadas = 0
    permissoes_atualizadas = 0

    for permissao_antiga in permissoes_antigas:
        for modulo_novo in modulos_novos:
            permissao = PermissaoUsuarioModulo.query.filter_by(
                usuario_id=permissao_antiga.usuario_id,
                modulo_id=modulo_novo.id,
            ).first()

            if not permissao:
                permissao = PermissaoUsuarioModulo(
                    usuario_id=permissao_antiga.usuario_id,
                    modulo_id=modulo_novo.id,
                )
                db.session.add(permissao)
                permissoes_criadas += 1
            else:
                permissoes_atualizadas += 1

            for campo in ACOES:
                valor_atual = bool(getattr(permissao, campo, False))
                valor_antigo = bool(getattr(permissao_antiga, campo, False))
                setattr(permissao, campo, valor_atual or valor_antigo)

            permissao.ativo = True
            permissao.garantir_visualizacao()

    return len(permissoes_antigas), permissoes_criadas, permissoes_atualizadas


def executar_seed():
    print("Seed de submódulos de refeições iniciado...")

    departamento = Departamento.query.filter_by(
        slug=DEPARTAMENTO_SLUG,
        ativo=True,
    ).first()

    if not departamento:
        print("Departamento Pessoal não encontrado ou inativo.")
        return

    modulos_novos, modulos_criados, modulos_atualizados = criar_ou_atualizar_modulos(departamento)
    permissoes_antigas, permissoes_criadas, permissoes_atualizadas = copiar_permissoes_antigas(
        departamento,
        modulos_novos,
    )

    db.session.commit()

    print("Seed de submódulos de refeições concluído com sucesso.")
    print(f"Módulos criados: {modulos_criados}")
    print(f"Módulos atualizados: {modulos_atualizados}")
    print(f"Permissões antigas encontradas: {permissoes_antigas}")
    print(f"Permissões copiadas/criadas: {permissoes_criadas}")
    print(f"Permissões atualizadas/preservadas: {permissoes_atualizadas}")
    print("Módulos processados:")

    for modulo in modulos_novos:
        print(f"- {modulo.nome} ({modulo.slug})")


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        executar_seed()
