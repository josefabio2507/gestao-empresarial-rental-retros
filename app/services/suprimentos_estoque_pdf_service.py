import os
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
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


def _nome_relacionado(objeto, atributo):
    relacionado = getattr(objeto, atributo, None)
    return getattr(relacionado, "sigla", None) or getattr(relacionado, "nome", None) or "-"


def _filtros_descricao(filtros, categorias):
    partes = []
    descricao = filtros.get("descricao")
    categoria_id = filtros.get("categoria_id")
    if descricao:
        partes.append(f"Descrição/código: {descricao}")
    if categoria_id:
        categoria = next((item for item in categorias if str(item.id) == str(categoria_id)), None)
        partes.append(f"Categoria: {categoria.nome if categoria else categoria_id}")
    if filtros.get("abaixo_minimo"):
        partes.append("Somente abaixo do estoque mínimo")
    return " | ".join(partes) if partes else "Todos os materiais estocáveis"


def _rodape(canvas, doc):
    canvas.saveState()
    largura, _ = A4
    canvas.setStrokeColor(COR_AMARELO)
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, 17 * mm, largura - doc.rightMargin, 17 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#68788a"))
    canvas.drawString(doc.leftMargin, 11 * mm, "Rental Retros | Suprimentos | Uso interno")
    canvas.drawRightString(largura - doc.rightMargin, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf_estoque_materiais(itens, filtros, categorias):
    """Gera o relatório de estoque com o padrão visual corporativo da Rental Retros."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=23 * mm,
        title="Relatório de Estoque de Materiais",
        author="Rental Retros",
    )
    styles = getSampleStyleSheet()
    texto = ParagraphStyle(
        "EstoqueTexto",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=COR_TEXTO,
    )
    texto_direita = ParagraphStyle("EstoqueTextoDireita", parent=texto, alignment=TA_RIGHT)
    cabecalho = ParagraphStyle(
        "EstoqueCabecalho",
        parent=texto,
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=8.5,
        textColor=colors.white,
    )
    titulo = ParagraphStyle(
        "EstoqueTitulo",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=22,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    subtitulo = ParagraphStyle(
        "EstoqueSubtitulo",
        parent=texto,
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor("#d8e6f3"),
    )
    destaque = ParagraphStyle(
        "EstoqueDestaque",
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
        Paragraph("SUPRIMENTOS | ESTOQUE", subtitulo),
        Spacer(1, 3),
        Paragraph("Relatório de Estoque de Materiais", titulo),
        Spacer(1, 2),
        Paragraph("Posição atual dos materiais estocáveis", subtitulo),
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
    abaixo_minimo = sum(
        1 for item in itens
        if item.estoque_minimo is not None and item.saldo_estoque < item.estoque_minimo
    )
    resumo = Table([
        [Paragraph("Filtros aplicados", destaque), Paragraph("Gerado em", destaque), Paragraph("Materiais", destaque), Paragraph("Abaixo do mínimo", destaque)],
        [Paragraph(_texto(_filtros_descricao(filtros, categorias)), texto), Paragraph(gerado_em, texto), Paragraph(str(len(itens)), texto_direita), Paragraph(str(abaixo_minimo), texto_direita)],
    ], colWidths=[doc.width * 0.43, doc.width * 0.25, doc.width * 0.14, doc.width * 0.18])
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

    secao = ParagraphStyle("EstoqueSecao", parent=destaque, fontSize=11, leading=13, textColor=COR_AZUL)
    elementos.extend([Paragraph("Posição dos materiais", secao), Spacer(1, 6)])

    colunas = ["Código", "Material", "Categoria", "Unidade", "Saldo", "Estoque mínimo", "Status"]
    dados = [[Paragraph(coluna, cabecalho) for coluna in colunas]]
    for item in itens:
        item_abaixo_minimo = item.estoque_minimo is not None and item.saldo_estoque < item.estoque_minimo
        dados.append([
            Paragraph(_texto(item.codigo_interno), texto),
            Paragraph(_texto(item.descricao), texto),
            Paragraph(_texto(_nome_relacionado(item, "categoria")), texto),
            Paragraph(_texto(_nome_relacionado(item, "unidade_medida")), texto),
            Paragraph(_decimal_brasil(item.saldo_estoque), texto_direita),
            Paragraph(_decimal_brasil(item.estoque_minimo), texto_direita),
            Paragraph("Abaixo do mínimo" if item_abaixo_minimo else "Normal", texto),
        ])
    if not itens:
        dados.append([Paragraph("Nenhum material encontrado para os filtros informados.", texto)] + [""] * 6)

    tabela = Table(dados, colWidths=[48, 133, 82, 48, 55, 67, 68], repeatRows=1, hAlign="LEFT")
    estilo_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, COR_BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_CINZA]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (4, 1), (5, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if not itens:
        estilo_tabela.extend([("SPAN", (0, 1), (-1, 1)), ("ALIGN", (0, 1), (-1, 1), "CENTER")])
    tabela.setStyle(TableStyle(estilo_tabela))
    elementos.extend([tabela, Spacer(1, 10)])
    elementos.append(Paragraph(
        f"Relatório gerado em {gerado_em}. Quantidades apresentadas conforme a unidade de cada material.",
        ParagraphStyle("EstoqueNota", parent=texto, fontSize=7, textColor=colors.HexColor("#68788a")),
    ))

    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer


def nome_arquivo_estoque_pdf():
    return f"relatorio_estoque_materiais_{agora_brasil().strftime('%Y%m%d_%H%M%S')}.pdf"
