import os
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.utils.datas import agora_brasil


COR_AZUL = colors.HexColor("#082c52")
COR_AMARELO = colors.HexColor("#f4b400")
COR_CINZA = colors.HexColor("#f5f7fa")
COR_TEXTO = colors.HexColor("#17324d")
COR_BORDA = colors.HexColor("#d9e2ec")


def _texto(valor):
    return escape(str(valor if valor not in (None, "") else "-"))


def _decimal_brasil(valor):
    if valor is None:
        return "-"
    return f"{valor:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _filtros_descricao(filtros, colaboradores, itens):
    partes = []
    colaborador_id = filtros.get("colaborador_id")
    item_id = filtros.get("item_id")
    tipo_material = filtros.get("tipo_material")

    if colaborador_id:
        colaborador = next((c for c in colaboradores if str(c.id) == str(colaborador_id)), None)
        partes.append(
            f"Colaborador: {colaborador.matricula} - {colaborador.nome}"
            if colaborador else f"Colaborador: {colaborador_id}"
        )
    if item_id:
        item = next((i for i in itens if str(i.id) == str(item_id)), None)
        partes.append(
            f"Item: {item.codigo_interno or '-'} - {item.descricao}"
            if item else f"Item: {item_id}"
        )
    if tipo_material:
        partes.append(f"Tipo: {tipo_material}")

    return " | ".join(partes) if partes else "Todas as entregas de EPIs e uniformes"


def _rodape(canvas, doc):
    canvas.saveState()
    largura, _ = landscape(A4)
    canvas.setStrokeColor(COR_AMARELO)
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, 17 * mm, largura - doc.rightMargin, 17 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#68788a"))
    canvas.drawString(doc.leftMargin, 11 * mm, "Rental Retros | Segurança do Trabalho | Uso interno")
    canvas.drawRightString(largura - doc.rightMargin, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf_entregas_epi(entregas, filtros, colaboradores, itens):
    """Gera o relatório de EPIs e uniformes no padrão visual corporativo da Rental Retros."""
    buffer = BytesIO()
    pagina = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagina,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=11 * mm,
        bottomMargin=23 * mm,
        title="Relatório de EPIs e Uniformes",
        author="Rental Retros",
    )
    styles = getSampleStyleSheet()
    texto = ParagraphStyle(
        "EpiTexto",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8.2,
        textColor=COR_TEXTO,
    )
    texto_direita = ParagraphStyle("EpiTextoDireita", parent=texto, alignment=TA_RIGHT)
    cabecalho = ParagraphStyle(
        "EpiCabecalho",
        parent=texto,
        fontName="Helvetica-Bold",
        fontSize=6.7,
        leading=8,
        textColor=colors.white,
    )
    titulo = ParagraphStyle(
        "EpiTitulo",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=22,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    subtitulo = ParagraphStyle(
        "EpiSubtitulo",
        parent=texto,
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#d8e6f3"),
    )
    destaque = ParagraphStyle(
        "EpiDestaque",
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
        Paragraph("SEGURANÇA DO TRABALHO | EPIs", subtitulo),
        Spacer(1, 3),
        Paragraph("Relatório de EPIs e Uniformes", titulo),
        Spacer(1, 2),
        Paragraph("Histórico de entregas registradas aos colaboradores", subtitulo),
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
    elementos.extend([faixa, Spacer(1, 10)])

    gerado_em = agora_brasil().strftime("%d/%m/%Y %H:%M")
    ativas = sum(1 for entrega in entregas if entrega.status == "Ativa")
    canceladas = len(entregas) - ativas
    resumo = Table([
        [Paragraph("Filtros aplicados", destaque), Paragraph("Gerado em", destaque), Paragraph("Entregas", destaque), Paragraph("Ativas", destaque), Paragraph("Canceladas", destaque)],
        [Paragraph(_texto(_filtros_descricao(filtros, colaboradores, itens)), texto), Paragraph(gerado_em, texto), Paragraph(str(len(entregas)), texto_direita), Paragraph(str(ativas), texto_direita), Paragraph(str(canceladas), texto_direita)],
    ], colWidths=[doc.width * 0.47, doc.width * 0.20, doc.width * 0.11, doc.width * 0.10, doc.width * 0.12])
    resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_CINZA),
        ("BOX", (0, 0), (-1, -1), 0.5, COR_BORDA),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, COR_BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    elementos.extend([resumo, Spacer(1, 14)])

    secao = ParagraphStyle("EpiSecao", parent=destaque, fontSize=11, leading=13, textColor=COR_AZUL)
    elementos.extend([Paragraph("Entregas registradas", secao), Spacer(1, 6)])

    colunas = ["Data", "Colaborador", "Item", "Tipo", "Qtd.", "Motivo", "Documento", "Status", "Entregue por"]
    dados = [[Paragraph(coluna, cabecalho) for coluna in colunas]]
    for entrega in entregas:
        unidade = getattr(getattr(entrega.item, "unidade_medida", None), "sigla", "") or ""
        documento = getattr(getattr(entrega, "movimentacao_estoque", None), "documento_numero", None)
        entregue_por = getattr(getattr(entrega, "entregue_por", None), "nome", None)
        dados.append([
            Paragraph(entrega.data_entrega.strftime("%d/%m/%Y"), texto),
            Paragraph(_texto(f"{entrega.colaborador.matricula} - {entrega.colaborador.nome}"), texto),
            Paragraph(_texto(f"{entrega.item.codigo_interno or '-'} - {entrega.item.descricao}"), texto),
            Paragraph(_texto(entrega.tipo_material), texto),
            Paragraph(_texto(f"{_decimal_brasil(entrega.quantidade)} {unidade}".strip()), texto_direita),
            Paragraph(_texto(entrega.motivo_entrega), texto),
            Paragraph(_texto(documento), texto),
            Paragraph(_texto(entrega.status), texto),
            Paragraph(_texto(entregue_por), texto),
        ])
    if not entregas:
        dados.append([Paragraph("Nenhuma entrega encontrada para os filtros informados.", texto)] + [""] * 8)

    tabela = Table(
        dados,
        colWidths=[45, 126, 150, 48, 58, 82, 72, 56, 90],
        repeatRows=1,
        hAlign="LEFT",
    )
    estilo_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, COR_BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_CINZA]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if not entregas:
        estilo_tabela.extend([("SPAN", (0, 1), (-1, 1)), ("ALIGN", (0, 1), (-1, 1), "CENTER")])
    tabela.setStyle(TableStyle(estilo_tabela))
    elementos.extend([tabela, Spacer(1, 10)])
    elementos.append(Paragraph(
        f"Relatório gerado em {gerado_em}. Quantidades apresentadas conforme a unidade de medida de cada item.",
        ParagraphStyle("EpiNota", parent=texto, fontSize=7, textColor=colors.HexColor("#68788a")),
    ))

    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer


def nome_arquivo_entregas_epi_pdf():
    return f"relatorio_epis_uniformes_{agora_brasil().strftime('%Y%m%d_%H%M%S')}.pdf"
