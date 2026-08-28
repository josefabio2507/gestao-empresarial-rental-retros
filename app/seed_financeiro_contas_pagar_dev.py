import os
from datetime import date, datetime, timedelta

from sqlalchemy import inspect as sa_inspect

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    FinanceiroCartaoCredito,
    FinanceiroContaPagarBaixa,
    FinanceiroContaPagarTitulo,
    FiscalDocumento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosCategoriaItem,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosOrdemCompra,
    SuprimentosOrdemCompraItem,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.financeiro_contas_pagar_service import gerar_contas_pagar_xml, recalcular_pagamento_titulo, registrar_baixa_titulo, salvar_titulo
from app.services.suprimentos_service import (
    adicionar_item_requisicao,
    aprovar_cotacao,
    enviar_cotacao_para_aprovacao,
    enviar_requisicao_compra,
    gerar_ordens_compra_cotacao,
    preparar_financeiro_ordem_compra,
    provisionar_financeiro_ordem_compra,
    salvar_cotacao,
    salvar_proposta_cotacao,
    salvar_requisicao_compra,
    selecionar_proposta_vencedora,
)


def ambiente_local_liberado(app):
    if os.environ.get("ALLOW_DEV_SEED") != "1":
        return False

    if app.config.get("TESTING"):
        return True

    ambiente = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("APP_ENV")
        or os.environ.get("ENV")
        or ""
    ).lower()

    return ambiente in {"development", "dev", "local"}


def obter_ou_criar(modelo, filtro, dados):
    registro = modelo.query.filter_by(**filtro).first()
    if not registro:
        registro = modelo(**filtro)
        db.session.add(registro)

    for campo, valor in dados.items():
        setattr(registro, campo, valor)

    return registro


def garantir_financeiro_contas_pagar():
    departamento = obter_ou_criar(
        Departamento,
        {"slug": "financeiro"},
        {
            "nome": "Financeiro",
            "descricao": "Controle financeiro, contas, fluxo de caixa e relatorios.",
            "icone": "grafico",
            "ativo": True,
            "ordem": 1,
        },
    )
    db.session.flush()

    modulo = obter_ou_criar(
        Modulo,
        {"departamento_id": departamento.id, "slug": "contas_a_pagar"},
        {
            "nome": "Contas a Pagar",
            "descricao": "Vencimentos e aprovacoes",
            "icone": None,
            "ativo": True,
            "ordem": 1,
        },
    )
    db.session.flush()
    return departamento, modulo


def criar_usuario_demo(modulo):
    nivel = obter_ou_criar(
        NivelAcesso,
        {"slug": "usuario"},
        {"nome": "Usuario", "descricao": "Usuario local de testes.", "ativo": True},
    )
    db.session.flush()

    usuario = obter_ou_criar(
        Usuario,
        {"email": "financeiro.demo@rentalretros.local"},
        {
            "nome": "Financeiro Demo",
            "nivel_acesso_id": nivel.id,
            "ativo": True,
            "precisa_trocar_senha": False,
        },
    )
    usuario.definir_senha("Demo@12345")

    permissao = PermissaoUsuarioModulo.query.filter_by(
        usuario_id=usuario.id,
        modulo_id=modulo.id,
    ).first()
    if not permissao:
        permissao = PermissaoUsuarioModulo(usuario_id=usuario.id, modulo_id=modulo.id)
        db.session.add(permissao)

    permissao.pode_visualizar = True
    permissao.pode_criar = True
    permissao.pode_editar = True
    permissao.pode_excluir = True
    permissao.pode_exportar = True
    permissao.ativo = True
    permissao.garantir_visualizacao()
    return usuario



