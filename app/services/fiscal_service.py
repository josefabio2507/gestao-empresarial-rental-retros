import os
import re
import base64
import gzip
import tempfile
import uuid
from importlib import metadata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from flask import current_app
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import requests
from signxml import XMLSigner, methods
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import FiscalCertificadoA1, FiscalControleNSU, FiscalDocumento, FiscalManifestacaoNFe
from app.utils.datas import agora_brasil


EXTENSOES_CERTIFICADO = {".pfx", ".p12"}

STATUS_RESUMO_LOCALIZADO = "Resumo localizado"
STATUS_AGUARDANDO_MANIFESTACAO = "Aguardando manifestacao"
STATUS_CIENCIA_REGISTRADA = "Ciencia registrada"
STATUS_XML_BAIXADO = "XML baixado"
STATUS_VINCULADO_OC = "Vinculado a OC"
STATUS_CONFIRMADA = "Confirmada"
STATUS_DESCONHECIDA = "Desconhecida"
STATUS_OPERACAO_NAO_REALIZADA = "Operacao nao realizada"
STATUS_CANCELADA = "Cancelada"

TIPO_RESUMO_NFE = "resNFe"
TIPO_XML_COMPLETO = "procNFe"
TIPO_EVENTO = "evento"

EVENTOS_MANIFESTACAO = {
    "ciencia": {
        "codigo": "210210",
        "label": "Ciencia da Operacao",
        "descricao_oficial": "Ciencia da Operacao",
        "status": STATUS_CIENCIA_REGISTRADA,
    },
    "confirmacao": {
        "codigo": "210200",
        "label": "Confirmacao da Operacao",
        "descricao_oficial": "Confirmacao da Operacao",
        "status": STATUS_CONFIRMADA,
    },
    "desconhecimento": {
        "codigo": "210220",
        "label": "Desconhecimento da Operacao",
        "descricao_oficial": "Desconhecimento da Operacao",
        "status": STATUS_DESCONHECIDA,
    },
    "nao_realizada": {
        "codigo": "210240",
        "label": "Operacao nao Realizada",
        "descricao_oficial": "Operacao nao Realizada",
        "status": STATUS_OPERACAO_NAO_REALIZADA,
    },
}

CODIGO_ORGAO_MANIFESTACAO_DESTINATARIO = "91"
VERSAO_EVENTO_MANIFESTACAO = "1.00"
VERSAO_ENVIO_EVENTO = "1.00"
NAMESPACE_NFE = "http://www.portalfiscal.inf.br/nfe"
NAMESPACE_SOAP12 = "http://www.w3.org/2003/05/soap-envelope"
NAMESPACE_RECEPCAO_EVENTO = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4"
ENDPOINT_RECEPCAO_EVENTO_PRODUCAO = (
    "https://www.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx"
)
ENDPOINT_RECEPCAO_EVENTO_HOMOLOGACAO = (
    "https://hom.nfe.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx"
)
MENSAGEM_MANIFESTACAO_FALHOU = (
    "Não foi possível transmitir a manifestação à Sefaz. "
    "O sistema registrou o diagnóstico técnico para análise. "
    "Verifique o certificado, o ambiente configurado e tente novamente."
)

STATUS_DOCUMENTOS_FISCAIS = [
    STATUS_RESUMO_LOCALIZADO,
    STATUS_AGUARDANDO_MANIFESTACAO,
    STATUS_CIENCIA_REGISTRADA,
    STATUS_XML_BAIXADO,
    STATUS_VINCULADO_OC,
    STATUS_CONFIRMADA,
    STATUS_DESCONHECIDA,
    STATUS_OPERACAO_NAO_REALIZADA,
    STATUS_CANCELADA,
]


class FiscalIntegracaoErro(Exception):
    pass


class NFeXMLSigner(XMLSigner):
    def check_deprecated_methods(self):
        return


def somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def _diretorio_config(chave):
    caminho = current_app.config.get(chave, "").strip()
    os.makedirs(caminho, exist_ok=True)
    return caminho


