import os
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.utils.datas import agora_brasil

AZUL = colors.HexColor("#082c52")
AMARELO = colors.HexColor("#f4b400")
CINZA = colors.HexColor("#f5f7fa")
TEXTO = colors.HexColor("#17324d")
BORDA = colors.HexColor("#d9e2ec")


def _moeda(valor):
    numero = float(valor or 0)
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _numero(valor, casas=2):
    if valor is None:
        return "-"
    return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data(valor):
    return valor.strftime("%d/%m/%Y") if valor else "-"


def _periodo(inicio, fim):
    if not inicio and not fim:
        return "Todo o período"
    return f"{_data(inicio)} a {_data(fim)}"


def _p(valor, estilo):
    return Paragraph(escape(str(valor if valor not in (None, "") else "-")), estilo)


def _estilos():
    base = getSampleStyleSheet()
    texto = ParagraphStyle("TextoCC", parent=base["Normal"], fontName="Helvetica", fontSize=7.2, leading=8.7, textColor=TEXTO)
    return {
        "texto": texto,
        "direita": ParagraphStyle("DireitaCC", parent=texto, alignment=TA_RIGHT),
        "cabecalho": ParagraphStyle("CabecalhoCC", parent=texto, fontName="Helvetica-Bold", fontSize=7, textColor=colors.white),
        "titulo": ParagraphStyle("TituloCC", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=colors.white, alignment=TA_LEFT),
        "subtitulo": ParagraphStyle("SubtituloCC", parent=texto, fontSize=8.3, textColor=colors.HexColor("#d8e6f3")),
        "secao": ParagraphStyle("SecaoCC", parent=texto, fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=AZUL),
        "destaque": ParagraphStyle("DestaqueCC", parent=texto, fontName="Helvetica-Bold", fontSize=8.2),
    }


def _rodape(canvas, doc):
    canvas.saveState()
    largura = doc.pagesize[0]
    canvas.setStrokeColor(AMARELO)
    canvas.line(doc.leftMargin, 17 * mm, largura - doc.rightMargin, 17 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#68788a"))
    canvas.drawString(doc.leftMargin, 11 * mm, "Rental Retros | Operação | Uso interno")
    canvas.drawRightString(largura - doc.rightMargin, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _faixa(doc, titulo, descricao, estilos):
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "img", "logo-rental-retros.png")
    bloco = [_p("OPERAÇÃO | CENTRAL DE CUSTOS", estilos["subtitulo"]), Spacer(1, 3), _p(titulo, estilos["titulo"]), Spacer(1, 2), _p(descricao, estilos["subtitulo"])]
    faixa = Table([[bloco, Image(logo_path, width=83, height=56)]], colWidths=[doc.width - 92, 92], rowHeights=[64])
    faixa.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AZUL), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 14), ("RIGHTPADDING", (1, 0), (1, 0), 10), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    return faixa


def _tabela(dados, larguras, estilos, alinhadas=()):
    tabela = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    regras = [("BACKGROUND", (0, 0), (-1, 0), AZUL), ("GRID", (0, 0), (-1, -1), .35, BORDA), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA]), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    for coluna in alinhadas:
        regras.append(("ALIGN", (coluna, 1), (coluna, -1), "RIGHT"))
    tabela.setStyle(TableStyle(regras))
    return tabela


