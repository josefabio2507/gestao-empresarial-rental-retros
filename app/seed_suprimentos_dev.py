import os

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    SuprimentosCategoriaItem,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosUnidadeMedida,
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


def executar_seed():
    if not ambiente_local_liberado(app):
        print("Seed dev de Suprimentos bloqueado. Use ALLOW_DEV_SEED=1 em ambiente local/desenvolvimento.")
        return

    print("Seed dev de Suprimentos iniciado...")

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

    db.session.commit()
    print("Seed dev de Suprimentos concluido com sucesso.")


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        executar_seed()