def garantir_modulo_suprimentos_ordens_compra(usuario):
    departamento = obter_ou_criar(
        Departamento,
        {"slug": "suprimentos"},
        {
            "nome": "Suprimentos",
            "descricao": "Compras, fornecedores, requisicoes e ordens de compra.",
            "icone": "caixa",
            "ativo": True,
            "ordem": 2,
        },
    )
    db.session.flush()
    modulo = obter_ou_criar(
        Modulo,
        {"departamento_id": departamento.id, "slug": "ordens_compra"},
        {
            "nome": "Ordens de Compra",
            "descricao": "Controle de ordens de compra.",
            "icone": None,
            "ativo": True,
            "ordem": 9,
        },
    )
    db.session.flush()
    permissao = PermissaoUsuarioModulo.query.filter_by(usuario_id=usuario.id, modulo_id=modulo.id).first()
    if not permissao:
        permissao = PermissaoUsuarioModulo(usuario_id=usuario.id, modulo_id=modulo.id)
        db.session.add(permissao)
    permissao.pode_visualizar = True
    permissao.pode_criar = True
    permissao.pode_editar = True
    permissao.pode_excluir = True
    permissao.pode_exportar = True
    permissao.ativo = True
    permissao.garantir_visualizacao()
    return modulo

def conceder_acesso_demo_sistema_completo(usuario):
    """Libera todos os modulos ativos para o usuario demo local."""
    modulos = Modulo.query.filter_by(ativo=True).all()
    for modulo in modulos:
        permissao = PermissaoUsuarioModulo.query.filter_by(
            usuario_id=usuario.id,
            modulo_id=modulo.id,
        ).first()
        if not permissao:
            permissao = PermissaoUsuarioModulo(usuario_id=usuario.id, modulo_id=modulo.id)
            db.session.add(permissao)

        permissao.pode_visualizar = True
        permissao.pode_criar = True
        permissao.pode_editar = True
        permissao.pode_excluir = True
        permissao.pode_aprovar = True
        permissao.pode_exportar = True
        permissao.ativo = True
        permissao.garantir_visualizacao()

def criar_base_demo():
    fornecedores = {}
    for documento, razao, email in [
        ("11222333000181", "FORNECEDOR DEMO PECAS LTDA", "pecas@demo.local"),
        ("11444777000161", "EPI SEGURO DEMO LTDA", "epi@demo.local"),
        ("19131243000197", "SERVICOS HIDRAULICOS DEMO ME", "servicos@demo.local"),
        ("52998224725", "PRESTADOR AUTONOMO DEMO", "autonomo@demo.local"),
    ]:
        fornecedores[razao] = obter_ou_criar(
            SuprimentosFornecedor,
            {"cnpj_cpf": documento},
            {
                "razao_social": razao,
                "nome_fantasia": razao,
                "tipo_pessoa": "fisica" if len(documento) == 11 else "juridica",
                "email": email,
                "telefone": "5513999990000",
                "ativo": True,
            },
        )

    centros = {}
    for codigo, nome, classe in [
        ("ADM", "ADMINISTRATIVO", "CENTRO DE CUSTO"),
        ("MAN", "MANUTENCAO", "CENTRO DE CUSTO"),
        ("OPE", "OPERACAO", "CENTRO DE CUSTO"),
    ]:
        centros[nome] = obter_ou_criar(
            CentroCusto,
            {"codigo": codigo},
            {"nome": nome, "classe": classe, "descricao": None, "ativo": True},
        )

    db.session.flush()
    return fornecedores, centros


def criar_cartao_demo(nome, usuario, centro, dados):
    cartao = FinanceiroCartaoCredito.query.filter_by(nome=nome).first()
    if not cartao:
        cartao = FinanceiroCartaoCredito(nome=nome)
        db.session.add(cartao)

    cartao.banco = dados["banco"]
    cartao.bandeira = dados.get("bandeira")
    cartao.ultimos_4_digitos = dados.get("ultimos_4_digitos")
    cartao.titular_responsavel = dados.get("titular_responsavel")
    cartao.dia_fechamento = dados["dia_fechamento"]
    cartao.dia_vencimento = dados["dia_vencimento"]
    cartao.limite = dados.get("limite")
    cartao.centro_custo_id = centro.id if centro else None
    cartao.observacoes = dados.get("observacoes")
    cartao.ativo = dados.get("ativo", True)
    cartao.criado_por_usuario_id = usuario.id
    cartao.atualizado_por_usuario_id = usuario.id
    return cartao


