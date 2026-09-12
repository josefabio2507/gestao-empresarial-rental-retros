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


def _moeda_brl(valor):
    if valor is None:
        return "-"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _filtros_descricao(filtros, itens, fornecedores):
    partes = []
    item_id = filtros.get("item_id")
    fornecedor_id = filtros.get("fornecedor_id")
    documento = filtros.get("documento")
    data_inicio = filtros.get("data_inicio")
    data_fim = filtros.get("data_fim")

    if item_id:
        item = next((registro for registro in itens if str(registro.id) == str(item_id)), None)
        partes.append(
            f"Item: {(item.codigo_interno or '-') + ' - ' + item.descricao if item else item_id}"
        )
    if fornecedor_id:
        fornecedor = next(
            (registro for registro in fornecedores if str(registro.id) == str(fornecedor_id)),
            None,
        )
        partes.append(
            f"Fornecedor: {fornecedor.razao_social if fornecedor else fornecedor_id}"
        )
    if documento:
        partes.append(f"Documento: {documento}")
    if data_inicio:
        partes.append(f"Data inicial: {data_inicio}")
    if data_fim:
        partes.append(f"Data final: {data_fim}")

    return " | ".join(partes) if partes else "Todas as movimentações"


def _rodape(canvas, doc):
    canvas.saveState()
    largura, _ = landscape(A4)
    canvas.setStrokeColor(COR_AMARELO)
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, 17 * mm, largura - doc.rightMargin, 17 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#68788a"))
    canvas.drawString(doc.leftMargin, 11 * mm, "Rental Retros | Suprimentos | Uso interno")
    canvas.drawRightString(largura - doc.rightMargin, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


def gerar_pdf_historico_estoque(movimentacoes, filtros, itens, fornecedores):
    """Gera o histórico de estoque seguindo o padrão visual corporativo da Rental Retros."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=11 * mm,
        leftMargin=11 * mm,
        topMargin=11 * mm,
        bottomMargin=23 * mm,
        title="Relatório do Histórico de Estoque",
        author="Rental Retros",
    )
    styles = getSampleStyleSheet()
    texto = ParagraphStyle(
        "HistoricoEstoqueTexto",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.2,
        leading=7.2,
        textColor=COR_TEXTO,
    )
    texto_direita = ParagraphStyle(
        "HistoricoEstoqueTextoDireita", parent=texto, alignment=TA_RIGHT
    )
    cabecalho = ParagraphStyle(
        "HistoricoEstoqueCabecalho",
        parent=texto,
        fontName="Helvetica-Bold",
        fontSize=6.1,
        leading=7,
        textColor=colors.white,
    )
    titulo = ParagraphStyle(
        "HistoricoEstoqueTitulo",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    subtitulo = ParagraphStyle(
        "HistoricoEstoqueSubtitulo",
        parent=texto,
        fontSize=8.2,
        leading=9.5,
        textColor=colors.HexColor("#d8e6f3"),
    )
    destaque = ParagraphStyle(
        "HistoricoEstoqueDestaque",
        parent=texto,
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=9.5,
        textColor=COR_TEXTO,
    )
    elementos = []

    caminho_logo = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "static",
        "img",
        "logo-rental-retros.png",
    )
    logo = Image(caminho_logo, width=83, height=56)
    bloco_titulo = [
        Paragraph("SUPRIMENTOS | ESTOQUE", subtitulo),
        Spacer(1, 3),
        Paragraph("Relatório do Histórico de Estoque", titulo),
        Spacer(1, 2),
        Paragraph("Movimentações conforme os filtros aplicados na tela", subtitulo),
    ]
    faixa = Table([[bloco_titulo, logo]], colWidths=[doc.width - 92, 92], rowHeights=[64])
    faixa.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COR_AZUL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 14),
                ("RIGHTPADDING", (1, 0), (1, 0), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    elementos.extend([faixa, Spacer(1, 10)])

    gerado_em = agora_brasil().strftime("%d/%m/%Y %H:%M")
    quantidade_entradas = sum(1 for mov in movimentacoes if mov.tipo == "Entrada")
    quantidade_saidas = sum(1 for mov in movimentacoes if mov.tipo == "Saida")
    resumo = Table(
        [
            [
                Paragraph("Filtros aplicados", destaque),
                Paragraph("Gerado em", destaque),
                Paragraph("Registros", destaque),
                Paragraph("Entradas", destaque),
                Paragraph("Saídas", destaque),
            ],
            [
                Paragraph(_texto(_filtros_descricao(filtros, itens, fornecedores)), texto),
                Paragraph(gerado_em, texto),
                Paragraph(str(len(movimentacoes)), texto_direita),
                Paragraph(str(quantidade_entradas), texto_direita),
                Paragraph(str(quantidade_saidas), texto_direita),
            ],
        ],
        colWidths=[doc.width * 0.48, doc.width * 0.20, doc.width * 0.10, doc.width * 0.11, doc.width * 0.11],
    )
    resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COR_CINZA),
                ("BOX", (0, 0), (-1, -1), 0.5, COR_BORDA),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, COR_BORDA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    elementos.extend([resumo, Spacer(1, 12)])

    secao = ParagraphStyle(
        "HistoricoEstoqueSecao",
        parent=destaque,
        fontSize=10.5,
        leading=12,
        textColor=COR_AZUL,
    )
    elementos.extend([Paragraph("Movimentações de estoque", secao), Spacer(1, 6)])

    colunas = [
        "Data", "Tipo", "Origem", "Item", "Documento", "OC", "Fornecedor",
        "Centro de custo", "Responsável", "Qtd.", "Valor unit.", "Total", "Status",
    ]
    dados = [[Paragraph(coluna, cabecalho) for coluna in colunas]]
    for mov in movimentacoes:
        ordem = mov.ordem_compra.numero if mov.ordem_compra else "-"
        fornecedor = mov.fornecedor.razao_social if mov.fornecedor else "-"
        centro_custo = mov.centro_custo.nome if mov.centro_custo else "-"
        responsavel = mov.responsavel.nome if mov.responsavel else "-"
        documento = " ".join(
            parte for parte in [mov.documento_tipo, mov.documento_numero] if parte
        ) or "-"
        dados.append(
            [
                Paragraph(mov.movimentado_em.strftime("%d/%m/%Y %H:%M"), texto),
                Paragraph(_texto(mov.tipo), texto),
                Paragraph(_texto(mov.origem), texto),
                Paragraph(_texto(f"{mov.item.codigo_interno or '-'} - {mov.item.descricao}"), texto),
                Paragraph(_texto(documento), texto),
                Paragraph(_texto(ordem), texto),
                Paragraph(_texto(fornecedor), texto),
                Paragraph(_texto(centro_custo), texto),
                Paragraph(_texto(responsavel), texto),
                Paragraph(_decimal_brasil(mov.quantidade), texto_direita),
                Paragraph(_moeda_brl(mov.valor_unitario), texto_direita),
                Paragraph(_moeda_brl(mov.valor_total_snapshot), texto_direita),
                Paragraph(_texto(mov.status), texto),
            ]
        )

    if not movimentacoes:
        dados.append(
            [Paragraph("Nenhuma movimentação encontrada para os filtros informados.", texto)]
            + [""] * 12
        )

    tabela = Table(
        dados,
        colWidths=[52, 38, 58, 90, 62, 45, 78, 75, 65, 38, 52, 52, 45],
        repeatRows=1,
        hAlign="LEFT",
    )
    estilo_tabela = [
        ("BACKGROUND", (0, 0), (-1, 0), COR_AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, COR_BORDA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_CINZA]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (9, 1), (11, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if not movimentacoes:
        estilo_tabela.extend(
            [("SPAN", (0, 1), (-1, 1)), ("ALIGN", (0, 1), (-1, 1), "CENTER")]
        )
    tabela.setStyle(TableStyle(estilo_tabela))
    elementos.extend([tabela, Spacer(1, 10)])
    elementos.append(
        Paragraph(
            f"Relatório gerado em {gerado_em}. Valores e quantidades reproduzem o histórico exibido conforme os filtros informados.",
            ParagraphStyle(
                "HistoricoEstoqueNota",
                parent=texto,
                fontSize=7,
                textColor=colors.HexColor("#68788a"),
            ),
        )
    )

    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer


def nome_arquivo_historico_estoque_pdf():
    return f"relatorio_historico_estoque_{agora_brasil().strftime('%Y%m%d_%H%M%S')}.pdf"
