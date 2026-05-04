from app import create_app
from app.extensions import db
from app.models import Departamento, Modulo


app = create_app()


DEPARTAMENTOS = [
    {
        "nome": "Administração",
        "slug": "administracao",
        "descricao": "Gestão administrativa, usuários, permissões e configurações do sistema.",
        "modulos": [
            {
                "nome": "Usuários",
                "slug": "usuarios",
                "descricao": "Cadastro e gestão de usuários do sistema.",
            },
            {
                "nome": "Permissões",
                "slug": "permissoes",
                "descricao": "Gestão de permissões por usuário, departamento, módulo e ação.",
            },
        ],
    },
    {
        "nome": "Departamento Pessoal",
        "slug": "departamento_pessoal",
        "descricao": "Gestão de pessoas e rotinas trabalhistas.",
        "modulos": [
            {
                "nome": "Colaboradores",
                "slug": "colaboradores",
                "descricao": "Cadastro e consulta de colaboradores.",
            },
            {
                "nome": "Pedido de Refeições",
                "slug": "pedido_refeicoes",
                "descricao": "Controle de refeições, bebidas, pedidos e relatórios.",
            },
        ],
    },
    {
        "nome": "Financeiro",
        "slug": "financeiro",
        "descricao": "Controle financeiro, contas, relatórios e conferências.",
        "modulos": [],
    },
    {
        "nome": "Operação",
        "slug": "operacao",
        "descricao": "Gestão operacional e acompanhamento das frentes de serviço.",
        "modulos": [],
    },
    {
        "nome": "Segurança do Trabalho",
        "slug": "seguranca_trabalho",
        "descricao": "Gestão de segurança, documentos, treinamentos e rotinas de SST.",
        "modulos": [],
    },
]


def criar_ou_atualizar_departamento(nome, slug, descricao):
    departamento = Departamento.query.filter_by(slug=slug).first()

    if departamento:
        departamento.nome = nome
        departamento.descricao = descricao
        departamento.ativo = True
        return departamento, False

    departamento = Departamento(
        nome=nome,
        slug=slug,
        descricao=descricao,
        ativo=True,
    )

    db.session.add(departamento)
    db.session.flush()

    return departamento, True


def criar_ou_atualizar_modulo(departamento, nome, slug, descricao):
    modulo = Modulo.query.filter_by(
        departamento_id=departamento.id,
        slug=slug,
    ).first()

    if modulo:
        modulo.nome = nome
        modulo.descricao = descricao
        modulo.ativo = True
        return modulo, False

    modulo = Modulo(
        departamento_id=departamento.id,
        nome=nome,
        slug=slug,
        descricao=descricao,
        ativo=True,
    )

    db.session.add(modulo)
    db.session.flush()

    return modulo, True


with app.app_context():
    departamentos_criados = 0
    departamentos_atualizados = 0
    modulos_criados = 0
    modulos_atualizados = 0

    for item in DEPARTAMENTOS:
        departamento, criado = criar_ou_atualizar_departamento(
            nome=item["nome"],
            slug=item["slug"],
            descricao=item["descricao"],
        )

        if criado:
            departamentos_criados += 1
        else:
            departamentos_atualizados += 1

        for modulo_item in item["modulos"]:
            modulo, criado_modulo = criar_ou_atualizar_modulo(
                departamento=departamento,
                nome=modulo_item["nome"],
                slug=modulo_item["slug"],
                descricao=modulo_item["descricao"],
            )

            if criado_modulo:
                modulos_criados += 1
            else:
                modulos_atualizados += 1

    db.session.commit()

    print("Seed inicial de produção executada com sucesso.")
    print(f"Departamentos criados: {departamentos_criados}")
    print(f"Departamentos atualizados: {departamentos_atualizados}")
    print(f"Módulos criados: {modulos_criados}")
    print(f"Módulos atualizados: {modulos_atualizados}")