import json
from pathlib import Path

from sqlalchemy import func

from app.extensions import db
from app.models import (
    SuprimentosCategoriaItem,
    SuprimentosItem,
    SuprimentosUnidadeMedida,
)


ARQUIVO_DADOS = Path(__file__).resolve().parent / "data" / "suprimentos_itens_nota_fiscal.json"
CATEGORIA_TECNICA_SLUG = "item_sem_categoria"
CATEGORIA_TECNICA_NOME = "ITEM SEM CATEGORIA"
TIPO_PADRAO = "material"


def normalizar_texto(valor):
    if valor is None:
        return ""
    return " ".join(str(valor).strip().upper().split())


def carregar_itens():
    with ARQUIVO_DADOS.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def obter_categoria_tecnica():
    categoria = SuprimentosCategoriaItem.query.filter_by(slug=CATEGORIA_TECNICA_SLUG).first()

    if not categoria:
        categoria = SuprimentosCategoriaItem(
            nome=CATEGORIA_TECNICA_NOME,
            slug=CATEGORIA_TECNICA_SLUG,
            descricao="CATEGORIA TECNICA PARA ITENS CLASSIFICADOS PELO CAMPO TIPO.",
            ativo=True,
        )
        db.session.add(categoria)
        db.session.flush()
    else:
        categoria.nome = CATEGORIA_TECNICA_NOME
        categoria.ativo = True

    return categoria


def obter_unidade(sigla, unidades_cache):
    sigla = normalizar_texto(sigla) or "UN"

    if sigla in unidades_cache:
        return unidades_cache[sigla]

    unidade = SuprimentosUnidadeMedida.query.filter(
        func.upper(func.trim(SuprimentosUnidadeMedida.sigla)) == sigla
    ).first()

    if not unidade:
        unidade = SuprimentosUnidadeMedida(
            nome=sigla,
            sigla=sigla,
            descricao="UNIDADE IMPORTADA DO CADASTRO DE ITENS DE NOTA FISCAL.",
            ativo=True,
        )
        db.session.add(unidade)
        db.session.flush()
    else:
        unidade.ativo = True

    unidades_cache[sigla] = unidade
    return unidade


def indexar_itens_existentes():
    por_codigo = {}
    por_descricao = {}

    for item in SuprimentosItem.query.all():
        codigo = normalizar_texto(item.codigo_interno)
        descricao = normalizar_texto(item.descricao)

        if codigo:
            por_codigo[codigo] = item
        if descricao:
            por_descricao.setdefault(descricao, item)

    return por_codigo, por_descricao


def executar_seed():
    print("Seed de itens de nota fiscal iniciado...")

    dados = carregar_itens()
    categoria = obter_categoria_tecnica()
    unidades_cache = {}
    itens_por_codigo, itens_por_descricao = indexar_itens_existentes()

    criados = 0
    atualizados = 0
    ignorados_sem_dados = 0
    ignorados_descricao_existente = 0
    ignorados_conflito_descricao = 0
    descricoes_processadas = set()

    for registro in dados:
        codigo = normalizar_texto(registro.get("codigo_interno"))
        descricao = normalizar_texto(registro.get("descricao"))
        ncm = normalizar_texto(registro.get("ncm")) or None

        if not codigo or not descricao:
            ignorados_sem_dados += 1
            continue

        if descricao in descricoes_processadas:
            ignorados_descricao_existente += 1
            continue

        descricoes_processadas.add(descricao)

        item_por_codigo = itens_por_codigo.get(codigo)
        item_por_descricao = itens_por_descricao.get(descricao)

        if item_por_codigo and item_por_descricao and item_por_codigo.id != item_por_descricao.id:
            ignorados_conflito_descricao += 1
            continue

        if not item_por_codigo and item_por_descricao:
            ignorados_descricao_existente += 1
            continue

        unidade = obter_unidade(registro.get("unidade"), unidades_cache)

        if item_por_codigo:
            item = item_por_codigo
            atualizados += 1
        else:
            item = SuprimentosItem(codigo_interno=codigo, ativo=True)
            db.session.add(item)
            itens_por_codigo[codigo] = item
            itens_por_descricao[descricao] = item
            criados += 1

        item.descricao = descricao
        item.categoria_id = categoria.id
        item.unidade_medida_id = unidade.id
        item.tipo = TIPO_PADRAO
        item.item_estocavel = True
        item.ncm = ncm
        item.ativo = True

    db.session.commit()

    print("Itens lidos no arquivo:", len(dados))
    print("Itens criados:", criados)
    print("Itens atualizados por codigo interno:", atualizados)
    print("Itens ignorados por dados obrigatorios ausentes:", ignorados_sem_dados)
    print("Itens ignorados por descricao duplicada/existente:", ignorados_descricao_existente)
    print("Itens ignorados por conflito entre codigo e descricao:", ignorados_conflito_descricao)
    print("Seed de itens de nota fiscal concluido com sucesso.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()

    with app.app_context():
        executar_seed()