def _fernet_certificado():
    chave = (current_app.config.get("FISCAL_CERTIFICADO_CRYPTO_KEY") or "").strip()
    if chave:
        try:
            return Fernet(chave.encode())
        except ValueError as exc:
            raise FiscalIntegracaoErro(
                "FISCAL_CERTIFICADO_CRYPTO_KEY invalida. Gere uma chave Fernet valida antes de cadastrar o certificado A1."
            ) from exc

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


def extrair_metadados_resumo_nfe(xml_bytes):
    raiz = ElementTree.fromstring(xml_bytes)
    chave = somente_digitos(_texto(raiz, "chNFe"))

    return {
        "chave_acesso": chave,
        "modelo": chave[20:22] if len(chave) == 44 else "55",
        "serie": str(int(chave[22:25])) if len(chave) == 44 else "",
        "numero": str(int(chave[25:34])) if len(chave) == 44 else "",
        "natureza_operacao": None,
        "data_emissao": _parse_data(_texto(raiz, "dhEmi") or _texto(raiz, "dEmi")),
        "emitente_nome": _texto(raiz, "xNome"),
        "emitente_cnpj": somente_digitos(_texto(raiz, "CNPJ") or _texto(raiz, "CPF")),
        "destinatario_nome": "",
        "destinatario_cnpj": "",
        "valor_total": _parse_decimal(_texto(raiz, "vNF")),
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


def _validar_resumo(metadados):
    if len(metadados["chave_acesso"]) != 44:
        return False, "Resumo sem chave de acesso de NF-e valida."
    if not metadados["numero"]:
        return False, "Resumo sem numero de NF-e."
    if not metadados["emitente_cnpj"]:
        return False, "Resumo sem CNPJ/CPF do emitente."
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
        for campo, valor in metadados.items():
            setattr(existente, campo, valor)
        existente.xml_path = xml_path
        existente.tipo_distribuicao = TIPO_XML_COMPLETO
        existente.tem_xml_completo = True
        existente.status = STATUS_XML_BAIXADO if not existente.ordem_compra_id else STATUS_VINCULADO_OC
        existente.xml_completo_baixado_em = agora_brasil()
        existente.ultima_consulta_em = agora_brasil()
        existente.danfe_path = gerar_danfe_pdf(existente)
        db.session.commit()
        return True, "XML já existia na Central Fiscal e foi atualizado.", existente

    documento = FiscalDocumento(
        nsu=nsu,
        xml_path=xml_path,
        tipo_distribuicao=TIPO_XML_COMPLETO,
        tem_xml_completo=True,
        status=STATUS_XML_BAIXADO,
        xml_completo_baixado_em=agora_brasil(),
        ultima_consulta_em=agora_brasil(),
        **metadados,
    )
    db.session.add(documento)
    db.session.flush()
    documento.danfe_path = gerar_danfe_pdf(documento)
    db.session.commit()
    return True, "XML armazenado e DANFE gerado com sucesso.", documento


def salvar_resumo_nfe_bytes(xml_bytes, nsu=None, cnpj_destinatario=None):
    if not xml_bytes:
        return False, "Resumo de NF-e vazio.", None

    try:
        metadados = extrair_metadados_resumo_nfe(xml_bytes)
    except ElementTree.ParseError:
        return False, "Nao foi possivel ler o resumo da NF-e.", None

    valido, mensagem = _validar_resumo(metadados)
    if not valido:
        return False, mensagem, None

    if cnpj_destinatario:
        metadados["destinatario_cnpj"] = somente_digitos(cnpj_destinatario)

    documento = FiscalDocumento.query.filter_by(chave_acesso=metadados["chave_acesso"]).first()
    if documento and documento.tem_xml_completo:
        documento.ultima_consulta_em = agora_brasil()
        db.session.commit()
        return True, "Resumo ignorado porque o XML completo ja esta armazenado.", documento

    if not documento:
        documento = FiscalDocumento(
            nsu=nsu,
            xml_path=None,
            danfe_path=None,
            tipo_distribuicao=TIPO_RESUMO_NFE,
            tem_xml_completo=False,
            status=STATUS_AGUARDANDO_MANIFESTACAO,
            manifestacao_status=STATUS_AGUARDANDO_MANIFESTACAO,
            ultima_consulta_em=agora_brasil(),
            **metadados,
        )
        db.session.add(documento)
    else:
        for campo, valor in metadados.items():
            if valor not in (None, ""):
                setattr(documento, campo, valor)
        documento.nsu = nsu or documento.nsu
        documento.tipo_distribuicao = TIPO_RESUMO_NFE
        documento.tem_xml_completo = False
        documento.status = documento.status or STATUS_AGUARDANDO_MANIFESTACAO
        documento.manifestacao_status = documento.manifestacao_status or STATUS_AGUARDANDO_MANIFESTACAO
        documento.ultima_consulta_em = agora_brasil()

    db.session.commit()
    return True, "Resumo da NF-e localizado e aguardando manifestacao.", documento


def salvar_xml_documento(arquivo, usuario, nsu=None):
    if not arquivo:
        return False, "Envie um arquivo XML válido.", None

    return salvar_xml_documento_bytes(arquivo.read(), nsu=nsu)


def rotulos_status_documento():
    return STATUS_DOCUMENTOS_FISCAIS


def eventos_manifestacao_disponiveis():
    return EVENTOS_MANIFESTACAO


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

    cnpjs_empresa = [
        certificado.cnpj_empresa
        for certificado in FiscalCertificadoA1.query.filter_by(ativo=True).all()
    ]
    if not cnpjs_empresa:
        return []

    return (
        FiscalDocumento.query
        .filter(
            FiscalDocumento.emitente_cnpj == cnpj,
            FiscalDocumento.destinatario_cnpj.in_(cnpjs_empresa),
            FiscalDocumento.tem_xml_completo.is_(True),
            FiscalDocumento.xml_path.isnot(None),
            FiscalDocumento.ordem_compra_id.is_(None),
            FiscalDocumento.status.in_([STATUS_XML_BAIXADO, STATUS_CONFIRMADA]),
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
    if not documento.tem_xml_completo or not documento.xml_path:
        return False, "A NF-e ainda nao possui XML completo disponivel para vinculo com O.C.", None
    if documento.emitente_cnpj != somente_digitos(ordem.fornecedor_cnpj_cpf_snapshot):
        return False, "O emitente da NF-e não corresponde ao fornecedor da O.C.", None

    if not documento.danfe_path or not os.path.exists(documento.danfe_path):
        documento.danfe_path = gerar_danfe_pdf(documento)

    documento.ordem_compra_id = ordem.id
    documento.vinculado_por_usuario_id = usuario.id
    documento.vinculado_em = agora_brasil()
    documento.status = STATUS_VINCULADO_OC
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

    try:
        senha_criptografada = criptografar_senha_certificado(senha)
    except FiscalIntegracaoErro as exc:
        return False, str(exc), None

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
        senha_criptografada=senha_criptografada,
        cadastrado_por_usuario_id=usuario.id,
        observacoes=(form_data.get("observacoes") or "").strip().upper() or None,
    )
    db.session.add(certificado)
    db.session.commit()
    return True, "Certificado A1 cadastrado com segurança.", certificado


def _versao_pynfe_instalada():
    try:
        return metadata.version("pynfe")
    except metadata.PackageNotFoundError:
        return "nao instalada"


def _endpoint_recepcao_evento(homologacao):
    configurado = (current_app.config.get("FISCAL_SEFAZ_RECEPCAO_EVENTO_URL") or "").strip()
    if configurado:
        return configurado
    if homologacao:
        return ENDPOINT_RECEPCAO_EVENTO_HOMOLOGACAO
    return ENDPOINT_RECEPCAO_EVENTO_PRODUCAO


def _dh_evento_sefaz():
    return agora_brasil().astimezone().isoformat(timespec="seconds")


def _certificado_pem_do_a1(certificado_path, senha):
    with open(certificado_path, "rb") as origem:
        conteudo = origem.read()

    chave, certificado, adicionais = pkcs12.load_key_and_certificates(
        conteudo,
        senha.encode() if senha else None,
    )
    if not chave or not certificado:
        raise FiscalIntegracaoErro("Certificado A1 sem chave privada ou certificado público válido.")

    chave_pem = chave.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    certificado_pem = certificado.public_bytes(serialization.Encoding.PEM)
    if adicionais:
        certificado_pem += b"".join(
            item.public_bytes(serialization.Encoding.PEM) for item in adicionais
        )
    return chave_pem, certificado_pem


class SefazManifestacaoDestinatarioAdapter:
    metodos_pynfe_candidatos = (
        "manifestar",
        "manifestacao_destinatario",
        "evento_manifestacao_destinatario",
        "recepcao_evento_manifestacao_destinatario",
    )

    def __init__(self, comunicacao, certificado_path, senha, uf, homologacao):
        self.comunicacao = comunicacao
        self.certificado_path = certificado_path
        self.senha = senha
        self.uf = uf
        self.homologacao = homologacao

    def manifestar(self, cnpj, chave_acesso, evento_codigo, justificativa=None):
        metodos_detectados = self.metodos_manifestacao_detectados()
        self._registrar_diagnostico(
            "diagnostico_manifestacao_destinatario",
            cnpj=cnpj,
            chave_acesso=chave_acesso,
            evento_codigo=evento_codigo,
            metodos_detectados=metodos_detectados,
        )

        resposta = self._manifestar_via_pynfe(
            metodos_detectados,
            cnpj,
            chave_acesso,
            evento_codigo,
            justificativa=justificativa,
        )
        if resposta is not None:
            return resposta

        return self._manifestar_via_fallback(
            cnpj,
            chave_acesso,
            evento_codigo,
            justificativa=justificativa,
        )

    def metodos_manifestacao_detectados(self):
        return [
            nome
            for nome in self.metodos_pynfe_candidatos
            if hasattr(self.comunicacao, nome)
        ]

    def _manifestar_via_pynfe(self, metodos_detectados, cnpj, chave_acesso, evento_codigo, justificativa=None):
        for nome_metodo in metodos_detectados:
            metodo = getattr(self.comunicacao, nome_metodo)
            tentativas = (
                {
                    "cnpj": cnpj,
                    "chave": chave_acesso,
                    "evento": evento_codigo,
                    "justificativa": justificativa,
                },
                {
                    "cnpj": cnpj,
                    "chave_acesso": chave_acesso,
                    "evento_codigo": evento_codigo,
                    "justificativa": justificativa,
                },
                {
                    "cnpj": cnpj,
                    "chave": chave_acesso,
                    "tp_evento": evento_codigo,
                    "justificativa": justificativa,
                },
            )
            for parametros in tentativas:
                try:
                    resposta = metodo(**parametros)
                    self._registrar_diagnostico(
                        "manifestacao_destinatario_pynfe_enviada",
                        metodo=nome_metodo,
                        parametros=list(parametros.keys()),
                    )
                    return getattr(resposta, "text", resposta)
                except TypeError as exc:
                    self._registrar_diagnostico(
                        "manifestacao_destinatario_pynfe_assinatura_incompativel",
                        metodo=nome_metodo,
                        erro=str(exc),
                    )
                    continue

        if not metodos_detectados:
            self._registrar_diagnostico(
                "manifestacao_destinatario_pynfe_sem_metodo_compativel",
                detalhe="PyNFe sem metodo pronto para manifestacao neste ambiente.",
            )
        return None

    def _manifestar_via_fallback(self, cnpj, chave_acesso, evento_codigo, justificativa=None):
        endpoint = _endpoint_recepcao_evento(self.homologacao)
        self._registrar_diagnostico(
            "manifestacao_destinatario_fallback_iniciado",
            endpoint=endpoint,
            ambiente="homologacao" if self.homologacao else "producao",
        )

        xml_assinado = self._montar_xml_evento_assinado(
            cnpj,
            chave_acesso,
            evento_codigo,
            justificativa=justificativa,
        )
        envelope = self._envelope_soap(xml_assinado)
        chave_pem, certificado_pem = _certificado_pem_do_a1(self.certificado_path, self.senha)

        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cert_file, tempfile.NamedTemporaryFile(
            suffix=".key",
            delete=False,
        ) as key_file:
            cert_file.write(certificado_pem)
            key_file.write(chave_pem)
            cert_file.flush()
            key_file.flush()
            cert_path = cert_file.name
            key_path = key_file.name

        try:
            resposta = requests.post(
                endpoint,
                data=envelope,
                headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                cert=(cert_path, key_path),
                timeout=60,
            )
            self._registrar_diagnostico(
                "manifestacao_destinatario_fallback_resposta",
                endpoint=endpoint,
                http_status=resposta.status_code,
            )
            resposta.raise_for_status()
            return resposta.text
        finally:
            for caminho in (cert_path, key_path):
                try:
                    os.remove(caminho)
                except OSError:
                    current_app.logger.warning("Nao foi possivel remover arquivo temporario fiscal: %s", caminho)

    def _montar_xml_evento_assinado(self, cnpj, chave_acesso, evento_codigo, justificativa=None):
        dados_evento = next(
            (dados for dados in EVENTOS_MANIFESTACAO.values() if dados["codigo"] == evento_codigo),
            None,
        )
        if not dados_evento:
            raise FiscalIntegracaoErro("Evento de manifestacao invalido para envio a Sefaz.")

        identificador = f"ID{evento_codigo}{chave_acesso}01"
        nsmap = {None: NAMESPACE_NFE}
        env_evento = etree.Element(
            etree.QName(NAMESPACE_NFE, "envEvento"),
            nsmap=nsmap,
            versao=VERSAO_ENVIO_EVENTO,
        )
        etree.SubElement(env_evento, etree.QName(NAMESPACE_NFE, "idLote")).text = uuid.uuid4().hex[:15]
        evento = etree.SubElement(
            env_evento,
            etree.QName(NAMESPACE_NFE, "evento"),
            versao=VERSAO_EVENTO_MANIFESTACAO,
        )
        inf_evento = etree.SubElement(evento, etree.QName(NAMESPACE_NFE, "infEvento"), Id=identificador)
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "cOrgao")).text = CODIGO_ORGAO_MANIFESTACAO_DESTINATARIO
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "tpAmb")).text = "2" if self.homologacao else "1"
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "CNPJ")).text = cnpj
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "chNFe")).text = chave_acesso
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "dhEvento")).text = _dh_evento_sefaz()
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "tpEvento")).text = evento_codigo
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "nSeqEvento")).text = "1"
        etree.SubElement(inf_evento, etree.QName(NAMESPACE_NFE, "verEvento")).text = VERSAO_EVENTO_MANIFESTACAO
        det_evento = etree.SubElement(
            inf_evento,
            etree.QName(NAMESPACE_NFE, "detEvento"),
            versao=VERSAO_EVENTO_MANIFESTACAO,
        )
        etree.SubElement(det_evento, etree.QName(NAMESPACE_NFE, "descEvento")).text = dados_evento["descricao_oficial"]
        if evento_codigo == EVENTOS_MANIFESTACAO["nao_realizada"]["codigo"]:
            etree.SubElement(det_evento, etree.QName(NAMESPACE_NFE, "xJust")).text = justificativa

        chave_pem, certificado_pem = _certificado_pem_do_a1(self.certificado_path, self.senha)
        signer = NFeXMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha1",
            digest_algorithm="sha1",
        )
        evento_assinado = signer.sign(
            evento,
            key=chave_pem,
            cert=certificado_pem,
            reference_uri=f"#{identificador}",
            always_add_key_value=False,
        )
        env_evento.remove(evento)
        env_evento.append(evento_assinado)
        return etree.tostring(env_evento, encoding="utf-8", xml_declaration=True)

    def _envelope_soap(self, xml_evento):
        envelope = etree.Element(etree.QName(NAMESPACE_SOAP12, "Envelope"), nsmap={"soap12": NAMESPACE_SOAP12})
        body = etree.SubElement(envelope, etree.QName(NAMESPACE_SOAP12, "Body"))
        metodo = etree.SubElement(
            body,
            etree.QName(NAMESPACE_RECEPCAO_EVENTO, "nfeRecepcaoEventoNF"),
        )
        dados = etree.SubElement(metodo, etree.QName(NAMESPACE_RECEPCAO_EVENTO, "nfeDadosMsg"))
        dados.append(etree.fromstring(xml_evento))
        return etree.tostring(envelope, encoding="utf-8", xml_declaration=True)

    def _registrar_diagnostico(self, mensagem, **dados):
        current_app.logger.info(
            "[fiscal_manifestacao] %s | pynfe=%s uf=%s ambiente=%s dados=%s",
            mensagem,
            _versao_pynfe_instalada(),
            self.uf,
            "homologacao" if self.homologacao else "producao",
            dados,
        )


