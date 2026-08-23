from app import create_app
from app.extensions import db
from app.models import (
    NivelAcesso,
    Usuario,
    Departamento,
    Modulo,
    Equipe,
)


app = create_app()


NIVEIS_ACESSO = [
    {
        "nome": "Administrador",
        "slug": "administrador",
        "descricao": "Acesso total ao sistema."
    },
    {
        "nome": "Diretoria",
        "slug": "diretoria",
        "descricao": "Acesso amplo para consulta, dashboards e relatórios."
    },
    {
        "nome": "Gestor",
        "slug": "gestor",
        "descricao": "Gerencia módulos autorizados do departamento."
    },
    {
        "nome": "Operador",
        "slug": "operador",
        "descricao": "Executa cadastros e edições conforme permissão."
    },
    {
        "nome": "Consulta",
        "slug": "consulta",
        "descricao": "Acesso apenas para visualização."
    },
]


DEPARTAMENTOS = [
    {
        "nome": "Financeiro",
        "slug": "financeiro",
        "descricao": "Controle financeiro, contas, fluxo de caixa e relatórios.",
        "icone": "grafico",
        "ordem": 1,
        "modulos": [
            ("Contas a Pagar", "contas_a_pagar", "Vencimentos e aprovações"),
            ("Contas a Receber", "contas_a_receber", "Clientes e recebimentos"),
            ("Fluxo de Caixa", "fluxo_de_caixa", "Entradas e saídas"),
            ("Orçamentos", "orcamentos", "Planejamento e previsão"),
            ("Faturamento", "faturamento", "Emissão e acompanhamento"),
            ("Relatórios", "relatorios", "Indicadores e análise"),
        ],
    },
    {
        "nome": "Operação",
        "slug": "operacao",
        "descricao": "Execução, equipes e produtividade operacional.",
        "icone": "engrenagem",
        "ordem": 2,
        "modulos": [
            ("Ordens de Serviço", "ordens_de_servico", "Abertura e acompanhamento"),
            ("Equipes", "equipes", "Times e alocação"),
            ("Cronograma", "cronograma", "Prazos e agenda"),
            ("Checklists", "checklists", "Inspeções e rotinas"),
            ("Apontamentos", "apontamentos", "Horas e produção"),
            ("Indicadores", "indicadores", "Desempenho operacional"),
            ("Gestao de Veiculos e EPGs", "gestao_veiculos_epgs", "Pool operacional de veiculos, equipamentos e EPGs"),
        ],
    },
    {
        "nome": "Departamento Pessoal",
        "slug": "departamento_pessoal",
        "descricao": "Gestão de pessoas e rotinas trabalhistas.",
        "icone": "usuarios",
        "ordem": 3,
        "modulos": [
            ("Colaboradores", "colaboradores", "Cadastro e consulta de colaboradores"),
            ("Admissão", "admissao", "Cadastro e integração"),
            ("Folha de Pagamento", "folha_de_pagamento", "Processamento mensal"),
            ("Ponto", "ponto", "Jornadas e marcações"),
            ("Férias", "ferias", "Programação e controle"),
            ("Documentos", "documentos", "Arquivos e pendências"),
            ("Pedido de Refeições", "pedido_refeicoes", "Controle de refeições, bebidas e pedidos"),
        ],
    },
    {
        "nome": "Segurança do Trabalho",
        "slug": "seguranca_trabalho",
        "descricao": "Conformidade, prevenção e inspeções.",
        "icone": "escudo",
        "ordem": 4,
        "modulos": [
            ("EPIs", "epis", "Entrega e controle"),
            ("Treinamentos", "treinamentos", "Capacitação e validade"),
            ("Inspeções", "inspecoes", "Rotinas e auditorias"),
            ("Incidentes", "incidentes", "Registros e análise"),
            ("APR", "apr", "Análise preliminar de risco"),
            ("Documentação", "documentacao", "Laudos e certificados"),
        ],
    },
]

EQUIPES_INICIAIS = [
    "TMC - INFRAESTRUTURA",
    "TMC - GUARUJA",
    "TMC - FIXA PORTO",
    "TMC - SANTOS",
    "TMC - CALCETARIA",
    "TMC - LIMPEZA II",
    "TMC - FIXA GUARUJA",
    "OPERACAO",
    "ADMINISTRACAO",
    "TMC - LIMPEZA",
    "TMC - AMV",
    "TEG TEAG",
    "TMC - FIXA PARATINGA",
]