def criar_titulo_demo(chave, usuario, fornecedor, centro, dados):
    titulo = FinanceiroContaPagarTitulo.query.filter_by(numero_documento=chave).first()
    if not titulo:
        titulo = FinanceiroContaPagarTitulo(numero_documento=chave)
        db.session.add(titulo)

    titulo.fornecedor_id = fornecedor.id
    titulo.fornecedor_nome_snapshot = fornecedor.razao_social
    titulo.fornecedor_cnpj_cpf_snapshot = fornecedor.cnpj_cpf
    titulo.descricao = dados["descricao"]
    titulo.numero_nfe = dados.get("numero_nfe")
    titulo.chave_acesso_nfe = dados.get("chave_acesso_nfe")
    titulo.origem_lancamento = dados.get("origem_lancamento", "Manual")
    titulo.tipo_pagamento = dados.get("tipo_pagamento", "Faturado")
    titulo.forma_pagamento = dados.get("forma_pagamento", "Boleto")
    titulo.competencia = dados.get("competencia")
    titulo.data_emissao = dados.get("data_emissao")
    titulo.data_vencimento = dados["data_vencimento"]
    titulo.valor_original = dados["valor_original"]
    titulo.valor_desconto = dados.get("valor_desconto", 0)
    titulo.valor_acrescimo = dados.get("valor_acrescimo", 0)
    titulo.valor_juros_multa = dados.get("valor_juros_multa", 0)
    titulo.valor_pago = dados.get("valor_pago", 0)
    titulo.parcela_numero = dados.get("parcela_numero", 1)
    titulo.total_parcelas = dados.get("total_parcelas", 1)
    titulo.centro_custo_id = centro.id if centro else None
    titulo.status = dados.get("status", "Agendado")
    titulo.observacoes = dados.get("observacoes")
    titulo.criado_por_usuario_id = usuario.id
    titulo.atualizado_por_usuario_id = usuario.id
    return titulo



def criar_baixa_demo(titulo, usuario, valor, forma, observacoes, dias_atras=0):
    if not titulo:
        return None
    baixa = FinanceiroContaPagarBaixa.query.filter_by(
        titulo_id=titulo.id,
        observacoes=observacoes,
    ).first()
    if baixa:
        recalcular_pagamento_titulo(titulo, usuario=usuario)
        return baixa
    sucesso, mensagem, baixa = registrar_baixa_titulo(
        titulo,
        {
            "data_pagamento": (date.today() - timedelta(days=dias_atras)).isoformat(),
            "valor_pago": str(valor).replace(".", ","),
            "forma_pagamento": forma,
            "conta_pagamento_descricao": "Conta demo local",
            "observacoes": observacoes,
        },
        usuario=usuario,
    )
    if not sucesso:
        print(f"Falha ao criar baixa demo: {mensagem}")
    return baixa

def criar_titulo_cartao_demo(chave, usuario, fornecedor, centro, cartao, data_compra, descricao, valor, parcela=1, total=1):
    titulo = FinanceiroContaPagarTitulo.query.filter_by(numero_documento=chave).first()
    sucesso, mensagem, _ = salvar_titulo(
        {
            "fornecedor_id": str(fornecedor.id),
            "fornecedor_nome_snapshot": "",
            "fornecedor_cnpj_cpf_snapshot": "",
            "descricao": descricao,
            "numero_documento": chave,
            "data_emissao": data_compra.isoformat(),
            "data_compra_cartao": data_compra.isoformat(),
            "data_vencimento": (data_compra + timedelta(days=30)).isoformat(),
            "competencia": data_compra.strftime("%Y-%m"),
            "valor_original": valor,
            "valor_desconto": "0,00",
            "valor_acrescimo": "0,00",
            "valor_juros_multa": "0,00",
            "valor_pago": "0,00",
            "origem_lancamento": "Manual",
            "tipo_pagamento": "Cartao de Credito",
            "forma_pagamento": "Cartao de Credito",
            "cartao_credito_id": str(cartao.id),
            "parcela_numero": str(parcela),
            "total_parcelas": str(total),
            "centro_custo_id": str(centro.id),
            "status": "Agendado",
            "observacoes": "Dado ficticio local da Missao 17.2.",
        },
        titulo=titulo,
        usuario=usuario,
    )
    if not sucesso:
        print(f"Falha ao criar titulo de cartao {chave}: {mensagem}")