class PyNFeDistribuicaoClient:
    def __init__(self, certificado_path, senha, uf, homologacao):
        try:
            from pynfe.processamento.comunicacao import ComunicacaoSefaz
        except ImportError as exc:
            raise FiscalIntegracaoErro(
                "Biblioteca PyNFe não instalada. Instale as dependências do requirements.txt e refaça o deploy."
            ) from exc

        self.comunicacao = ComunicacaoSefaz(uf, certificado_path, senha, homologacao)
        self.adaptador_manifestacao = SefazManifestacaoDestinatarioAdapter(
            self.comunicacao,
            certificado_path,
            senha,
            uf,
            homologacao,
        )

    def consultar(self, cnpj, ultimo_nsu):
        nsu = int(ultimo_nsu or 0)
        if hasattr(self.comunicacao, "consulta_distribuicao"):
            resposta = self.comunicacao.consulta_distribuicao(cnpj=cnpj, nsu=nsu)
        else:
            resposta = self.comunicacao.consulta_notas_cnpj(cnpj=cnpj, nsu=nsu)
        return getattr(resposta, "text", resposta)

    def manifestar(self, cnpj, chave_acesso, evento_codigo, justificativa=None):
        return self.adaptador_manifestacao.manifestar(
            cnpj,
            chave_acesso,
            evento_codigo,
            justificativa=justificativa,
        )

    def baixar_xml_completo(self, cnpj, chave_acesso, ultimo_nsu):
        if hasattr(self.comunicacao, "consulta_distribuicao_chave"):
            resposta = self.comunicacao.consulta_distribuicao_chave(cnpj=cnpj, chave=chave_acesso)
        else:
            resposta = self.consultar(cnpj, ultimo_nsu)
        return getattr(resposta, "text", resposta)


