import os
import textwrap
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 24
LINE_HEIGHT = 9


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


def _quantidade(valor):
    numero = _decimal(valor)
    return f"{numero:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")


def _formatar_chave(chave):
    chave = "".join(ch for ch in str(chave or "") if ch.isdigit())
    return " ".join(chave[i:i + 4] for i in range(0, len(chave), 4))


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


def _endereco(pessoa):
    ender = _filho(pessoa, "enderEmit") or _filho(pessoa, "enderDest")
    if ender is None:
        return ""
    partes = [
        _texto(ender, "xLgr"),
        _texto(ender, "nro"),
        _texto(ender, "xCpl"),
        _texto(ender, "xBairro"),
        _texto(ender, "xMun"),
        _texto(ender, "UF"),
        _texto(ender, "CEP"),
    ]
    return " - ".join(parte for parte in partes if parte)


def _dados_pessoa(pessoa):
    return {
        "nome": _texto(pessoa, "xNome"),
        "documento": _formatar_documento(_texto(pessoa, "CNPJ") or _texto(pessoa, "CPF")),
        "ie": _texto(pessoa, "IE"),
        "fone": _texto(_filho(pessoa, "enderEmit") or _filho(pessoa, "enderDest"), "fone"),
        "endereco": _endereco(pessoa),
    }


def _dados_produto(det):
    prod = _filho(det, "prod")
    imposto = _filho(det, "imposto")
    return {
        "codigo": _texto(prod, "cProd"),
        "descricao": _texto(prod, "xProd"),
        "ncm": _texto(prod, "NCM"),
        "cfop": _texto(prod, "CFOP"),
        "unidade": _texto(prod, "uCom"),
        "quantidade": _quantidade(_texto(prod, "qCom")),
        "valor_unitario": _moeda(_texto(prod, "vUnCom")),
        "valor_total": _moeda(_texto(prod, "vProd")),
        "icms": _moeda(_texto(imposto, "vICMS")),
        "ipi": _moeda(_texto(imposto, "vIPI")),
        "aliq_icms": _quantidade(_texto(imposto, "pICMS")),
        "aliq_ipi": _quantidade(_texto(imposto, "pIPI")),
    }


def extrair_dados_danfe(xml_path):
    raiz = ElementTree.parse(xml_path).getroot()
    inf_nfe = _descendente(raiz, "infNFe")
    ide = _filho(inf_nfe, "ide")
    emit = _filho(inf_nfe, "emit")
    dest = _filho(inf_nfe, "dest")
    total = _descendente(inf_nfe, "ICMSTot")
    transp = _filho(inf_nfe, "transp")
    cobr = _filho(inf_nfe, "cobr")
    inf_prot = _descendente(raiz, "infProt")
    inf_adic = _filho(inf_nfe, "infAdic")

    chave = (inf_nfe.attrib.get("Id") or "").replace("NFe", "") if inf_nfe is not None else ""
    if not chave:
        chave = _texto(inf_prot, "chNFe")

    produtos = [_dados_produto(det) for det in raiz.iter() if _tag(det) == "det"]
    volumes = []
    if transp is not None:
        for vol in transp.iter():
            if _tag(vol) == "vol":
                volumes.append(
                    {
                        "qVol": _texto(vol, "qVol"),
                        "esp": _texto(vol, "esp"),
                        "marca": _texto(vol, "marca"),
                        "pesoL": _texto(vol, "pesoL"),
                        "pesoB": _texto(vol, "pesoB"),
                    }
                )

    duplicatas = []
    if cobr is not None:
        for dup in cobr.iter():
            if _tag(dup) == "dup":
                duplicatas.append(
                    {
                        "numero": _texto(dup, "nDup"),
                        "vencimento": _data_br(_texto(dup, "dVenc")),
                        "valor": _moeda(_texto(dup, "vDup")),
                    }
                )

    return {
        "chave": chave,
        "natureza": _texto(ide, "natOp"),
        "numero": _texto(ide, "nNF"),
        "serie": _texto(ide, "serie"),
        "modelo": _texto(ide, "mod"),
        "emissao": _data_br(_texto(ide, "dhEmi") or _texto(ide, "dEmi")),
        "saida": _data_br(_texto(ide, "dhSaiEnt") or _texto(ide, "dSaiEnt")),
        "tipo_nf": "SAIDA" if _texto(ide, "tpNF") == "1" else "ENTRADA",
        "protocolo": _texto(inf_prot, "nProt"),
        "data_autorizacao": _data_br(_texto(inf_prot, "dhRecbto")),
        "emitente": _dados_pessoa(emit),
        "destinatario": _dados_pessoa(dest),
        "produtos": produtos,
        "totais": {
            "base_icms": _moeda(_texto(total, "vBC")),
            "valor_icms": _moeda(_texto(total, "vICMS")),
            "base_st": _moeda(_texto(total, "vBCST")),
            "valor_st": _moeda(_texto(total, "vST")),
            "produtos": _moeda(_texto(total, "vProd")),
            "frete": _moeda(_texto(total, "vFrete")),
            "seguro": _moeda(_texto(total, "vSeg")),
            "desconto": _moeda(_texto(total, "vDesc")),
            "ipi": _moeda(_texto(total, "vIPI")),
            "nota": _moeda(_texto(total, "vNF")),
        },
        "transportadora": {
            "modalidade": _texto(transp, "modFrete"),
            "nome": _texto(_filho(transp, "transporta"), "xNome"),
            "documento": _formatar_documento(_texto(_filho(transp, "transporta"), "CNPJ") or _texto(_filho(transp, "transporta"), "CPF")),
            "placa": _texto(_filho(transp, "veicTransp"), "placa"),
            "uf": _texto(_filho(transp, "veicTransp"), "UF"),
            "volumes": volumes,
        },
        "duplicatas": duplicatas,
        "info_adicional": "\n".join(
            item for item in [_texto(inf_adic, "infCpl"), _texto(inf_adic, "infAdFisco")] if item
        ),
    }