def gerar_slug(texto):
    texto = texto.strip().lower()
    substituicoes = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    for original, novo in substituicoes.items():
        texto = texto.replace(original, novo)

    caracteres = []
    for caractere in texto:
        if caractere.isalnum():
            caracteres.append(caractere)
        else:
            caracteres.append("_")

    slug = "".join(caracteres)

    while "__" in slug:
        slug = slug.replace("__", "_")

    return slug.strip("_")


ADMIN_EMAIL = "admin@rentalretros.com.br"
ADMIN_SENHA_TEMPORARIA = "Admin@123"


def criar_niveis_acesso():
    for item in NIVEIS_ACESSO:
        nivel = NivelAcesso.query.filter_by(slug=item["slug"]).first()

        if not nivel:
            nivel = NivelAcesso(
                nome=item["nome"],
                slug=item["slug"],
                descricao=item["descricao"],
                ativo=True,
            )
            db.session.add(nivel)
            print(f"[OK] Nível criado: {item['nome']}")
        else:
            print(f"[AVISO] Nível já existe: {item['nome']}")


def criar_departamentos_e_modulos():
    for item in DEPARTAMENTOS:
        departamento = Departamento.query.filter_by(slug=item["slug"]).first()

        if not departamento:
            departamento = Departamento(
                nome=item["nome"],
                slug=item["slug"],
                descricao=item["descricao"],
                icone=item["icone"],
                ordem=item["ordem"],
                ativo=True,
            )
            db.session.add(departamento)
            db.session.flush()
            print(f"[OK] Departamento criado: {item['nome']}")
        else:
            print(f"[AVISO] Departamento já existe: {item['nome']}")

        for ordem, modulo_item in enumerate(item["modulos"], start=1):
            nome, slug, descricao = modulo_item

            modulo = Modulo.query.filter_by(
                departamento_id=departamento.id,
                slug=slug
            ).first()

            if not modulo:
                modulo = Modulo(
                    departamento_id=departamento.id,
                    nome=nome,
                    slug=slug,
                    descricao=descricao,
                    ordem=ordem,
                    ativo=True,
                )
                db.session.add(modulo)
                print(f"[OK] Módulo criado: {item['nome']} > {nome}")
            else:
                print(f"[AVISO] Módulo já existe: {item['nome']} > {nome}")


def criar_admin_inicial():
    nivel_admin = NivelAcesso.query.filter_by(slug="administrador").first()

    if not nivel_admin:
        print("[ERRO] Nível administrador não encontrado.")
        return

    email_normalizado = ADMIN_EMAIL.strip().lower()

    usuario = Usuario.query.filter_by(email=email_normalizado).first()

    if not usuario:
        usuario = Usuario(
            nome="Administrador",
            email=email_normalizado,
            nivel_acesso_id=nivel_admin.id,
            ativo=True,
        )
        usuario.definir_senha(ADMIN_SENHA_TEMPORARIA)

        db.session.add(usuario)
        print("[OK] Usuário administrador criado.")
        print(f"     E-mail: {ADMIN_EMAIL}")
        print(f"     Senha temporária: {ADMIN_SENHA_TEMPORARIA}")
    else:
        print("[AVISO] Usuário administrador já existe.")

def criar_equipes_iniciais():
    for nome_equipe in EQUIPES_INICIAIS:
        slug = gerar_slug(nome_equipe)

        equipe = Equipe.query.filter_by(slug=slug).first()

        if not equipe:
            equipe = Equipe(
                nome=nome_equipe,
                slug=slug,
                ativo=True,
            )
            db.session.add(equipe)
            print(f"[OK] Equipe criada: {nome_equipe}")
        else:
            print(f"[AVISO] Equipe já existe: {nome_equipe}")


def executar_seed():
    with app.app_context():
        criar_niveis_acesso()
        db.session.commit()

        criar_departamentos_e_modulos()
        db.session.commit()

        criar_admin_inicial()
        db.session.commit()

        criar_equipes_iniciais()
        db.session.commit()

        print("=" * 60)
        print("Seed executado com sucesso.")
        print("=" * 60)


if __name__ == "__main__":
    executar_seed()
