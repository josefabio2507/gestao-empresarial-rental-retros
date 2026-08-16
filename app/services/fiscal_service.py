import os
import re
import base64
import gzip
from datetime import datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from flask import current_app
from cryptography.fernet import Fernet, InvalidToken
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import FiscalCertificadoA1, FiscalControleNSU, FiscalDocumento
from app.utils.datas import agora_brasil


EXTENSOES_CERTIFICADO = {".pfx", ".p12"}


class FiscalIntegracaoErro(Exception):
    pass


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def _diretorio_config(chave):
    caminho = current_app.config.get(chave, "").strip()
    os.makedirs(caminho, exist_ok=True)
    return caminho


def _fernet_certificado():
    chave = current_app.config.get("FISCAL_CERTIFICADO_CRYPTO_KEY") or ""
    if chave:
        return Fernet(chave.encode())

    import hashlib

    segredo = current_app.config.get("SECRET_KEY") or "chave-local-desenvolvimento"
    chave_derivada = base64.urlsafe_b64encode(hashlib.sha256(segredo.encode()).digest())
    return Fernet(chave_derivada)


def criptografar_senha_certificado(senha):
    return _fernet_certificado().encrypt(senha.encode()).decode()


def descriptografar_senha_certificado(certificado):
    if not certificado.senha_criptografada:
        raise FiscalIntegracaoErro(
            "Recadastre o certificado A1 para habilitar a consulta Sefaz com PyNFe."
        )

    try:
        return _fernet_certificado().decrypt(certificado.senha_criptografada.encode()).decode()
    except InvalidToken as exc:
        raise FiscalIntegracaoErro(
            "Não foi possível descriptografar a senha do certificado. Confira FISCAL_CERTIFICADO_CRYPTO_KEY."
        ) from exc


def _texto(elemento, nome):
    if elemento is None:
        return ""
    for item in elemento.iter():
        if item.tag.split("}")[-1] == nome and item.text:
            return item.text.strip()
    return ""


def _filho(elemento, nome):
    for item in elemento.iter():
        if item.tag.split("}")[-1] == nome:
            return item
    return None


