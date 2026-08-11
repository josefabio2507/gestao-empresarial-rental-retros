import os
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosAlcadaAprovacao,
    SuprimentosCategoriaItem,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.suprimentos_service import slugificar


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
    criado = False

    if not registro:
        registro = modelo(**filtro)
        db.session.add(registro)
        criado = True

    for campo, valor in dados.items():
        setattr(registro, campo, valor)

    return registro, criado


def criar_usuario_demo(nome, email):
    nivel = NivelAcesso.query.filter_by(slug="usuario").first()
    if not nivel:
        nivel = NivelAcesso(nome="Usuario", slug="usuario", ativo=True)
        db.session.add(nivel)
        db.session.flush()

    usuario = Usuario.query.filter_by(email=email).first()
    criado = False

    if not usuario:
        usuario = Usuario(
            nome=nome,
            email=email,
            nivel_acesso_id=nivel.id,
            ativo=True,
            precisa_trocar_senha=False,
        )
        usuario.definir_senha("Demo@12345")
        db.session.add(usuario)
        criado = True

    usuario.nome = nome
    usuario.nivel_acesso_id = nivel.id
    usuario.ativo = True
    usuario.precisa_trocar_senha = False
    return usuario, criado


def garantir_permissao(usuario, departamento_slug, modulo_slug, **acoes):
    departamento = Departamento.query.filter_by(slug=departamento_slug).first()
    if not departamento:
        return None

    modulo = Modulo.query.filter_by(
        departamento_id=departamento.id,
        slug=modulo_slug,
    ).first()
    if not modulo:
        return None

    permissao = PermissaoUsuarioModulo.query.filter_by(
        usuario_id=usuario.id,
        modulo_id=modulo.id,
    ).first()

    if not permissao:
        permissao = PermissaoUsuarioModulo(
            usuario_id=usuario.id,
            modulo_id=modulo.id,
            ativo=True,
        )
        db.session.add(permissao)

    permissao.pode_visualizar = acoes.get("visualizar", permissao.pode_visualizar)
    permissao.pode_criar = acoes.get("criar", permissao.pode_criar)
    permissao.pode_editar = acoes.get("editar", permissao.pode_editar)
    permissao.pode_excluir = acoes.get("excluir", permissao.pode_excluir)
    permissao.pode_aprovar = acoes.get("aprovar", permissao.pode_aprovar)
    permissao.pode_exportar = acoes.get("exportar", permissao.pode_exportar)
    permissao.ativo = True
    permissao.garantir_visualizacao()
    return permissao