def criar_ordem_compra_demo(usuario, fornecedor, centro, cartao=None, com_cartao=False):
    codigo_item = "OC-DEMO-CARTAO" if com_cartao else "OC-DEMO-FATURADO"
    categoria = obter_ou_criar(
        SuprimentosCategoriaItem,
        {"slug": "demo-financeiro-oc"},
        {"nome": "DEMO FINANCEIRO OC", "ativo": True},
    )
    unidade = obter_ou_criar(
        SuprimentosUnidadeMedida,
        {"sigla": "UN"},
        {"nome": "UNIDADE", "ativo": True},
    )
    db.session.flush()

    item = obter_ou_criar(
        SuprimentosItem,
        {"codigo_interno": codigo_item},
        {
            "descricao": "ITEM FICTICIO INTEGRACAO OC CARTAO" if com_cartao else "ITEM FICTICIO INTEGRACAO OC FATURADO",
            "categoria_id": categoria.id,
            "unidade_medida_id": unidade.id,
            "centro_custo_padrao_id": centro.id,
            "tipo": "material",
            "item_estocavel": False,
            "ativo": True,
        },
    )
    db.session.flush()

    obter_ou_criar(
        SuprimentosFornecedorItem,
        {"fornecedor_id": fornecedor.id, "item_id": item.id},
        {"ativo": True, "fornecedor_preferencial": True},
    )
    db.session.flush()

    chave_titulo = "OC-CARTAO-DEMO-01/02" if com_cartao else "OC-FATURADA-DEMO-01/03"
    titulo_existente = FinanceiroContaPagarTitulo.query.filter_by(numero_documento=chave_titulo).first()
    if titulo_existente and titulo_existente.ordem_compra:
        return titulo_existente.ordem_compra

    numero_oc_demo = f"OC-CP-DEMO-{'CARTAO' if com_cartao else 'FATURADO'}-{date.today().strftime('%Y%m%d')}-{fornecedor.id}"
    ordem_existente = SuprimentosOrdemCompra.query.filter_by(numero=numero_oc_demo).first()
    if ordem_existente:
        return ordem_existente

    sucesso, mensagem, requisicao = salvar_requisicao_compra(
        {"centro_custo_id": str(centro.id), "justificativa": "Teste local da integracao O.C. com Contas a Pagar"},
        usuario,
    )
    if not sucesso:
        print(f"Falha ao criar requisicao demo O.C.: {mensagem}")
        return None
    adicionar_item_requisicao({"item_id": str(item.id), "quantidade": "3" if not com_cartao else "2"}, requisicao)
    enviar_requisicao_compra(requisicao)

    _, _, cotacao = salvar_cotacao({"requisicao_id": str(requisicao.id), "observacoes": "Cotacao ficticia local"}, usuario)
    _, _, proposta = salvar_proposta_cotacao(
        {
            "requisicao_item_id": str(requisicao.itens[0].id),
            "fornecedor_id": str(fornecedor.id),
            "preco_unitario": "333,33" if not com_cartao else "250,00",
            "prazo_entrega_dias": "5",
            "condicao_pagamento": "Parcelado",
            "observacoes": "Dado ficticio local da Missao 17.3",
        },
        cotacao,
    )
    selecionar_proposta_vencedora({"proposta_id": str(proposta.id)}, cotacao, usuario)
    enviar_cotacao_para_aprovacao(cotacao, usuario)
    aprovar_cotacao(cotacao, usuario, {"observacoes_aprovacao": "Aprovacao ficticia local"})
    _, mensagem_ordem, ordens = gerar_ordens_compra_cotacao(cotacao, usuario)
    ordem = ordens[0] if ordens else SuprimentosOrdemCompra.query.filter_by(
        cotacao_id=cotacao.id,
        fornecedor_id=fornecedor.id,
    ).first()
    if not ordem:
        ordem = SuprimentosOrdemCompra(
            numero=numero_oc_demo,
            cotacao_id=cotacao.id,
            requisicao_id=requisicao.id,
            fornecedor_id=fornecedor.id,
            criado_por_usuario_id=usuario.id,
            fornecedor_razao_social_snapshot=fornecedor.razao_social,
            fornecedor_cnpj_cpf_snapshot=fornecedor.cnpj_cpf,
            condicao_pagamento_snapshot="Parcelado",
            status="Gerada",
        )
        db.session.add(ordem)
        db.session.flush()
        db.session.add(
            SuprimentosOrdemCompraItem(
                ordem_compra_id=ordem.id,
                cotacao_proposta_id=proposta.id,
                requisicao_item_id=requisicao.itens[0].id,
                item_id=item.id,
                item_codigo_snapshot=item.codigo_interno,
                item_descricao_snapshot=item.descricao,
                unidade_medida_snapshot=unidade.sigla,
                quantidade=requisicao.itens[0].quantidade,
                preco_unitario=proposta.preco_unitario,
                prazo_entrega_dias=proposta.prazo_entrega_dias,
                observacoes="Dado ficticio local da Missao 17.3.",
            )
        )
        db.session.flush()

    dados_financeiros = {
        "tipo_pagamento_financeiro": "Cartao de Credito" if com_cartao else "Faturado",
        "forma_pagamento_financeiro": "Cartao de Credito" if com_cartao else "Boleto",
        "condicao_pagamento_financeiro": "Parcelado",
        "data_primeiro_vencimento_financeiro": (date.today() + timedelta(days=20)).isoformat(),
        "numero_parcelas_financeiro": "2" if com_cartao else "3",
        "observacoes_financeiras": "Dado ficticio local da Missao 17.3.",
    }
    if com_cartao and cartao:
        dados_financeiros["cartao_credito_id"] = str(cartao.id)

    sucesso, mensagem = preparar_financeiro_ordem_compra(ordem, dados_financeiros)
    if not sucesso:
        print(f"Falha ao preparar financeiro da O.C. demo: {mensagem}")
        return ordem
    sucesso, mensagem = provisionar_financeiro_ordem_compra(ordem, usuario=usuario)
    if not sucesso:
        print(f"Falha ao gerar Contas a Pagar da O.C. demo: {mensagem}")
    return ordem