def _texto_xml(raiz, nome):
    for item in raiz.iter():
        if item.tag.split("}")[-1] == nome and item.text:
            return item.text.strip()
    return ""


def _doczips(raiz):
    for item in raiz.iter():
        if item.tag.split("}")[-1] == "docZip" and item.text:
            yield item.attrib.get("NSU"), item.attrib.get("schema", ""), item.text.strip()


def _xml_doczip(conteudo_base64):
    compactado = base64.b64decode(conteudo_base64)
    return gzip.decompress(compactado)


def _status_retorno_evento(xml_resposta):
    if isinstance(xml_resposta, bytes):
        xml_bytes = xml_resposta
    else:
        xml_bytes = str(xml_resposta).encode()

    try:
        raiz = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        return {
            "status_retorno": "",
            "motivo_retorno": "Retorno da Sefaz recebido sem XML legivel.",
            "protocolo": "",
            "xml_bytes": xml_bytes,
        }

    inf_evento = _filho(raiz, "infEvento")
    origem_status = inf_evento if inf_evento is not None else raiz
    return {
        "status_retorno": _texto_xml(origem_status, "cStat"),
        "motivo_retorno": _texto_xml(origem_status, "xMotivo"),
        "protocolo": _texto_xml(origem_status, "nProt"),
        "xml_bytes": xml_bytes,
    }