def executar_seed():
    if not ambiente_local_liberado(app):
        print("Seed dev de Suprimentos bloqueado. Use ALLOW_DEV_SEED=1 em ambiente local/desenvolvimento.")
        return

    print("Seed dev de Suprimentos iniciado...")

    aprovadores_demo = []
    for nome, email in [
        ("Gerente Suprimentos Demo", "gerente.suprimentos@rentalretros.local"),
        ("Diretoria Demo", "diretoria@rentalretros.local"),
    ]:
        usuario, _ = criar_usuario_demo(nome, email)
        aprovadores_demo.append(usuario)

    db.session.flush()

    for usuario in aprovadores_demo:
        garantir_permissao(usuario, "suprimentos", "cotacoes", visualizar=True, aprovar=True)

    categorias = {}
    for nome in ["PECAS", "EPI", "FERRAMENTAS", "SERVICOS", "CONSUMO"]:
        categoria, _ = obter_ou_criar(
            SuprimentosCategoriaItem,
            {"slug": slugificar(nome)},
            {"nome": nome, "descricao": None, "ativo": True},
        )
        categorias[nome] = categoria

    unidades = {}
    for sigla, nome in [
        ("UN", "UNIDADE"),
        ("KG", "QUILOGRAMA"),
        ("L", "LITRO"),
        ("M", "METRO"),
        ("CX", "CAIXA"),
        ("PAR", "PAR"),
        ("H", "HORA"),
    ]:
        unidade, _ = obter_ou_criar(
            SuprimentosUnidadeMedida,
            {"sigla": sigla},
            {"nome": nome, "descricao": None, "ativo": True},
        )
        unidades[sigla] = unidade

    centros = {}
    for codigo, nome in [
        ("ADM", "ADMINISTRATIVO"),
        ("OPE", "OPERACAO"),
        ("MAN", "MANUTENCAO"),
        ("SEG", "SEGURANCA DO TRABALHO"),
    ]:
        centro, _ = obter_ou_criar(
            CentroCusto,
            {"codigo": codigo},
            {"nome": nome, "descricao": None, "ativo": True},
        )
        centros[nome] = centro

    fornecedores = {}
    for documento, razao in [
        ("11222333000181", "FORNECEDOR DEMO PECAS LTDA"),
        ("11444777000161", "EPI SEGURO DEMO LTDA"),
        ("19131243000197", "SERVICOS HIDRAULICOS DEMO ME"),
    ]:
        fornecedor, _ = obter_ou_criar(
            SuprimentosFornecedor,
            {"cnpj_cpf": documento},
            {
                "razao_social": razao,
                "nome_fantasia": razao,
                "tipo_pessoa": "juridica",
                "email": "demo@rentalretros.local",
                "telefone": "5511999990000",
                "ativo": True,
            },
        )
        fornecedores[razao] = fornecedor

    itens_dados = [
        ("DEMO-001", "FILTRO DE OLEO DEMO", "PECAS", "UN", "MANUTENCAO", "peca", True),
        ("DEMO-002", "LUVA DE SEGURANCA DEMO", "EPI", "PAR", "SEGURANCA DO TRABALHO", "epi", True),
        ("DEMO-003", "DISCO DE CORTE DEMO", "FERRAMENTAS", "UN", "OPERACAO", "ferramenta", True),
        ("DEMO-004", "SERVICO DE MANUTENCAO HIDRAULICA DEMO", "SERVICOS", "H", "MANUTENCAO", "servico", False),
        ("DEMO-005", "DETERGENTE DESENGRAXANTE DEMO", "CONSUMO", "L", "OPERACAO", "consumo", True),
    ]

    itens = {}
    for codigo, descricao, categoria, unidade, centro, tipo, estocavel in itens_dados:
        item, _ = obter_ou_criar(
            SuprimentosItem,
            {"codigo_interno": codigo},
            {
                "descricao": descricao,
                "categoria_id": categorias[categoria].id,
                "unidade_medida_id": unidades[unidade].id,
                "centro_custo_padrao_id": centros[centro].id,
                "tipo": tipo,
                "item_estocavel": estocavel,
                "ativo": True,
            },
        )
        itens[descricao] = item

    db.session.flush()

    vinculos = [
        ("FORNECEDOR DEMO PECAS LTDA", "FILTRO DE OLEO DEMO", "45.90"),
        ("EPI SEGURO DEMO LTDA", "LUVA DE SEGURANCA DEMO", "12.50"),
        ("SERVICOS HIDRAULICOS DEMO ME", "SERVICO DE MANUTENCAO HIDRAULICA DEMO", "180.00"),
    ]

    for fornecedor_nome, item_descricao, preco in vinculos:
        obter_ou_criar(
            SuprimentosFornecedorItem,
            {
                "fornecedor_id": fornecedores[fornecedor_nome].id,
                "item_id": itens[item_descricao].id,
            },
            {
                "preco_referencia": preco,
                "condicao_pagamento": "DEMO LOCAL - SEM FINANCEIRO GERADO",
                "fornecedor_preferencial": True,
                "ativo": True,
            },
        )

    if aprovadores_demo:
        alcadas_demo = [
            (aprovadores_demo[0], Decimal("0.00"), Decimal("1000.00"), "5513999990001", "ALCADA DEMO LOCAL ATE R$ 1.000,00"),
            (aprovadores_demo[1], Decimal("1000.01"), None, "5513999990002", "ALCADA DEMO LOCAL ACIMA DE R$ 1.000,00"),
        ]

        for usuario, valor_minimo, valor_maximo, telefone_whatsapp, observacoes in alcadas_demo:
            existente = SuprimentosAlcadaAprovacao.query.filter_by(
                usuario_aprovador_id=usuario.id,
                valor_minimo=valor_minimo,
                valor_maximo=valor_maximo,
            ).first()

            if not existente:
                existente = SuprimentosAlcadaAprovacao(
                    usuario_aprovador_id=usuario.id,
                    valor_minimo=valor_minimo,
                    valor_maximo=valor_maximo,
                )
                db.session.add(existente)

            existente.observacoes = observacoes
            existente.telefone_whatsapp = telefone_whatsapp
            existente.ativo = True

    db.session.commit()
    print("Seed dev de Suprimentos concluido com sucesso.")


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        executar_seed()