def _texto_linhas(texto, largura=70, max_linhas=None):
    linhas = []
    for bloco in str(texto or "").splitlines() or [""]:
        linhas.extend(textwrap.wrap(bloco, width=largura) or [""])
    return linhas[:max_linhas] if max_linhas else linhas


def _box(pdf, x, y, w, h, titulo=None):
    pdf.setStrokeColor(colors.black)
    pdf.rect(x, y, w, h, stroke=1, fill=0)
    if titulo:
        pdf.setFont("Helvetica-Bold", 6)
        pdf.drawString(x + 3, y + h - 8, titulo[:70])


def _draw_campo(pdf, x, y, w, h, titulo, valor, fonte=8, linhas=1):
    _box(pdf, x, y, w, h, titulo)
    pdf.setFont("Helvetica", fonte)
    conteudo = _texto_linhas(valor, max(12, int(w / 4.2)), max_linhas=linhas)
    cursor = y + h - 18
    for linha in conteudo:
        pdf.drawString(x + 3, cursor, linha[:120])
        cursor -= fonte + 2


def _nova_pagina(pdf, dados, pagina):
    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, PAGE_HEIGHT - 20, f"DANFE - NF-e {dados['numero']} Serie {dados['serie']} - Continuacao")
    pdf.setFont("Helvetica", 7)
    pdf.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 20, f"Pagina {pagina}")
    return PAGE_HEIGHT - 42


def _desenhar_cabecalho(pdf, dados):
    topo = PAGE_HEIGHT - MARGIN
    pdf.setTitle(f"DANFE {dados['numero']}")
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(PAGE_WIDTH / 2, topo - 12, "DANFE")
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(PAGE_WIDTH / 2, topo - 25, "Documento Auxiliar da Nota Fiscal Eletronica")

    _draw_campo(pdf, MARGIN, topo - 72, 220, 48, "IDENTIFICACAO DO EMITENTE", f"{dados['emitente']['nome']}\n{dados['emitente']['endereco']}", 7, 3)
    _draw_campo(pdf, MARGIN + 224, topo - 72, 88, 48, "TIPO", dados["tipo_nf"], 10, 1)
    _draw_campo(pdf, MARGIN + 316, topo - 72, 90, 48, "NF-e", f"No. {dados['numero']}\nSerie {dados['serie']}", 9, 2)
    _draw_campo(pdf, MARGIN + 410, topo - 72, 137, 48, "CHAVE DE ACESSO", _formatar_chave(dados["chave"]), 7, 3)

    y = topo - 98
    _draw_campo(pdf, MARGIN, y, 270, 24, "NATUREZA DA OPERACAO", dados["natureza"], 8, 1)
    _draw_campo(pdf, MARGIN + 274, y, 273, 24, "PROTOCOLO DE AUTORIZACAO", f"{dados['protocolo']} {dados['data_autorizacao']}", 8, 1)

    y -= 26
    _draw_campo(pdf, MARGIN, y, 165, 24, "CNPJ", dados["emitente"]["documento"], 8, 1)
    _draw_campo(pdf, MARGIN + 169, y, 150, 24, "INSCRICAO ESTADUAL", dados["emitente"]["ie"], 8, 1)
    _draw_campo(pdf, MARGIN + 323, y, 109, 24, "DATA/HORA EMISSAO", dados["emissao"], 8, 1)
    _draw_campo(pdf, MARGIN + 436, y, 111, 24, "DATA/HORA SAIDA", dados["saida"], 8, 1)

    return y - 34


