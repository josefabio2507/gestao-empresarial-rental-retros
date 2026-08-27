import hashlib
import re
import json
import os
import platform
import secrets
import unicodedata
from io import BytesIO
from flask import current_app
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.services.email_service import enviar_email, smtp_configurado
from app.utils.datas import agora_brasil
from app.models import (
    CentroCusto,
    Departamento,
    Equipe,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosAlcadaAprovacao,
    SuprimentosCategoriaItem,
    SuprimentosComprador,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosCotacao,
    SuprimentosCotacaoProposta,
    SuprimentosRequisicaoCompra,
    SuprimentosRequisicaoCompraItem,
    SuprimentosOrdemCompra,
    SuprimentosOrdemCompraItem,
    SuprimentosOrdemCompraParcela,
    SuprimentosMovimentacaoEstoque,
    SuprimentosRecebimentoCompra,
    SuprimentosRecebimentoCompraItem,
    SuprimentosOrdemCompraItemEvidencia,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.google_drive_service import (
    GOOGLE_DRIVE_UPLOAD_SCOPES,
    GoogleDriveConfiguracaoErro,
    criar_google_drive_client_upload,
    erro_cota_storage_service_account,
    mensagem_cota_storage_service_account,
    upload_arquivo_google_drive,
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
STATUS_REQUISICAO_APROVADA = "Aprovada"
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
STATUS_COTACAO_REQUISICAO_ENVIADA = {
    STATUS_COTACAO_ABERTA,
    STATUS_COTACAO_EM_APROVACAO,
}
STATUS_COTACAO_REQUISICAO_APROVADA = {
    STATUS_COTACAO_APROVADA,
    STATUS_COTACAO_ENCERRADA,
}
STATUS_COTACAO_REQUISICAO_CANCELADA = {
    STATUS_COTACAO_REPROVADA,
    STATUS_COTACAO_CANCELADA,
}
STATUS_ORDEM_COMPRA_GERADA = "Gerada"
STATUS_ORDEM_COMPRA_PARCIAL = "Parcialmente Recebida"
STATUS_ORDEM_COMPRA_RECEBIDA = "Recebida"
STATUS_ORDEM_COMPRA_CANCELADA = "Cancelada"
CLASSE_CENTRO_CUSTO = "CENTRO DE CUSTO"
CLASSE_CENTRO_CUSTO_EQUIPES = "CENTRO DE CUSTO EQUIPES"
CLASSE_CENTRO_EPG_VEICULOS = "CENTRO DE EGP VEÍCULOS"
CLASSES_CENTRO_CUSTO = [
    CLASSE_CENTRO_CUSTO,
    CLASSE_CENTRO_CUSTO_EQUIPES,
    CLASSE_CENTRO_EPG_VEICULOS,
]
STATUS_FINANCEIRO_PENDENTE = "Pendente de Financeiro"
STATUS_FINANCEIRO_PREPARADO = "Preparado para Financeiro"
STATUS_FINANCEIRO_PROVISIONADO = "Provisionado"
STATUS_FINANCEIRO_CANCELADO = "Cancelado"
STATUS_RECEBIMENTO_COMPRA_REGISTRADO = "Registrado"
STATUS_RECEBIMENTO_COMPRA_CANCELADO = "Cancelado"
TIPO_MOVIMENTACAO_ESTOQUE_ENTRADA = "Entrada"
TIPO_MOVIMENTACAO_ESTOQUE_SAIDA = "Saida"
ORIGEM_MOVIMENTACAO_ESTOQUE_RECEBIMENTO_OC = "Recebimento OC"
ORIGEM_MOVIMENTACAO_ESTOQUE_AJUSTE_ENTRADA = "Ajuste Entrada"
ORIGEM_MOVIMENTACAO_ESTOQUE_AJUSTE_SAIDA = "Ajuste Saida"
ORIGEM_MOVIMENTACAO_ESTOQUE_CONSUMO_INTERNO = "Consumo Interno"
ORIGEM_MOVIMENTACAO_ESTOQUE_INVENTARIO = "Inventario"
STATUS_MOVIMENTACAO_ESTOQUE_REGISTRADA = "Registrada"
STATUS_MOVIMENTACAO_ESTOQUE_CANCELADA = "Cancelada"
TIPOS_MOVIMENTACAO_MANUAL_ESTOQUE = {
    "ajuste_entrada": {
        "tipo": TIPO_MOVIMENTACAO_ESTOQUE_ENTRADA,
        "origem": ORIGEM_MOVIMENTACAO_ESTOQUE_AJUSTE_ENTRADA,
    },
    "ajuste_saida": {
        "tipo": TIPO_MOVIMENTACAO_ESTOQUE_SAIDA,
        "origem": ORIGEM_MOVIMENTACAO_ESTOQUE_AJUSTE_SAIDA,
    },
    "consumo_interno": {
        "tipo": TIPO_MOVIMENTACAO_ESTOQUE_SAIDA,
        "origem": ORIGEM_MOVIMENTACAO_ESTOQUE_CONSUMO_INTERNO,
    },
    "inventario": {
        "origem": ORIGEM_MOVIMENTACAO_ESTOQUE_INVENTARIO,
    },
}
TIPOS_DOCUMENTO_RECEBIMENTO = {
    "Nota Fiscal",
    "Cupom Fiscal",
    "Romaneio",
    "Outro",
}
STATUS_EVIDENCIA_OC_PENDENTE = "Pendente"
STATUS_EVIDENCIA_OC_EVIDENCIADO = "Evidenciado"
STATUS_EVIDENCIA_OC_CANCELADO = "Cancelado"
EXTENSOES_IMAGEM_EVIDENCIA_OC = {".jpg", ".jpeg", ".png", ".webp"}
MIME_IMAGEM_EVIDENCIA_OC = "image/jpeg"
TAMANHO_MAXIMO_IMAGEM_EVIDENCIA_OC = (800, 800)
QUALIDADE_IMAGEM_EVIDENCIA_OC = 70


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


def _extensao_arquivo(nome_arquivo):
    nome_arquivo = texto(nome_arquivo).lower()
    if "." not in nome_arquivo:
        return ""
    return f".{nome_arquivo.rsplit('.', 1)[1]}"


def _normalizar_imagem_para_jpg(file_storage):
    if not file_storage or not texto(file_storage.filename):
        return None, None

    extensao = _extensao_arquivo(file_storage.filename)
    if extensao not in EXTENSOES_IMAGEM_EVIDENCIA_OC:
        return None, "Arquivo invalido. Envie apenas imagens JPG, JPEG, PNG ou WEBP."

    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise RuntimeError("Biblioteca Pillow nao instalada.") from exc

    try:
        file_storage.stream.seek(0)
        imagem = Image.open(file_storage.stream)
        imagem.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return None, "Arquivo invalido. A foto enviada nao foi reconhecida como imagem."

    imagem = ImageOps.exif_transpose(imagem)

    if imagem.mode in ("RGBA", "LA") or (
        imagem.mode == "P" and "transparency" in imagem.info
    ):
        fundo = Image.new("RGB", imagem.size, (255, 255, 255))
        fundo.paste(imagem.convert("RGBA"), mask=imagem.convert("RGBA").split()[-1])
        imagem = fundo
    else:
        imagem = imagem.convert("RGB")

    imagem.thumbnail(TAMANHO_MAXIMO_IMAGEM_EVIDENCIA_OC)
    saida = BytesIO()
    imagem.save(
        saida,
        format="JPEG",
        quality=QUALIDADE_IMAGEM_EVIDENCIA_OC,
        optimize=True,
    )

    return saida.getvalue(), None


def _sequencia_item_ordem_compra(ordem_compra, ordem_compra_item):
    itens = sorted(ordem_compra.itens, key=lambda item: item.id or 0)
    for indice, item in enumerate(itens, start=1):
        if item.id == ordem_compra_item.id:
            return indice
    return 1


def _nome_arquivo_evidencia_oc(ordem_compra, ordem_compra_item, numero_foto):
    sequencia = _sequencia_item_ordem_compra(ordem_compra, ordem_compra_item)
    numero_oc = re.sub(r"[^A-Za-z0-9_-]+", "-", ordem_compra.numero or str(ordem_compra.id))
    timestamp = agora_brasil().strftime("%Y%m%d-%H%M%S")
    return f"OC-{numero_oc}_ITEM-{sequencia:03d}_FOTO-{numero_foto}_{timestamp}.jpg"


def status_evidencia_item_oc(ordem_compra_item):
    evidencia = getattr(ordem_compra_item, "evidencia", None)
    if evidencia and evidencia.status != STATUS_EVIDENCIA_OC_CANCELADO:
        return STATUS_EVIDENCIA_OC_EVIDENCIADO
    return STATUS_EVIDENCIA_OC_PENDENTE


def totalizar_evidencias_ordem_compra(ordem_compra):
    total_itens = len(ordem_compra.itens)
    evidenciados = sum(
        1
        for item in ordem_compra.itens
        if status_evidencia_item_oc(item) == STATUS_EVIDENCIA_OC_EVIDENCIADO
    )
    return {
        "total_itens": total_itens,
        "evidenciados": evidenciados,
        "pendentes": max(total_itens - evidenciados, 0),
    }


def salvar_evidencia_item_ordem_compra(
    ordem_compra,
    ordem_compra_item,
    form_data,
    files_data,
    usuario,
    drive_service=None,
):
    if not ordem_compra or not ordem_compra_item:
        return False, "Ordem de compra ou item nao encontrado.", None

    if ordem_compra_item.ordem_compra_id != ordem_compra.id:
        return False, "Item nao pertence a ordem de compra informada.", None

    data_evidencia = data_ou_none(form_data.get("data_evidencia")) or date.today()
    destino_real = texto_maiusculo(form_data.get("destino_real"))
    observacao = texto_maiusculo(form_data.get("observacao")) or None

    if not destino_real:
        return False, "Destino/aplicacao real e obrigatorio.", None

    evidencia = ordem_compra_item.evidencia
    foto_1 = files_data.get("foto_1") if files_data else None
    foto_2 = files_data.get("foto_2") if files_data else None
    tem_foto_1_nova = bool(foto_1 and texto(foto_1.filename))
    tem_foto_2_nova = bool(foto_2 and texto(foto_2.filename))

    if not evidencia and not tem_foto_1_nova and not tem_foto_2_nova:
        return False, "Envie ao menos uma foto para registrar a evidencia.", None

    if evidencia and evidencia.foto_1_drive_file_id and tem_foto_1_nova:
        return False, "A foto 1 ja foi registrada. Nesta versao, fotos registradas nao sao substituidas.", evidencia

    if evidencia and evidencia.foto_2_drive_file_id and tem_foto_2_nova:
        return False, "A foto 2 ja foi registrada. Nesta versao, fotos registradas nao sao substituidas.", evidencia

    imagens_para_upload = []
    for numero_foto, arquivo in [(1, foto_1), (2, foto_2)]:
        if not arquivo or not texto(arquivo.filename):
            continue

        conteudo, erro = _normalizar_imagem_para_jpg(arquivo)
        if erro:
            return False, erro, evidencia

        imagens_para_upload.append(
            {
                "numero_foto": numero_foto,
                "nome": _nome_arquivo_evidencia_oc(ordem_compra, ordem_compra_item, numero_foto),
                "conteudo": conteudo,
            }
        )

    uploads = {}
    if imagens_para_upload:
        folder_id = current_app.config.get("GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID", "").strip()
        if not folder_id:
            return False, "Configure GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID para salvar as fotos no Google Drive.", evidencia

        try:
            service = drive_service or criar_google_drive_client_upload(scopes=GOOGLE_DRIVE_UPLOAD_SCOPES)
            for imagem in imagens_para_upload:
                arquivo_drive = upload_arquivo_google_drive(
                    service,
                    folder_id,
                    imagem["nome"],
                    imagem["conteudo"],
                    MIME_IMAGEM_EVIDENCIA_OC,
                )
                uploads[imagem["numero_foto"]] = {
                    "id": arquivo_drive.get("id"),
                    "nome": arquivo_drive.get("name") or imagem["nome"],
                    "link": arquivo_drive.get("webViewLink") or arquivo_drive.get("webContentLink"),
                }
        except GoogleDriveConfiguracaoErro as exc:
            return False, str(exc), evidencia
        except Exception as exc:
            current_app.logger.exception("Falha ao enviar evidencia de OC para o Google Drive.")
            if erro_cota_storage_service_account(exc):
                return False, mensagem_cota_storage_service_account(), evidencia
            return False, "Nao foi possivel enviar a foto para o Google Drive.", evidencia

    if not evidencia:
        evidencia = SuprimentosOrdemCompraItemEvidencia(
            ordem_compra=ordem_compra,
            ordem_compra_item=ordem_compra_item,
            criado_por=usuario,
            numero_oc_snapshot=ordem_compra.numero,
            numero_item_snapshot=f"{_sequencia_item_ordem_compra(ordem_compra, ordem_compra_item):03d}",
            descricao_item_snapshot=ordem_compra_item.item_descricao_snapshot,
            unidade_medida_snapshot=ordem_compra_item.unidade_medida_snapshot,
            quantidade_snapshot=ordem_compra_item.quantidade,
        )
        db.session.add(evidencia)

    evidencia.destino_real = destino_real
    evidencia.observacao = observacao
    evidencia.data_evidencia = data_evidencia
    evidencia.status = STATUS_EVIDENCIA_OC_EVIDENCIADO

    if 1 in uploads:
        evidencia.foto_1_drive_file_id = uploads[1]["id"]
        evidencia.foto_1_nome_arquivo = uploads[1]["nome"]
        evidencia.foto_1_link = uploads[1]["link"]
    if 2 in uploads:
        evidencia.foto_2_drive_file_id = uploads[2]["id"]
        evidencia.foto_2_nome_arquivo = uploads[2]["nome"]
        evidencia.foto_2_link = uploads[2]["link"]

    if not evidencia.foto_1_drive_file_id and evidencia.foto_2_drive_file_id:
        evidencia.foto_1_drive_file_id = evidencia.foto_2_drive_file_id
        evidencia.foto_1_nome_arquivo = evidencia.foto_2_nome_arquivo
        evidencia.foto_1_link = evidencia.foto_2_link
        evidencia.foto_2_drive_file_id = None
        evidencia.foto_2_nome_arquivo = None
        evidencia.foto_2_link = None

    db.session.commit()
    return True, "Evidencia salva com sucesso.", evidencia


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


def buscar_centros_custo(nome=None, status=None, classe=None):
    query = CentroCusto.query
    nome = texto(nome)
    classe = texto(classe).upper()

    if nome:
        query = query.filter(
            CentroCusto.nome.ilike(f"%{nome}%")
            | CentroCusto.codigo.ilike(f"%{nome}%")
        )

    if classe:
        query = query.filter(CentroCusto.classe == classe)

    query = filtrar_status(query, CentroCusto, status)
    return query.order_by(CentroCusto.nome.asc()).all()


def buscar_centros_custo_ativos(classe=None):
    query = CentroCusto.query.filter_by(ativo=True)
    classe = texto(classe).upper()

    if classe:
        query = query.filter(CentroCusto.classe == classe)

    return query.order_by(CentroCusto.nome.asc()).all()


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
    classe = texto(form_data.get("classe")).upper() or CLASSE_CENTRO_CUSTO

    if not nome:
        return False, "Nome do centro de custo e obrigatorio.", centro

    if classe not in CLASSES_CENTRO_CUSTO:
        return False, "Classe de centro de custo invalida.", centro

    if codigo_centro_custo_ja_existe(codigo, getattr(centro, "id", None)):
        return False, "Ja existe centro de custo cadastrado com este codigo.", centro

    if centro is None:
        centro = CentroCusto(ativo=True)
        db.session.add(centro)

    centro.codigo = codigo
    centro.nome = nome
    centro.classe = classe
    centro.descricao = texto_maiusculo(form_data.get("descricao")) or None
    db.session.commit()
    return True, "Centro de custo salvo com sucesso.", centro


def buscar_centro_custo_ativo_por_classe(centro_id, classe):
    centro_id = inteiro_ou_none(centro_id)

    if not centro_id:
        return None

    return (
        CentroCusto.query
        .filter(
            CentroCusto.id == centro_id,
            CentroCusto.ativo.is_(True),
            CentroCusto.classe == classe,
        )
        .first()
    )


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


def gerar_proximo_codigo_item(item_id_ignorado=None):
    maior_numero = 0
    maior_tamanho = 6

    query = SuprimentosItem.query.with_entities(SuprimentosItem.id, SuprimentosItem.codigo_interno)
    if item_id_ignorado is not None:
        query = query.filter(SuprimentosItem.id != item_id_ignorado)

    maior_id = 0
    for item_id, codigo in query:
        maior_id = max(maior_id, item_id or 0)
        codigo = texto(codigo)

        if not re.fullmatch(r"\d{1,12}", codigo):
            continue

        numero = int(codigo)
        if numero > maior_numero:
            maior_numero = numero
            maior_tamanho = max(6, len(codigo))

    if maior_numero == 0:
        maior_numero = maior_id

    while True:
        proximo_codigo = str(maior_numero + 1).zfill(maior_tamanho)
        if len(proximo_codigo) > 60:
            proximo_codigo = str(maior_id + 1)

        if not codigo_item_ja_existe(proximo_codigo, item_id_ignorado):
            return proximo_codigo

        maior_numero += 1
        maior_id += 1


def categoria_padrao_item_id():
    categoria = (
        SuprimentosCategoriaItem.query
        .filter(func.lower(SuprimentosCategoriaItem.slug) == "sem_categoria")
        .first()
    )

    if categoria:
        return categoria.id

    categoria = (
        SuprimentosCategoriaItem.query
        .filter(func.upper(func.trim(SuprimentosCategoriaItem.nome)) == "SEM CATEGORIA")
        .first()
    )

    if categoria:
        return categoria.id

    categoria = (
        SuprimentosCategoriaItem.query
        .filter(SuprimentosCategoriaItem.ativo.is_(True))
        .order_by(SuprimentosCategoriaItem.id.asc())
        .first()
    )

    if categoria:
        return categoria.id

    categoria = SuprimentosCategoriaItem(
        nome="SEM CATEGORIA",
        slug="sem_categoria",
        descricao="Categoria interna usada quando o cadastro de item nao exige categoria.",
        ativo=True,
    )
    db.session.add(categoria)
    db.session.flush()
    return categoria.id


def salvar_item(form_data, item=None):
    descricao = texto_maiusculo(form_data.get("descricao"))
    tipo = texto(form_data.get("tipo"))
    unidade_medida_id = inteiro_ou_none(form_data.get("unidade_medida_id"))
    centro_custo_padrao_id = inteiro_ou_none(form_data.get("centro_custo_padrao_id"))
    estoque_minimo = decimal_ou_none(form_data.get("estoque_minimo"))
    ncm = texto_maiusculo(form_data.get("ncm")) or None
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    if not descricao:
        return False, "Descricao do item e obrigatoria.", item

    if not unidade_medida_id:
        return False, "Unidade de medida e obrigatoria.", item

    if tipo not in TIPOS_ITEM:
        return False, "Tipo do item e invalido.", item

    if estoque_minimo is not None and estoque_minimo < 0:
        return False, "Estoque minimo nao pode ser negativo.", item

    codigo_interno = item.codigo_interno if item and item.codigo_interno else gerar_proximo_codigo_item(getattr(item, "id", None))
    categoria_id = categoria_padrao_item_id()

    if item is None:
        item = SuprimentosItem(ativo=True, codigo_interno=codigo_interno)
        db.session.add(item)
    else:
        item.codigo_interno = codigo_interno

    item.descricao = descricao
    item.categoria_id = categoria_id
    item.unidade_medida_id = unidade_medida_id
    item.centro_custo_padrao_id = centro_custo_padrao_id
    item.tipo = tipo
    item.item_estocavel = False if tipo == "servico" else bool_form(form_data.get("item_estocavel"))
    item.ncm = ncm
    item.estoque_minimo = estoque_minimo
    item.observacoes = observacoes
    db.session.flush()
    db.session.commit()
    db.session.refresh(item)

    if (
        item.descricao != descricao
        or item.unidade_medida_id != unidade_medida_id
        or item.centro_custo_padrao_id != centro_custo_padrao_id
        or item.tipo != tipo
        or item.ncm != ncm
        or item.observacoes != observacoes
    ):
        db.session.rollback()
        return False, "Nao foi possivel confirmar a atualizacao do item. Tente salvar novamente.", item

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
    ano = agora_brasil().year
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
    sub_centro_custo_equipe_id = inteiro_ou_none(form_data.get("sub_centro_custo_equipe_id"))
    sub_centro_custo_veiculo_id = inteiro_ou_none(form_data.get("sub_centro_custo_veiculo_id"))
    centro_custo_busca = texto(form_data.get("centro_custo_busca"))
    sub_centro_custo_equipe_busca = texto(form_data.get("sub_centro_custo_equipe_busca"))
    sub_centro_custo_veiculo_busca = texto(form_data.get("sub_centro_custo_veiculo_busca"))

    if not justificativa:
        return False, "Justificativa e obrigatoria.", requisicao

    if centro_custo_busca and not centro_custo_id:
        return False, "Selecione um centro de custo da lista.", requisicao

    if sub_centro_custo_equipe_busca and not sub_centro_custo_equipe_id:
        return False, "Selecione um sub centro de custo - Equipe da lista.", requisicao

    if sub_centro_custo_veiculo_busca and not sub_centro_custo_veiculo_id:
        return False, "Selecione um sub centro de custo - Placa do veiculo da lista.", requisicao

    if centro_custo_id and not buscar_centro_custo_ativo_por_classe(centro_custo_id, CLASSE_CENTRO_CUSTO):
        return False, "Centro de custo nao encontrado, inativo ou fora da classe permitida.", requisicao

    if (
        sub_centro_custo_equipe_id
        and not buscar_centro_custo_ativo_por_classe(
            sub_centro_custo_equipe_id,
            CLASSE_CENTRO_CUSTO_EQUIPES,
        )
    ):
        return False, "Sub centro de custo - Equipe nao encontrado, inativo ou fora da classe permitida.", requisicao

    if (
        sub_centro_custo_veiculo_id
        and not buscar_centro_custo_ativo_por_classe(
            sub_centro_custo_veiculo_id,
            CLASSE_CENTRO_EPG_VEICULOS,
        )
    ):
        return False, "Sub centro de custo - Placa do veiculo nao encontrado, inativo ou fora da classe permitida.", requisicao

    if requisicao and requisicao.status != STATUS_REQUISICAO_RASCUNHO:
        return False, "Somente requisicoes em rascunho podem ser editadas.", requisicao

    if requisicao and requisicao_tem_cotacao_vinculada(requisicao):
        return False, "Somente requisicoes sem cotacao vinculada podem ser editadas.", requisicao

    if requisicao is None:
        requisicao = SuprimentosRequisicaoCompra(
            numero=gerar_numero_requisicao(),
            solicitante_usuario_id=usuario.id,
            status=STATUS_REQUISICAO_RASCUNHO,
        )
        db.session.add(requisicao)

    requisicao.centro_custo_id = centro_custo_id
    requisicao.sub_centro_custo_equipe_id = sub_centro_custo_equipe_id
    requisicao.sub_centro_custo_veiculo_id = sub_centro_custo_veiculo_id
    requisicao.justificativa = justificativa
    requisicao.observacoes = observacoes
    db.session.commit()

    return True, "Requisicao salva com sucesso.", requisicao


def nome_subcentro_equipe_requisicao(requisicao):
    if not requisicao:
        return "-"

    if getattr(requisicao, "sub_centro_custo_equipe", None):
        return requisicao.sub_centro_custo_equipe.nome

    if getattr(requisicao, "equipe", None):
        return requisicao.equipe.nome

    return "-"


def nome_subcentro_veiculo_requisicao(requisicao):
    if not requisicao:
        return "-"

    if getattr(requisicao, "sub_centro_custo_veiculo", None):
        return requisicao.sub_centro_custo_veiculo.nome

    if getattr(requisicao, "veiculo_placa", None):
        return requisicao.veiculo_placa

    return "-"


def requisicao_tem_cotacao_vinculada(requisicao):
    if not requisicao or not requisicao.id:
        return False

    return (
        db.session.query(SuprimentosCotacao.id)
        .filter(
            SuprimentosCotacao.requisicao_id == requisicao.id,
            SuprimentosCotacao.status != STATUS_COTACAO_CANCELADA,
        )
        .first()
        is not None
    )


def requisicao_compra_pode_editar(requisicao):
    return bool(requisicao and requisicao.pode_editar and not requisicao_tem_cotacao_vinculada(requisicao))


def adicionar_item_requisicao(form_data, requisicao):
    if not requisicao_compra_pode_editar(requisicao):
        return False, "Somente requisicoes sem cotacao vinculada podem receber itens.", None

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


def editar_item_requisicao(form_data, requisicao, requisicao_item):
    if not requisicao_compra_pode_editar(requisicao):
        return False, "Somente requisicoes sem cotacao vinculada podem ter itens editados."

    if not requisicao_item or requisicao_item.requisicao_id != requisicao.id:
        return False, "Item nao pertence a requisicao."

    item_id = inteiro_ou_none(form_data.get("item_id"))
    quantidade = decimal_ou_none(form_data.get("quantidade"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    if not item_id:
        return False, "Item e obrigatorio."

    item = buscar_por_id(SuprimentosItem, item_id)

    if not item or not item.ativo:
        return False, "Item nao encontrado ou inativo."

    if quantidade is None or quantidade <= 0:
        return False, "Quantidade deve ser maior que zero."

    existente = SuprimentosRequisicaoCompraItem.query.filter(
        SuprimentosRequisicaoCompraItem.requisicao_id == requisicao.id,
        SuprimentosRequisicaoCompraItem.item_id == item.id,
        SuprimentosRequisicaoCompraItem.id != requisicao_item.id,
    ).first()

    if existente:
        return False, "Este item ja foi adicionado a requisicao."

    requisicao_item.item_id = item.id
    requisicao_item.item_codigo_snapshot = item.codigo_interno
    requisicao_item.item_descricao_snapshot = item.descricao
    requisicao_item.unidade_medida_snapshot = item.unidade_medida.sigla
    requisicao_item.quantidade = quantidade
    requisicao_item.observacoes = observacoes
    db.session.commit()

    return True, "Item atualizado com sucesso."


def remover_item_requisicao(requisicao, requisicao_item):
    if not requisicao_compra_pode_editar(requisicao):
        return False, "Somente requisicoes sem cotacao vinculada podem ter itens removidos."

    if requisicao_item.requisicao_id != requisicao.id:
        return False, "Item nao pertence a requisicao."

    db.session.delete(requisicao_item)
    db.session.commit()
    return True, "Item removido com sucesso."


def enviar_requisicao_compra(requisicao):
    if not requisicao_compra_pode_editar(requisicao):
        return False, "Somente requisicoes sem cotacao vinculada podem ser enviadas para analise."

    if not requisicao.itens:
        return False, "Adicione ao menos um item antes de enviar."

    requisicao.status = STATUS_REQUISICAO_ENVIADA
    requisicao.enviada_em = agora_brasil()
    db.session.commit()
    return True, "Requisicao enviada para analise."


def cancelar_requisicao_compra(requisicao, motivo=None):
    if requisicao.status == STATUS_REQUISICAO_CANCELADA:
        return False, "Requisicao ja esta cancelada."

    requisicao.status = STATUS_REQUISICAO_CANCELADA
    requisicao.cancelada_em = agora_brasil()
    requisicao.motivo_cancelamento = texto_maiusculo(motivo) or None
    db.session.commit()
    return True, "Requisicao cancelada com sucesso."


def sincronizar_status_requisicao_por_cotacao(cotacao):
    if not cotacao or not cotacao.requisicao:
        return

    if cotacao.status in STATUS_COTACAO_REQUISICAO_ENVIADA:
        cotacao.requisicao.status = STATUS_REQUISICAO_ENVIADA
        cotacao.requisicao.cancelada_em = None
        cotacao.requisicao.motivo_cancelamento = None
        return

    if cotacao.status in STATUS_COTACAO_REQUISICAO_APROVADA:
        cotacao.requisicao.status = STATUS_REQUISICAO_APROVADA
        cotacao.requisicao.cancelada_em = None
        cotacao.requisicao.motivo_cancelamento = None
        return

    if cotacao.status in STATUS_COTACAO_REQUISICAO_CANCELADA:
        cotacao.requisicao.status = STATUS_REQUISICAO_CANCELADA
        cotacao.requisicao.cancelada_em = agora_brasil()
        cotacao.requisicao.motivo_cancelamento = f"COTACAO {cotacao.status.upper()}"


def gerar_numero_cotacao():
    ano = agora_brasil().year
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
    ano = agora_brasil().year
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
    ano = agora_brasil().year
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


def buscar_ordens_compra(
    numero=None,
    status=None,
    fornecedor_id=None,
    status_financeiro=None,
    centro_custo_id=None,
    sub_centro_custo_equipe_id=None,
    sub_centro_custo_veiculo_id=None,
):
    query = (
        SuprimentosOrdemCompra.query
        .join(SuprimentosRequisicaoCompra, SuprimentosOrdemCompra.requisicao_id == SuprimentosRequisicaoCompra.id)
        .outerjoin(Equipe, SuprimentosRequisicaoCompra.equipe_id == Equipe.id)
        .options(
            joinedload(SuprimentosOrdemCompra.cotacao),
            joinedload(SuprimentosOrdemCompra.requisicao).joinedload(SuprimentosRequisicaoCompra.centro_custo),
            joinedload(SuprimentosOrdemCompra.requisicao).joinedload(SuprimentosRequisicaoCompra.equipe),
            joinedload(SuprimentosOrdemCompra.requisicao).joinedload(SuprimentosRequisicaoCompra.sub_centro_custo_equipe),
            joinedload(SuprimentosOrdemCompra.requisicao).joinedload(SuprimentosRequisicaoCompra.sub_centro_custo_veiculo),
        )
    )
    numero = texto(numero).upper()
    fornecedor_id = inteiro_ou_none(fornecedor_id)
    centro_custo_id = inteiro_ou_none(centro_custo_id)
    sub_centro_custo_equipe_id = inteiro_ou_none(sub_centro_custo_equipe_id)
    sub_centro_custo_veiculo_id = inteiro_ou_none(sub_centro_custo_veiculo_id)

    if numero:
        query = query.filter(SuprimentosOrdemCompra.numero.ilike(f"%{numero}%"))

    if status:
        query = query.filter(SuprimentosOrdemCompra.status == status)

    if fornecedor_id:
        query = query.filter(SuprimentosOrdemCompra.fornecedor_id == fornecedor_id)

    if status_financeiro:
        query = query.filter(SuprimentosOrdemCompra.status_financeiro == status_financeiro)

    if centro_custo_id:
        query = query.filter(SuprimentosRequisicaoCompra.centro_custo_id == centro_custo_id)

    if sub_centro_custo_equipe_id:
        query = query.filter(SuprimentosRequisicaoCompra.sub_centro_custo_equipe_id == sub_centro_custo_equipe_id)

    if sub_centro_custo_veiculo_id:
        query = query.filter(SuprimentosRequisicaoCompra.sub_centro_custo_veiculo_id == sub_centro_custo_veiculo_id)

    return query.order_by(SuprimentosOrdemCompra.criado_em.desc()).all()


def buscar_ordens_aguardando_financeiro():
    return (
        SuprimentosOrdemCompra.query
        .filter(
            SuprimentosOrdemCompra.status != STATUS_ORDEM_COMPRA_CANCELADA,
            SuprimentosOrdemCompra.status_financeiro.in_(
                [STATUS_FINANCEIRO_PENDENTE, STATUS_FINANCEIRO_PREPARADO]
            ),
        )
        .order_by(SuprimentosOrdemCompra.previsao_vencimento.asc(), SuprimentosOrdemCompra.gerada_em.desc())
        .all()
    )


def buscar_ordens_compra_cotacao(cotacao):
    return (
        SuprimentosOrdemCompra.query
        .filter_by(cotacao_id=cotacao.id)
        .order_by(SuprimentosOrdemCompra.numero.asc())
        .all()
    )


def buscar_cotacoes_aprovadas_sem_ordem_compra(numero=None):
    numero = texto(numero).upper()
    query = SuprimentosCotacao.query.filter(
        SuprimentosCotacao.status == STATUS_COTACAO_APROVADA,
    )

    if numero:
        query = query.filter(SuprimentosCotacao.numero.ilike(f"%{numero}%"))

    cotacoes = query.order_by(SuprimentosCotacao.aprovada_em.desc(), SuprimentosCotacao.criado_em.desc()).all()
    return [
        cotacao
        for cotacao in cotacoes
        if not any(
            ordem.status != STATUS_ORDEM_COMPRA_CANCELADA
            for ordem in buscar_ordens_compra_cotacao(cotacao)
        )
    ]


def calcular_parcelas_previstas(valor_total, quantidade_parcelas):
    quantidade_parcelas = int(quantidade_parcelas or 1)
    valor_total = Decimal(valor_total or 0).quantize(Decimal("0.01"))

    if quantidade_parcelas <= 1:
        return [valor_total]

    valor_base = (valor_total / Decimal(quantidade_parcelas)).quantize(Decimal("0.01"))
    parcelas = [valor_base for _ in range(quantidade_parcelas)]
    diferenca = valor_total - sum(parcelas, Decimal("0.00"))
    parcelas[-1] = (parcelas[-1] + diferenca).quantize(Decimal("0.01"))
    return parcelas


def criar_parcelas_financeiras_ordem(ordem, previsao_vencimento, quantidade_parcelas, observacoes=None):
    for parcela in list(ordem.parcelas_financeiras):
        db.session.delete(parcela)
    db.session.flush()

    valores = calcular_parcelas_previstas(ordem.valor_total, quantidade_parcelas)
    for indice, valor in enumerate(valores, start=1):
        vencimento = previsao_vencimento + timedelta(days=30 * (indice - 1))
        db.session.add(
            SuprimentosOrdemCompraParcela(
                ordem_compra_id=ordem.id,
                numero_parcela=indice,
                valor_previsto=valor,
                data_vencimento=vencimento,
                status="Prevista",
                observacoes=observacoes,
            )
        )


def preparar_financeiro_ordem_compra(ordem, form_data):
    if ordem.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return False, "Ordem de compra cancelada nao pode ser preparada para financeiro."

    previsao_vencimento = data_ou_none((form_data or {}).get("previsao_vencimento"))
    quantidade_parcelas = inteiro_ou_none((form_data or {}).get("quantidade_parcelas")) or 1
    observacoes = texto_maiusculo((form_data or {}).get("observacoes_financeiras")) or None

    if not previsao_vencimento:
        return False, "Previsao de vencimento e obrigatoria."

    if quantidade_parcelas < 1:
        return False, "Quantidade de parcelas deve ser maior ou igual a 1."

    ordem.previsao_vencimento = previsao_vencimento
    ordem.quantidade_parcelas = quantidade_parcelas
    ordem.observacoes_financeiras = observacoes
    ordem.status_financeiro = STATUS_FINANCEIRO_PREPARADO
    ordem.preparado_financeiro_em = agora_brasil()
    criar_parcelas_financeiras_ordem(ordem, previsao_vencimento, quantidade_parcelas, observacoes)
    db.session.commit()
    return True, "Dados financeiros preparados com sucesso."


def provisionar_financeiro_ordem_compra(ordem):
    if ordem.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return False, "Ordem de compra cancelada nao pode ser provisionada."

    if not ordem.parcelas_financeiras:
        return False, "Prepare as parcelas financeiras antes de provisionar."

    ordem.status_financeiro = STATUS_FINANCEIRO_PROVISIONADO
    ordem.provisionado_financeiro_em = agora_brasil()
    db.session.commit()
    return True, "Ordem de compra provisionada para o futuro Financeiro."


def buscar_saldos_estoque(descricao=None, categoria_id=None, somente_abaixo_minimo=False):
    descricao = texto(descricao).upper()
    categoria_id = inteiro_ou_none(categoria_id)
    somente_abaixo_minimo = bool(somente_abaixo_minimo)

    query = (
        SuprimentosItem.query
        .options(
            joinedload(SuprimentosItem.categoria),
            joinedload(SuprimentosItem.unidade_medida),
            joinedload(SuprimentosItem.movimentacoes_estoque),
        )
        .filter(
            SuprimentosItem.item_estocavel.is_(True),
            SuprimentosItem.ativo.is_(True),
        )
    )

    if descricao:
        query = query.filter(
            SuprimentosItem.descricao.ilike(f"%{descricao}%")
            | SuprimentosItem.codigo_interno.ilike(f"%{descricao}%")
        )

    if categoria_id:
        query = query.filter(SuprimentosItem.categoria_id == categoria_id)

    itens = query.order_by(SuprimentosItem.descricao.asc()).all()

    if somente_abaixo_minimo:
        itens = [
            item
            for item in itens
            if item.estoque_minimo is not None and item.saldo_estoque < item.estoque_minimo
        ]

    return itens


def buscar_movimentacoes_estoque(
    item_id=None,
    fornecedor_id=None,
    documento=None,
    data_inicio=None,
    data_fim=None,
):
    item_id = inteiro_ou_none(item_id)
    fornecedor_id = inteiro_ou_none(fornecedor_id)
    documento = texto_maiusculo(documento)
    data_inicio = data_ou_none(data_inicio)
    data_fim = data_ou_none(data_fim)

    query = (
        SuprimentosMovimentacaoEstoque.query
        .options(
            joinedload(SuprimentosMovimentacaoEstoque.item).joinedload(SuprimentosItem.unidade_medida),
            joinedload(SuprimentosMovimentacaoEstoque.ordem_compra),
            joinedload(SuprimentosMovimentacaoEstoque.fornecedor),
            joinedload(SuprimentosMovimentacaoEstoque.responsavel),
            joinedload(SuprimentosMovimentacaoEstoque.centro_custo),
        )
    )

    if item_id:
        query = query.filter(SuprimentosMovimentacaoEstoque.item_id == item_id)

    if fornecedor_id:
        query = query.filter(SuprimentosMovimentacaoEstoque.fornecedor_id == fornecedor_id)

    if documento:
        query = query.filter(SuprimentosMovimentacaoEstoque.documento_numero.ilike(f"%{documento}%"))

    if data_inicio:
        query = query.filter(SuprimentosMovimentacaoEstoque.movimentado_em >= datetime.combine(data_inicio, datetime.min.time()))

    if data_fim:
        query = query.filter(
            SuprimentosMovimentacaoEstoque.movimentado_em
            < datetime.combine(data_fim + timedelta(days=1), datetime.min.time())
        )

    return query.order_by(SuprimentosMovimentacaoEstoque.movimentado_em.desc()).all()


def _periodo_relatorios(data_inicio=None, data_fim=None):
    data_inicio = data_ou_none(data_inicio)
    data_fim = data_ou_none(data_fim)
    return data_inicio, data_fim


def _dentro_periodo(data_referencia, data_inicio, data_fim):
    if not data_referencia:
        return False

    data = data_referencia.date() if hasattr(data_referencia, "date") else data_referencia

    if data_inicio and data < data_inicio:
        return False

    if data_fim and data > data_fim:
        return False

    return True


def _ordem_passa_filtros(ordem, data_inicio, data_fim, fornecedor_id, centro_custo_id, categoria_id):
    if not _dentro_periodo(ordem.gerada_em or ordem.criado_em, data_inicio, data_fim):
        return False

    if ordem.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return False

    if fornecedor_id and ordem.fornecedor_id != fornecedor_id:
        return False

    if centro_custo_id and (
        not ordem.requisicao or ordem.requisicao.centro_custo_id != centro_custo_id
    ):
        return False

    if categoria_id:
        return any(
            ordem_item.item and ordem_item.item.categoria_id == categoria_id
            for ordem_item in ordem.itens
        )

    return True


def _valor_ordem_filtrado(ordem, categoria_id=None):
    total = Decimal("0.00")

    for ordem_item in ordem.itens:
        if categoria_id and (not ordem_item.item or ordem_item.item.categoria_id != categoria_id):
            continue
        total += Decimal(ordem_item.valor_total)

    return total


def indicadores_suprimentos(data_inicio=None, data_fim=None, fornecedor_id=None, centro_custo_id=None, categoria_id=None):
    data_inicio, data_fim = _periodo_relatorios(data_inicio, data_fim)
    fornecedor_id = inteiro_ou_none(fornecedor_id)
    centro_custo_id = inteiro_ou_none(centro_custo_id)
    categoria_id = inteiro_ou_none(categoria_id)

    ordens = (
        SuprimentosOrdemCompra.query
        .options(
            joinedload(SuprimentosOrdemCompra.itens).joinedload(SuprimentosOrdemCompraItem.item),
            joinedload(SuprimentosOrdemCompra.requisicao).joinedload(SuprimentosRequisicaoCompra.centro_custo),
            joinedload(SuprimentosOrdemCompra.fornecedor),
        )
        .all()
    )
    ordens_filtradas = [
        ordem
        for ordem in ordens
        if _ordem_passa_filtros(
            ordem,
            data_inicio,
            data_fim,
            fornecedor_id,
            centro_custo_id,
            categoria_id,
        )
    ]

    total_compras = sum(
        (_valor_ordem_filtrado(ordem, categoria_id) for ordem in ordens_filtradas),
        Decimal("0.00"),
    )

    requisicoes = [
        requisicao
        for requisicao in SuprimentosRequisicaoCompra.query.all()
        if _dentro_periodo(requisicao.criado_em, data_inicio, data_fim)
        and (not centro_custo_id or requisicao.centro_custo_id == centro_custo_id)
    ]
    cotacoes = [
        cotacao
        for cotacao in SuprimentosCotacao.query.all()
        if _dentro_periodo(cotacao.criado_em, data_inicio, data_fim)
    ]
    movimentacoes = [
        movimentacao
        for movimentacao in SuprimentosMovimentacaoEstoque.query.options(
            joinedload(SuprimentosMovimentacaoEstoque.item),
        ).all()
        if _dentro_periodo(movimentacao.movimentado_em, data_inicio, data_fim)
        and (not categoria_id or (movimentacao.item and movimentacao.item.categoria_id == categoria_id))
    ]

    return {
        "filtros": {
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "fornecedor_id": fornecedor_id,
            "centro_custo_id": centro_custo_id,
            "categoria_id": categoria_id,
        },
        "cards": {
            "total_compras": total_compras,
            "ordens": len(ordens_filtradas),
            "requisicoes": len(requisicoes),
            "cotacoes": len(cotacoes),
            "itens_abaixo_minimo": len(
                [
                    item
                    for item in buscar_saldos_estoque(categoria_id=categoria_id)
                    if item.estoque_minimo is not None and item.saldo_estoque < item.estoque_minimo
                ]
            ),
        },
        "compras_por_fornecedor": _agrupar_compras_por_fornecedor(ordens_filtradas, categoria_id),
        "compras_por_centro_custo": _agrupar_compras_por_centro_custo(ordens_filtradas, categoria_id),
        "requisicoes_por_status": _contar_por_status(requisicoes),
        "cotacoes_por_status": _contar_por_status(cotacoes),
        "ordens_por_status": _contar_por_status(ordens_filtradas),
        "movimentacoes_por_tipo": _agrupar_movimentacoes_por_tipo(movimentacoes),
        "itens_abaixo_minimo": [
            item
            for item in buscar_saldos_estoque(categoria_id=categoria_id, somente_abaixo_minimo=True)
        ],
    }


def _contar_por_status(registros):
    totais = {}
    for registro in registros:
        totais[registro.status] = totais.get(registro.status, 0) + 1
    return sorted(totais.items())


def _agrupar_compras_por_fornecedor(ordens, categoria_id=None):
    totais = {}
    for ordem in ordens:
        chave = ordem.fornecedor_razao_social_snapshot or "Fornecedor nao informado"
        totais[chave] = totais.get(chave, Decimal("0.00")) + _valor_ordem_filtrado(ordem, categoria_id)
    return sorted(totais.items(), key=lambda item: item[1], reverse=True)


def _agrupar_compras_por_centro_custo(ordens, categoria_id=None):
    totais = {}
    for ordem in ordens:
        centro = ordem.requisicao.centro_custo if ordem.requisicao else None
        chave = centro.nome if centro else "Sem centro definido"
        totais[chave] = totais.get(chave, Decimal("0.00")) + _valor_ordem_filtrado(ordem, categoria_id)
    return sorted(totais.items(), key=lambda item: item[1], reverse=True)


def _agrupar_movimentacoes_por_tipo(movimentacoes):
    totais = {}
    for movimentacao in movimentacoes:
        chave = f"{movimentacao.tipo} - {movimentacao.origem}"
        totais[chave] = totais.get(chave, Decimal("0.000")) + Decimal(movimentacao.quantidade)
    return sorted(totais.items())


def registrar_movimentacao_manual_estoque(form_data, usuario):
    item_id = inteiro_ou_none(form_data.get("item_id"))
    operacao = texto(form_data.get("operacao"))
    quantidade_informada = decimal_ou_none(form_data.get("quantidade"))
    saldo_inventario = decimal_ou_none(form_data.get("saldo_inventario"))
    documento_tipo = texto_maiusculo(form_data.get("documento_tipo")) or None
    documento_numero = texto_maiusculo(form_data.get("documento_numero")) or None
    centro_custo_id = inteiro_ou_none(form_data.get("centro_custo_id"))
    centro_custo_busca = texto(form_data.get("centro_custo_busca"))
    data_movimentacao = data_ou_none(form_data.get("data_movimentacao"))
    motivo = texto_maiusculo(form_data.get("motivo"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    item = buscar_por_id(SuprimentosItem, item_id) if item_id else None
    centro_custo = buscar_centro_custo_ativo_por_classe(centro_custo_id, CLASSE_CENTRO_CUSTO_EQUIPES) if centro_custo_id else None

    if centro_custo_busca and not centro_custo_id:
        return False, "Selecione um centro de custo da lista.", None

    if centro_custo_id and not centro_custo:
        return False, "Centro de custo deve ser da classe CENTRO DE CUSTO EQUIPES.", None

    if not item or not item.ativo or not item.item_estocavel:
        return False, "Informe um item estocavel ativo.", None

    if operacao not in TIPOS_MOVIMENTACAO_MANUAL_ESTOQUE:
        return False, "Informe o tipo de movimentacao.", None

    if not data_movimentacao:
        return False, "Data da movimentacao e obrigatoria.", None

    if not motivo:
        return False, "Motivo da movimentacao e obrigatorio.", None

    configuracao = TIPOS_MOVIMENTACAO_MANUAL_ESTOQUE[operacao]

    if operacao == "inventario":
        if saldo_inventario is None:
            return False, "Informe o saldo contado no inventario.", None

        if saldo_inventario < 0:
            return False, "Saldo contado no inventario nao pode ser negativo.", None

        saldo_atual = Decimal(item.saldo_estoque).quantize(Decimal("0.001"))
        diferenca = (saldo_inventario - saldo_atual).quantize(Decimal("0.001"))

        if diferenca == 0:
            return False, "Inventario sem diferenca nao gera movimentacao.", None

        quantidade = diferenca
        tipo = TIPO_MOVIMENTACAO_ESTOQUE_ENTRADA if diferenca > 0 else TIPO_MOVIMENTACAO_ESTOQUE_SAIDA
    else:
        if quantidade_informada is None:
            return False, "Quantidade e obrigatoria.", None

        if quantidade_informada <= 0:
            return False, "Quantidade deve ser maior que zero.", None

        tipo = configuracao["tipo"]
        quantidade = quantidade_informada

        if tipo == TIPO_MOVIMENTACAO_ESTOQUE_SAIDA:
            saldo_atual = Decimal(item.saldo_estoque)
            if quantidade_informada > saldo_atual:
                return False, "Saida nao pode ser maior que o saldo atual do item.", None
            quantidade = quantidade_informada * Decimal("-1")

    movimentacao = SuprimentosMovimentacaoEstoque(
        item_id=item.id,
        responsavel_usuario_id=usuario.id if usuario else None,
        centro_custo_id=centro_custo.id if centro_custo else None,
        tipo=tipo,
        origem=configuracao["origem"],
        status=STATUS_MOVIMENTACAO_ESTOQUE_REGISTRADA,
        documento_tipo=documento_tipo,
        documento_numero=documento_numero,
        quantidade=quantidade,
        observacoes=motivo if not observacoes else f"{motivo} | {observacoes}",
        movimentado_em=datetime.combine(data_movimentacao, datetime.min.time()),
    )
    db.session.add(movimentacao)
    db.session.commit()

    return True, "Movimentacao de estoque registrada com sucesso.", movimentacao


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


def buscar_usuarios_ativos():
    return (
        Usuario.query
        .filter(Usuario.ativo.is_(True))
        .order_by(Usuario.nome.asc())
        .all()
    )


def buscar_alcadas_aprovacao(apenas_ativas=False):
    query = (
        SuprimentosAlcadaAprovacao.query
        .options(
            joinedload(SuprimentosAlcadaAprovacao.usuario_aprovador),
            joinedload(SuprimentosAlcadaAprovacao.centro_custo),
            joinedload(SuprimentosAlcadaAprovacao.categoria),
        )
    )

    if apenas_ativas:
        query = query.filter(SuprimentosAlcadaAprovacao.ativo.is_(True))

    return (
        query
        .order_by(
            SuprimentosAlcadaAprovacao.ativo.desc(),
            SuprimentosAlcadaAprovacao.valor_minimo.asc(),
        )
        .all()
    )


def salvar_alcada_aprovacao(form_data, alcada=None):
    usuario_aprovador_id = inteiro_ou_none(form_data.get("usuario_aprovador_id"))
    centro_custo_id = inteiro_ou_none(form_data.get("centro_custo_id"))
    categoria_id = inteiro_ou_none(form_data.get("categoria_id"))
    valor_minimo = decimal_ou_none(form_data.get("valor_minimo"))
    valor_maximo = decimal_ou_none(form_data.get("valor_maximo"))
    telefone_whatsapp = normalizar_telefone_brasil(form_data.get("telefone_whatsapp")) or None
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None
    ativo = form_data.get("ativo") == "on" or form_data.get("ativo") == "true"

    usuario = buscar_por_id(Usuario, usuario_aprovador_id)
    if not usuario or not usuario.ativo:
        return False, "Aprovador e obrigatorio.", alcada

    if centro_custo_id:
        centro = buscar_por_id(CentroCusto, centro_custo_id)
        if not centro or not centro.ativo:
            return False, "Centro de custo nao encontrado ou inativo.", alcada

    if categoria_id:
        categoria = buscar_por_id(SuprimentosCategoriaItem, categoria_id)
        if not categoria or not categoria.ativo:
            return False, "Categoria nao encontrada ou inativa.", alcada

    if valor_minimo is None or valor_minimo < 0:
        return False, "Valor minimo deve ser maior ou igual a zero.", alcada

    if valor_maximo is not None and valor_maximo < valor_minimo:
        return False, "Valor maximo deve ser maior ou igual ao valor minimo.", alcada

    if telefone_whatsapp and not telefone_brasil_valido(telefone_whatsapp):
        return False, "Telefone WhatsApp da alcada invalido.", alcada

    if alcada is None:
        alcada = SuprimentosAlcadaAprovacao()
        db.session.add(alcada)

    alcada.usuario_aprovador_id = usuario.id
    alcada.centro_custo_id = centro_custo_id
    alcada.categoria_id = categoria_id
    alcada.valor_minimo = valor_minimo
    alcada.valor_maximo = valor_maximo
    alcada.telefone_whatsapp = telefone_whatsapp
    alcada.observacoes = observacoes
    alcada.ativo = ativo

    db.session.commit()
    return True, "Alcada de aprovacao salva com sucesso.", alcada


def alterar_status_alcada_aprovacao(alcada):
    alcada.ativo = not alcada.ativo
    db.session.commit()
    return True, "Status da alcada atualizado com sucesso."


def buscar_compradores_suprimentos(apenas_ativos=False):
    query = (
        SuprimentosComprador.query
        .options(
            joinedload(SuprimentosComprador.usuario_comprador),
            joinedload(SuprimentosComprador.centro_custo),
        )
    )

    if apenas_ativos:
        query = query.filter(SuprimentosComprador.ativo.is_(True))

    return (
        query
        .order_by(
            SuprimentosComprador.ativo.desc(),
            SuprimentosComprador.nome.asc(),
        )
        .all()
    )


def salvar_comprador_suprimentos(form_data, comprador=None):
    usuario_comprador_id = inteiro_ou_none(form_data.get("usuario_comprador_id"))
    centro_custo_id = inteiro_ou_none(form_data.get("centro_custo_id"))
    nome = texto_maiusculo(form_data.get("nome"))
    telefone_whatsapp = normalizar_telefone_brasil(form_data.get("telefone_whatsapp"))
    email = texto(form_data.get("email")).lower() or None
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None
    ativo = form_data.get("ativo") == "on" or form_data.get("ativo") == "true"

    if usuario_comprador_id:
        usuario = buscar_por_id(Usuario, usuario_comprador_id)
        if not usuario or not usuario.ativo:
            return False, "Usuario comprador nao encontrado ou inativo.", comprador
        if not nome:
            nome = texto_maiusculo(usuario.nome)

    if not nome:
        return False, "Nome do comprador e obrigatorio.", comprador

    if not telefone_whatsapp:
        return False, "Telefone WhatsApp do comprador e obrigatorio.", comprador

    if not telefone_brasil_valido(telefone_whatsapp):
        return False, "Telefone WhatsApp do comprador invalido.", comprador

    if email and not email_valido(email):
        return False, "E-mail do comprador invalido.", comprador

    if centro_custo_id:
        centro = buscar_por_id(CentroCusto, centro_custo_id)
        if not centro or not centro.ativo:
            return False, "Centro de custo nao encontrado ou inativo.", comprador

    if comprador is None:
        comprador = SuprimentosComprador()
        db.session.add(comprador)

    comprador.usuario_comprador_id = usuario_comprador_id
    comprador.centro_custo_id = centro_custo_id
    comprador.nome = nome
    comprador.telefone_whatsapp = telefone_whatsapp
    comprador.email = email
    comprador.observacoes = observacoes
    comprador.ativo = ativo

    db.session.commit()
    return True, "Comprador salvo com sucesso.", comprador


def alterar_status_comprador_suprimentos(comprador):
    comprador.ativo = not comprador.ativo
    db.session.commit()
    return True, "Status do comprador atualizado com sucesso."


def encontrar_comprador_para_requisicao(requisicao):
    if not requisicao:
        return None

    compradores = buscar_compradores_suprimentos(apenas_ativos=True)
    comprador_centro = next(
        (
            comprador
            for comprador in compradores
            if comprador.centro_custo_id and comprador.centro_custo_id == requisicao.centro_custo_id
        ),
        None,
    )
    if comprador_centro:
        return comprador_centro

    return next((comprador for comprador in compradores if not comprador.centro_custo_id), None)


def link_requisicao_producao(requisicao):
    base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    return f"{base_url}/suprimentos/requisicoes/{requisicao.id}"


def gerar_mensagem_whatsapp_requisicao_compra(requisicao, comprador=None):
    linhas = [
        "*Rental Retros - Nova Requisicao Aberta*",
        "",
        f"Requisicao: {requisicao.numero}",
        f"Solicitante: {requisicao.solicitante.nome if requisicao.solicitante else '-'}",
        f"Centro de custo: {requisicao.centro_custo.nome if requisicao.centro_custo else '-'}",
    ]

    if comprador:
        linhas.append(f"Comprador: {comprador.nome}")

    linhas.extend(
        [
            "",
            "Acesse o link para analisar no sistema:",
            link_requisicao_producao(requisicao),
        ]
    )
    return "\n".join(linhas)


def gerar_link_whatsapp_requisicao_compra(requisicao):
    if not requisicao:
        return False, "Requisicao nao encontrada.", None

    comprador = encontrar_comprador_para_requisicao(requisicao)
    if not comprador:
        return False, "Cadastre um comprador ativo para enviar a requisicao por WhatsApp.", None

    if not telefone_brasil_valido(comprador.telefone_whatsapp):
        return False, "Telefone WhatsApp do comprador invalido.", None

    mensagem = gerar_mensagem_whatsapp_requisicao_compra(requisicao, comprador)
    return True, "Link do WhatsApp gerado com sucesso.", f"https://wa.me/{comprador.telefone_whatsapp}?text={quote(mensagem)}"


def email_comprador_requisicao(comprador):
    if not comprador:
        return None

    if comprador.email:
        return comprador.email

    if comprador.usuario_comprador and comprador.usuario_comprador.email:
        return comprador.usuario_comprador.email

    return None


def gerar_assunto_email_requisicao_compra(requisicao):
    return f"Nova Requisicao de Compra {requisicao.numero}"


def gerar_corpo_email_requisicao_compra(requisicao, comprador=None):
    linhas = [
        "Rental Retros - Nova Requisicao Aberta",
        "",
        f"Requisicao: {requisicao.numero}",
        f"Solicitante: {requisicao.solicitante.nome if requisicao.solicitante else '-'}",
        f"Centro de custo: {requisicao.centro_custo.nome if requisicao.centro_custo else '-'}",
        "",
        "Acesse o link para analisar no sistema:",
        link_requisicao_producao(requisicao),
        "",
        "Rental Retros",
    ]
    return "\n".join(linhas)


def gerar_link_mailto_requisicao_compra(requisicao):
    comprador = encontrar_comprador_para_requisicao(requisicao)
    destinatario = email_comprador_requisicao(comprador)

    if not destinatario:
        return False, "Informe o e-mail no cadastro do comprador.", None

    if not email_valido(destinatario):
        return False, "E-mail do comprador invalido.", None

    assunto = gerar_assunto_email_requisicao_compra(requisicao)
    corpo = gerar_corpo_email_requisicao_compra(requisicao, comprador)
    return True, "Link de e-mail gerado com sucesso.", (
        f"mailto:{destinatario}?subject={quote(assunto)}&body={quote(corpo)}"
    )


def outlook_classic_habilitado():
    configuracao = str(current_app.config.get("OUTLOOK_CLASSIC_EMAIL_ENABLED", "auto")).lower()
    if configuracao in {"1", "true", "sim", "yes"}:
        return True
    if configuracao in {"0", "false", "nao", "no"}:
        return False

    base_url = current_app.config.get("BASE_URL", "")
    return platform.system().lower() == "windows" and (
        base_url.startswith("http://127.0.0.1")
        or base_url.startswith("http://localhost")
    )


def enviar_email_outlook_classic(destinatario, assunto, corpo):
    if not outlook_classic_habilitado():
        return False, "Outlook Classic nao habilitado neste ambiente."

    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return False, "Biblioteca local do Outlook nao instalada."

    try:
        pythoncom.CoInitialize()
        outlook = win32com.client.Dispatch("Outlook.Application")
        email = outlook.CreateItem(0)
        email.To = destinatario
        email.Subject = assunto
        email.Body = corpo
        email.Send()
        return True, None
    except Exception:
        return False, "Nao foi possivel criar/enviar o e-mail pelo Outlook Classic."
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def enviar_email_requisicao_compra(requisicao):
    comprador = encontrar_comprador_para_requisicao(requisicao)
    destinatario = email_comprador_requisicao(comprador)

    if not comprador:
        return False, "Cadastre um comprador ativo para enviar a requisicao por e-mail.", None

    if not destinatario:
        return False, "Informe o e-mail no cadastro do comprador.", None

    if not email_valido(destinatario):
        return False, "E-mail do comprador invalido.", None

    assunto = gerar_assunto_email_requisicao_compra(requisicao)
    corpo = gerar_corpo_email_requisicao_compra(requisicao, comprador)

    if smtp_configurado():
        sucesso, erro = enviar_email(destinatario, assunto, corpo)
        if sucesso:
            return True, "E-mail enviado automaticamente ao comprador.", None
        return False, erro or "Falha ao enviar e-mail.", None

    sucesso_outlook, erro_outlook = enviar_email_outlook_classic(destinatario, assunto, corpo)
    if sucesso_outlook:
        return True, "E-mail criado e enviado automaticamente pelo Outlook Classic.", None

    sucesso, mensagem, link_mailto = gerar_link_mailto_requisicao_compra(requisicao)
    if not sucesso:
        return False, mensagem, None

    return True, f"{erro_outlook} Use a abertura manual do e-mail.", link_mailto


def fornecedores_disponiveis_para_cotacao(cotacao):
    fornecedores = {}
    if not cotacao or not cotacao.requisicao:
        return []

    for requisicao_item in cotacao.requisicao.itens:
        for fornecedor in fornecedores_disponiveis_para_requisicao_item(requisicao_item):
            fornecedores[fornecedor.id] = fornecedor

    return sorted(fornecedores.values(), key=lambda fornecedor: fornecedor.razao_social)


def fornecedor_disponivel_para_cotacao(cotacao, fornecedor_id):
    fornecedor_id = inteiro_ou_none(fornecedor_id)
    if not fornecedor_id:
        return None

    return next(
        (
            fornecedor
            for fornecedor in fornecedores_disponiveis_para_cotacao(cotacao)
            if fornecedor.id == fornecedor_id
        ),
        None,
    )


def itens_cotacao_para_fornecedor(cotacao, fornecedor):
    if not cotacao or not fornecedor or not cotacao.requisicao:
        return []

    itens = []
    for requisicao_item in cotacao.requisicao.itens:
        vinculo = SuprimentosFornecedorItem.query.filter_by(
            fornecedor_id=fornecedor.id,
            item_id=requisicao_item.item_id,
            ativo=True,
        ).first()
        if vinculo:
            itens.append(requisicao_item)

    return itens


def gerar_mensagem_solicitacao_cotacao_fornecedor(cotacao, fornecedor):
    itens = itens_cotacao_para_fornecedor(cotacao, fornecedor)
    requisicao = cotacao.requisicao
    linhas = [
        "*Rental Retros - Solicitacao de Cotacao*",
        "",
        f"Cotacao: {cotacao.numero}",
        f"Requisicao: {requisicao.numero if requisicao else '-'}",
        f"Fornecedor: {fornecedor.razao_social}",
        f"Centro de custo: {requisicao.centro_custo.nome if requisicao and requisicao.centro_custo else '-'}",
        f"Equipe: {nome_subcentro_equipe_requisicao(requisicao)}",
        f"Placa do veiculo: {nome_subcentro_veiculo_requisicao(requisicao)}",
        f"Justificativa: {requisicao.justificativa if requisicao else '-'}",
        "",
        "*Itens para cotar:*",
    ]

    if itens:
        for item in itens:
            linhas.append(
                f"- {item.item_descricao_snapshot} | Qtd: "
                f"{formatar_decimal_brasil(item.quantidade)} {item.unidade_medida_snapshot}"
            )
    else:
        linhas.append("- Nenhum item vinculado ao fornecedor")

    linhas.extend(
        [
            "",
            "Por favor, responder informando preco unitario, prazo de entrega e condicao de pagamento.",
            "",
            "Rental Retros",
        ]
    )
    return "\n".join(linhas)


def gerar_link_whatsapp_solicitacao_cotacao_fornecedor(cotacao, fornecedor):
    if not cotacao:
        return False, "Cotacao nao encontrada.", None

    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas podem ser enviadas aos fornecedores.", None

    fornecedores_ids = {item.id for item in fornecedores_disponiveis_para_cotacao(cotacao)}
    if not fornecedor or fornecedor.id not in fornecedores_ids:
        return False, "Fornecedor nao disponivel para os itens desta cotacao.", None

    telefone = normalizar_telefone_brasil(fornecedor.telefone)
    if not telefone:
        return False, "Fornecedor sem telefone cadastrado.", None

    if not telefone_brasil_valido(telefone):
        return False, "Telefone do fornecedor invalido.", None

    mensagem = gerar_mensagem_solicitacao_cotacao_fornecedor(cotacao, fornecedor)
    return True, "Link do WhatsApp gerado com sucesso.", f"https://wa.me/{telefone}?text={quote(mensagem)}"


def gerar_assunto_email_solicitacao_cotacao_fornecedor(cotacao):
    return f"Solicitacao de Cotacao {cotacao.numero}"


def gerar_corpo_email_solicitacao_cotacao_fornecedor(cotacao, fornecedor):
    return gerar_mensagem_solicitacao_cotacao_fornecedor(cotacao, fornecedor).replace("*", "")


def gerar_link_mailto_solicitacao_cotacao_fornecedor(cotacao, fornecedor):
    if not fornecedor.email:
        return False, "Fornecedor sem e-mail cadastrado.", None

    if not email_valido(fornecedor.email):
        return False, "E-mail do fornecedor invalido.", None

    assunto = gerar_assunto_email_solicitacao_cotacao_fornecedor(cotacao)
    corpo = gerar_corpo_email_solicitacao_cotacao_fornecedor(cotacao, fornecedor)
    return True, "Link de e-mail gerado com sucesso.", (
        f"mailto:{fornecedor.email}?subject={quote(assunto)}&body={quote(corpo)}"
    )


def enviar_email_solicitacao_cotacao_fornecedor(cotacao, fornecedor):
    if not cotacao:
        return False, "Cotacao nao encontrada.", None

    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas podem ser enviadas aos fornecedores.", None

    fornecedores_ids = {item.id for item in fornecedores_disponiveis_para_cotacao(cotacao)}
    if not fornecedor or fornecedor.id not in fornecedores_ids:
        return False, "Fornecedor nao disponivel para os itens desta cotacao.", None

    if not fornecedor.email:
        return False, "Fornecedor sem e-mail cadastrado.", None

    if not email_valido(fornecedor.email):
        return False, "E-mail do fornecedor invalido.", None

    assunto = gerar_assunto_email_solicitacao_cotacao_fornecedor(cotacao)
    corpo = gerar_corpo_email_solicitacao_cotacao_fornecedor(cotacao, fornecedor)

    if smtp_configurado():
        sucesso, erro = enviar_email(fornecedor.email, assunto, corpo)
        if sucesso:
            return True, "E-mail enviado automaticamente ao fornecedor.", None
        return False, erro or "Falha ao enviar e-mail.", None

    sucesso_outlook, erro_outlook = enviar_email_outlook_classic(fornecedor.email, assunto, corpo)
    if sucesso_outlook:
        return True, "E-mail criado e enviado automaticamente pelo Outlook Classic.", None

    sucesso, mensagem, link_mailto = gerar_link_mailto_solicitacao_cotacao_fornecedor(cotacao, fornecedor)
    if not sucesso:
        return False, mensagem, None

    return True, f"{erro_outlook} Use a abertura manual do e-mail.", link_mailto


def gerar_mensagem_ordem_compra_fornecedor(ordem):
    fornecedor = ordem.fornecedor if ordem else None
    requisicao = ordem.requisicao if ordem else None
    cotacao = ordem.cotacao if ordem else None
    linhas = [
        "*Rental Retros - Ordem de Compra*",
        "",
        f"Ordem de compra: {ordem.numero}",
        f"Cotacao: {cotacao.numero if cotacao else '-'}",
        f"Requisicao: {requisicao.numero if requisicao else '-'}",
        f"Fornecedor: {fornecedor.razao_social if fornecedor else ordem.fornecedor_razao_social_snapshot}",
        f"CNPJ/CPF: {ordem.fornecedor_cnpj_cpf_snapshot or '-'}",
        f"Condicao de pagamento: {ordem.condicao_pagamento_snapshot or '-'}",
        f"Previsao de vencimento: {ordem.previsao_vencimento.strftime('%d/%m/%Y') if ordem.previsao_vencimento else '-'}",
        f"Total da OC: {formatar_moeda_brl(ordem.valor_total)}",
        "",
        "*Itens:*",
    ]

    for item in ordem.itens:
        linhas.append(
            f"- {item.item_descricao_snapshot} | Qtd: "
            f"{formatar_decimal_brasil(item.quantidade)} {item.unidade_medida_snapshot} | "
            f"Unit.: {formatar_moeda_brl(item.preco_unitario)} | "
            f"Total: {formatar_moeda_brl(item.valor_total)}"
        )
        if item.prazo_entrega_dias is not None:
            linhas.append(f"  Prazo: {item.prazo_entrega_dias} dias")
        if item.observacoes:
            linhas.append(f"  Observacoes: {item.observacoes}")

    if ordem.observacoes:
        linhas.extend(["", f"Observacoes da OC: {ordem.observacoes}"])

    linhas.extend(
        [
            "",
            "Por favor, confirme o recebimento desta Ordem de Compra.",
            "",
            "Rental Retros",
        ]
    )
    return "\n".join(linhas)


def gerar_link_whatsapp_ordem_compra_fornecedor(ordem):
    if not ordem:
        return False, "Ordem de compra nao encontrada.", None

    if ordem.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return False, "Ordem de compra cancelada nao pode ser enviada.", None

    fornecedor = ordem.fornecedor
    if not fornecedor:
        return False, "Fornecedor da ordem de compra nao encontrado.", None

    telefone = normalizar_telefone_brasil(fornecedor.telefone)
    if not telefone:
        return False, "Fornecedor sem telefone cadastrado.", None

    if not telefone_brasil_valido(telefone):
        return False, "Telefone do fornecedor invalido.", None

    mensagem = gerar_mensagem_ordem_compra_fornecedor(ordem)
    return True, "Link do WhatsApp gerado com sucesso.", f"https://wa.me/{telefone}?text={quote(mensagem)}"


def gerar_assunto_email_ordem_compra_fornecedor(ordem):
    return f"Ordem de Compra {ordem.numero} - Rental Retros"


def gerar_corpo_email_ordem_compra_fornecedor(ordem):
    return gerar_mensagem_ordem_compra_fornecedor(ordem).replace("*", "")


def gerar_link_mailto_ordem_compra_fornecedor(ordem):
    fornecedor = ordem.fornecedor if ordem else None
    if not fornecedor or not fornecedor.email:
        return False, "Fornecedor sem e-mail cadastrado.", None

    if not email_valido(fornecedor.email):
        return False, "E-mail do fornecedor invalido.", None

    assunto = gerar_assunto_email_ordem_compra_fornecedor(ordem)
    corpo = gerar_corpo_email_ordem_compra_fornecedor(ordem)
    return True, "Link de e-mail gerado com sucesso.", (
        f"mailto:{fornecedor.email}?subject={quote(assunto)}&body={quote(corpo)}"
    )


def enviar_email_ordem_compra_fornecedor(ordem):
    if not ordem:
        return False, "Ordem de compra nao encontrada.", None

    if ordem.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return False, "Ordem de compra cancelada nao pode ser enviada.", None

    fornecedor = ordem.fornecedor
    if not fornecedor:
        return False, "Fornecedor da ordem de compra nao encontrado.", None

    if not fornecedor.email:
        return False, "Fornecedor sem e-mail cadastrado.", None

    if not email_valido(fornecedor.email):
        return False, "E-mail do fornecedor invalido.", None

    assunto = gerar_assunto_email_ordem_compra_fornecedor(ordem)
    corpo = gerar_corpo_email_ordem_compra_fornecedor(ordem)

    if smtp_configurado():
        sucesso, erro = enviar_email(fornecedor.email, assunto, corpo)
        if sucesso:
            return True, "E-mail enviado automaticamente ao fornecedor.", None
        return False, erro or "Falha ao enviar e-mail.", None

    sucesso_outlook, erro_outlook = enviar_email_outlook_classic(fornecedor.email, assunto, corpo)
    if sucesso_outlook:
        return True, "E-mail criado e enviado automaticamente pelo Outlook Classic.", None

    sucesso, mensagem, link_mailto = gerar_link_mailto_ordem_compra_fornecedor(ordem)
    if not sucesso:
        return False, mensagem, None

    return True, f"{erro_outlook} Use a abertura manual do e-mail.", link_mailto


def valor_total_propostas_selecionadas(cotacao):
    return sum(
        (Decimal(proposta.valor_total) for proposta in cotacao.propostas if proposta.selecionada),
        Decimal("0.00"),
    )


def categorias_propostas_selecionadas(cotacao):
    return {
        proposta.item.categoria_id
        for proposta in cotacao.propostas
        if proposta.selecionada and proposta.item and proposta.item.categoria_id
    }


def encontrar_alcada_para_cotacao(cotacao):
    total = valor_total_propostas_selecionadas(cotacao)
    centro_custo_id = cotacao.requisicao.centro_custo_id if cotacao.requisicao else None
    categorias = categorias_propostas_selecionadas(cotacao)

    candidatas = []
    for alcada in buscar_alcadas_aprovacao(apenas_ativas=True):
        if total < Decimal(alcada.valor_minimo):
            continue

        if alcada.valor_maximo is not None and total > Decimal(alcada.valor_maximo):
            continue

        if alcada.centro_custo_id and alcada.centro_custo_id != centro_custo_id:
            continue

        if alcada.categoria_id and alcada.categoria_id not in categorias:
            continue

        candidatas.append(alcada)

    return sorted(
        candidatas,
        key=lambda item: (
            0 if item.centro_custo_id else 1,
            0 if item.categoria_id else 1,
            Decimal(item.valor_minimo),
        ),
        reverse=False,
    )[0] if candidatas else None


def usuario_pode_aprovar_cotacao_alcada(cotacao, usuario):
    if not usuario or not getattr(usuario, "is_authenticated", True):
        return False

    if getattr(usuario, "is_admin", False):
        return True

    return cotacao.aprovador_usuario_id == usuario.id


def telefone_whatsapp_cotacao(cotacao):
    if cotacao.alcada_aprovacao and cotacao.alcada_aprovacao.telefone_whatsapp:
        return cotacao.alcada_aprovacao.telefone_whatsapp

    if cotacao.aprovador and cotacao.aprovador.colaborador and cotacao.aprovador.colaborador.telefone:
        return normalizar_telefone_brasil(cotacao.aprovador.colaborador.telefone)

    return None


def link_cotacao_producao(cotacao):
    base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    return f"{base_url}/suprimentos/cotacoes/{cotacao.id}/mapa-comparativo"


def _hash_token_aprovacao_publica(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def link_aprovacao_publica_cotacao(token):
    base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    return f"{base_url}/suprimentos/cotacoes/aprovacao/{token}"


def gerar_token_aprovacao_publica_cotacao(cotacao):
    token = secrets.token_urlsafe(40)
    validade_dias = inteiro_ou_none(
        current_app.config.get("SUPRIMENTOS_APROVACAO_PUBLICA_VALIDADE_DIAS")
    ) or 7

    cotacao.aprovacao_publica_token_hash = _hash_token_aprovacao_publica(token)
    cotacao.aprovacao_publica_expira_em = agora_brasil() + timedelta(days=validade_dias)
    cotacao.aprovacao_publica_usado_em = None
    db.session.commit()

    return token


def buscar_cotacao_por_token_aprovacao_publica(token):
    token = texto(token)
    if not token:
        return None, "Link de aprovacao invalido."

    cotacao = SuprimentosCotacao.query.filter_by(
        aprovacao_publica_token_hash=_hash_token_aprovacao_publica(token)
    ).first()

    if not cotacao:
        return None, "Link de aprovacao invalido."

    if cotacao.aprovacao_publica_usado_em:
        return None, "Este link de aprovacao ja foi utilizado."

    if cotacao.aprovacao_publica_expira_em and cotacao.aprovacao_publica_expira_em < agora_brasil():
        return None, "Este link de aprovacao expirou. Solicite um novo envio pelo WhatsApp."

    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return None, "Esta cotacao nao esta mais aguardando aprovacao."

    if not cotacao.aprovador_usuario_id:
        return None, "Esta cotacao nao possui aprovador definido."

    return cotacao, None


def gerar_mensagem_whatsapp_aprovacao_cotacao(cotacao):
    token = gerar_token_aprovacao_publica_cotacao(cotacao)
    selecionadas = [proposta for proposta in cotacao.propostas if proposta.selecionada]
    fornecedores = sorted(
        {
            proposta.fornecedor_razao_social_snapshot
            for proposta in selecionadas
            if proposta.fornecedor_razao_social_snapshot
        }
    )

    linhas = [
        "*Rental Retros - Aprovacao de Cotacao*",
        "",
        f"Cotacao: {cotacao.numero}",
        f"Requisicao: {cotacao.requisicao.numero if cotacao.requisicao else '-'}",
        f"Valor total: {formatar_moeda_brl(valor_total_propostas_selecionadas(cotacao))}",
        f"Centro de custo: {cotacao.requisicao.centro_custo.nome if cotacao.requisicao and cotacao.requisicao.centro_custo else '-'}",
        f"Equipe: {nome_subcentro_equipe_requisicao(cotacao.requisicao if cotacao else None)}",
        f"Placa do veiculo: {nome_subcentro_veiculo_requisicao(cotacao.requisicao if cotacao else None)}",
        f"Solicitante: {cotacao.requisicao.solicitante.nome if cotacao.requisicao and cotacao.requisicao.solicitante else '-'}",
        f"Aprovador: {cotacao.aprovador.nome if cotacao.aprovador else '-'}",
        "",
        "*Fornecedores selecionados:*",
    ]

    if fornecedores:
        for fornecedor in fornecedores:
            linhas.append(f"- {fornecedor}")
    else:
        linhas.append("- Nenhum fornecedor selecionado")

    linhas.extend(["", "*Itens selecionados:*"])
    if selecionadas:
        for proposta in sorted(selecionadas, key=lambda item: item.item_descricao_snapshot):
            linhas.append(
                f"- {proposta.item_descricao_snapshot} | Qtd: "
                f"{formatar_decimal_brasil(proposta.quantidade_snapshot)} "
                f"{proposta.unidade_medida_snapshot} | Total: {formatar_moeda_brl(proposta.valor_total)}"
            )
    else:
        linhas.append("- Nenhum item selecionado")

    linhas.extend(
        [
            "",
            "Acesse o link direto para aprovar ou reprovar:",
            link_aprovacao_publica_cotacao(token),
        ]
    )

    return "\n".join(linhas)


def gerar_link_whatsapp_aprovacao_cotacao(cotacao):
    if not cotacao:
        return False, "Cotacao nao encontrada.", None

    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return False, "Somente cotacoes em aprovacao podem ser enviadas por WhatsApp.", None

    telefone = telefone_whatsapp_cotacao(cotacao)
    if not telefone:
        return False, "Informe o telefone WhatsApp na alcada do aprovador.", None

    if not telefone_brasil_valido(telefone):
        return False, "Telefone WhatsApp da alcada invalido.", None

    mensagem = gerar_mensagem_whatsapp_aprovacao_cotacao(cotacao)
    return True, "Link do WhatsApp gerado com sucesso.", f"https://wa.me/{telefone}?text={quote(mensagem)}"


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
    sincronizar_status_requisicao_por_cotacao(cotacao)
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
    proposta.selecionada_em = agora_brasil()

    if cotacao.status == STATUS_COTACAO_REPROVADA:
        cotacao.status = STATUS_COTACAO_ABERTA
        cotacao.reprovada_em = None
        cotacao.reprovada_por_usuario_id = None
        cotacao.observacoes_aprovacao = None
        sincronizar_status_requisicao_por_cotacao(cotacao)

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

    alcada = encontrar_alcada_para_cotacao(cotacao)

    if not alcada:
        return False, "Nao existe aprovador configurado para este valor de proposta."

    cotacao.status = STATUS_COTACAO_EM_APROVACAO
    cotacao.enviada_aprovacao_em = agora_brasil()
    cotacao.aprovada_em = None
    cotacao.aprovada_por_usuario_id = None
    cotacao.aprovador_usuario_id = alcada.usuario_aprovador_id
    cotacao.alcada_aprovacao_id = alcada.id
    cotacao.reprovada_em = None
    cotacao.reprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = None
    cotacao.aprovacao_publica_token_hash = None
    cotacao.aprovacao_publica_expira_em = None
    cotacao.aprovacao_publica_usado_em = None
    sincronizar_status_requisicao_por_cotacao(cotacao)
    db.session.commit()

    return True, "Cotacao enviada para aprovacao com sucesso."


def aprovar_cotacao(cotacao, usuario, form_data=None):
    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return False, "Somente cotacoes em aprovacao podem ser aprovadas."

    if not usuario_pode_aprovar_cotacao_alcada(cotacao, usuario):
        return False, "Somente o aprovador definido pela alcada pode aprovar esta cotacao."

    cotacao.status = STATUS_COTACAO_APROVADA
    cotacao.aprovada_em = agora_brasil()
    cotacao.aprovada_por_usuario_id = usuario.id
    cotacao.reprovada_em = None
    cotacao.reprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = texto_maiusculo((form_data or {}).get("observacoes_aprovacao"))
    sincronizar_status_requisicao_por_cotacao(cotacao)
    db.session.commit()

    return True, "Cotacao aprovada com sucesso."


def reprovar_cotacao(cotacao, usuario, form_data=None):
    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return False, "Somente cotacoes em aprovacao podem ser reprovadas."

    if not usuario_pode_aprovar_cotacao_alcada(cotacao, usuario):
        return False, "Somente o aprovador definido pela alcada pode reprovar esta cotacao."

    justificativa = texto_maiusculo((form_data or {}).get("observacoes_aprovacao"))

    if not justificativa:
        return False, "Informe a justificativa da reprovacao."

    cotacao.status = STATUS_COTACAO_REPROVADA
    cotacao.reprovada_em = agora_brasil()
    cotacao.reprovada_por_usuario_id = usuario.id
    cotacao.aprovada_em = None
    cotacao.aprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = justificativa
    sincronizar_status_requisicao_por_cotacao(cotacao)
    db.session.commit()

    return True, "Cotacao reprovada e liberada para ajustes."


def aprovar_cotacao_por_link_publico(cotacao, form_data=None):
    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return False, "Somente cotacoes em aprovacao podem ser aprovadas."

    cotacao.status = STATUS_COTACAO_APROVADA
    cotacao.aprovada_em = agora_brasil()
    cotacao.aprovada_por_usuario_id = cotacao.aprovador_usuario_id
    cotacao.reprovada_em = None
    cotacao.reprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = texto_maiusculo((form_data or {}).get("observacoes_aprovacao"))
    cotacao.aprovacao_publica_usado_em = agora_brasil()
    cotacao.aprovacao_publica_token_hash = None
    cotacao.aprovacao_publica_expira_em = None
    sincronizar_status_requisicao_por_cotacao(cotacao)
    db.session.commit()

    return True, "Cotacao aprovada com sucesso."


def reprovar_cotacao_por_link_publico(cotacao, form_data=None):
    if cotacao.status != STATUS_COTACAO_EM_APROVACAO:
        return False, "Somente cotacoes em aprovacao podem ser reprovadas."

    justificativa = texto_maiusculo((form_data or {}).get("observacoes_aprovacao"))

    if not justificativa:
        return False, "Informe a justificativa da reprovacao."

    cotacao.status = STATUS_COTACAO_REPROVADA
    cotacao.reprovada_em = agora_brasil()
    cotacao.reprovada_por_usuario_id = cotacao.aprovador_usuario_id
    cotacao.aprovada_em = None
    cotacao.aprovada_por_usuario_id = None
    cotacao.observacoes_aprovacao = justificativa
    cotacao.aprovacao_publica_usado_em = agora_brasil()
    cotacao.aprovacao_publica_token_hash = None
    cotacao.aprovacao_publica_expira_em = None
    sincronizar_status_requisicao_por_cotacao(cotacao)
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
    previsao_vencimento = data_ou_none((form_data or {}).get("previsao_vencimento"))
    quantidade_parcelas = inteiro_ou_none((form_data or {}).get("quantidade_parcelas")) or 1
    observacoes_financeiras = texto_maiusculo((form_data or {}).get("observacoes_financeiras")) or None

    if quantidade_parcelas < 1:
        return False, "Quantidade de parcelas deve ser maior ou igual a 1.", []

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
            status_financeiro=STATUS_FINANCEIRO_PENDENTE,
            previsao_vencimento=previsao_vencimento,
            quantidade_parcelas=quantidade_parcelas,
            observacoes_financeiras=observacoes_financeiras,
            observacoes=observacoes,
            gerada_em=agora_brasil(),
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

        if previsao_vencimento:
            ordem.status_financeiro = STATUS_FINANCEIRO_PREPARADO
            ordem.preparado_financeiro_em = agora_brasil()
            criar_parcelas_financeiras_ordem(
                ordem,
                previsao_vencimento,
                quantidade_parcelas,
                observacoes_financeiras,
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

    if not texto(form_data.get("data_documento")):
        return False, "Data de recebimento e obrigatoria.", None

    if data_documento is None:
        return False, "Data de recebimento invalida.", None

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
        recebido_em=agora_brasil(),
    )
    db.session.add(recebimento)
    db.session.flush()

    for ordem_item, quantidade, observacao_item in itens_recebidos:
        recebimento_item = SuprimentosRecebimentoCompraItem(
            recebimento_id=recebimento.id,
            ordem_compra_item_id=ordem_item.id,
            item_id=ordem_item.item_id,
            item_codigo_snapshot=ordem_item.item_codigo_snapshot,
            item_descricao_snapshot=ordem_item.item_descricao_snapshot,
            unidade_medida_snapshot=ordem_item.unidade_medida_snapshot,
            quantidade_recebida=quantidade,
            observacoes=observacao_item,
        )
        db.session.add(recebimento_item)
        db.session.flush()
        registrar_entrada_estoque_recebimento_item(recebimento_item)

    db.session.flush()
    for ordem_item in ordem_compra.itens:
        db.session.expire(ordem_item, ["recebimentos"])
    atualizar_status_recebimento_ordem(ordem_compra)
    db.session.commit()

    return True, "Recebimento registrado com sucesso.", recebimento


def editar_recebimento_ordem_compra(form_data, recebimento):
    if not recebimento:
        return False, "Recebimento nao encontrado."

    if recebimento.status != STATUS_RECEBIMENTO_COMPRA_REGISTRADO:
        return False, "Somente recebimentos registrados podem ser editados."

    tipo_documento = texto(form_data.get("tipo_documento"))
    numero_documento = texto_maiusculo(form_data.get("numero_documento"))
    data_documento = data_ou_none(form_data.get("data_documento"))
    observacoes = texto_maiusculo(form_data.get("observacoes")) or None

    if tipo_documento not in TIPOS_DOCUMENTO_RECEBIMENTO:
        return False, "Tipo de documento e obrigatorio."

    if not numero_documento:
        return False, "Numero do documento e obrigatorio."

    if not texto(form_data.get("data_documento")):
        return False, "Data de recebimento e obrigatoria."

    if data_documento is None:
        return False, "Data de recebimento invalida."

    recebimento.tipo_documento = tipo_documento
    recebimento.numero_documento = numero_documento
    recebimento.data_documento = data_documento
    recebimento.observacoes = observacoes

    for recebimento_item in recebimento.itens:
        movimentacao = recebimento_item.movimentacao_estoque
        if movimentacao:
            movimentacao.documento_tipo = tipo_documento
            movimentacao.documento_numero = numero_documento

    db.session.commit()
    return True, "Recebimento atualizado com sucesso."

def registrar_entrada_estoque_recebimento_item(recebimento_item):
    item = recebimento_item.item

    if not item or not item.item_estocavel:
        return None

    existente = SuprimentosMovimentacaoEstoque.query.filter_by(
        recebimento_item_id=recebimento_item.id,
    ).first()

    if existente:
        return existente

    ordem_item = recebimento_item.ordem_compra_item
    recebimento = recebimento_item.recebimento
    ordem_compra = recebimento.ordem_compra if recebimento else None
    valor_unitario = ordem_item.preco_unitario if ordem_item else None
    valor_total = None

    if valor_unitario is not None:
        valor_total = recebimento_item.quantidade_recebida * valor_unitario

    movimentacao = SuprimentosMovimentacaoEstoque(
        item_id=recebimento_item.item_id,
        recebimento_item_id=recebimento_item.id,
        ordem_compra_id=ordem_compra.id if ordem_compra else None,
        fornecedor_id=ordem_compra.fornecedor_id if ordem_compra else None,
        tipo=TIPO_MOVIMENTACAO_ESTOQUE_ENTRADA,
        origem=ORIGEM_MOVIMENTACAO_ESTOQUE_RECEBIMENTO_OC,
        status=STATUS_MOVIMENTACAO_ESTOQUE_REGISTRADA,
        documento_tipo=recebimento.tipo_documento if recebimento else None,
        documento_numero=recebimento.numero_documento if recebimento else None,
        quantidade=recebimento_item.quantidade_recebida,
        valor_unitario=valor_unitario,
        valor_total_snapshot=valor_total,
        observacoes=recebimento_item.observacoes,
        movimentado_em=recebimento.recebido_em if recebimento else agora_brasil(),
    )
    db.session.add(movimentacao)
    return movimentacao


def cancelar_ordem_compra(ordem_compra, motivo=None):
    if ordem_compra.status == STATUS_ORDEM_COMPRA_CANCELADA:
        return False, "Ordem de compra ja esta cancelada."

    if ordem_compra.status in [STATUS_ORDEM_COMPRA_PARCIAL, STATUS_ORDEM_COMPRA_RECEBIDA]:
        return False, "Ordem de compra com recebimento nao pode ser cancelada."

    ordem_compra.status = STATUS_ORDEM_COMPRA_CANCELADA
    ordem_compra.status_financeiro = STATUS_FINANCEIRO_CANCELADO
    ordem_compra.cancelada_em = agora_brasil()
    ordem_compra.motivo_cancelamento = texto_maiusculo(motivo) or None
    for parcela in ordem_compra.parcelas_financeiras:
        parcela.status = "Cancelada"
    db.session.commit()
    return True, "Ordem de compra cancelada com sucesso."


def encerrar_cotacao(cotacao):
    if not cotacao.pode_editar:
        return False, "Somente cotacoes abertas podem ser encerradas."

    if not cotacao.propostas:
        return False, "Registre ao menos uma proposta antes de encerrar."

    cotacao.status = STATUS_COTACAO_ENCERRADA
    cotacao.encerrada_em = agora_brasil()
    sincronizar_status_requisicao_por_cotacao(cotacao)
    db.session.commit()
    return True, "Cotacao encerrada com sucesso."


def cancelar_cotacao(cotacao):
    if cotacao.status == STATUS_COTACAO_CANCELADA:
        return False, "Cotacao ja esta cancelada."

    cotacao.status = STATUS_COTACAO_CANCELADA
    cotacao.encerrada_em = agora_brasil()
    sincronizar_status_requisicao_por_cotacao(cotacao)
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