def _caminho_evento(chave_acesso, evento):
    diretorio = _diretorio_config("FISCAL_XML_DIR")
    return os.path.join(diretorio, f"{chave_acesso}-{evento}.xml")


def processar_resposta_distribuicao_dfe(xml_resposta, cnpj_destinatario=None):
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
    resumos = 0
    ignorados = 0

    for nsu, schema, conteudo in _doczips(raiz):
        try:
            xml_documento = _xml_doczip(conteudo)
        except (OSError, ValueError):
            ignorados += 1
            continue

        schema = (schema or "").lower()
        if "resnfe" in schema:
            sucesso, _, _ = salvar_resumo_nfe_bytes(
                xml_documento,
                nsu=nsu,
                cnpj_destinatario=cnpj_destinatario,
            )
            if sucesso:
                resumos += 1
            else:
                ignorados += 1
            continue

        if "procnfe" not in schema and "nfe" not in schema:
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
        "resumos": resumos,
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
        resultado = processar_resposta_distribuicao_dfe(resposta, cnpj_destinatario=cnpj)
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
        controle.status = "Consultado" if (resultado["importados"] or resultado["resumos"]) else "Aguardando análise"

    controle.mensagem = (
        f"Sefaz: {resultado['motivo'] or 'retorno recebido'}. "
        f"XMLs importados: {resultado['importados']}. "
        f"Resumos localizados: {resultado['resumos']}. "
        f"Documentos ignorados/resumidos: {resultado['ignorados']}."
    )
    db.session.commit()
    return True, controle.mensagem, controle