def criar_documento_fiscal_demo(chave, fornecedor, dados):
    documento = FiscalDocumento.query.filter_by(chave_acesso=chave).first()
    emissao = dados.get("data_emissao") or datetime.combine(date.today(), datetime.min.time())
    if isinstance(emissao, date) and not isinstance(emissao, datetime):
        emissao = datetime.combine(emissao, datetime.min.time())

    if not documento:
        documento = FiscalDocumento(
            chave_acesso=chave,
            emitente_nome=fornecedor.razao_social,
            emitente_cnpj=fornecedor.cnpj_cpf,
            destinatario_nome="RENTAL RETROS DEMO",
            destinatario_cnpj="12345678000190",
            valor_total=dados["valor_total"],
        )
        db.session.add(documento)

    documento.nsu = dados.get("nsu")
    documento.modelo = "55"
    documento.serie = dados.get("serie", "1")
    documento.numero = dados["numero"]
    documento.natureza_operacao = dados.get("natureza_operacao", "VENDA MERCADORIA DEMO")
    documento.data_emissao = emissao
    documento.emitente_nome = fornecedor.razao_social
    documento.emitente_cnpj = fornecedor.cnpj_cpf
    documento.destinatario_nome = "RENTAL RETROS DEMO"
    documento.destinatario_cnpj = "12345678000190"
    documento.valor_total = dados["valor_total"]
    documento.xml_path = dados.get("xml_path", f"local/demo/{chave}.xml")
    documento.danfe_path = dados.get("danfe_path", f"local/demo/{chave}.pdf")
    documento.tipo_distribuicao = "procNFe"
    documento.tem_xml_completo = True
    documento.manifestacao_status = dados.get("manifestacao_status", "Ciencia registrada")
    documento.status = dados.get("status", "XML baixado")
    documento.ordem_compra_id = dados.get("ordem_compra_id")
    documento.financeiro_status = dados.get("financeiro_status", "Pendente de geracao")
    documento.financeiro_integrado = dados.get("financeiro_integrado", False)
    documento.financeiro_ignorado = dados.get("financeiro_ignorado", False)
    documento.financeiro_observacoes = dados.get("financeiro_observacoes")
    return documento

