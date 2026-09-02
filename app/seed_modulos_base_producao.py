from app.extensions import db
from app.models import Departamento, Modulo


DEPARTAMENTOS_BASE = [
    {
        "nome": "Administração",
        "slug": "administracao",
        "descricao": "Gestão administrativa, usuários, permissões e auditoria do sistema.",
        "icone": "admin",
        "ordem": 0,
        "modulos": [],
    },
    {
        "nome": "Financeiro",
        "slug": "financeiro",
        "descricao": "Controle financeiro, contas, fluxo de caixa e relatórios.",
        "icone": "grafico",
        "ordem": 1,
        "modulos": [
            ("Contas a Pagar", "contas_a_pagar", "Vencimentos e aprovações"),
            ("Contas a Receber", "contas_a_receber", "Clientes e recebimentos"),
            ("Clientes", "clientes", "Cadastro central de clientes financeiros"),
            ("Fluxo de Caixa", "fluxo_de_caixa", "Entradas e saídas"),
            ("Orçamentos", "orcamentos", "Planejamento e previsão"),
            ("Faturamento", "faturamento", "Emissão e acompanhamento"),
            ("Relatórios", "relatorios", "Indicadores e análise"),
        ],
    },
    {
        "nome": "Suprimentos",
        "slug": "suprimentos",
        "descricao": "Cadastro de fornecedores, itens, centros de custo e base do processo de compras.",
        "icone": "compras",
        "ordem": 2,
        "modulos": [
            ("Fornecedores", "fornecedores", "Cadastro e consulta de fornecedores"),
            ("Categorias", "categorias", "Categorias de itens, materiais e servicos"),
            ("Unidades de Medida", "unidades_medida", "Unidades usadas nos itens de compra"),
            ("Itens", "itens", "Materiais, servicos, pecas, EPIs e consumo"),
            ("Centros de Custo", "centros_custo", "Centros de custo para compras e integracao futura"),
            ("Fornecedor x Item", "fornecedor_itens", "Vinculo comercial entre fornecedores e itens"),
            ("Requisicoes de Compra", "requisicoes_compra", "Solicitacao interna de compras e servicos"),
            ("Cotacoes", "cotacoes", "Registro de propostas de fornecedores para requisicoes enviadas"),
            ("Ordens de Compra", "ordens_compra", "Geracao e consulta de ordens de compra aprovadas"),
            ("Estoque", "estoque", "Consulta de saldos e historico de movimentacoes de estoque"),
            ("Indicadores", "indicadores", "Indicadores e relatorios gerenciais de Suprimentos"),
            ("Alcadas de Aprovacao", "alcadas_aprovacao", "Cadastro de aprovadores por valor de proposta"),
            ("Compradores", "compradores", "Cadastro de compradores para envio de requisicoes por WhatsApp"),
        ],
    },
    {
        "nome": "Operação",
        "slug": "operacao",
        "descricao": "Execução, equipes e produtividade operacional.",
        "icone": "engrenagem",
        "ordem": 3,
        "modulos": [
            ("Veículos e Equipamentos", "veiculos_equipamentos", "Cadastro, consulta, edição e controle de status da frota operacional"),
            ("Pool de Veículos", "pool_veiculos", "Responsabilidade operacional, disponibilidade e histórico de leituras"),
            ("Abastecimento", "abastecimento", "Registro e consulta de abastecimentos dos veículos"),
            ("Multas de Trânsito", "multas_transito", "Cadastro e consulta de multas de trânsito por veículo"),
            ("Impostos e Taxas", "impostos_taxas", "Cadastro e consulta de parcelas de IPVA e licenciamento"),
            ("Central de Custos", "central_custos", "Consulta consolidada de custos por veículo ou equipamento"),
            ("Ordens de Serviço", "ordens_de_servico", "Abertura e acompanhamento"),
            ("Equipes", "equipes", "Times e alocação"),
            ("Cronograma", "cronograma", "Prazos e agenda"),
            ("Checklists", "checklists", "Inspeções e rotinas"),
            ("Apontamentos", "apontamentos", "Horas e produção"),
            ("Indicadores", "indicadores", "Desempenho operacional"),
        ],
    },
    {
        "nome": "Departamento Pessoal",
        "slug": "departamento_pessoal",
        "descricao": "Gestão de pessoas e rotinas trabalhistas.",
        "icone": "usuarios",
        "ordem": 4,
        "modulos": [
            ("Colaboradores", "colaboradores", "Cadastro e consulta de colaboradores"),
            ("Admissão", "admissao", "Cadastro e integração"),
            ("Folha de Pagamento", "folha_de_pagamento", "Processamento mensal"),
            ("Ponto", "ponto", "Jornadas e marcações"),
            ("Férias", "ferias", "Programação e controle"),
            ("Documentos", "documentos", "Arquivos e pendências"),
            ("Pedido de Refeições", "pedido_refeicoes", "Controle de refeições, bebidas e pedidos"),
            ("Vale Transporte", "vale_transporte", "Cadastro de linhas e vínculos de Vale Transporte"),
        ],
    },
    {
        "nome": "Segurança do Trabalho",
        "slug": "seguranca_trabalho",
        "descricao": "Conformidade, prevenção e inspeções.",
        "icone": "escudo",
        "ordem": 5,
        "modulos": [
            ("EPIs", "epis", "Entrega e controle"),
            ("Treinamentos", "treinamentos", "Capacitação e validade"),
            ("Inspeções", "inspecoes", "Rotinas e auditorias"),
            ("Incidentes", "incidentes", "Registros e análise"),
            ("APR", "apr", "Análise preliminar de risco"),
            ("Documentação", "documentacao", "Laudos e certificados"),
        ],
    },
    {
        "nome": "Fiscal",
        "slug": "fiscal",
        "descricao": "Central de documentos fiscais, XMLs, DANFEs e integrações com compras.",
        "icone": "documentos",
        "ordem": 6,
        "modulos": [
            ("Documentos Fiscais", "documentos_fiscais", "Central fiscal para XMLs, DANFEs e vínculo com O.C."),
        ],
    },
]


