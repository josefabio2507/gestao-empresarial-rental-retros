import os
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.financeiro_contas_pagar_service import calcular_saldo_titulo
from app.services.financeiro_relatorios_service import moeda
from app.utils.datas import agora_brasil


COR_AZUL = colors.HexColor("#082c52")
COR_AZUL_CLARO = colors.HexColor("#eaf2f8")
COR_AMARELO = colors.HexColor("#f4b400")
COR_CINZA = colors.HexColor("#f5f7fa")
COR_TEXTO = colors.HexColor("#17324d")


def _data_formatada(valor):
    if not valor:
        return "-"
    if hasattr(valor, "strftime"):
        return valor.strftime("%d/%m/%Y")
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(valor)


def _periodo(filtros):
    inicio = filtros.get("vencimento_inicio") or filtros.get("data_inicio")
    fim = filtros.get("vencimento_fim") or filtros.get("data_fim")
    if inicio or fim:
        return f"{_data_formatada(inicio) if inicio else '-'} a {_data_formatada(fim) if fim else '-'}"
    return "Todos os vencimentos"


def _texto(valor):
    return escape(str(valor or "-"))


def _rodape(canvas, doc):
    canvas.saveState()
    largura, _ = A4
    canvas.setStrokeColor(COR_AMARELO)
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, 17 * mm, largura - doc.rightMargin, 17 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#68788a"))
    canvas.drawString(doc.leftMargin, 11 * mm, "Rental Retros | Financeiro | Uso interno")
    canvas.drawRightString(largura - doc.rightMargin, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf_titulos(titulos, filtros):
    """Gera o relatorio de titulos com identidade visual reutilizavel no Financeiro."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=23 * mm,
        title="Relatório de Títulos a Pagar",
        author="Rental Retros",
    )
    styles = getSampleStyleSheet()
    texto = ParagraphStyle(
        "RelatorioTexto",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=COR_TEXTO,
    )
    texto_direita = ParagraphStyle(
        "RelatorioTextoDireita",
        parent=texto,
        alignment=TA_RIGHT,
    )
    cabecalho = ParagraphStyle(
        "RelatorioCabecalho",
        parent=texto,
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=8.5,
        textColor=colors.white,
    )
    titulo = ParagraphStyle(
        "RelatorioTitulo",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=22,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    subtitulo = ParagraphStyle(
        "RelatorioSubtitulo",
        parent=texto,
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#d8e6f3"),
    )
    destaque = ParagraphStyle(
        "RelatorioDestaque",
        parent=texto,
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=COR_TEXTO,
    )
    elementos = []

    caminho_logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "img", "logo-rental-retros.png")
    logo = Image(caminho_logo, width=83, height=56)
    bloco_titulo = [
        Paragraph("FINANCEIRO | CONTAS A PAGAR", subtitulo),
        Spacer(1, 3),
        Paragraph("Relatório de Títulos a Pagar", titulo),
        Spacer(1, 2),
        Paragraph("Pagamentos programados por período", subtitulo),
    ]
    faixa = Table([[bloco_titulo, logo]], colWidths=[doc.width - 92, 92], rowHeights=[64])
    faixa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_AZUL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (1, 0), (1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elementos.append(faixa)
    elementos.append(Spacer(1, 10))

    periodo = _periodo(filtros)
    gerado_em = agora_brasil().strftime("%d/%m/%Y %H:%M")
    resumo = Table([
        [Paragraph("Período selecionado", destaque), Paragraph("Gerado em", destaque), Paragraph("Títulos", destaque)],
        [Paragraph(_texto(periodo), texto), Paragraph(gerado_em, texto), Paragraph(str(len(titulos)), texto_direita)],
    ], colWidths=[doc.width * 0.48, doc.width * 0.30, doc.width * 0.22])
    resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_CINZA),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e2ec")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#d9e2ec")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
    ]))
    elementos.append(resumo)
    elementos.append(Spacer(1, 14))

    elementos.append(Paragraph("Títulos previstos para pagamento", ParagraphStyle(
        "Secao",
        parent=destaque,
        fontSize=11,
        leading=13,
        textColor=COR_AZUL,
    )))
    elementos.append(Spacer(1, 6))

    colunas = ["Data prevista", "Fornecedor", "ID", "Descrição", "Documento", "Forma de pagamento", "Valor"]
    tabela = [[Paragraph(_texto(coluna), cabecalho) for coluna in colunas]]
    for titulo_item in titulos:
        tabela.append([
            Paragraph(_data_formatada(titulo_item.data_vencimento), texto),
            Paragraph(_texto(titulo_item.fornecedor_nome_snapshot), texto),
            Paragraph(str(titulo_item.id), texto_direita),
            Paragraph(_texto(titulo_item.descricao), texto),
            Paragraph(_texto(titulo_item.numero_documento), texto),
            Paragraph(_texto(titulo_item.forma_pagamento), texto),
            Paragraph(moeda(titulo_item.valor_original), texto_direita),
        ])

    if not titulos:
        tabela.append([Paragraph("Nenhum título encontrado para os filtros informados.", texto)] + [""] * (len(colunas) - 1))

    larguras = [49, 101, 28, 133, 58, 75, 57]
    tabela_pdf = Table(tabela, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    estilo_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d9e2ec")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_CINZA]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("ALIGN", (6, 1), (6, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if not titulos:
        estilo_tabela.extend([
            ("SPAN", (0, 1), (-1, 1)),
            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
        ])
    tabela_pdf.setStyle(TableStyle(estilo_tabela))
    elementos.append(tabela_pdf)
    elementos.append(Spacer(1, 12))

    total_original = sum((titulo_item.valor_original or 0 for titulo_item in titulos), 0)
    total_pago = sum((titulo_item.valor_pago or 0 for titulo_item in titulos), 0)
    saldo_aberto = sum((calcular_saldo_titulo(titulo_item) or 0 for titulo_item in titulos), 0)
    totais = Table([
        [Paragraph("Subtotal dos títulos", destaque), Paragraph(moeda(total_original), texto_direita)],
        [Paragraph("Total pago", destaque), Paragraph(moeda(total_pago), texto_direita)],
        [Paragraph("Saldo em aberto", destaque), Paragraph(moeda(saldo_aberto), texto_direita)],
    ], colWidths=[doc.width - 90, 90], hAlign="RIGHT")
    totais.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.2, COR_AMARELO),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#d9e2ec")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elementos.append(totais)
    elementos.append(Spacer(1, 6))
    elementos.append(Paragraph(
        f"Relatório gerado em {gerado_em}. Valores apresentados em reais.",
        ParagraphStyle("Nota", parent=texto, fontSize=7, textColor=colors.HexColor("#68788a")),
    ))

    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer


def nome_arquivo_titulos_pdf():
    return f"relatorio_titulos_a_pagar_{agora_brasil().strftime('%Y%m%d_%H%M%S')}.pdf"