def executar_seed():
    app = create_app()
    if not ambiente_local_liberado(app):
        print("Seed dev de Contas a Pagar bloqueado. Use ALLOW_DEV_SEED=1 em ambiente local/desenvolvimento.")
        return

    with app.app_context():
        inspector = sa_inspect(db.engine)
        if "departamentos" not in inspector.get_table_names():
            db.create_all()

        from app.seed_modulos_base_producao import executar_seed as executar_seed_modulos_base

        executar_seed_modulos_base()
        _, modulo = garantir_financeiro_contas_pagar()
        usuario = criar_usuario_demo(modulo)
        garantir_modulo_suprimentos_ordens_compra(usuario)
        conceder_acesso_demo_sistema_completo(usuario)
        fornecedores, centros = criar_base_demo()
        hoje = date.today()
        competencia = hoje.replace(day=1)

        titulo_vencido = criar_titulo_demo(
            "CP-DEMO-001",
            usuario,
            fornecedores["FORNECEDOR DEMO PECAS LTDA"],
            centros["MANUTENCAO"],
            {
                "descricao": "PECAS PARA MANUTENCAO DE MAQUINA",
                "numero_nfe": "9001",
                "chave_acesso_nfe": "35260811222333000181550010000090011000090018",
                "data_emissao": hoje - timedelta(days=10),
                "data_vencimento": hoje - timedelta(days=2),
                "competencia": competencia,
                "valor_original": 1250.75,
                "status": "Agendado",
                "observacoes": "Titulo demo vencido para validar indicador visual.",
            },
        )
        titulo_conferencia = criar_titulo_demo(
            "CP-DEMO-002",
            usuario,
            fornecedores["EPI SEGURO DEMO LTDA"],
            centros["OPERACAO"],
            {
                "descricao": "COMPRA DE EPIS PARA OPERACAO",
                "numero_nfe": "9002",
                "data_emissao": hoje - timedelta(days=3),
                "data_vencimento": hoje + timedelta(days=3),
                "competencia": competencia,
                "valor_original": 680.00,
                "forma_pagamento": "Pix",
                "status": "Aguardando conferencia",
                "observacoes": "Titulo demo aguardando conferencia.",
            },
        )
        titulo_parcelado = criar_titulo_demo(
            "CP-DEMO-003",
            usuario,
            fornecedores["SERVICOS HIDRAULICOS DEMO ME"],
            centros["MANUTENCAO"],
            {
                "descricao": "SERVICO HIDRAULICO PARCELADO",
                "data_emissao": hoje,
                "data_vencimento": hoje + timedelta(days=12),
                "competencia": competencia,
                "valor_original": 2100.00,
                "tipo_pagamento": "Faturado",
                "forma_pagamento": "Transferencia",
                "parcela_numero": 1,
                "total_parcelas": 2,
                "status": "Agendado",
            },
        )

        db.session.flush()
        criar_baixa_demo(titulo_vencido, usuario, "1250.75", "Boleto", "Baixa total ficticia sem comprovante - Missao 17.5", dias_atras=1)
        criar_baixa_demo(titulo_parcelado, usuario, "700.00", "Transferencia", "Baixa parcial ficticia - Missao 17.5", dias_atras=0)

        cartao_adm = criar_cartao_demo(
            "CARTAO ADMINISTRATIVO DEMO",
            usuario,
            centros["ADMINISTRATIVO"],
            {
                "banco": "BANCO DEMO",
                "bandeira": "VISA",
                "ultimos_4_digitos": "1234",
                "titular_responsavel": "FINANCEIRO DEMO",
                "dia_fechamento": 20,
                "dia_vencimento": 28,
                "limite": 15000.00,
                "observacoes": "Cartao ficticio para testes locais.",
            },
        )
        cartao_operacao = criar_cartao_demo(
            "CARTAO OPERACAO DEMO",
            usuario,
            centros["OPERACAO"],
            {
                "banco": "COOPERATIVA DEMO",
                "bandeira": "MASTERCARD",
                "ultimos_4_digitos": "9876",
                "titular_responsavel": "OPERACAO DEMO",
                "dia_fechamento": 10,
                "dia_vencimento": 18,
                "limite": 25000.00,
                "observacoes": "Cartao ficticio para compras operacionais.",
            },
        )
        db.session.flush()

        compra_antes_fechamento = hoje.replace(day=min(15, hoje.day))
        criar_titulo_cartao_demo(
            "CP-CARTAO-DEMO-001",
            usuario,
            fornecedores["PRESTADOR AUTONOMO DEMO"],
            centros["ADMINISTRATIVO"],
            cartao_adm,
            compra_antes_fechamento,
            "DESPESA ADMINISTRATIVA NO CARTAO",
            "349,90",
        )
        criar_titulo_cartao_demo(
            "CP-CARTAO-DEMO-002",
            usuario,
            fornecedores["FORNECEDOR DEMO PECAS LTDA"],
            centros["MANUTENCAO"],
            cartao_adm,
            hoje,
            "PARCELA DE PECAS NO CARTAO",
            "780,50",
            parcela=1,
            total=3,
        )
        criar_titulo_cartao_demo(
            "CP-CARTAO-DEMO-003",
            usuario,
            fornecedores["EPI SEGURO DEMO LTDA"],
            centros["OPERACAO"],
            cartao_operacao,
            hoje,
            "COMPRA OPERACIONAL NO CARTAO",
            "465,30",
        )

        ordem_faturada = criar_ordem_compra_demo(usuario, fornecedores["FORNECEDOR DEMO PECAS LTDA"], centros["MANUTENCAO"], com_cartao=False)
        criar_ordem_compra_demo(usuario, fornecedores["EPI SEGURO DEMO LTDA"], centros["OPERACAO"], cartao=cartao_operacao, com_cartao=True)

        criar_documento_fiscal_demo(
            "35260811222333000181550010000174011000174011",
            fornecedores["FORNECEDOR DEMO PECAS LTDA"],
            {
                "numero": "17401",
                "serie": "1",
                "data_emissao": hoje - timedelta(days=1),
                "valor_total": 1490.75,
                "financeiro_status": "Pendente de conferencia",
            },
        )
        if ordem_faturada:
            criar_documento_fiscal_demo(
                "35260811222333000181550010000174021000174022",
                fornecedores["FORNECEDOR DEMO PECAS LTDA"],
                {
                    "numero": "17402",
                    "serie": "1",
                    "data_emissao": hoje - timedelta(days=2),
                    "valor_total": ordem_faturada.valor_total,
                    "ordem_compra_id": ordem_faturada.id,
                    "financeiro_status": "Ja integrado via O.C.",
                },
            )
        xml_gerado = criar_documento_fiscal_demo(
            "35260819131243000197550010000174031000174033",
            fornecedores["SERVICOS HIDRAULICOS DEMO ME"],
            {
                "numero": "17403",
                "serie": "1",
                "data_emissao": hoje - timedelta(days=4),
                "valor_total": 960.00,
                "financeiro_status": "Pendente de geracao",
            },
        )
        db.session.flush()
        if not FinanceiroContaPagarTitulo.query.filter_by(fiscal_documento_id=xml_gerado.id).first():
            gerar_contas_pagar_xml(
                xml_gerado,
                {
                    "tipo_pagamento": "Faturado",
                    "forma_pagamento": "Boleto",
                    "condicao_pagamento": "Parcelado",
                    "numero_parcelas": "2",
                    "data_primeiro_vencimento": (hoje + timedelta(days=15)).isoformat(),
                    "centro_custo_id": str(centros["MANUTENCAO"].id),
                    "observacoes": "Dado ficticio local da Missao 17.4.",
                },
                usuario=usuario,
            )

        db.session.commit()
        print("Seed dev de Contas a Pagar concluido com dados ficticios das Missoes 17.2, 17.3, 17.4 e 17.5.")
        print("Usuario demo: financeiro.demo@rentalretros.local")
        print("Senha demo: Demo@12345")


if __name__ == "__main__":
    executar_seed()





