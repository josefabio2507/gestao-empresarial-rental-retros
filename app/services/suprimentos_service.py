import re
import json
import os
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import func

from app.extensions import db
from app.models import (
    CentroCusto,
    Equipe,
    SuprimentosCategoriaItem,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosCotacao,
    SuprimentosCotacaoProposta,
    SuprimentosRequisicaoCompra,
    SuprimentosRequisicaoCompraItem,
    SuprimentosOrdemCompra,
    SuprimentosOrdemCompraItem,
    SuprimentosRecebimentoCompra,
    SuprimentosRecebimentoCompraItem,
    SuprimentosUnidadeMedida,
)


TIPOS_PESSOA = {"juridica", "fisica"}
TIPOS_ITEM = {
    "material",
    "servico",
    "epi",
    "ferramenta",
    "peca",
    "equipamento",
    "consumo",
}
STATUS_REQUISICAO_RASCUNHO = "Rascunho"
STATUS_REQUISICAO_ENVIADA = "Enviada para Analise"
STATUS_REQUISICAO_CANCELADA = "Cancelada"
STATUS_COTACAO_ABERTA = "Aberta"
STATUS_COTACAO_EM_APROVACAO = "Em Aprovacao"
STATUS_COTACAO_APROVADA = "Aprovada"
STATUS_COTACAO_REPROVADA = "Reprovada"
STATUS_COTACAO_ENCERRADA = "Encerrada"
STATUS_COTACAO_CANCELADA = "Cancelada"
STATUS_COTACAO_EDITAVEIS = {
    STATUS_COTACAO_ABERTA,
    STATUS_COTACAO_REPROVADA,
}
STATUS_ORDEM_COMPRA_GERADA = "Gerada"
STATUS_ORDEM_COMPRA_PARCIAL = "Parcialmente Recebida"
STATUS_ORDEM_COMPRA_RECEBIDA = "Recebida"
STATUS_ORDEM_COMPRA_CANCELADA = "Cancelada"
STATUS_RECEBIMENTO_COMPRA_REGISTRADO = "Registrado"
STATUS_RECEBIMENTO_COMPRA_CANCELADO = "Cancelado"
TIPOS_DOCUMENTO_RECEBIMENTO = {
    "Nota Fiscal",
    "Cupom Fiscal",
    "Romaneio",
    "Outro",
}


def texto(valor):
    return valor.strip() if valor else ""


def texto_maiusculo(valor):
    valor = texto(valor)
    return valor.upper() if valor else ""


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def email_valido(valor):
    valor = texto(valor).lower()
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", valor))


def normalizar_telefone_brasil(valor):
    digitos = somente_digitos(valor)

    if not digitos:
        return ""

    if digitos.startswith("55") and len(digitos) in [12, 13]:
        return digitos

    if len(digitos) in [10, 11]:
        return f"55{digitos}"

    return digitos


def telefone_brasil_valido(valor):
    telefone = normalizar_telefone_brasil(valor)

    if not telefone.startswith("55"):
        return False

    numero_nacional = telefone[2:]
    return len(numero_nacional) in [10, 11]


def slugificar(valor):
    valor = texto(valor).lower()
    valor = unicodedata.normalize("NFKD", valor)
    valor = valor.encode("ascii", "ignore").decode("ascii")
    valor = re.sub(r"[^a-z0-9]+", "_", valor)
    return valor.strip("_")


def decimal_ou_none(valor):
    valor = texto(str(valor)) if valor is not None else ""

    if not valor:
        return None

    valor = valor.replace("R$", "").replace(" ", "")
    valor = valor.replace(".", "").replace(",", ".")

    try:
        return Decimal(valor)
    except InvalidOperation:
        return None


def formatar_moeda_brl(valor):
    if valor is None:
        return "-"

    try:
        valor_decimal = Decimal(valor).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return "-"

    texto_valor = f"{valor_decimal:,.2f}"
    texto_valor = texto_valor.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto_valor}"


def formatar_decimal_brasil(valor, casas=3):
    if valor is None:
        return "-"

    try:
        valor_decimal = Decimal(valor).quantize(Decimal(f"0.{'0' * casas}"))
    except (InvalidOperation, TypeError, ValueError):
        return "-"

    texto_valor = f"{valor_decimal:,.{casas}f}"
    return texto_valor.replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro_ou_none(valor):
    valor = texto(str(valor)) if valor is not None else ""

    if not valor:
        return None

    try:
        return int(valor)
    except ValueError:
        return None