def gerar_pdf_descritivo(dados, inicio=None, fim=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=13*mm, bottomMargin=23*mm, title="Relatório descritivo da Central de Custos", author="Rental Retros")
    e = _estilos()
    veiculo = dados["veiculo"]
    elementos = [_faixa(doc, "Relatório descritivo de custos", f"{veiculo.identificacao} - {veiculo.descricao}", e), Spacer(1, 10)]
    resumo = [[_p("Período", e["cabecalho"]), _p("Centro de custo", e["cabecalho"]), _p("Total geral", e["cabecalho"])], [_p(_periodo(inicio, fim), e["texto"]), _p(veiculo.centro_custo, e["texto"]), _p(_moeda(dados["total_geral"]), e["direita"])]]
    elementos += [_tabela(resumo, [doc.width*.34, doc.width*.43, doc.width*.23], e, (2,)), Spacer(1, 10)]
    ind = dados["indicadores"]
    metricas = [[_p(ind["rotulo_uso"], e["cabecalho"]), _p("Litros abastecidos", e["cabecalho"]), _p(ind["rotulo_consumo"], e["cabecalho"]), _p(ind["rotulo_custo"], e["cabecalho"])], [_p(f'{_numero(ind["uso_periodo"])} {ind["unidade_uso"]}', e["direita"]), _p(_numero(ind["litros"], 3), e["direita"]), _p(f'{_numero(ind["consumo_por_litro"])} {ind["unidade_uso"]}/l', e["direita"]), _p(f'{_moeda(ind["custo_por_unidade"])} / {ind["unidade_uso"]}' if ind["custo_por_unidade"] is not None else "-", e["direita"])]]
    elementos += [_tabela(metricas, [doc.width/4]*4, e, (0,1,2,3)), Spacer(1, 12)]
    for indice, grupo in enumerate(dados["grupos"].values()):
        if indice:
            elementos.append(Spacer(1, 10))
        elementos += [_p(f'{grupo["titulo"]} · {_moeda(grupo["total"])}', e["secao"]), Spacer(1, 5)]
        linhas = [[_p(x, e["cabecalho"]) for x in ("Data", "Descrição", "Documento/Responsável", "Valor")]]
        for linha in grupo["linhas"]:
            linhas.append([_p(_data(linha["data"]), e["texto"]), _p(linha["descricao"], e["texto"]), _p(linha.get("documento", linha.get("responsavel", "-")), e["texto"]), _p(_moeda(linha["valor"]), e["direita"])])
        if not grupo["linhas"]:
            linhas.append([_p(grupo["mensagem_vazio"], e["texto"]), "", "", ""])
        elementos.append(_tabela(linhas, [58, 205, 152, 86], e, (3,)))
    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer


def gerar_pdf_consolidado(dados, inicio=None, fim=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=23*mm, title="Relatório consolidado da Central de Custos", author="Rental Retros")
    e = _estilos()
    elementos = [_faixa(doc, "Relatório consolidado de custos", "Todos os veículos e equipamentos ativos", e), Spacer(1, 10), _p(f"Período selecionado: {_periodo(inicio, fim)}", e["destaque"]), Spacer(1, 8)]
    colunas = ("Veículo/equipamento", "Abastecimento", "Km/horas", "Consumo", "Custo/km ou h", "Manutenção", "Multas", "Impostos e taxas", "Total")
    tabela = [[_p(x, e["cabecalho"]) for x in colunas]]
    for linha in dados["linhas"]:
        ind = linha["indicadores"]
        tabela.append([_p(f'{linha["veiculo"].identificacao} - {linha["veiculo"].descricao}', e["texto"]), _p(_moeda(linha["abastecimento"]), e["direita"]), _p(f'{_numero(ind["uso_periodo"])} {ind["unidade_uso"]}', e["direita"]), _p(f'{_numero(ind["consumo_por_litro"])} {ind["unidade_uso"]}/l', e["direita"]), _p(_moeda(ind["custo_por_unidade"]) if ind["custo_por_unidade"] is not None else "-", e["direita"]), _p(_moeda(linha["manutencao"]), e["direita"]), _p(_moeda(linha["multas"]), e["direita"]), _p(_moeda(linha["impostos_taxas"]), e["direita"]), _p(_moeda(linha["total_geral"]), e["direita"])])
    totais = dados["totais"]
    tabela.append([_p("TOTAIS", e["destaque"]), _p(_moeda(totais["abastecimento"]), e["direita"]), "", "", "", _p(_moeda(totais["manutencao"]), e["direita"]), _p(_moeda(totais["multas"]), e["direita"]), _p(_moeda(totais["impostos_taxas"]), e["direita"]), _p(_moeda(dados["total_geral"]), e["direita"])])
    elementos.append(_tabela(tabela, [150, 75, 62, 68, 66, 75, 68, 83, 75], e, tuple(range(1, 9))))
    elementos += [Spacer(1, 12), _p(f'Valor global do relatório: {_moeda(dados["total_geral"])}', e["secao"]), Spacer(1, 4), _p(f'Gerado em {agora_brasil().strftime("%d/%m/%Y %H:%M")}. Km ou horas calculados entre a menor e a maior leitura de abastecimento do período.', e["texto"])]
    doc.build(elementos, onFirstPage=_rodape, onLaterPages=_rodape)
    buffer.seek(0)
    return buffer


def nome_pdf(prefixo):
    return f"{prefixo}_{agora_brasil().strftime('%Y%m%d_%H%M%S')}.pdf"