def _desenhar_destinatario(pdf, dados, y):
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, y + 20, "DESTINATARIO / REMETENTE")
    _draw_campo(pdf, MARGIN, y - 4, 315, 24, "NOME / RAZAO SOCIAL", dados["destinatario"]["nome"], 8, 1)
    _draw_campo(pdf, MARGIN + 319, y - 4, 110, 24, "CNPJ / CPF", dados["destinatario"]["documento"], 8, 1)
    _draw_campo(pdf, MARGIN + 433, y - 4, 114, 24, "INSCRICAO ESTADUAL", dados["destinatario"]["ie"], 8, 1)
    _draw_campo(pdf, MARGIN, y - 30, 547, 24, "ENDERECO", dados["destinatario"]["endereco"], 8, 1)
    return y - 42


def _desenhar_totais(pdf, dados, y):
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, y + 20, "CALCULO DO IMPOSTO")
    campos = [
        ("BASE ICMS", "base_icms"), ("VALOR ICMS", "valor_icms"), ("BASE ICMS ST", "base_st"),
        ("VALOR ST", "valor_st"), ("VALOR PRODUTOS", "produtos"), ("FRETE", "frete"),
        ("SEGURO", "seguro"), ("DESCONTO", "desconto"), ("IPI", "ipi"), ("VALOR DA NOTA", "nota"),
    ]
    largura = 54.7
    for indice, (titulo, chave) in enumerate(campos):
        _draw_campo(pdf, MARGIN + indice * largura, y - 4, largura, 24, titulo, dados["totais"][chave], 7, 1)
    return y - 34


def _desenhar_transportes(pdf, dados, y):
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, y + 20, "TRANSPORTADOR / VOLUMES TRANSPORTADOS")
    transp = dados["transportadora"]
    volumes = transp["volumes"][0] if transp["volumes"] else {}
    _draw_campo(pdf, MARGIN, y - 4, 215, 24, "RAZAO SOCIAL", transp["nome"], 7, 1)
    _draw_campo(pdf, MARGIN + 219, y - 4, 70, 24, "FRETE", transp["modalidade"], 7, 1)
    _draw_campo(pdf, MARGIN + 293, y - 4, 105, 24, "CNPJ / CPF", transp["documento"], 7, 1)
    _draw_campo(pdf, MARGIN + 402, y - 4, 70, 24, "PLACA", transp["placa"], 7, 1)
    _draw_campo(pdf, MARGIN + 476, y - 4, 71, 24, "UF", transp["uf"], 7, 1)
    _draw_campo(pdf, MARGIN, y - 30, 80, 24, "QUANTIDADE", volumes.get("qVol", ""), 7, 1)
    _draw_campo(pdf, MARGIN + 84, y - 30, 105, 24, "ESPECIE", volumes.get("esp", ""), 7, 1)
    _draw_campo(pdf, MARGIN + 193, y - 30, 134, 24, "MARCA", volumes.get("marca", ""), 7, 1)
    _draw_campo(pdf, MARGIN + 331, y - 30, 105, 24, "PESO LIQUIDO", volumes.get("pesoL", ""), 7, 1)
    _draw_campo(pdf, MARGIN + 440, y - 30, 107, 24, "PESO BRUTO", volumes.get("pesoB", ""), 7, 1)
    return y - 62


