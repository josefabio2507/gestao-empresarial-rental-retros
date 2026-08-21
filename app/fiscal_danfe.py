import os
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from flask import current_app, has_app_context

try:
    from brazilfiscalreport.danfe import Danfe
except Exception:  # pragma: no cover - validado no deploy quando a dependência é instalada
    Danfe = None


def _tag(elemento):
    return elemento.tag.split("}")[-1] if elemento is not None else ""


def _filho(elemento, nome):
    if elemento is None:
        return None
    for item in list(elemento):
        if _tag(item) == nome:
            return item
    return None


def _descendente(elemento, nome):
    if elemento is None:
        return None
    for item in elemento.iter():
        if _tag(item) == nome:
            return item
    return None


def _texto(elemento, nome, padrao=""):
    item = _descendente(elemento, nome)
    if item is None or item.text is None:
        return padrao
    return item.text.strip()


def _decimal(valor):
    try:
        return Decimal(str(valor or "0").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _moeda(valor):
    numero = _decimal(valor)
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar_documento(valor):
    digitos = "".join(ch for ch in str(valor or "") if ch.isdigit())
    if len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return valor or ""


def _data_br(valor):
    if not valor:
        return ""
    valor = valor.replace("Z", "")
    data = valor[:10]
    hora = valor[11:16] if len(valor) >= 16 else ""
    try:
        ano, mes, dia = data.split("-")
        return f"{dia}/{mes}/{ano} {hora}".strip()
    except ValueError:
        return valor


def extrair_dados_danfe(xml_path):
    raiz = ElementTree.parse(xml_path).getroot()
    inf_nfe = _descendente(raiz, "infNFe")
    ide = _filho(inf_nfe, "ide")
    emit = _filho(inf_nfe, "emit")
    dest = _filho(inf_nfe, "dest")
    total = _descendente(inf_nfe, "ICMSTot")
    inf_prot = _descendente(raiz, "infProt")

    chave = (inf_nfe.attrib.get("Id") or "").replace("NFe", "") if inf_nfe is not None else ""
    if not chave:
        chave = _texto(inf_prot, "chNFe")

    produtos = []
    for det in raiz.iter():
        if _tag(det) != "det":
            continue
        prod = _filho(det, "prod")
        produtos.append(
            {
                "codigo": _texto(prod, "cProd"),
                "descricao": _texto(prod, "xProd"),
                "ncm": _texto(prod, "NCM"),
                "cfop": _texto(prod, "CFOP"),
                "valor_total": _moeda(_texto(prod, "vProd")),
            }
        )

    return {
        "chave": chave,
        "numero": _texto(ide, "nNF"),
        "serie": _texto(ide, "serie"),
        "emissao": _data_br(_texto(ide, "dhEmi") or _texto(ide, "dEmi")),
        "protocolo": _texto(inf_prot, "nProt"),
        "emitente": {
            "nome": _texto(emit, "xNome"),
            "documento": _formatar_documento(_texto(emit, "CNPJ") or _texto(emit, "CPF")),
        },
        "destinatario": {
            "nome": _texto(dest, "xNome"),
            "documento": _formatar_documento(_texto(dest, "CNPJ") or _texto(dest, "CPF")),
        },
        "produtos": produtos,
        "totais": {"nota": _moeda(_texto(total, "vNF"))},
    }


def _garantir_xml_local(documento, caminho_pdf):
    xml_path = getattr(documento, "xml_path", None)
    if xml_path and os.path.exists(xml_path):
        return xml_path

    chave_acesso = getattr(documento, "chave_acesso", "")
    if not chave_acesso:
        raise FileNotFoundError("XML completo nao encontrado para gerar DANFE.")

    try:
        from app.fiscal_drive_storage import MIME_XML, baixar_arquivo_fiscal_drive
    except Exception as exc:
        raise FileNotFoundError("XML completo nao encontrado localmente e o Drive fiscal nao esta disponivel.") from exc

    arquivo_drive = baixar_arquivo_fiscal_drive(f"{chave_acesso}.xml", "FISCAL_XML_DIR", MIME_XML)
    if not arquivo_drive:
        raise FileNotFoundError("XML completo nao encontrado localmente nem na pasta XMLs do Drive.")

    destino = xml_path or os.path.join(os.path.dirname(caminho_pdf), f"{chave_acesso}.xml")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as arquivo:
        arquivo.write(arquivo_drive.read())

    documento.xml_path = destino
    return destino


def gerar_danfe_pdf_xml(documento, caminho):
    if Danfe is None:
        raise RuntimeError("A biblioteca BrazilFiscalReport nao esta instalada para gerar DANFE profissional.")

    xml_path = _garantir_xml_local(documento, caminho)
    with open(xml_path, "rb") as arquivo:
        xml_content = arquivo.read().decode("utf-8", errors="replace")

    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    danfe = Danfe(xml=xml_content)
    resultado = danfe.output(caminho)

    if not os.path.exists(caminho) and isinstance(resultado, (bytes, bytearray)):
        with open(caminho, "wb") as arquivo:
            arquivo.write(resultado)

    if not os.path.exists(caminho) or os.path.getsize(caminho) == 0:
        raise RuntimeError("A biblioteca fiscal nao retornou um DANFE PDF valido.")

    if has_app_context():
        current_app.logger.warning(
            "[fiscal_danfe] DANFE profissional gerado com BrazilFiscalReport. NF-e: %s. Arquivo: %s",
            getattr(documento, "chave_acesso", ""),
            os.path.basename(caminho),
        )
    return caminho


def aplicar_gerador_danfe_completo(app):
    from app.services import fiscal_service

    if getattr(fiscal_service, "_gerador_danfe_completo_aplicado", False):
        return

    def gerar_danfe_pdf_profissional(documento):
        caminho = fiscal_service._caminho_danfe(documento.chave_acesso)
        return gerar_danfe_pdf_xml(documento, caminho)

    fiscal_service.gerar_danfe_pdf = gerar_danfe_pdf_profissional
    fiscal_service._gerador_danfe_completo_aplicado = True
    app.logger.warning("[fiscal_danfe] Gerador profissional BrazilFiscalReport configurado.")