def criar_ou_atualizar_departamento(dados):
    departamento = Departamento.query.filter_by(slug=dados["slug"]).first()
    criado = False

    if not departamento:
        departamento = Departamento(slug=dados["slug"])
        db.session.add(departamento)
        criado = True

    departamento.nome = dados["nome"]
    departamento.descricao = dados["descricao"]
    departamento.icone = dados["icone"]
    departamento.ordem = dados["ordem"]
    departamento.ativo = True

    db.session.flush()
    return departamento, criado


def criar_ou_atualizar_modulo(departamento, ordem, dados_modulo):
    nome, slug, descricao = dados_modulo

    modulo = Modulo.query.filter_by(
        departamento_id=departamento.id,
        slug=slug,
    ).first()
    criado = False

    if not modulo:
        modulo = Modulo(
            departamento_id=departamento.id,
            slug=slug,
        )
        db.session.add(modulo)
        criado = True

    modulo.nome = nome
    modulo.descricao = descricao
    modulo.ordem = ordem
    modulo.ativo = True

    return modulo, criado


def executar_seed():
    print("Seed de módulos base iniciado...")

    departamentos_criados = 0
    departamentos_preservados = 0
    modulos_criados = 0
    modulos_preservados = 0
    processados = []

    for dados_departamento in DEPARTAMENTOS_BASE:
        departamento, departamento_criado = criar_ou_atualizar_departamento(
            dados_departamento,
        )

        if departamento_criado:
            departamentos_criados += 1
        else:
            departamentos_preservados += 1

        modulos_processados = []

        for ordem, dados_modulo in enumerate(dados_departamento["modulos"], start=1):
            modulo, modulo_criado = criar_ou_atualizar_modulo(
                departamento,
                ordem,
                dados_modulo,
            )

            if modulo_criado:
                modulos_criados += 1
            else:
                modulos_preservados += 1

            modulos_processados.append(f"{modulo.nome} ({modulo.slug})")

        processados.append(
            {
                "departamento": f"{departamento.nome} ({departamento.slug})",
                "modulos": modulos_processados,
            }
        )

    db.session.commit()

    print("Departamentos criados:", departamentos_criados)
    print("Departamentos atualizados/preservados:", departamentos_preservados)
    print("Módulos criados:", modulos_criados)
    print("Módulos atualizados/preservados:", modulos_preservados)
    print("Permissões alteradas: 0")
    print("Departamentos e módulos processados:")

    for item in processados:
        print(f"- {item['departamento']}")

        if not item["modulos"]:
            print("  Sem módulos base neste seed.")
            continue

        for modulo in item["modulos"]:
            print(f"  - {modulo}")

    print("Seed de módulos base concluído com sucesso.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()

    with app.app_context():
        executar_seed()