def _desenhar_produtos(pdf, dados, y):
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, y + 20, "DADOS DOS PRODUTOS / SERVICOS")
    colunas = [
        ("COD", 34), ("DESCRICAO", 182), ("NCM", 45), ("CFOP", 34), ("UN", 24),
        ("QTD", 45), ("VLR UNIT", 52), ("VLR TOTAL", 54), ("ICMS", 38), ("IPI", 39),
    ]
    x = MARGIN
    pdf.setFont("Helvetica-Bold", 6)
    for titulo, largura in colunas:
        _box(pdf, x, y - 4, largura, 14)
        pdf.drawString(x + 2, y + 1, titulo)
        x += largura
    y -= 18

    pagina = 1
    for produto in dados["produtos"] or []:
        linhas_desc = _texto_linhas(produto["descricao"], 36, 2)
        altura = max(18, 8 + len(linhas_desc) * 8)
        if y - altura < 110:
            pagina += 1
            y = _nova_pagina(pdf, dados, pagina)
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(MARGIN, y + 10, "DADOS DOS PRODUTOS / SERVICOS - CONTINUACAO")
            y -= 12

        x = MARGIN
        valores = [
            produto["codigo"], "\n".join(linhas_desc), produto["ncm"], produto["cfop"], produto["unidade"],
            produto["quantidade"], produto["valor_unitario"], produto["valor_total"], produto["icms"], produto["ipi"],
        ]
        pdf.setFont("Helvetica", 6)
        for valor, (_, largura) in zip(valores, colunas):
            _box(pdf, x, y - altura, largura, altura)
            cursor = y - 8
            for linha in str(valor or "").splitlines()[:3]:
                pdf.drawString(x + 2, cursor, linha[:40])
                cursor -= 7
            x += largura
        y -= altura
    return y - 16


def _desenhar_duplicatas(pdf, dados, y):
    if not dados["duplicatas"]:
        return y
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, y + 20, "FATURA / DUPLICATAS")
    x = MARGIN
    for dup in dados["duplicatas"][:6]:
        _draw_campo(pdf, x, y - 4, 90, 24, dup["numero"] or "DUP", f"{dup['vencimento']}  R$ {dup['valor']}", 6, 1)
        x += 91
    return y - 34


def _desenhar_adicionais(pdf, dados, y):
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, y + 20, "DADOS ADICIONAIS")
    _box(pdf, MARGIN, y - 70, 547, 86, "INFORMACOES COMPLEMENTARES")
    pdf.setFont("Helvetica", 6)
    cursor = y + 5
    for linha in _texto_linhas(dados["info_adicional"], 130, 10):
        pdf.drawString(MARGIN + 4, cursor, linha[:150])
        cursor -= 7


def gerar_danfe_pdf_xml(documento, caminho):
    if not getattr(documento, "xml_path", None) or not os.path.exists(documento.xml_path):
        raise FileNotFoundError("XML completo nao encontrado para gerar DANFE completo.")

    dados = extrair_dados_danfe(documento.xml_path)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    pdf = canvas.Canvas(caminho, pagesize=A4)
    y = _desenhar_cabecalho(pdf, dados)
    y = _desenhar_destinatario(pdf, dados, y)
    y = _desenhar_totais(pdf, dados, y)
    y = _desenhar_transportes(pdf, dados, y)
    y = _desenhar_duplicatas(pdf, dados, y)
    y = _desenhar_produtos(pdf, dados, y)
    if y < 120:
        _nova_pagina(pdf, dados, 2)
        y = PAGE_HEIGHT - 60
    _desenhar_adicionais(pdf, dados, y)
    pdf.save()
    return caminho


def aplicar_gerador_danfe_completo(app):
    from app.services import fiscal_service

    if getattr(fiscal_service, "_gerador_danfe_completo_aplicado", False):
        return

    original_gerar_danfe = fiscal_service.gerar_danfe_pdf

    def gerar_danfe_pdf_completo(documento):
        caminho = fiscal_service._caminho_danfe(documento.chave_acesso)
        try:
            return gerar_danfe_pdf_xml(documento, caminho)
        except Exception as exc:
            current_app.logger.exception(
                "[fiscal_danfe] Falha ao gerar DANFE completo para NF-e %s: %s",
                getattr(documento, "chave_acesso", ""),
                exc,
            )
            return original_gerar_danfe(documento)

    fiscal_service.gerar_danfe_pdf = gerar_danfe_pdf_completo
    fiscal_service._gerador_danfe_completo_aplicado = True
    app.logger.warning("[fiscal_danfe] Gerador de DANFE completo a partir do XML configurado.")
