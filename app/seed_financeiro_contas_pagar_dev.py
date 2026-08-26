import os
from datetime import date, timedelta

from sqlalchemy import inspect as sa_inspect

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    FinanceiroContaPagarTitulo,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosFornecedor,
    Usuario,
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


def executar_seed():
    app = create_app()
    if not ambiente_local_liberado(app):
        print("Seed dev de Contas a Pagar bloqueado. Use ALLOW_DEV_SEED=1 em ambiente local/desenvolvimento.")
        return

    with app.app_context():
        inspector = sa_inspect(db.engine)
        if "departamentos" not in inspector.get_table_names():
            db.create_all()

        _, modulo = garantir_financeiro_contas_pagar()
        usuario = criar_usuario_demo(modulo)
        fornecedores, centros = criar_base_demo()
        hoje = date.today()
        competencia = hoje.replace(day=1)

        criar_titulo_demo(
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
        criar_titulo_demo(
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
        criar_titulo_demo(
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
        criar_titulo_demo(
            "CP-DEMO-004",
            usuario,
            fornecedores["PRESTADOR AUTONOMO DEMO"],
            centros["ADMINISTRATIVO"],
            {
                "descricao": "DESPESA ADMINISTRATIVA NO CARTAO",
                "data_emissao": hoje,
                "data_vencimento": hoje + timedelta(days=25),
                "competencia": competencia,
                "valor_original": 349.90,
                "tipo_pagamento": "Cartao de Credito",
                "forma_pagamento": "Cartao de Credito",
                "status": "Agendado",
                "observacoes": "Registro informativo; fatura de cartao fica para fase futura.",
            },
        )

        db.session.commit()
        print("Seed dev de Contas a Pagar concluido com sucesso.")
        print("Usuario demo: financeiro.demo@rentalretros.local")
        print("Senha demo: Demo@12345")


if __name__ == "__main__":
    executar_seed()