def _cliente_fiscal_documento(documento, cliente_cls=None):
    cnpj = somente_digitos(documento.destinatario_cnpj)
    if len(cnpj) != 14:
        return None, None, "Documento sem CNPJ destinatario valido."

    certificado = certificado_ativo_empresa(cnpj)
    if not certificado:
        return None, None, "Cadastre um certificado A1 ativo para o CNPJ destinatario antes de manifestar."

    uf = (current_app.config.get("FISCAL_SEFAZ_UF") or "").strip().lower()
    if not uf:
        return None, None, "Configure FISCAL_SEFAZ_UF para consultar a Sefaz com PyNFe."

    senha = descriptografar_senha_certificado(certificado)
    cliente = (cliente_cls or PyNFeDistribuicaoClient)(
        certificado.arquivo_path,
        senha,
        uf,
        current_app.config.get("FISCAL_SEFAZ_HOMOLOGACAO", False),
    )
    return cliente, cnpj, ""


def manifestar_documento_fiscal(documento_id, evento, usuario, justificativa=None, cliente_cls=None):
    documento = db.session.get(FiscalDocumento, documento_id)
    if not documento:
        return False, "Documento fiscal nao encontrado.", None
    if documento.tem_xml_completo and evento == "ciencia":
        return False, "Documento ja possui XML completo baixado.", documento

    dados_evento = EVENTOS_MANIFESTACAO.get(evento)
    if not dados_evento:
        return False, "Evento de manifestacao invalido.", documento
    if evento == "nao_realizada" and not (justificativa or "").strip():
        return False, "Informe a justificativa para Operacao nao Realizada.", documento

    try:
        cliente, cnpj, mensagem = _cliente_fiscal_documento(documento, cliente_cls=cliente_cls)
        if not cliente:
            return False, mensagem, documento

        resposta = cliente.manifestar(
            cnpj,
            documento.chave_acesso,
            dados_evento["codigo"],
            justificativa=(justificativa or "").strip() or None,
        )
        retorno = _status_retorno_evento(resposta)
    except FiscalIntegracaoErro as exc:
        current_app.logger.exception(
            "[fiscal_manifestacao] Falha de integracao ao manifestar NF-e %s: %s",
            documento.chave_acesso,
            exc,
        )
        return False, MENSAGEM_MANIFESTACAO_FALHOU, documento
    except Exception as exc:
        current_app.logger.exception(
            "[fiscal_manifestacao] Erro inesperado ao manifestar NF-e %s: %s",
            documento.chave_acesso,
            exc,
        )
        return False, MENSAGEM_MANIFESTACAO_FALHOU, documento

    caminho_evento = _caminho_evento(documento.chave_acesso, evento)
    with open(caminho_evento, "wb") as destino:
        destino.write(retorno["xml_bytes"])

    manifestacao = FiscalManifestacaoNFe(
        documento_id=documento.id,
        chave_acesso=documento.chave_acesso,
        evento=evento,
        status_retorno=retorno["status_retorno"],
        motivo_retorno=retorno["motivo_retorno"],
        protocolo=retorno["protocolo"],
        xml_evento_path=caminho_evento,
        usuario_id=usuario.id,
    )
    db.session.add(manifestacao)

    documento.manifestacao_status = dados_evento["status"]
    documento.manifestacao_evento = evento
    documento.manifestacao_protocolo = retorno["protocolo"] or documento.manifestacao_protocolo
    documento.manifestacao_em = agora_brasil()
    documento.manifestado_por_usuario_id = usuario.id
    documento.status = dados_evento["status"]
    db.session.commit()

    mensagem_final = f"{dados_evento['label']} registrada para a NF-e."
    try:
        controle = FiscalControleNSU.query.filter_by(cnpj_empresa=cnpj).first()
        ultimo_nsu = controle.ultimo_nsu if controle else documento.nsu or "0"
        resposta_xml = cliente.baixar_xml_completo(cnpj, documento.chave_acesso, ultimo_nsu)
        processar_resposta_distribuicao_dfe(resposta_xml, cnpj_destinatario=cnpj)
        db.session.refresh(documento)
        if documento.tem_xml_completo and documento.xml_path:
            mensagem_final += " XML completo baixado e DANFE gerado automaticamente."
    except Exception:
        mensagem_final += " O XML completo ainda nao foi disponibilizado pela Sefaz."

    return True, mensagem_final, documento