def _parse_data(valor):
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.strptime(valor[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _parse_decimal(valor):
    try:
        return Decimal((valor or "0").replace(",", "."))
    except (InvalidOperation, AttributeError):
        return Decimal("0")


def extrair_metadados_xml(xml_bytes):
    raiz = ElementTree.fromstring(xml_bytes)
    inf_nfe = _filho(raiz, "infNFe")
    emit = _filho(raiz, "emit")
    dest = _filho(raiz, "dest")
    total = _filho(raiz, "ICMSTot")

    chave = ""
    if inf_nfe is not None:
        chave = (inf_nfe.attrib.get("Id") or "").replace("NFe", "")
    if not chave:
        chave = _texto(raiz, "chNFe")

    return {
        "chave_acesso": somente_digitos(chave),
        "modelo": "55",
        "serie": _texto(raiz, "serie"),
        "numero": _texto(raiz, "nNF"),
        "natureza_operacao": _texto(raiz, "natOp"),
        "data_emissao": _parse_data(_texto(raiz, "dhEmi") or _texto(raiz, "dEmi")),
        "emitente_nome": _texto(emit, "xNome"),
        "emitente_cnpj": somente_digitos(_texto(emit, "CNPJ")),
        "destinatario_nome": _texto(dest, "xNome"),
        "destinatario_cnpj": somente_digitos(_texto(dest, "CNPJ")),
        "valor_total": _parse_decimal(_texto(total, "vNF")),
    }


def _validar_metadados(metadados):
    if len(metadados["chave_acesso"]) != 44:
        return False, "XML sem chave de acesso de NF-e válida."
    if not metadados["numero"]:
        return False, "XML sem número de NF-e."
    if not metadados["emitente_cnpj"]:
        return False, "XML sem CNPJ do emitente."
    if not metadados["destinatario_cnpj"]:
        return False, "XML sem CNPJ do destinatário."
    return True, ""


def _caminho_xml(chave_acesso):
    return os.path.join(_diretorio_config("FISCAL_XML_DIR"), f"{chave_acesso}.xml")


def _caminho_danfe(chave_acesso):
    return os.path.join(_diretorio_config("FISCAL_DANFE_DIR"), f"{chave_acesso}.pdf")


def gerar_danfe_pdf(documento):
    caminho = _caminho_danfe(documento.chave_acesso)
    pdf = canvas.Canvas(caminho, pagesize=A4)
    largura, altura = A4
    y = altura - 50

    linhas = [
        "DANFE - Documento Auxiliar da NF-e",
        f"Chave de acesso: {documento.chave_acesso}",
        f"Numero/Serie: {documento.numero} / {documento.serie or '-'}",
        f"Emissao: {documento.data_emissao.strftime('%d/%m/%Y %H:%M') if documento.data_emissao else '-'}",
        f"Emitente: {documento.emitente_nome} - {documento.emitente_cnpj}",
        f"Destinatario: {documento.destinatario_nome or '-'} - {documento.destinatario_cnpj}",
        f"Valor total: R$ {documento.valor_total}",
        "",
        "PDF gerado automaticamente a partir do XML armazenado na Central Fiscal.",
    ]

    pdf.setTitle(f"DANFE {documento.numero}")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, linhas[0])
    y -= 32
    pdf.setFont("Helvetica", 10)
    for linha in linhas[1:]:
        pdf.drawString(40, y, linha[:120])
        y -= 20
    pdf.line(40, y - 5, largura - 40, y - 5)
    pdf.showPage()
    pdf.save()
    return caminho


def salvar_xml_documento_bytes(xml_bytes, nsu=None):
    if not xml_bytes:
        return False, "Envie um arquivo XML válido.", None

    try:
        metadados = extrair_metadados_xml(xml_bytes)
    except ElementTree.ParseError:
        return False, "Não foi possível ler o XML informado.", None

    valido, mensagem = _validar_metadados(metadados)
    if not valido:
        return False, mensagem, None

    existente = FiscalDocumento.query.filter_by(chave_acesso=metadados["chave_acesso"]).first()
    xml_path = _caminho_xml(metadados["chave_acesso"])
    with open(xml_path, "wb") as destino:
        destino.write(xml_bytes)

    if existente:
        existente.xml_path = xml_path
        existente.danfe_path = gerar_danfe_pdf(existente)
        db.session.commit()
        return True, "XML já existia na Central Fiscal e foi atualizado.", existente

    documento = FiscalDocumento(nsu=nsu, xml_path=xml_path, **metadados)
    db.session.add(documento)
    db.session.flush()
    documento.danfe_path = gerar_danfe_pdf(documento)
    db.session.commit()
    return True, "XML armazenado e DANFE gerado com sucesso.", documento


def salvar_xml_documento(arquivo, usuario, nsu=None):
    if not arquivo:
        return False, "Envie um arquivo XML válido.", None

    return salvar_xml_documento_bytes(arquivo.read(), nsu=nsu)


def buscar_documentos_fiscais(filtros=None):
    filtros = filtros or {}
    consulta = FiscalDocumento.query

    numero = (filtros.get("numero") or "").strip()
    fornecedor = (filtros.get("fornecedor") or "").strip()
    status = (filtros.get("status") or "").strip()

    if numero:
        consulta = consulta.filter(FiscalDocumento.numero.ilike(f"%{numero}%"))
    if fornecedor:
        digitos = somente_digitos(fornecedor)
        if digitos:
            consulta = consulta.filter(FiscalDocumento.emitente_cnpj.contains(digitos))
        else:
            consulta = consulta.filter(FiscalDocumento.emitente_nome.ilike(f"%{fornecedor}%"))
    if status:
        consulta = consulta.filter(FiscalDocumento.status == status)

    return consulta.order_by(FiscalDocumento.data_emissao.desc(), FiscalDocumento.id.desc()).all()


def buscar_documentos_para_ordem_compra(ordem):
    cnpj = somente_digitos(ordem.fornecedor_cnpj_cpf_snapshot)
    if not cnpj:
        return []

    return (
        FiscalDocumento.query
        .filter(
            FiscalDocumento.emitente_cnpj == cnpj,
            FiscalDocumento.status == "Disponivel",
        )
        .order_by(FiscalDocumento.data_emissao.desc(), FiscalDocumento.id.desc())
        .all()
    )


def vincular_documento_ordem_compra(documento_id, ordem, usuario):
    try:
        documento_id = int(documento_id)
    except (TypeError, ValueError):
        return False, "Documento fiscal não encontrado.", None

    documento = db.session.get(FiscalDocumento, documento_id)

    if not documento:
        return False, "Documento fiscal não encontrado.", None
    if ordem.status == "Cancelada":
        return False, "O.C. cancelada não pode receber vínculo fiscal.", None
    if documento.ordem_compra_id and documento.ordem_compra_id != ordem.id:
        return False, "Documento fiscal já vinculado a outra O.C.", None
    if documento.emitente_cnpj != somente_digitos(ordem.fornecedor_cnpj_cpf_snapshot):
        return False, "O emitente da NF-e não corresponde ao fornecedor da O.C.", None

    if not documento.danfe_path or not os.path.exists(documento.danfe_path):
        documento.danfe_path = gerar_danfe_pdf(documento)

    documento.ordem_compra_id = ordem.id
    documento.vinculado_por_usuario_id = usuario.id
    documento.vinculado_em = agora_brasil()
    documento.status = "Vinculado"
    db.session.commit()
    return True, "NF-e vinculada à O.C. e DANFE associado automaticamente.", documento


def salvar_certificado_a1(form_data, arquivo, usuario):
    cnpj = somente_digitos(form_data.get("cnpj_empresa"))
    razao_social = (form_data.get("razao_social") or "").strip().upper()
    senha = form_data.get("senha") or ""

    if len(cnpj) != 14:
        return False, "Informe o CNPJ da empresa com 14 dígitos.", None
    if not razao_social:
        return False, "Informe a razão social.", None
    if not senha:
        return False, "Informe a senha do certificado.", None
    if not arquivo or not arquivo.filename:
        return False, "Envie o arquivo do certificado A1.", None

    _, extensao = os.path.splitext(arquivo.filename.lower())
    if extensao not in EXTENSOES_CERTIFICADO:
        return False, "Certificado A1 deve estar em arquivo .pfx ou .p12.", None

    diretorio = _diretorio_config("FISCAL_CERTIFICADOS_DIR")
    nome_seguro = secure_filename(f"{cnpj}{extensao}")
    caminho = os.path.join(diretorio, nome_seguro)
    arquivo.save(caminho)

    FiscalCertificadoA1.query.filter_by(cnpj_empresa=cnpj, ativo=True).update({"ativo": False})

    certificado = FiscalCertificadoA1(
        cnpj_empresa=cnpj,
        razao_social=razao_social,
        nome_arquivo_original=secure_filename(arquivo.filename),
        arquivo_path=caminho,
        senha_hash=generate_password_hash(senha),
        senha_criptografada=criptografar_senha_certificado(senha),
        cadastrado_por_usuario_id=usuario.id,
        observacoes=(form_data.get("observacoes") or "").strip().upper() or None,
    )
    db.session.add(certificado)
    db.session.commit()
    return True, "Certificado A1 cadastrado com segurança.", certificado


class PyNFeDistribuicaoClient:
    def __init__(self, certificado_path, senha, uf, homologacao):
        try:
            from pynfe.processamento.comunicacao import ComunicacaoSefaz
        except ImportError as exc:
            raise FiscalIntegracaoErro(
                "Biblioteca PyNFe não instalada. Instale as dependências do requirements.txt e refaça o deploy."
            ) from exc

        self.comunicacao = ComunicacaoSefaz(uf, certificado_path, senha, homologacao)

    def consultar(self, cnpj, ultimo_nsu):
        nsu = int(ultimo_nsu or 0)
        if hasattr(self.comunicacao, "consulta_distribuicao"):
            resposta = self.comunicacao.consulta_distribuicao(cnpj=cnpj, nsu=nsu)
        else:
            resposta = self.comunicacao.consulta_notas_cnpj(cnpj=cnpj, nsu=nsu)
        return getattr(resposta, "text", resposta)


def _texto_xml(raiz, nome):
    for item in raiz.iter():
        if item.tag.split("}")[-1] == nome and item.text:
            return item.text.strip()
    return ""


def _doczips(raiz):
    for item in raiz.iter():
        if item.tag.split("}")[-1] == "docZip" and item.text:
            yield item.attrib.get("NSU"), item.text.strip()


def _xml_doczip(conteudo_base64):
    compactado = base64.b64decode(conteudo_base64)
    return gzip.decompress(compactado)


def processar_resposta_distribuicao_dfe(xml_resposta):
    if isinstance(xml_resposta, bytes):
        xml_bytes = xml_resposta
    else:
        xml_bytes = str(xml_resposta).encode()

    raiz = ElementTree.fromstring(xml_bytes)
    cstat = _texto_xml(raiz, "cStat")
    motivo = _texto_xml(raiz, "xMotivo")
    ultimo_nsu = _texto_xml(raiz, "ultNSU")
    max_nsu = _texto_xml(raiz, "maxNSU")

    importados = 0
    ignorados = 0

    for nsu, conteudo in _doczips(raiz):
        try:
            xml_documento = _xml_doczip(conteudo)
        except (OSError, ValueError):
            ignorados += 1
            continue

        sucesso, _, _ = salvar_xml_documento_bytes(xml_documento, nsu=nsu)
        if sucesso:
            importados += 1
        else:
            ignorados += 1

    return {
        "cstat": cstat,
        "motivo": motivo,
        "ultimo_nsu": ultimo_nsu,
        "max_nsu": max_nsu,
        "importados": importados,
        "ignorados": ignorados,
    }


def certificado_ativo_empresa(cnpj):
    return (
        FiscalCertificadoA1.query
        .filter_by(cnpj_empresa=cnpj, ativo=True)
        .order_by(FiscalCertificadoA1.criado_em.desc())
        .first()
    )


def consultar_documentos_sefaz(cnpj_empresa, cliente_cls=None):
    cnpj = somente_digitos(cnpj_empresa)
    if len(cnpj) != 14:
        return False, "Informe o CNPJ da Rental Retros para consulta.", None

    controle = FiscalControleNSU.query.filter_by(cnpj_empresa=cnpj).first()
    if not controle:
        controle = FiscalControleNSU(cnpj_empresa=cnpj, ultimo_nsu="0")
        db.session.add(controle)
        db.session.flush()

    controle.consultado_em = agora_brasil()
    certificado = certificado_ativo_empresa(cnpj)
    if not certificado:
        controle.status = "Aguardando certificado"
        controle.mensagem = "Cadastre um certificado A1 ativo para este CNPJ antes de consultar a Sefaz."
        db.session.commit()
        return False, controle.mensagem, controle

    uf = (current_app.config.get("FISCAL_SEFAZ_UF") or "").strip().lower()
    if not uf:
        controle.status = "Aguardando configuração"
        controle.mensagem = "Configure FISCAL_SEFAZ_UF para consultar a Sefaz com PyNFe."
        db.session.commit()
        return False, controle.mensagem, controle

    try:
        senha = descriptografar_senha_certificado(certificado)
        cliente = (cliente_cls or PyNFeDistribuicaoClient)(
            certificado.arquivo_path,
            senha,
            uf,
            current_app.config.get("FISCAL_SEFAZ_HOMOLOGACAO", False),
        )
        resposta = cliente.consultar(cnpj, controle.ultimo_nsu)
        resultado = processar_resposta_distribuicao_dfe(resposta)
    except FiscalIntegracaoErro as exc:
        controle.status = "Aguardando integração"
        controle.mensagem = str(exc)
        db.session.commit()
        return False, controle.mensagem, controle
    except Exception as exc:
        controle.status = "Erro"
        controle.mensagem = f"Falha ao consultar Sefaz: {exc}"
        db.session.commit()
        return False, controle.mensagem, controle

    if resultado["ultimo_nsu"]:
        controle.ultimo_nsu = resultado["ultimo_nsu"]
    if resultado["max_nsu"]:
        controle.max_nsu = resultado["max_nsu"]

    if resultado["cstat"] == "137":
        controle.status = "Sem novos documentos"
    elif resultado["cstat"] == "138":
        controle.status = "Consultado"
    elif resultado["cstat"] == "656":
        controle.status = "Uso indevido"
    else:
        controle.status = "Consultado" if resultado["importados"] else "Aguardando análise"

    controle.mensagem = (
        f"Sefaz: {resultado['motivo'] or 'retorno recebido'}. "
        f"XMLs importados: {resultado['importados']}. "
        f"Documentos ignorados/resumidos: {resultado['ignorados']}."
    )
    db.session.commit()
    return True, controle.mensagem, controle


def buscar_certificados():
    return FiscalCertificadoA1.query.order_by(FiscalCertificadoA1.criado_em.desc()).all()


def buscar_controles_nsu():
    return FiscalControleNSU.query.order_by(FiscalControleNSU.cnpj_empresa.asc()).all()