def data_ou_none(valor):
    valor = texto(valor)

    if not valor:
        return None

    for formato in ["%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue

    return None


def bool_form(valor):
    return valor in [True, "on", "true", "1", "sim", "Sim"]


def validar_cpf(cpf):
    cpf = somente_digitos(cpf)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    soma = sum(int(cpf[indice]) * (10 - indice) for indice in range(9))
    digito = (soma * 10) % 11
    digito = 0 if digito == 10 else digito

    if digito != int(cpf[9]):
        return False

    soma = sum(int(cpf[indice]) * (11 - indice) for indice in range(10))
    digito = (soma * 10) % 11
    digito = 0 if digito == 10 else digito

    return digito == int(cpf[10])


def validar_cnpj(cnpj):
    cnpj = somente_digitos(cnpj)

    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    pesos_primeiro = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_segundo = [6] + pesos_primeiro

    soma = sum(int(cnpj[indice]) * pesos_primeiro[indice] for indice in range(12))
    resto = soma % 11
    primeiro_digito = 0 if resto < 2 else 11 - resto

    if primeiro_digito != int(cnpj[12]):
        return False

    soma = sum(int(cnpj[indice]) * pesos_segundo[indice] for indice in range(13))
    resto = soma % 11
    segundo_digito = 0 if resto < 2 else 11 - resto

    return segundo_digito == int(cnpj[13])


def validar_cnpj_cpf(documento, tipo_pessoa):
    documento = somente_digitos(documento)

    if not documento:
        return True

    if tipo_pessoa == "juridica":
        return validar_cnpj(documento)

    if tipo_pessoa == "fisica":
        return validar_cpf(documento)

    return len(documento) in [11, 14] and (
        validar_cpf(documento) if len(documento) == 11 else validar_cnpj(documento)
    )


def buscar_por_id(modelo, registro_id):
    return db.session.get(modelo, registro_id)


def filtrar_status(query, modelo, status):
    if status == "ativos":
        return query.filter(modelo.ativo.is_(True))

    if status == "inativos":
        return query.filter(modelo.ativo.is_(False))

    return query


def buscar_fornecedores(nome=None, documento=None, status=None):
    query = SuprimentosFornecedor.query
    nome = texto(nome)
    documento = somente_digitos(documento)

    if nome:
        query = query.filter(
            SuprimentosFornecedor.razao_social.ilike(f"%{nome}%")
            | SuprimentosFornecedor.nome_fantasia.ilike(f"%{nome}%")
        )

    if documento:
        query = query.filter(SuprimentosFornecedor.cnpj_cpf.ilike(f"%{documento}%"))

    query = filtrar_status(query, SuprimentosFornecedor, status)
    return query.order_by(SuprimentosFornecedor.razao_social.asc()).all()


def buscar_fornecedores_ativos():
    return (
        SuprimentosFornecedor.query
        .filter_by(ativo=True)
        .order_by(SuprimentosFornecedor.razao_social.asc())
        .all()
    )


def documento_fornecedor_ja_existe(cnpj_cpf, fornecedor_id_ignorado=None):
    cnpj_cpf = somente_digitos(cnpj_cpf)

    if not cnpj_cpf:
        return False

    query = SuprimentosFornecedor.query.filter_by(cnpj_cpf=cnpj_cpf)

    if fornecedor_id_ignorado is not None:
        query = query.filter(SuprimentosFornecedor.id != fornecedor_id_ignorado)

    return query.first() is not None


def dados_fornecedor(form_data):
    return {
        "razao_social": texto_maiusculo(form_data.get("razao_social")),
        "nome_fantasia": texto_maiusculo(form_data.get("nome_fantasia")) or None,
        "tipo_pessoa": texto(form_data.get("tipo_pessoa")) or "juridica",
        "cnpj_cpf": somente_digitos(form_data.get("cnpj_cpf")) or None,
        "inscricao_estadual": texto_maiusculo(form_data.get("inscricao_estadual")) or None,
        "telefone": normalizar_telefone_brasil(form_data.get("telefone")) or None,
        "email": texto(form_data.get("email")).lower() or None,
        "pessoa_contato": texto_maiusculo(form_data.get("pessoa_contato")) or None,
        "endereco": texto_maiusculo(form_data.get("endereco")) or None,
        "cidade": texto_maiusculo(form_data.get("cidade")) or None,
        "uf": texto(form_data.get("uf")).upper()[:2] or None,
        "observacoes": texto_maiusculo(form_data.get("observacoes")) or None,
    }


def salvar_fornecedor(form_data, fornecedor=None):
    dados = dados_fornecedor(form_data)

    if not dados["razao_social"]:
        return False, "Razao social e obrigatoria.", fornecedor

    if dados["tipo_pessoa"] not in TIPOS_PESSOA:
        return False, "Tipo de pessoa invalido.", fornecedor

    if not dados["cnpj_cpf"]:
        return False, "CNPJ/CPF e obrigatorio.", fornecedor

    if not validar_cnpj_cpf(dados["cnpj_cpf"], dados["tipo_pessoa"]):
        return False, "CNPJ/CPF invalido.", fornecedor

    if not dados["email"]:
        return False, "E-mail e obrigatorio.", fornecedor

    if not email_valido(dados["email"]):
        return False, "E-mail invalido.", fornecedor

    if not dados["telefone"]:
        return False, "Telefone e obrigatorio.", fornecedor

    if not telefone_brasil_valido(dados["telefone"]):
        return False, "Telefone invalido. Informe DDD e numero.", fornecedor

    if documento_fornecedor_ja_existe(dados["cnpj_cpf"], getattr(fornecedor, "id", None)):
        return False, "Ja existe fornecedor cadastrado com este CNPJ/CPF.", fornecedor

    if fornecedor is None:
        fornecedor = SuprimentosFornecedor(ativo=True)
        db.session.add(fornecedor)

    for campo, valor in dados.items():
        setattr(fornecedor, campo, valor)

    db.session.commit()
    return True, "Fornecedor salvo com sucesso.", fornecedor


def alterar_status(registro):
    registro.ativo = not registro.ativo
    db.session.commit()
    return True, "Registro reativado com sucesso." if registro.ativo else "Registro inativado com sucesso."


def buscar_categorias(nome=None, status=None):
    query = SuprimentosCategoriaItem.query
    nome = texto(nome)

    if nome:
        query = query.filter(SuprimentosCategoriaItem.nome.ilike(f"%{nome}%"))

    query = filtrar_status(query, SuprimentosCategoriaItem, status)
    return query.order_by(SuprimentosCategoriaItem.nome.asc()).all()


def buscar_categorias_ativas():
    return (
        SuprimentosCategoriaItem.query
        .filter_by(ativo=True)
        .order_by(SuprimentosCategoriaItem.nome.asc())
        .all()
    )


def categoria_ja_existe(nome, categoria_id_ignorado=None):
    nome = texto(nome)

    if not nome:
        return False

    query = SuprimentosCategoriaItem.query.filter(
        func.lower(func.trim(SuprimentosCategoriaItem.nome)) == nome.lower()
    )

    if categoria_id_ignorado is not None:
        query = query.filter(SuprimentosCategoriaItem.id != categoria_id_ignorado)

    return query.first() is not None


def salvar_categoria(form_data, categoria=None):
    nome = texto_maiusculo(form_data.get("nome"))

    if not nome:
        return False, "Nome da categoria e obrigatorio.", categoria

    if categoria_ja_existe(nome, getattr(categoria, "id", None)):
        return False, "Ja existe categoria cadastrada com este nome.", categoria

    if categoria is None:
        categoria = SuprimentosCategoriaItem(ativo=True)
        db.session.add(categoria)

    categoria.nome = nome
    categoria.slug = slugificar(nome)
    categoria.descricao = texto_maiusculo(form_data.get("descricao")) or None
    db.session.commit()
    return True, "Categoria salva com sucesso.", categoria


def buscar_unidades(nome=None, status=None):
    query = SuprimentosUnidadeMedida.query
    nome = texto(nome)

    if nome:
        query = query.filter(
            SuprimentosUnidadeMedida.nome.ilike(f"%{nome}%")
            | SuprimentosUnidadeMedida.sigla.ilike(f"%{nome}%")
        )

    query = filtrar_status(query, SuprimentosUnidadeMedida, status)
    return query.order_by(SuprimentosUnidadeMedida.sigla.asc()).all()


def buscar_unidades_ativas():
    return (
        SuprimentosUnidadeMedida.query
        .filter_by(ativo=True)
        .order_by(SuprimentosUnidadeMedida.sigla.asc())
        .all()
    )


def sigla_unidade_ja_existe(sigla, unidade_id_ignorado=None):
    sigla = texto(sigla).upper()

    if not sigla:
        return False

    query = SuprimentosUnidadeMedida.query.filter(
        func.upper(func.trim(SuprimentosUnidadeMedida.sigla)) == sigla
    )

    if unidade_id_ignorado is not None:
        query = query.filter(SuprimentosUnidadeMedida.id != unidade_id_ignorado)

    return query.first() is not None


def salvar_unidade(form_data, unidade=None):
    nome = texto_maiusculo(form_data.get("nome"))
    sigla = texto(form_data.get("sigla")).upper()

    if not nome:
        return False, "Nome da unidade e obrigatorio.", unidade

    if not sigla:
        return False, "Sigla da unidade e obrigatoria.", unidade

    if sigla_unidade_ja_existe(sigla, getattr(unidade, "id", None)):
        return False, "Ja existe unidade cadastrada com esta sigla.", unidade

    if unidade is None:
        unidade = SuprimentosUnidadeMedida(ativo=True)
        db.session.add(unidade)

    unidade.nome = nome
    unidade.sigla = sigla
    unidade.descricao = texto_maiusculo(form_data.get("descricao")) or None
    db.session.commit()
    return True, "Unidade de medida salva com sucesso.", unidade


def buscar_centros_custo(nome=None, status=None):
    query = CentroCusto.query
    nome = texto(nome)

    if nome:
        query = query.filter(
            CentroCusto.nome.ilike(f"%{nome}%")
            | CentroCusto.codigo.ilike(f"%{nome}%")
        )

    query = filtrar_status(query, CentroCusto, status)
    return query.order_by(CentroCusto.nome.asc()).all()


def buscar_centros_custo_ativos():
    return CentroCusto.query.filter_by(ativo=True).order_by(CentroCusto.nome.asc()).all()


def buscar_equipes_ativas():
    return Equipe.query.filter_by(ativo=True).order_by(Equipe.nome.asc()).all()


def codigo_centro_custo_ja_existe(codigo, centro_id_ignorado=None):
    codigo = texto(codigo).upper()

    if not codigo:
        return False

    query = CentroCusto.query.filter(func.upper(func.trim(CentroCusto.codigo)) == codigo)

    if centro_id_ignorado is not None:
        query = query.filter(CentroCusto.id != centro_id_ignorado)

    return query.first() is not None


def salvar_centro_custo(form_data, centro=None):
    nome = texto_maiusculo(form_data.get("nome"))
    codigo = texto(form_data.get("codigo")).upper() or None

    if not nome:
        return False, "Nome do centro de custo e obrigatorio.", centro

    if codigo_centro_custo_ja_existe(codigo, getattr(centro, "id", None)):
        return False, "Ja existe centro de custo cadastrado com este codigo.", centro

    if centro is None:
        centro = CentroCusto(ativo=True)
        db.session.add(centro)

    centro.codigo = codigo
    centro.nome = nome
    centro.descricao = texto_maiusculo(form_data.get("descricao")) or None
    db.session.commit()
    return True, "Centro de custo salvo com sucesso.", centro


def buscar_itens(descricao=None, categoria_id=None, tipo=None, estocavel=None, status=None):
    query = SuprimentosItem.query
    descricao = texto(descricao)

    if descricao:
        query = query.filter(
            SuprimentosItem.descricao.ilike(f"%{descricao}%")
            | SuprimentosItem.codigo_interno.ilike(f"%{descricao}%")
        )

    if categoria_id:
        query = query.filter(SuprimentosItem.categoria_id == categoria_id)

    if tipo:
        query = query.filter(SuprimentosItem.tipo == tipo)

    if estocavel == "sim":
        query = query.filter(SuprimentosItem.item_estocavel.is_(True))
    elif estocavel == "nao":
        query = query.filter(SuprimentosItem.item_estocavel.is_(False))

    query = filtrar_status(query, SuprimentosItem, status)
    return query.order_by(SuprimentosItem.descricao.asc()).all()


def buscar_itens_ativos():
    return SuprimentosItem.query.filter_by(ativo=True).order_by(SuprimentosItem.descricao.asc()).all()


def codigo_item_ja_existe(codigo, item_id_ignorado=None):
    codigo = texto(codigo).upper()

    if not codigo:
        return False

    query = SuprimentosItem.query.filter(
        func.upper(func.trim(SuprimentosItem.codigo_interno)) == codigo
    )

    if item_id_ignorado is not None:
        query = query.filter(SuprimentosItem.id != item_id_ignorado)

    return query.first() is not None


def salvar_item(form_data, item=None):
    codigo = texto(form_data.get("codigo_interno")).upper() or None
    descricao = texto_maiusculo(form_data.get("descricao"))
    tipo = texto(form_data.get("tipo"))
    categoria_id = inteiro_ou_none(form_data.get("categoria_id"))
    unidade_medida_id = inteiro_ou_none(form_data.get("unidade_medida_id"))
    centro_custo_padrao_id = inteiro_ou_none(form_data.get("centro_custo_padrao_id"))
    estoque_minimo = decimal_ou_none(form_data.get("estoque_minimo"))

    if not descricao:
        return False, "Descricao do item e obrigatoria.", item

    if not categoria_id:
        return False, "Categoria e obrigatoria.", item

    if not unidade_medida_id:
        return False, "Unidade de medida e obrigatoria.", item

    if tipo not in TIPOS_ITEM:
        return False, "Tipo do item e invalido.", item

    if codigo_item_ja_existe(codigo, getattr(item, "id", None)):
        return False, "Ja existe item cadastrado com este codigo interno.", item

    if estoque_minimo is not None and estoque_minimo < 0:
        return False, "Estoque minimo nao pode ser negativo.", item

    if item is None:
        item = SuprimentosItem(ativo=True)
        db.session.add(item)

    item.codigo_interno = codigo
    item.descricao = descricao
    item.categoria_id = categoria_id
    item.unidade_medida_id = unidade_medida_id
    item.centro_custo_padrao_id = centro_custo_padrao_id
    item.tipo = tipo
    item.item_estocavel = False if tipo == "servico" else bool_form(form_data.get("item_estocavel"))
    item.ncm = texto_maiusculo(form_data.get("ncm")) or None
    item.estoque_minimo = estoque_minimo
    item.observacoes = texto_maiusculo(form_data.get("observacoes")) or None
    db.session.commit()
    return True, "Item salvo com sucesso.", item


def buscar_vinculos_fornecedor_item(fornecedor_id=None, item_id=None, status=None):
    query = SuprimentosFornecedorItem.query

    if fornecedor_id:
        query = query.filter(SuprimentosFornecedorItem.fornecedor_id == fornecedor_id)

    if item_id:
        query = query.filter(SuprimentosFornecedorItem.item_id == item_id)

    query = filtrar_status(query, SuprimentosFornecedorItem, status)
    return (
        query
        .join(SuprimentosFornecedor)
        .join(SuprimentosItem)
        .order_by(SuprimentosFornecedor.razao_social.asc(), SuprimentosItem.descricao.asc())
        .all()
    )


def vinculo_fornecedor_item_ja_existe(fornecedor_id, item_id, vinculo_id_ignorado=None):
    if not fornecedor_id or not item_id:
        return False

    query = SuprimentosFornecedorItem.query.filter_by(
        fornecedor_id=fornecedor_id,
        item_id=item_id,
    )

    if vinculo_id_ignorado is not None:
        query = query.filter(SuprimentosFornecedorItem.id != vinculo_id_ignorado)

    return query.first() is not None


def salvar_vinculo_fornecedor_item(form_data, vinculo=None):
    fornecedor_id = inteiro_ou_none(form_data.get("fornecedor_id"))
    item_id = inteiro_ou_none(form_data.get("item_id"))
    preco_referencia = decimal_ou_none(form_data.get("preco_referencia"))
    prazo_entrega_dias = inteiro_ou_none(form_data.get("prazo_entrega_dias"))

    if not fornecedor_id:
        return False, "Fornecedor e obrigatorio.", vinculo

    if not item_id:
        return False, "Item e obrigatorio.", vinculo

    if vinculo_fornecedor_item_ja_existe(
        fornecedor_id,
        item_id,
        getattr(vinculo, "id", None),
    ):
        return False, "Ja existe vinculo cadastrado para este fornecedor e item.", vinculo

    if preco_referencia is not None and preco_referencia < 0:
        return False, "Preco de referencia nao pode ser negativo.", vinculo

    if prazo_entrega_dias is not None and prazo_entrega_dias < 0:
        return False, "Prazo de entrega nao pode ser negativo.", vinculo

    if vinculo is None:
        vinculo = SuprimentosFornecedorItem(ativo=True)
        db.session.add(vinculo)

    vinculo.fornecedor_id = fornecedor_id
    vinculo.item_id = item_id
    vinculo.codigo_item_fornecedor = texto_maiusculo(form_data.get("codigo_item_fornecedor")) or None
    vinculo.descricao_item_fornecedor = texto_maiusculo(form_data.get("descricao_item_fornecedor")) or None
    vinculo.preco_referencia = preco_referencia
    vinculo.prazo_entrega_dias = prazo_entrega_dias
    vinculo.condicao_pagamento = texto_maiusculo(form_data.get("condicao_pagamento")) or None
    vinculo.observacoes = texto_maiusculo(form_data.get("observacoes")) or None
    vinculo.fornecedor_preferencial = bool_form(form_data.get("fornecedor_preferencial"))
    db.session.commit()
    return True, "Vinculo fornecedor x item salvo com sucesso.", vinculo


def gerar_numero_requisicao():
    ano = datetime.utcnow().year
    prefixo = f"RC-{ano}-"
    ultima = (
        SuprimentosRequisicaoCompra.query
        .filter(SuprimentosRequisicaoCompra.numero.like(f"{prefixo}%"))
        .order_by(SuprimentosRequisicaoCompra.numero.desc())
        .first()
    )

    if not ultima:
        return f"{prefixo}0001"

    try:
        sequencial = int(ultima.numero.rsplit("-", 1)[1]) + 1
    except (IndexError, ValueError):
        sequencial = 1

    return f"{prefixo}{sequencial:04d}"


def buscar_requisicoes_compra(numero=None, status=None, solicitante_id=None):
    query = SuprimentosRequisicaoCompra.query
    numero = texto(numero).upper()

    if numero:
        query = query.filter(SuprimentosRequisicaoCompra.numero.ilike(f"%{numero}%"))

    if status:
        query = query.filter(SuprimentosRequisicaoCompra.status == status)

    if solicitante_id:
        query = query.filter(SuprimentosRequisicaoCompra.solicitante_usuario_id == solicitante_id)

    return query.order_by(SuprimentosRequisicaoCompra.criado_em.desc()).all()


def salvar_requisicao_compra(form_data, usuario, requisicao=None):
    justificativa = texto_maiusculo(form_data.get("justificativa"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None
    centro_custo_id = inteiro_ou_none(form_data.get("centro_custo_id"))
    equipe_id = inteiro_ou_none(form_data.get("equipe_id"))
    veiculo_placa = texto_maiusculo(form_data.get("veiculo_placa")) or None

    if not justificativa:
        return False, "Justificativa e obrigatoria.", requisicao

    if equipe_id:
        equipe = buscar_por_id(Equipe, equipe_id)
        if not equipe or not equipe.ativo:
            return False, "Equipe nao encontrada ou inativa.", requisicao

    if requisicao and not requisicao.pode_editar:
        return False, "Somente requisicoes em rascunho podem ser editadas.", requisicao

    if requisicao is None:
        requisicao = SuprimentosRequisicaoCompra(
            numero=gerar_numero_requisicao(),
            solicitante_usuario_id=usuario.id,
            status=STATUS_REQUISICAO_RASCUNHO,
        )
        db.session.add(requisicao)

    requisicao.centro_custo_id = centro_custo_id
    requisicao.equipe_id = equipe_id
    requisicao.veiculo_placa = veiculo_placa
    requisicao.justificativa = justificativa
    requisicao.observacoes = observacoes
    db.session.commit()

    return True, "Requisicao salva com sucesso.", requisicao


def adicionar_item_requisicao(form_data, requisicao):
    if not requisicao.pode_editar:
        return False, "Somente requisicoes em rascunho podem receber itens.", None

    item_id = inteiro_ou_none(form_data.get("item_id"))
    quantidade = decimal_ou_none(form_data.get("quantidade"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    if not item_id:
        return False, "Item e obrigatorio.", None

    item = buscar_por_id(SuprimentosItem, item_id)

    if not item or not item.ativo:
        return False, "Item nao encontrado ou inativo.", None

    if quantidade is None or quantidade <= 0:
        return False, "Quantidade deve ser maior que zero.", None

    existente = SuprimentosRequisicaoCompraItem.query.filter_by(
        requisicao_id=requisicao.id,
        item_id=item.id,
    ).first()

    if existente:
        return False, "Este item ja foi adicionado a requisicao.", None

    requisicao_item = SuprimentosRequisicaoCompraItem(
        requisicao_id=requisicao.id,
        item_id=item.id,
        item_codigo_snapshot=item.codigo_interno,
        item_descricao_snapshot=item.descricao,
        unidade_medida_snapshot=item.unidade_medida.sigla,
        quantidade=quantidade,
        observacoes=observacoes,
    )
    db.session.add(requisicao_item)
    db.session.commit()

    return True, "Item adicionado com sucesso.", requisicao_item


def remover_item_requisicao(requisicao, requisicao_item):
    if not requisicao.pode_editar:
        return False, "Somente requisicoes em rascunho podem ter itens removidos."

    if requisicao_item.requisicao_id != requisicao.id:
        return False, "Item nao pertence a requisicao."

    db.session.delete(requisicao_item)
    db.session.commit()
    return True, "Item removido com sucesso."


def enviar_requisicao_compra(requisicao):
    if not requisicao.pode_editar:
        return False, "Somente requisicoes em rascunho podem ser enviadas."

    if not requisicao.itens:
        return False, "Adicione ao menos um item antes de enviar."

    requisicao.status = STATUS_REQUISICAO_ENVIADA
    requisicao.enviada_em = datetime.utcnow()
    db.session.commit()
    return True, "Requisicao enviada para analise."


def cancelar_requisicao_compra(requisicao, motivo=None):
    if requisicao.status == STATUS_REQUISICAO_CANCELADA:
        return False, "Requisicao ja esta cancelada."

    requisicao.status = STATUS_REQUISICAO_CANCELADA
    requisicao.cancelada_em = datetime.utcnow()
    requisicao.motivo_cancelamento = texto_maiusculo(motivo) or None
    db.session.commit()
    return True, "Requisicao cancelada com sucesso."


def gerar_numero_cotacao():
    ano = datetime.utcnow().year
    prefixo = f"COT-{ano}-"
    ultima = (
        SuprimentosCotacao.query
        .filter(SuprimentosCotacao.numero.like(f"{prefixo}%"))
        .order_by(SuprimentosCotacao.numero.desc())
        .first()
    )

    if not ultima:
        return f"{prefixo}0001"

    try:
        sequencial = int(ultima.numero.rsplit("-", 1)[1]) + 1
    except (IndexError, ValueError):
        sequencial = 1

    return f"{prefixo}{sequencial:04d}"


def gerar_numero_ordem_compra():
    ano = datetime.utcnow().year
    prefixo = f"OC-{ano}-"
    ultima = (
        SuprimentosOrdemCompra.query
        .filter(SuprimentosOrdemCompra.numero.like(f"{prefixo}%"))
        .order_by(SuprimentosOrdemCompra.numero.desc())
        .first()
    )

    if not ultima:
        return f"{prefixo}0001"

    try:
        sequencial = int(ultima.numero.rsplit("-", 1)[1]) + 1
    except (IndexError, ValueError):
        sequencial = 1

    return f"{prefixo}{sequencial:04d}"


def gerar_numero_recebimento_compra():
    ano = datetime.utcnow().year
    prefixo = f"REC-{ano}-"
    ultimo = (
        SuprimentosRecebimentoCompra.query
        .filter(SuprimentosRecebimentoCompra.numero.like(f"{prefixo}%"))
        .order_by(SuprimentosRecebimentoCompra.numero.desc())
        .first()
    )

    if not ultimo:
        return f"{prefixo}0001"

    try:
        sequencial = int(ultimo.numero.rsplit("-", 1)[1]) + 1
    except (IndexError, ValueError):
        sequencial = 1

    return f"{prefixo}{sequencial:04d}"


def buscar_ordens_compra(numero=None, status=None, fornecedor_id=None):
    query = SuprimentosOrdemCompra.query
    numero = texto(numero).upper()
    fornecedor_id = inteiro_ou_none(fornecedor_id)

    if numero:
        query = query.filter(SuprimentosOrdemCompra.numero.ilike(f"%{numero}%"))

    if status:
        query = query.filter(SuprimentosOrdemCompra.status == status)

    if fornecedor_id:
        query = query.filter(SuprimentosOrdemCompra.fornecedor_id == fornecedor_id)

    return query.order_by(SuprimentosOrdemCompra.criado_em.desc()).all()


def buscar_ordens_compra_cotacao(cotacao):
    return (
        SuprimentosOrdemCompra.query
        .filter_by(cotacao_id=cotacao.id)
        .order_by(SuprimentosOrdemCompra.numero.asc())
        .all()
    )


def buscar_cotacoes(numero=None, status=None):
    query = SuprimentosCotacao.query
    numero = texto(numero).upper()

    if numero:
        query = query.filter(SuprimentosCotacao.numero.ilike(f"%{numero}%"))

    if status:
        query = query.filter(SuprimentosCotacao.status == status)

    return query.order_by(SuprimentosCotacao.criado_em.desc()).all()


def requisicoes_disponiveis_para_cotacao():
    return (
        SuprimentosRequisicaoCompra.query
        .filter(SuprimentosRequisicaoCompra.status == STATUS_REQUISICAO_ENVIADA)
        .order_by(SuprimentosRequisicaoCompra.numero.asc())
        .all()
    )


def salvar_cotacao(form_data, usuario, cotacao=None):
    requisicao_id = inteiro_ou_none(form_data.get("requisicao_id"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    if cotacao and not cotacao.pode_editar:
        return False, "Somente cotacoes abertas podem ser editadas.", cotacao

    if cotacao is None:
        requisicao = buscar_por_id(SuprimentosRequisicaoCompra, requisicao_id)

        if not requisicao:
            return False, "Requisicao e obrigatoria.", None

        if requisicao.status != STATUS_REQUISICAO_ENVIADA:
            return False, "Somente requisicoes enviadas para analise podem iniciar cotacao.", None

        if not requisicao.itens:
            return False, "Requisicao sem itens nao pode iniciar cotacao.", None

        cotacao = SuprimentosCotacao(
            numero=gerar_numero_cotacao(),
            requisicao_id=requisicao.id,
            criado_por_usuario_id=usuario.id,
            status=STATUS_COTACAO_ABERTA,
        )
        db.session.add(cotacao)

    cotacao.observacoes = observacoes
    db.session.commit()
    return True, "Cotacao salva com sucesso.", cotacao


def fornecedores_disponiveis_para_requisicao_item(requisicao_item):
    return (
        SuprimentosFornecedor.query
        .join(SuprimentosFornecedorItem)
        .filter(
            SuprimentosFornecedorItem.item_id == requisicao_item.item_id,
            SuprimentosFornecedorItem.ativo.is_(True),
            SuprimentosFornecedor.ativo.is_(True),
        )
        .order_by(SuprimentosFornecedor.razao_social.asc())
        .all()
    )


def salvar_proposta_cotacao(form_data, cotacao):
    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas podem receber propostas.", None

    requisicao_item_id = inteiro_ou_none(form_data.get("requisicao_item_id"))
    fornecedor_id = inteiro_ou_none(form_data.get("fornecedor_id"))
    preco_unitario = decimal_ou_none(form_data.get("preco_unitario"))
    prazo_entrega_dias = inteiro_ou_none(form_data.get("prazo_entrega_dias"))
    condicao_pagamento = texto_maiusculo(form_data.get("condicao_pagamento")) or None
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    requisicao_item = buscar_por_id(SuprimentosRequisicaoCompraItem, requisicao_item_id)
    fornecedor = buscar_por_id(SuprimentosFornecedor, fornecedor_id)

    if not requisicao_item or requisicao_item.requisicao_id != cotacao.requisicao_id:
        return False, "Item da requisicao e obrigatorio.", None

    if not fornecedor or not fornecedor.ativo:
        return False, "Fornecedor e obrigatorio.", None

    vinculo = SuprimentosFornecedorItem.query.filter_by(
        fornecedor_id=fornecedor.id,
        item_id=requisicao_item.item_id,
        ativo=True,
    ).first()

    if not vinculo:
        return False, "Fornecedor nao esta vinculado ao item selecionado.", None

    if preco_unitario is None or preco_unitario < 0:
        return False, "Preco unitario deve ser maior ou igual a zero.", None

    if prazo_entrega_dias is not None and prazo_entrega_dias < 0:
        return False, "Prazo de entrega nao pode ser negativo.", None

    existente = SuprimentosCotacaoProposta.query.filter_by(
        cotacao_id=cotacao.id,
        fornecedor_id=fornecedor.id,
        requisicao_item_id=requisicao_item.id,
    ).first()

    if existente:
        return False, "Ja existe proposta deste fornecedor para este item.", None

    proposta = SuprimentosCotacaoProposta(
        cotacao_id=cotacao.id,
        fornecedor_id=fornecedor.id,
        requisicao_item_id=requisicao_item.id,
        item_id=requisicao_item.item_id,
        fornecedor_razao_social_snapshot=fornecedor.razao_social,
        item_descricao_snapshot=requisicao_item.item_descricao_snapshot,
        unidade_medida_snapshot=requisicao_item.unidade_medida_snapshot,
        quantidade_snapshot=requisicao_item.quantidade,
        preco_unitario=preco_unitario,
        prazo_entrega_dias=prazo_entrega_dias,
        condicao_pagamento=condicao_pagamento,
        observacoes=observacoes,
        ativo=True,
    )
    db.session.add(proposta)
    db.session.commit()

    return True, "Proposta registrada com sucesso.", proposta


def remover_proposta_cotacao(cotacao, proposta):
    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas podem ter propostas removidas."

    if proposta.cotacao_id != cotacao.id:
        return False, "Proposta nao pertence a cotacao."

    db.session.delete(proposta)
    db.session.commit()
    return True, "Proposta removida com sucesso."


def menor_preco_item_cotacao(cotacao, requisicao_item_id):
    valores = [
        proposta.preco_unitario
        for proposta in cotacao.propostas
        if proposta.requisicao_item_id == requisicao_item_id
    ]

    return min(valores) if valores else None


def propostas_selecionadas_por_item(cotacao):
    return {
        proposta.requisicao_item_id: proposta
        for proposta in cotacao.propostas
        if proposta.selecionada
    }


def selecionar_proposta_vencedora(form_data, cotacao, usuario):
    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas ou reprovadas podem ter vencedor selecionado.", None

    proposta_id = inteiro_ou_none(form_data.get("proposta_id"))
    justificativa = texto_maiusculo(form_data.get("justificativa_selecao"))

    if not proposta_id:
        return False, "Selecione uma proposta.", None

    proposta = SuprimentosCotacaoProposta.query.filter_by(
        id=proposta_id,
        cotacao_id=cotacao.id,
    ).first()

    if not proposta:
        return False, "Proposta nao encontrada nesta cotacao.", None

    menor_preco = menor_preco_item_cotacao(cotacao, proposta.requisicao_item_id)

    if menor_preco is None:
        return False, "Nao ha propostas para comparar neste item.", None

    escolha_fora_menor_preco = proposta.preco_unitario > menor_preco

    if escolha_fora_menor_preco and not justificativa:
        return False, "Informe a justificativa para escolher proposta acima do menor preco.", None

    for proposta_item in cotacao.propostas:
        if proposta_item.requisicao_item_id == proposta.requisicao_item_id:
            proposta_item.selecionada = False
            proposta_item.justificativa_selecao = None
            proposta_item.selecionada_por_usuario_id = None
            proposta_item.selecionada_em = None

    proposta.selecionada = True
    proposta.justificativa_selecao = justificativa
    proposta.selecionada_por_usuario_id = usuario.id
    proposta.selecionada_em = datetime.utcnow()

    if cotacao.status == STATUS_COTACAO_REPROVADA:
        cotacao.status = STATUS_COTACAO_ABERTA
        cotacao.reprovada_em = None
        cotacao.reprovada_por_usuario_id = None
        cotacao.observacoes_aprovacao = None

    db.session.commit()

    return True, "Proposta vencedora selecionada com sucesso.", proposta


def enviar_cotacao_para_aprovacao(cotacao, usuario):
    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas ou reprovadas podem ser enviadas para aprovacao."

    if not cotacao.propostas:
        return False, "Registre propostas antes de enviar para aprovacao."

    selecionadas = propostas_selecionadas_por_item(cotacao)
    itens_sem_vencedor = [
        item
        for item in cotacao.requisicao.itens
        if item.id not in selecionadas
    ]

    if itens_sem_vencedor:
        return False, "Selecione uma proposta vencedora para todos os itens antes de enviar para aprovacao."

    cotacao.status = STATUS_COTACAO_EM_APROVACAO
    cotacao.enviada_aprovacao_em = datetime.utcnow()
    cotacao.aprovada_em = None
    cotacao.aprovada_por_usuario_id = None
    cotacao.reprovada_em = None
    cotacao.reprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = None
    db.session.commit()

    return True, "Cotacao enviada para aprovacao com sucesso."


def aprovar_cotacao(cotacao, usuario, form_data=None):
    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return False, "Somente cotacoes em aprovacao podem ser aprovadas."

    cotacao.status = STATUS_COTACAO_APROVADA
    cotacao.aprovada_em = datetime.utcnow()
    cotacao.aprovada_por_usuario_id = usuario.id
    cotacao.reprovada_em = None
    cotacao.reprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = texto_maiusculo((form_data or {}).get("observacoes_aprovacao"))
    db.session.commit()

    return True, "Cotacao aprovada com sucesso."


def reprovar_cotacao(cotacao, usuario, form_data=None):
    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return False, "Somente cotacoes em aprovacao podem ser reprovadas."

    justificativa = texto_maiusculo((form_data or {}).get("observacoes_aprovacao"))

    if not justificativa:
        return False, "Informe a justificativa da reprovacao."

    cotacao.status = STATUS_COTACAO_REPROVADA
    cotacao.reprovada_em = datetime.utcnow()
    cotacao.reprovada_por_usuario_id = usuario.id
    cotacao.aprovada_em = None
    cotacao.aprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = justificativa
    db.session.commit()

    return True, "Cotacao reprovada e liberada para ajustes."


def gerar_ordens_compra_cotacao(cotacao, usuario, form_data=None):
    if cotacao.status != STATUS_COTACAO_APROVADA:
        return False, "Somente cotacoes aprovadas podem gerar ordem de compra.", []

    existentes = [
        ordem
        for ordem in buscar_ordens_compra_cotacao(cotacao)
        if ordem.status != STATUS_ORDEM_COMPRA_CANCELADA
    ]

    if existentes:
        return False, "Esta cotacao ja possui ordem de compra gerada.", existentes

    selecionadas = [
        proposta
        for proposta in cotacao.propostas
        if proposta.selecionada
    ]

    if not selecionadas:
        return False, "Selecione propostas vencedoras antes de gerar ordem de compra.", []

    selecionadas_por_item = {proposta.requisicao_item_id: proposta for proposta in selecionadas}
    itens_sem_vencedor = [
        item
        for item in cotacao.requisicao.itens
        if item.id not in selecionadas_por_item
    ]

    if itens_sem_vencedor:
        return False, "A cotacao aprovada precisa ter vencedor em todos os itens.", []

    observacoes = texto_maiusculo((form_data or {}).get("observacoes")) or None
    propostas_por_fornecedor = {}

    for proposta in selecionadas:
        propostas_por_fornecedor.setdefault(proposta.fornecedor_id, []).append(proposta)

    ordens = []

    for fornecedor_id, propostas in sorted(propostas_por_fornecedor.items()):
        fornecedor = propostas[0].fornecedor
        condicoes = sorted(
            {
                proposta.condicao_pagamento
                for proposta in propostas
                if proposta.condicao_pagamento
            }
        )
        ordem = SuprimentosOrdemCompra(
            numero=gerar_numero_ordem_compra(),
            cotacao_id=cotacao.id,
            requisicao_id=cotacao.requisicao_id,
            fornecedor_id=fornecedor_id,
            criado_por_usuario_id=usuario.id,
            fornecedor_razao_social_snapshot=fornecedor.razao_social,
            fornecedor_cnpj_cpf_snapshot=fornecedor.cnpj_cpf,
            condicao_pagamento_snapshot=" | ".join(condicoes) if condicoes else None,
            status=STATUS_ORDEM_COMPRA_GERADA,
            observacoes=observacoes,
            gerada_em=datetime.utcnow(),
        )
        db.session.add(ordem)
        db.session.flush()

        for proposta in sorted(propostas, key=lambda item: item.item_descricao_snapshot):
            requisicao_item = proposta.requisicao_item
            db.session.add(
                SuprimentosOrdemCompraItem(
                    ordem_compra_id=ordem.id,
                    cotacao_proposta_id=proposta.id,
                    requisicao_item_id=proposta.requisicao_item_id,
                    item_id=proposta.item_id,
                    item_codigo_snapshot=requisicao_item.item_codigo_snapshot,
                    item_descricao_snapshot=proposta.item_descricao_snapshot,
                    unidade_medida_snapshot=proposta.unidade_medida_snapshot,
                    quantidade=proposta.quantidade_snapshot,
                    preco_unitario=proposta.preco_unitario,
                    prazo_entrega_dias=proposta.prazo_entrega_dias,
                    observacoes=proposta.observacoes,
                )
            )

        ordens.append(ordem)

    db.session.commit()
    return True, "Ordem de compra gerada com sucesso.", ordens


def atualizar_status_recebimento_ordem(ordem_compra):
    if ordem_compra.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return

    if not ordem_compra.itens:
        ordem_compra.status = STATUS_ORDEM_COMPRA_GERADA
        return

    saldos = [item.saldo_receber for item in ordem_compra.itens]
    quantidades_recebidas = [item.quantidade_recebida for item in ordem_compra.itens]

    if all(saldo <= 0 for saldo in saldos):
        ordem_compra.status = STATUS_ORDEM_COMPRA_RECEBIDA
    elif any(quantidade > 0 for quantidade in quantidades_recebidas):
        ordem_compra.status = STATUS_ORDEM_COMPRA_PARCIAL
    else:
        ordem_compra.status = STATUS_ORDEM_COMPRA_GERADA


def registrar_recebimento_ordem_compra(form_data, ordem_compra, usuario):
    if not ordem_compra.pode_receber:
        return False, "Somente ordens geradas ou parcialmente recebidas podem receber itens.", None

    tipo_documento = texto(form_data.get("tipo_documento"))
    numero_documento = texto_maiusculo(form_data.get("numero_documento"))
    data_documento = data_ou_none(form_data.get("data_documento"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None
    itens_recebidos = []

    if tipo_documento not in TIPOS_DOCUMENTO_RECEBIMENTO:
        return False, "Tipo de documento e obrigatorio.", None

    if not numero_documento:
        return False, "Numero do documento e obrigatorio.", None

    if texto(form_data.get("data_documento")) and data_documento is None:
        return False, "Data do documento invalida.", None

    for item in ordem_compra.itens:
        quantidade = decimal_ou_none(form_data.get(f"quantidade_recebida_{item.id}"))
        observacao_item = texto_maiusculo(form_data.get(f"observacoes_item_{item.id}")) or None

        if quantidade is None or quantidade == 0:
            continue

        if quantidade < 0:
            return False, "Quantidade recebida nao pode ser negativa.", None

        if quantidade > item.saldo_receber:
            return False, "Quantidade recebida nao pode ser maior que o saldo do item.", None

        itens_recebidos.append((item, quantidade, observacao_item))

    if not itens_recebidos:
        return False, "Informe quantidade recebida para ao menos um item.", None

    recebimento = SuprimentosRecebimentoCompra(
        numero=gerar_numero_recebimento_compra(),
        ordem_compra_id=ordem_compra.id,
        recebido_por_usuario_id=usuario.id,
        status=STATUS_RECEBIMENTO_COMPRA_REGISTRADO,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        data_documento=data_documento,
        observacoes=observacoes,
        recebido_em=datetime.utcnow(),
    )
    db.session.add(recebimento)
    db.session.flush()

    for ordem_item, quantidade, observacao_item in itens_recebidos:
        db.session.add(
            SuprimentosRecebimentoCompraItem(
                recebimento_id=recebimento.id,
                ordem_compra_item_id=ordem_item.id,
                item_id=ordem_item.item_id,
                item_codigo_snapshot=ordem_item.item_codigo_snapshot,
                item_descricao_snapshot=ordem_item.item_descricao_snapshot,
                unidade_medida_snapshot=ordem_item.unidade_medida_snapshot,
                quantidade_recebida=quantidade,
                observacoes=observacao_item,
            )
        )

    db.session.flush()
    for ordem_item in ordem_compra.itens:
        db.session.expire(ordem_item, ["recebimentos"])
    atualizar_status_recebimento_ordem(ordem_compra)
    db.session.commit()

    return True, "Recebimento registrado com sucesso.", recebimento


def cancelar_ordem_compra(ordem_compra, motivo=None):
    if ordem_compra.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return False, "Ordem de compra ja esta cancelada."

    if ordem_compra.status in [STATUS_ORDEM_COMPRA_PARCIAL, STATUS_ORDEM_COMPRA_RECEBIDA]:
        return False, "Ordem de compra com recebimento nao pode ser cancelada."

    ordem_compra.status = STATUS_ORDEM_COMPRA_CANCELADA
    ordem_compra.cancelada_em = datetime.utcnow()
    ordem_compra.motivo_cancelamento = texto_maiusculo(motivo) or None
    db.session.commit()
    return True, "Ordem de compra cancelada com sucesso."


def encerrar_cotacao(cotacao):
    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas podem ser encerradas."

    if not cotacao.propostas:
        return False, "Registre ao menos uma proposta antes de encerrar."

    cotacao.status = STATUS_COTACAO_ENCERRADA
    cotacao.encerrada_em = datetime.utcnow()
    db.session.commit()
    return True, "Cotacao encerrada com sucesso."


def cancelar_cotacao(cotacao):
    if cotacao.status == STATUS_COTACAO_CANCELADA:
        return False, "Cotacao ja esta cancelada."

    cotacao.status = STATUS_COTACAO_CANCELADA
    cotacao.encerrada_em = datetime.utcnow()
    db.session.commit()
    return True, "Cotacao cancelada com sucesso."


def montar_mapa_comparativo_cotacao(cotacao):
    propostas_por_item = {}

    for proposta in cotacao.propostas:
        propostas_por_item.setdefault(proposta.requisicao_item_id, []).append(proposta)

    grupos = []
    totais = {
        "itens": 0,
        "itens_com_proposta": 0,
        "propostas": 0,
    }

    for requisicao_item in cotacao.requisicao.itens:
        propostas = sorted(
            propostas_por_item.get(requisicao_item.id, []),
            key=lambda proposta: (
                proposta.preco_unitario,
                proposta.prazo_entrega_dias if proposta.prazo_entrega_dias is not None else 999999,
                proposta.fornecedor_razao_social_snapshot,
            ),
        )

        menor_preco = min((proposta.preco_unitario for proposta in propostas), default=None)
        menor_total = min((proposta.valor_total for proposta in propostas), default=None)
        prazos_informados = [
            proposta.prazo_entrega_dias
            for proposta in propostas
            if proposta.prazo_entrega_dias is not None
        ]
        menor_prazo = min(prazos_informados) if prazos_informados else None

        linhas = []

        for proposta in propostas:
            destaque_preco = proposta.preco_unitario == menor_preco if menor_preco is not None else False
            destaque_total = proposta.valor_total == menor_total if menor_total is not None else False
            destaque_prazo = (
                proposta.prazo_entrega_dias == menor_prazo
                if menor_prazo is not None and proposta.prazo_entrega_dias is not None
                else False
            )

            linhas.append(
                {
                    "proposta": proposta,
                    "valor_total": proposta.valor_total,
                    "menor_preco": destaque_preco,
                    "menor_total": destaque_total,
                    "menor_prazo": destaque_prazo,
                    "melhor_custo": destaque_preco and destaque_total,
                }
            )

        grupos.append(
            {
                "item": requisicao_item,
                "propostas": linhas,
                "menor_preco": menor_preco,
                "menor_total": menor_total,
                "menor_prazo": menor_prazo,
            }
        )

        totais["itens"] += 1
        totais["propostas"] += len(propostas)

        if propostas:
            totais["itens_com_proposta"] += 1

    totais["itens_sem_proposta"] = totais["itens"] - totais["itens_com_proposta"]

    return {
        "cotacao": cotacao,
        "grupos": grupos,
        "totais": totais,
    }


def normalizar_dados_cnpj_api(dados):
    razao_social = (
        dados.get("razao_social")
        or dados.get("nome")
        or dados.get("name")
        or ""
    )
    nome_fantasia = (
        dados.get("nome_fantasia")
        or dados.get("fantasia")
        or dados.get("alias")
        or ""
    )

    return {
        "razao_social": texto_maiusculo(razao_social),
        "nome_fantasia": texto_maiusculo(nome_fantasia),
        "email": texto(dados.get("email")).lower(),
        "telefone": normalizar_telefone_brasil(dados.get("ddd_telefone_1") or dados.get("telefone")),
        "endereco": texto_maiusculo(
            " ".join(
                item
                for item in [
                    dados.get("descricao_tipo_de_logradouro") or dados.get("tipo_logradouro"),
                    dados.get("logradouro"),
                    dados.get("numero"),
                    dados.get("complemento"),
                    dados.get("bairro"),
                    dados.get("cep"),
                ]
                if item
            )
        ),
        "cidade": texto_maiusculo(dados.get("municipio") or dados.get("cidade")),
        "uf": texto(dados.get("uf")).upper()[:2],
    }


def consultar_cnpj_publico(cnpj):
    cnpj = somente_digitos(cnpj)

    if not validar_cnpj(cnpj):
        return False, "CNPJ invalido.", None

    url_base = os.environ.get("SUPRIMENTOS_CNPJ_API_URL", "").strip()
    token = os.environ.get("SUPRIMENTOS_CNPJ_API_TOKEN", "").strip()

    if url_base:
        url = url_base.rstrip("/") + "/" + quote(cnpj)
    else:
        url = f"https://brasilapi.com.br/api/cnpj/v1/{quote(cnpj)}"

    headers = {"Accept": "application/json", "User-Agent": "Rental-Retros-Suprimentos/1.0"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        requisicao = Request(url, headers=headers)

        with urlopen(requisicao, timeout=8) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))

    except HTTPError as erro:
        if erro.code == 404:
            return False, "CNPJ nao encontrado na fonte publica configurada.", None

        return False, "Nao foi possivel consultar o CNPJ agora.", None
    except (URLError, TimeoutError, json.JSONDecodeError):
        return False, "Nao foi possivel consultar o CNPJ agora.", None

    dados_normalizados = normalizar_dados_cnpj_api(dados)

    if not dados_normalizados["razao_social"]:
        return False, "Consulta retornou dados incompletos.", None

    return True, "CNPJ consultado com sucesso.", dados_normalizados