def baixar_xml_completo_documento(documento_id, usuario, cliente_cls=None):
    documento = db.session.get(FiscalDocumento, documento_id)
    if not documento:
        return False, "Documento fiscal nao encontrado.", None
    if documento.tem_xml_completo and documento.xml_path:
        if not documento.danfe_path or not os.path.exists(documento.danfe_path):
            documento.danfe_path = gerar_danfe_pdf(documento)
            db.session.commit()
        return True, "XML completo ja estava disponivel.", documento
    if not documento.manifestacao_status:
        return False, "Manifeste a NF-e antes de baixar o XML completo.", documento

    try:
        cliente, cnpj, mensagem = _cliente_fiscal_documento(documento, cliente_cls=cliente_cls)
        if not cliente:
            return False, mensagem, documento

        controle = FiscalControleNSU.query.filter_by(cnpj_empresa=cnpj).first()
        ultimo_nsu = controle.ultimo_nsu if controle else documento.nsu or "0"
        resposta = cliente.baixar_xml_completo(cnpj, documento.chave_acesso, ultimo_nsu)
        resultado = processar_resposta_distribuicao_dfe(resposta, cnpj_destinatario=cnpj)
    except FiscalIntegracaoErro as exc:
        return False, str(exc), documento
    except Exception as exc:
        return False, f"Falha ao baixar XML completo na Sefaz: {exc}", documento

    db.session.refresh(documento)
    if documento.tem_xml_completo and documento.xml_path:
        return True, "XML completo baixado e DANFE gerado automaticamente.", documento

    return False, (
        "Manifestacao registrada, mas a Sefaz ainda nao retornou o XML completo. "
        f"Resumos: {resultado['resumos']}. Ignorados: {resultado['ignorados']}."
    ), documento


def buscar_certificados():
    return FiscalCertificadoA1.query.order_by(FiscalCertificadoA1.criado_em.desc()).all()


def buscar_controles_nsu():
    return FiscalControleNSU.query.order_by(FiscalControleNSU.cnpj_empresa.asc()).all()
