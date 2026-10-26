import uuid

from flask import flash, redirect, render_template, request, url_for, send_file
from io import BytesIO
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.operacao.ordens_servico import ordens_servico_bp
from app.operacao.ordens_servico.cadastro_service import (
    OrdemServicoCadastroErro,
    criar_ordem_servico,
    editar_ordem_servico,
)
from app.operacao.ordens_servico.consulta_service import (
    OrdemServicoConsultaErro,
    buscar_ordem_por_id,
    consultar_ordens,
)
from app.operacao.ordens_servico.localizacao_service import (
    OPCOES,
    LocalizacaoErro,
    buscar_apontamento,
    consultar_apontamentos,
    criar_apontamento,
    editar_apontamento,
)
from app.operacao.ordens_servico.diarios_producao_service import (
    DiarioProducaoErro,
    buscar_registro,
    consultar_registros,
    criar_registro,
    editar_registro,
)
from app.operacao.ordens_servico.circulacao_service import (
    OPCOES_CORTE,
    OPCOES_MOTIVO_PARALISACAO,
    CirculacaoErro,
    buscar_circulacao,
    consultar_circulacoes,
    criar_circulacao,
    editar_circulacao,
)
from app.operacao.ordens_servico.intervencoes_service import CATEGORIAS, IntervencaoErro, buscar_intervencao, consultar_intervencoes, criar_intervencao, editar_intervencao
from app.operacao.ordens_servico.monitoramento_service import MonitoramentoErro, obter_monitoramento
from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.models import Equipe, Colaborador, OperacaoChefeBoletim, OperacaoControleLiberacao, OperacaoServicoCatalogo, OperacaoMaterialCatalogo, OperacaoApontamentoDiario, OperacaoDiarioLocalizacao, OperacaoOrdemServico
from datetime import date, time, timedelta
from app.extensions import db


DEPARTAMENTO = "operacao"
MODULO = "ordens_de_servico"


@ordens_servico_bp.route("/")
@login_required
@module_permission_required("operacao", "ordens_de_servico", "visualizar")
def index():
    erro_configuracao = None
    ordens = []
    resumo = {"total": 0, "ativas": 0, "concluidas": 0, "desativadas": 0}
    progresso_por_os = {}
    try:
        resultado = consultar_ordens(request.args, request.args.get("pagina", 1), current_user)
        ordens = resultado.itens
        resumo = {
            "total": OperacaoOrdemServico.query.count(),
            "ativas": OperacaoOrdemServico.query.filter_by(ativo=True).count(),
            "concluidas": OperacaoOrdemServico.query.filter(
                OperacaoOrdemServico.data_inicial.isnot(None),
                OperacaoOrdemServico.data_final.isnot(None),
            ).count(),
            "desativadas": OperacaoOrdemServico.query.filter_by(ativo=False).count(),
        }
        for ordem in ordens:
            if not ordem.ativo:
                progresso_por_os[ordem.id_os_interno] = 0
            elif ordem.status_operacional == "Concluída" or ordem.data_final:
                progresso_por_os[ordem.id_os_interno] = 100
            else:
                total_dias = (ordem.data_programada_final - ordem.data_programada_inicial).days + 1
                dias_apontados = (
                    db.session.query(OperacaoApontamentoDiario.data_evento)
                    .filter(
                        OperacaoApontamentoDiario.id_os_interno == ordem.id_os_interno,
                        OperacaoApontamentoDiario.data_evento.between(
                            ordem.data_programada_inicial, ordem.data_programada_final
                        ),
                    )
                    .distinct()
                    .count()
                )
                progresso_por_os[ordem.id_os_interno] = min(100, round(dias_apontados * 100 / total_dias)) if total_dias else 0
    except OrdemServicoConsultaErro as exc:
        erro_configuracao = str(exc)
        resultado = None
    return render_template(
        "operacao/ordens_servico/index.html",
        ordens=ordens,
        filtros={chave: valor for chave, valor in request.args.items() if chave != "pagina"},
        paginacao=resultado,
        resumo=resumo,
        progresso_por_os=progresso_por_os,
        erro_configuracao=erro_configuracao,
        pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "criar"),
        pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "editar"),
        equipes=Equipe.query.filter_by(ativo=True).order_by(Equipe.nome.asc()).all(),
        status_operacionais=("Programada", "Em Andamento", "Concluída", "Cancelada"),
    )


@ordens_servico_bp.route("/<string:id_os_interno>")
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "visualizar")
def ficha(id_os_interno):
    try:
        ordem = buscar_ordem_por_id(id_os_interno, current_user)
    except OrdemServicoConsultaErro as exc:
        flash("Não foi possível consultar a Ordem de Serviço no momento.", "danger")
        registrar_log("operacao_ordem_servico_consulta_falhou", str(exc))
        return redirect(url_for("ordens_servico.index"))
    if not ordem:
        flash("Ordem de Serviço não encontrada ou sem identificação segura.", "warning")
        return redirect(url_for("ordens_servico.index"))
    try:
        monitoramento = obter_monitoramento(ordem.id_os_interno, current_user)
    except MonitoramentoErro as exc:
        flash("Não foi possível consolidar o monitoramento da Ordem de Serviço no momento.", "warning")
        registrar_log("operacao_ordem_servico_monitoramento_falhou", str(exc))
        monitoramento = None
    if monitoramento:
        novo_status = ordem.status_operacional
        if ordem.data_final:
            novo_status = "Concluída"
        elif ordem.data_inicial and monitoramento.total_apontamentos > 0:
            novo_status = "Em Andamento"
        if novo_status != ordem.status_operacional:
            ordem.status_operacional = novo_status
            db.session.commit()
    servicos_totais = {}
    registros_servico = OperacaoApontamentoDiario.query.filter_by(id_os_interno=ordem.id_os_interno).all()
    for registro in registros_servico:
        if registro.diario_servico:
            nome = registro.diario_servico.servico
            servicos_totais[nome] = servicos_totais.get(nome, 0) + registro.diario_servico.quantidade
    servicos_realizados = sorted(servicos_totais.items(), key=lambda item: item[0].casefold())
    materiais_totais = {}
    for registro in registros_servico:
        if registro.diario_material:
            material = registro.diario_material
            chave = (material.material_aplicado, material.tipo_material)
            materiais_totais[chave] = materiais_totais.get(chave, 0) + material.quantidade
    materiais_aplicados = sorted(materiais_totais.items(), key=lambda item: (item[0][0].casefold(), item[0][1]))
    desvios_programacao = []
    programacao_dias = []
    if ordem.equipe and ordem.data_programada_inicial and ordem.data_programada_final:
        desvios_programacao = (
            db.session.query(
                OperacaoApontamentoDiario.data_evento,
                OperacaoOrdemServico.codigo_os_rental,
                OperacaoOrdemServico.numero_os_cliente,
                OperacaoOrdemServico.local,
                OperacaoOrdemServico.trabalho_previsto,
            )
            .join(OperacaoDiarioLocalizacao)
            .join(OperacaoOrdemServico, OperacaoApontamentoDiario.id_os_interno == OperacaoOrdemServico.id_os_interno)
            .filter(
                OperacaoApontamentoDiario.equipe == ordem.equipe,
                OperacaoApontamentoDiario.id_os_interno != ordem.id_os_interno,
                OperacaoOrdemServico.ativo.is_(True),
                OperacaoApontamentoDiario.data_evento.between(
                    ordem.data_programada_inicial, ordem.data_programada_final
                ),
            )
            .order_by(OperacaoApontamentoDiario.data_evento.asc(), OperacaoOrdemServico.codigo_os_rental.asc())
            .all()
        )
        registros_periodo = (
            db.session.query(
                OperacaoApontamentoDiario.data_evento,
                OperacaoApontamentoDiario.id_os_interno,
                OperacaoOrdemServico.numero_os_cliente,
                OperacaoOrdemServico.local,
                OperacaoOrdemServico.trabalho_previsto,
            )
            .join(OperacaoDiarioLocalizacao)
            .join(OperacaoOrdemServico, OperacaoApontamentoDiario.id_os_interno == OperacaoOrdemServico.id_os_interno)
            .filter(
                OperacaoApontamentoDiario.equipe == ordem.equipe,
                OperacaoApontamentoDiario.data_evento.between(ordem.data_programada_inicial, ordem.data_programada_final),
                OperacaoOrdemServico.ativo.is_(True),
            )
            .all()
        )
        por_data = {}
        for registro in registros_periodo:
            por_data.setdefault(registro.data_evento, []).append(registro)
        nomes_dias = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
        total_dias = (ordem.data_programada_final - ordem.data_programada_inicial).days + 1
        dias_trabalhados = 0
        dias_desvio = 0
        cursor = ordem.data_programada_inicial
        while cursor <= ordem.data_programada_final:
            registros_dia = por_data.get(cursor, [])
            proprio = next((item for item in registros_dia if item.id_os_interno == ordem.id_os_interno), None)
            outro = next((item for item in registros_dia if item.id_os_interno != ordem.id_os_interno), None)
            if proprio:
                situacao, classe, observacao = "Trabalhou nesta OS", "trabalhou", "-"
                dias_trabalhados += 1
            elif outro:
                situacao, classe = "Trabalhou em outra OS", "desvio"
                observacao = (
                    f"OS: {outro.numero_os_cliente or '-'} | Local: {outro.local or '-'} | "
                    f"Trabalho: {outro.trabalho_previsto or '-'}"
                )
                dias_desvio += 1
            else:
                situacao, classe, observacao = "Sem registro", "sem-registro", "-"
            programacao_dias.append({"data": cursor, "dia_semana": nomes_dias[cursor.weekday()], "situacao": situacao, "classe": classe, "observacao": observacao})
            cursor += timedelta(days=1)
        programacao_resumo = {"total_dias": total_dias, "dias_trabalhados": dias_trabalhados, "dias_desvio": dias_desvio, "dias_sem_registro": total_dias - dias_trabalhados - dias_desvio, "percentual": round((dias_trabalhados / total_dias) * 100) if total_dias else 0}
    else:
        programacao_resumo = {"total_dias": 0, "dias_trabalhados": 0, "dias_desvio": 0, "dias_sem_registro": 0, "percentual": 0}
    return render_template(
        "operacao/ordens_servico/ficha.html",
        ordem=ordem,
        monitoramento=monitoramento,
        servicos_realizados=servicos_realizados,
        materiais_aplicados=materiais_aplicados,
        desvios_programacao=desvios_programacao,
        programacao_dias=programacao_dias,
        programacao_resumo=programacao_resumo,
    )


@ordens_servico_bp.route("/<string:id_os_interno>/relatorio-pdf")
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "visualizar")
def relatorio_pdf(id_os_interno):
    ordem = buscar_ordem_por_id(id_os_interno, current_user)
    if not ordem:
        flash("Ordem de Serviço não encontrada.", "warning")
        return redirect(url_for("ordens_servico.index"))
    monitoramento = obter_monitoramento(ordem.id_os_interno, current_user)
    registros = OperacaoApontamentoDiario.query.filter_by(id_os_interno=ordem.id_os_interno).all()
    controles = OperacaoControleLiberacao.query.filter_by(id_os_interno=ordem.id_os_interno).order_by(OperacaoControleLiberacao.data_evento).all()
    programacao_dias = []
    programacao_resumo = {"total_dias": 0, "dias_trabalhados": 0, "dias_desvio": 0, "dias_sem_registro": 0, "percentual": 0}
    if ordem.equipe and ordem.data_programada_inicial and ordem.data_programada_final:
        registros_periodo = (
            db.session.query(
                OperacaoApontamentoDiario.data_evento,
                OperacaoApontamentoDiario.id_os_interno,
                OperacaoOrdemServico.numero_os_cliente,
                OperacaoOrdemServico.local,
                OperacaoOrdemServico.trabalho_previsto,
            )
            .join(OperacaoDiarioLocalizacao)
            .join(OperacaoOrdemServico, OperacaoApontamentoDiario.id_os_interno == OperacaoOrdemServico.id_os_interno)
            .filter(
                OperacaoApontamentoDiario.equipe == ordem.equipe,
                OperacaoApontamentoDiario.data_evento.between(ordem.data_programada_inicial, ordem.data_programada_final),
                OperacaoOrdemServico.ativo.is_(True),
            )
            .all()
        )
        por_data = {}
        for registro in registros_periodo:
            por_data.setdefault(registro.data_evento, []).append(registro)
        nomes_dias = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
        total_dias = (ordem.data_programada_final - ordem.data_programada_inicial).days + 1
        dias_trabalhados = dias_desvio = 0
        cursor = ordem.data_programada_inicial
        while cursor <= ordem.data_programada_final:
            registros_dia = por_data.get(cursor, [])
            proprio = next((item for item in registros_dia if item.id_os_interno == ordem.id_os_interno), None)
            outro = next((item for item in registros_dia if item.id_os_interno != ordem.id_os_interno), None)
            if proprio:
                situacao, observacao = "Trabalhou nesta OS", "-"
                dias_trabalhados += 1
            elif outro:
                situacao = "Trabalhou em outra OS"
                observacao = f"OS: {outro.numero_os_cliente or '-'} | Local: {outro.local or '-'} | Trabalho: {outro.trabalho_previsto or '-'}"
                dias_desvio += 1
            else:
                situacao, observacao = "Sem registro", "-"
            programacao_dias.append((cursor, nomes_dias[cursor.weekday()], situacao, observacao))
            cursor += timedelta(days=1)
        programacao_resumo = {
            "total_dias": total_dias,
            "dias_trabalhados": dias_trabalhados,
            "dias_desvio": dias_desvio,
            "dias_sem_registro": total_dias - dias_trabalhados - dias_desvio,
            "percentual": round((dias_trabalhados / total_dias) * 100) if total_dias else 0,
        }
    servicos = {}
    materiais = {}
    for registro in registros:
        if registro.diario_servico:
            servicos[registro.diario_servico.servico] = servicos.get(registro.diario_servico.servico, 0) + registro.diario_servico.quantidade
        if registro.diario_material:
            material = registro.diario_material
            chave = (material.material_aplicado, "Novo" if material.tipo_material == "NOVO" else "Recuperado")
            materiais[chave] = materiais.get(chave, 0) + material.quantidade
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=13 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#FFFFFF"), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=11, leading=14, textColor=colors.HexColor("#0B477D"), spaceBefore=7, spaceAfter=5))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="TableSmall", parent=styles["BodyText"], fontSize=6.8, leading=8))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["BodyText"], fontSize=6.8, leading=8, textColor=colors.white))
    styles.add(ParagraphStyle(name="SummaryTableSmall", parent=styles["BodyText"], fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(name="SummaryTableHeader", parent=styles["BodyText"], fontSize=7.5, leading=9, textColor=colors.white))
    story = []
    logo = Image("app/static/img/logo-rental-retros.png", width=28*mm, height=19*mm)
    story.append(Table([[logo, Paragraph("FICHA DA ORDEM DE SERVIÇO", styles["BrandTitle"])]] , colWidths=[36*mm, 154*mm], rowHeights=[22*mm], style=TableStyle([["BACKGROUND", (0,0), (-1,-1), colors.HexColor("#082B4C")], ["VALIGN", (0,0), (-1,-1), "MIDDLE"], ["ALIGN", (0,0), (0,0), "CENTER"]])))
    story.append(Paragraph("Relatório detalhado para impressão", styles["Section"]))
    def section(title, rows):
        tabela = Table([[Paragraph(f"<b>{label}</b>", styles["Small"]), Paragraph(str(value or "-"), styles["Small"])] for label, value in rows], colWidths=[52*mm, 138*mm], style=TableStyle([["GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B7C7D6")], ["BACKGROUND", (0,0), (0,-1), colors.HexColor("#EAF2F8")], ["VALIGN", (0,0), (-1,-1), "TOP"], ["LEFTPADDING", (0,0), (-1,-1), 5], ["RIGHTPADDING", (0,0), (-1,-1), 5], ["TOPPADDING", (0,0), (-1,-1), 4], ["BOTTOMPADDING", (0,0), (-1,-1), 4]]))
        story.append(KeepTogether([Paragraph(title, styles["Section"]), tabela]))
    fmt = lambda value: value.strftime("%d/%m/%Y") if value else "-"
    fmt_dt = lambda value: value.strftime("%d/%m/%Y %H:%M:%S") if value else "-"
    nome_usuario = lambda usuario: getattr(usuario, "nome", None) or getattr(usuario, "email", None) or "-"
    section("1. Identificação", [("Código Rental", ordem.codigo_os_rental), ("OS do cliente", ordem.numero_os_cliente), ("Situação", ordem.status_identificacao), ("ID interno", ordem.id_os_interno), ("Cadastrada em", fmt_dt(ordem.criado_em)), ("Cadastrada por", nome_usuario(ordem.criado_por))])
    section("2. Programação e execução", [("Local", ordem.local), ("Equipe", ordem.equipe), ("Trabalho previsto", ordem.trabalho_previsto), ("Programação", f"{fmt(ordem.data_programada_inicial)} a {fmt(ordem.data_programada_final)}"), ("Datas realizadas", f"{fmt(ordem.data_inicial)} a {fmt(ordem.data_final)}"), ("Status", ordem.status_operacional), ("Supervisor", ordem.supervisor), ("Encarregado", ordem.encarregado)])
    if programacao_dias:
        story.append(Paragraph("3. Cronograma da Ordem de Serviço", styles["Section"]))
        resumo_cronograma = [
            [Paragraph("<b>Progresso de execução</b>", styles["Small"]), Paragraph(f"{programacao_resumo['dias_trabalhados']} de {programacao_resumo['total_dias']} dias ({programacao_resumo['percentual']}%)", styles["Small"])],
            [Paragraph("Dias em outra OS", styles["Small"]), Paragraph(str(programacao_resumo["dias_desvio"]), styles["Small"])],
            [Paragraph("Dias sem registro", styles["Small"]), Paragraph(str(programacao_resumo["dias_sem_registro"]), styles["Small"])],
        ]
        story.append(Table(resumo_cronograma, colWidths=[52*mm, 138*mm], style=TableStyle([["GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B7C7D6")], ["BACKGROUND", (0,0), (0,-1), colors.HexColor("#EAF2F8")], ["VALIGN", (0,0), (-1,-1), "MIDDLE"], ["LEFTPADDING", (0,0), (-1,-1), 5], ["RIGHTPADDING", (0,0), (-1,-1), 5], ["TOPPADDING", (0,0), (-1,-1), 4], ["BOTTOMPADDING", (0,0), (-1,-1), 4]])))
        preenchido = 190 * programacao_resumo["percentual"] / 100
        story.append(Spacer(1, 3*mm))
        story.append(Table([["", ""]], colWidths=[preenchido, 190 - preenchido], rowHeights=[4*mm], style=TableStyle([["BACKGROUND", (0,0), (0,0), colors.HexColor("#16836D")], ["BACKGROUND", (1,0), (1,0), colors.HexColor("#DCE5EC")], ["BOX", (0,0), (-1,-1), 0.25, colors.HexColor("#B7C7D6")]])))
        cronograma = [["Data", "Dia da semana", "Situação", "Observação"]] + [[fmt(data), dia, situacao, observacao] for data, dia, situacao, observacao in programacao_dias]
        cronograma = [[Paragraph(str(celula), styles["TableHeader"] if indice == 0 else styles["TableSmall"]) for celula in linha] for indice, linha in enumerate(cronograma)]
        story.append(Spacer(1, 3*mm))
        story.append(Table(cronograma, colWidths=[25*mm, 35*mm, 39*mm, 91*mm], repeatRows=1, style=TableStyle([["BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B477D")], ["TEXTCOLOR", (0,0), (-1,0), colors.white], ["GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B7C7D6")], ["VALIGN", (0,0), (-1,-1), "TOP"]])))
    section("4. Monitoramento", [("Localizações", monitoramento.localizacoes), ("Serviços", monitoramento.servicos), ("Materiais", monitoramento.materiais), ("Jornada total", monitoramento.total_jornada), ("Tempo improdutivo", monitoramento.tempo_improdutivo), ("Tempo produtivo", monitoramento.percentual_tempo_produtivo), ("Controles de liberação", monitoramento.total_controle_liberacao), ("Circulação de trens", monitoramento.total_circulacao), ("Intervenções adversas", monitoramento.total_intervencao), ("Último apontamento", fmt(monitoramento.ultimo_apontamento))])
    story.append(Paragraph("5. Serviços realizados", styles["Section"]))
    servicos_tabela = [["Serviço", "Total"]] + [[nome, f"{float(total):.2f}".replace('.', ',')] for nome, total in sorted(servicos.items())] or [["Nenhum serviço registrado", "-"]]
    servicos_tabela = [[Paragraph(str(celula), styles["SummaryTableHeader"] if i == 0 else styles["SummaryTableSmall"]) for celula in linha] for i, linha in enumerate(servicos_tabela)]
    story.append(Table(servicos_tabela, colWidths=[150*mm, 40*mm], style=TableStyle([["BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B477D")], ["TEXTCOLOR", (0,0), (-1,0), colors.white], ["GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B7C7D6")], ["ALIGN", (1,1), (1,-1), "RIGHT"]])))
    story.append(Paragraph("6. Materiais aplicados", styles["Section"]))
    materiais_tabela = [["Material", "Condição", "Total"]] + [[nome, tipo, f"{float(total):.2f}".replace('.', ',')] for (nome, tipo), total in sorted(materiais.items())] or [["Nenhum material registrado", "-", "-"]]
    materiais_tabela = [[Paragraph(str(celula), styles["SummaryTableHeader"] if i == 0 else styles["SummaryTableSmall"]) for celula in linha] for i, linha in enumerate(materiais_tabela)]
    story.append(Table(materiais_tabela, colWidths=[100*mm, 55*mm, 35*mm], style=TableStyle([["BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B477D")], ["TEXTCOLOR", (0,0), (-1,0), colors.white], ["GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B7C7D6")], ["ALIGN", (2,1), (2,-1), "RIGHT"]])))
    def tabela_detalhes(titulo, cabecalho, linhas, larguras):
        dados = [cabecalho] + (linhas or [["Nenhum registro", *(["-"] * (len(cabecalho) - 1))]])
        dados = [[Paragraph(str(celula), styles["TableHeader"] if indice == 0 else styles["TableSmall"]) for celula in linha] for indice, linha in enumerate(dados)]
        tabela = Table(dados, colWidths=larguras, repeatRows=1, style=TableStyle([["BACKGROUND", (0,0), (-1,0), colors.HexColor("#0B477D")], ["TEXTCOLOR", (0,0), (-1,0), colors.white], ["GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#B7C7D6")], ["VALIGN", (0,0), (-1,-1), "TOP"]]))
        story.append(KeepTogether([Paragraph(titulo, styles["Section"]), tabela]))
    def segundos_horario(inicio, fim):
        if not (inicio and fim):
            return 0
        total = (fim.hour * 3600 + fim.minute * 60 + fim.second) - (inicio.hour * 3600 + inicio.minute * 60 + inicio.second)
        return total + 86400 if total < 0 else total
    def duracao_formatada(segundos):
        return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}:{segundos % 60:02d}"
    localizacoes = [registro.diario_localizacao for registro in registros if registro.diario_localizacao]
    tabela_detalhes("7. Registros de apontamentos de localização", ["Data", "Local", "Equipe", "Encarregado", "Jornada"], [[fmt(registro.apontamento.data_evento), registro.local, registro.apontamento.equipe, registro.encarregado, registro.total_jornada] for registro in localizacoes], [26*mm, 43*mm, 38*mm, 53*mm, 30*mm])
    total_controles = sum(segundos_horario(controle.pedido_liberacao_ccp, controle.termino_embandeiramento) for controle in controles)
    tabela_detalhes("8. Registros de controles de liberação", ["Data", "Pedido CCP", "Embandeiramento", "Término", "Duração"], [[fmt(controle.data_evento), str(controle.pedido_liberacao_ccp or "-"), str(controle.liberacao_embandeiramento or "-"), str(controle.termino_embandeiramento or "-"), duracao_formatada(segundos_horario(controle.pedido_liberacao_ccp, controle.termino_embandeiramento))] for controle in controles] + [["TOTAL", "", "", "", duracao_formatada(total_controles)]], [27*mm, 30*mm, 42*mm, 30*mm, 61*mm])
    circulacoes = [registro.circulacao_trem for registro in registros if registro.circulacao_trem]
    total_circulacoes = sum(segundos_horario(registro.hora_inicio, registro.hora_fim) for registro in circulacoes)
    tabela_detalhes("9. Registros de circulação de trens", ["Data", "Prefixo", "Início", "Fim", "Via/Linha", "Duração"], [[fmt(registro.apontamento.data_evento), registro.prefixo or "-", str(registro.hora_inicio or "-"), str(registro.hora_fim or "-"), registro.via_linha or "-", duracao_formatada(segundos_horario(registro.hora_inicio, registro.hora_fim))] for registro in circulacoes] + [["TOTAL", "", "", "", "", duracao_formatada(total_circulacoes)]], [25*mm, 28*mm, 24*mm, 24*mm, 55*mm, 34*mm])
    intervencoes = [registro.intervencao_adversa for registro in registros if registro.intervencao_adversa]
    total_intervencoes = sum(segundos_horario(registro.hora_inicio, registro.hora_fim) for registro in intervencoes)
    tabela_detalhes("9. Registros de intervenções adversas", ["Data", "Categoria", "Intervenção", "Início", "Fim", "Duração"], [[fmt(registro.apontamento.data_evento), registro.categoria or "-", registro.intervencao or "-", str(registro.hora_inicio or "-"), str(registro.hora_fim or "-"), duracao_formatada(segundos_horario(registro.hora_inicio, registro.hora_fim))] for registro in intervencoes] + [["TOTAL", "", "", "", "", duracao_formatada(total_intervencoes)]], [24*mm, 39*mm, 62*mm, 20*mm, 20*mm, 25*mm])
    story.append(Paragraph("10. Pré-checagem para fechamento", styles["Section"]))
    for item in ["Identificação da OS do cliente informada.", "Equipe e encarregado responsáveis definidos.", "Jornada de trabalho completa, sem registro em aberto.", "Controles de liberação com campos obrigatórios preenchidos.", "Circulações de trens com hora de início e fim.", "Intervenções adversas com horários completos quando informados.", "Data final realizada somente após a data inicial."]:
        story.append(Paragraph("• " + item, styles["Small"]))
    def footer(canvas, doc):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor("#D0DCE6")); canvas.line(10*mm, 10*mm, 200*mm, 10*mm); canvas.setFont("Helvetica", 8); canvas.setFillColor(colors.HexColor("#5B6B78")); canvas.drawString(10*mm, 5*mm, "Rental Retros - Gestão Empresarial"); canvas.drawRightString(200*mm, 5*mm, f"Página {doc.page}"); canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=f"relatorio_{ordem.codigo_os_rental or ordem.id_os_interno}.pdf")


def _dados_formulario_localizacao(ordem, apontamento=None):
    def horario_para_formulario(valor):
        return valor.strftime("%H:%M") if valor else ""

    if apontamento:
        localizacao = apontamento.diario_localizacao
        return {
            "data_evento": apontamento.data_evento.isoformat(),
            "equipe": apontamento.equipe,
            "encarregado": localizacao.encarregado,
            "chefe_boletim": localizacao.chefe_boletim,
            "local": localizacao.local,
            "amv": localizacao.numero_amv or "",
            "sub": localizacao.sub or "",
            "km_inicio": localizacao.km_inicio or "",
            "km_fim": localizacao.km_fim or "",
            "hora_inicial": horario_para_formulario(localizacao.hora_inicial),
            "intervalo_jornada": horario_para_formulario(localizacao.intervalo_jornada) or "01:00",
            "hora_final": horario_para_formulario(localizacao.hora_final),
            "intervalo_inicio": horario_para_formulario(localizacao.intervalo_inicio),
            "intervalo_fim": horario_para_formulario(localizacao.intervalo_fim),
            "pedido_liberacao_ccp": horario_para_formulario(localizacao.pedido_liberacao_ccp),
            "liberacao_embandeiramento": horario_para_formulario(localizacao.liberacao_embandeiramento),
            "termino_embandeiramento": horario_para_formulario(localizacao.termino_embandeiramento),
            "observacao": localizacao.observacao or "",
        }
    return {
        "equipe": ordem.equipe or "",
        "encarregado": ordem.encarregado or "",
        "local": ordem.local or "",
        "intervalo_jornada": "01:00",
    }


@ordens_servico_bp.route("/<string:id_os_interno>/localizacao", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "visualizar")
def localizacao(id_os_interno):
    try:
        ordem = buscar_ordem_por_id(id_os_interno, current_user)
    except OrdemServicoConsultaErro:
        flash("Não foi possível consultar a Ordem de Serviço no momento.", "danger")
        return redirect(url_for("ordens_servico.index"))
    if not ordem:
        flash("Ordem de Serviço não encontrada ou sem identificação segura.", "warning")
        return redirect(url_for("ordens_servico.index"))
    if request.method == "POST":
        if not usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "criar"):
            return redirect(url_for("main.acesso_negado"))
        try:
            dados = request.form.to_dict()
            dados["numero_os"] = ordem.numero_os_cliente or ""
            apontamento, repetido = criar_apontamento(
                dados, id_os_interno, request.form.get("chave_idempotencia"), current_user
            )
        except LocalizacaoErro as exc:
            registrar_log("operacao_localizacao_gravacao_falhou", f"Falha ao registrar localização para OS {id_os_interno}.")
            flash(str(exc), "danger")
        else:
            acao = "recuperado" if repetido else "criado"
            flash(f"Apontamento de Localização {acao} com sucesso.", "success")
            return redirect(url_for("ordens_servico.localizacao", id_os_interno=id_os_interno))
    try:
        apontamentos = consultar_apontamentos(id_os_interno, current_user)
        erro_consulta = None
    except LocalizacaoErro as exc:
        apontamentos = []
        erro_consulta = str(exc)
    return render_template(
        "operacao/ordens_servico/localizacao.html",
        ordem=ordem,
        apontamentos=apontamentos,
        opcoes_localizacao={**OPCOES, "chefe_boletim": tuple(c.nome for c in OperacaoChefeBoletim.query.filter_by(ativo=True).order_by(OperacaoChefeBoletim.nome).all())},
        dados_localizacao=request.form.to_dict() if request.method == "POST" else _dados_formulario_localizacao(ordem),
        apontamento_edicao=None,
        controles_liberacao=OperacaoControleLiberacao.query.filter_by(id_os_interno=ordem.id_os_interno).order_by(OperacaoControleLiberacao.data_evento.desc(), OperacaoControleLiberacao.id.desc()).limit(3).all(),
        erro_consulta=erro_consulta,
        chave_idempotencia=str(uuid.uuid4()),
        pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "criar"),
        pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "editar"),
    )


@ordens_servico_bp.route("/<string:id_os_interno>/localizacao/<string:id_apontamento_diario>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "editar")
def editar_localizacao(id_os_interno, id_apontamento_diario):
    try:
        ordem = buscar_ordem_por_id(id_os_interno, current_user)
        apontamento = buscar_apontamento(id_os_interno, id_apontamento_diario, current_user, "editar")
    except (OrdemServicoConsultaErro, LocalizacaoErro) as exc:
        flash(str(exc), "danger")
        return redirect(url_for("ordens_servico.localizacao", id_os_interno=id_os_interno))
    if not ordem:
        flash("Ordem de Serviço não encontrada.", "warning")
        return redirect(url_for("ordens_servico.index"))
    if request.method == "POST":
        try:
            editar_apontamento(
                request.form.to_dict(), id_os_interno, id_apontamento_diario,
                request.form.get("versao"), current_user,
            )
        except LocalizacaoErro as exc:
            flash(str(exc), "danger")
        else:
            flash("Apontamento de Localização atualizado com sucesso.", "success")
            return redirect(url_for("ordens_servico.localizacao", id_os_interno=id_os_interno))
    try:
        apontamentos = consultar_apontamentos(id_os_interno, current_user)
    except LocalizacaoErro:
        apontamentos = []
    return render_template(
        "operacao/ordens_servico/localizacao.html",
        ordem=ordem,
        apontamentos=apontamentos,
        opcoes_localizacao={**OPCOES, "chefe_boletim": tuple(c.nome for c in OperacaoChefeBoletim.query.filter_by(ativo=True).order_by(OperacaoChefeBoletim.nome).all())},
        dados_localizacao=request.form.to_dict() if request.method == "POST" else _dados_formulario_localizacao(ordem, apontamento),
        apontamento_edicao=apontamento,
        controles_liberacao=OperacaoControleLiberacao.query.filter_by(id_os_interno=ordem.id_os_interno).order_by(OperacaoControleLiberacao.data_evento.desc(), OperacaoControleLiberacao.id.desc()).limit(3).all(),
        erro_consulta=None,
        chave_idempotencia=None,
        pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "criar"),
        pode_editar=True,
    )


@ordens_servico_bp.route("/<string:id_os_interno>/controles-liberacao", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "criar")
def controles_liberacao(id_os_interno):
    ordem = buscar_ordem_por_id(id_os_interno, current_user)
    if not ordem:
        return redirect(url_for("ordens_servico.index"))
    editar_id = request.args.get("editar_id") or request.form.get("editar_id")
    registro_edicao = db.session.get(OperacaoControleLiberacao, int(editar_id)) if editar_id and str(editar_id).isdigit() else None
    if request.method == "POST":
        try:
            data_evento = date.fromisoformat(request.form.get("data_evento", ""))
            def horario(nome):
                valor = request.form.get(nome, "").strip()
                return time.fromisoformat(valor) if valor else None
            alvo = registro_edicao or OperacaoControleLiberacao(id_os_interno=ordem.id_os_interno, criado_por_usuario_id=current_user.id)
            alvo.data_evento = data_evento; alvo.pedido_liberacao_ccp = horario("pedido_liberacao_ccp"); alvo.liberacao_embandeiramento = horario("liberacao_embandeiramento"); alvo.termino_embandeiramento = horario("termino_embandeiramento")
            db.session.add(alvo)
            db.session.commit(); flash("Controle de liberação cadastrado.", "success")
            return redirect(url_for("ordens_servico.controles_liberacao", id_os_interno=id_os_interno))
        except (ValueError, TypeError):
            db.session.rollback(); flash("Informe uma data válida.", "danger")
    controles = OperacaoControleLiberacao.query.filter_by(id_os_interno=ordem.id_os_interno).order_by(OperacaoControleLiberacao.data_evento.desc(), OperacaoControleLiberacao.id.desc()).all()
    return render_template("operacao/ordens_servico/controles_liberacao.html", ordem=ordem, controles=controles, data_evento_inicial=registro_edicao.data_evento.isoformat() if registro_edicao else request.args.get("data_evento", ""), registro_edicao=registro_edicao)


@ordens_servico_bp.route("/<string:id_os_interno>/controles-liberacao/<int:controle_id>/excluir", methods=["POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "editar")
def excluir_controle_liberacao(id_os_interno, controle_id):
    registro = db.session.get(OperacaoControleLiberacao, controle_id)
    if registro and registro.id_os_interno == id_os_interno:
        db.session.delete(registro); db.session.commit(); flash("Controle excluído.", "success")
    return redirect(url_for("ordens_servico.controles_liberacao", id_os_interno=id_os_interno))


@ordens_servico_bp.route("/chefes-boletim", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, "chefes_boletim", "editar")
def chefes_boletim():
    if request.method == "POST":
        matricula = (request.form.get("matricula") or "").strip().upper()
        nome = (request.form.get("nome") or "").strip().upper()
        if not matricula or not nome:
            flash("Informe matrícula e nome.", "danger")
        else:
            registro = OperacaoChefeBoletim.query.filter_by(matricula=matricula).first()
            if registro is None:
                registro = OperacaoChefeBoletim(matricula=matricula, nome=nome, ativo=True)
                db.session.add(registro)
            else:
                registro.nome = nome; registro.ativo = True
            db.session.commit()
            flash("Chefe de boletim cadastrado com sucesso.", "success")
            return redirect(url_for("ordens_servico.chefes_boletim"))
    return render_template("operacao/ordens_servico/chefes_boletim.html", chefes=OperacaoChefeBoletim.query.order_by(OperacaoChefeBoletim.nome).all())


@ordens_servico_bp.route("/servicos-catalogo", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, "servicos_catalogo", "editar")
def servicos_catalogo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip().upper()
        editar_id = request.form.get("editar_id")
        if nome:
            registro = db.session.get(OperacaoServicoCatalogo, int(editar_id)) if editar_id and editar_id.isdigit() else OperacaoServicoCatalogo.query.filter_by(nome=nome).first() or OperacaoServicoCatalogo(nome=nome)
            registro.ativo = True; db.session.add(registro); db.session.commit(); flash("Serviço cadastrado.", "success")
    return render_template("operacao/ordens_servico/servicos_catalogo.html", servicos=OperacaoServicoCatalogo.query.order_by(OperacaoServicoCatalogo.nome).all())


@ordens_servico_bp.route("/servicos-catalogo/<int:servico_id>/excluir", methods=["POST"])
@login_required
@module_permission_required(DEPARTAMENTO, "servicos_catalogo", "editar")
def excluir_servico_catalogo(servico_id):
    item=db.session.get(OperacaoServicoCatalogo, servico_id)
    if item: item.ativo=False; db.session.commit()
    return redirect(url_for("ordens_servico.servicos_catalogo"))


@ordens_servico_bp.route("/materiais-catalogo", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, "materiais_catalogo", "editar")
def materiais_catalogo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip().upper()
        editar_id = request.form.get("editar_id")
        if nome:
            registro = db.session.get(OperacaoMaterialCatalogo, int(editar_id)) if editar_id and editar_id.isdigit() else OperacaoMaterialCatalogo.query.filter_by(nome=nome).first() or OperacaoMaterialCatalogo(nome=nome)
            registro.ativo = True; db.session.add(registro); db.session.commit(); flash("Material cadastrado.", "success")
    return render_template("operacao/ordens_servico/materiais_catalogo.html", materiais=OperacaoMaterialCatalogo.query.order_by(OperacaoMaterialCatalogo.nome).all())


@ordens_servico_bp.route("/materiais-catalogo/<int:material_id>/excluir", methods=["POST"])
@login_required
@module_permission_required(DEPARTAMENTO, "materiais_catalogo", "editar")
def excluir_material_catalogo(material_id):
    item = db.session.get(OperacaoMaterialCatalogo, material_id)
    if item:
        item.ativo = False; db.session.commit()
    return redirect(url_for("ordens_servico.materiais_catalogo"))


def _dados_formulario_diario(ordem, diario, apontamento=None):
    if apontamento:
        registro = getattr(apontamento, f"diario_{diario}")
        dados = {
            "data_evento": apontamento.data_evento.isoformat(),
            "equipe": apontamento.equipe,
            "quantidade": f"{registro.quantidade:.2f}".replace(".", ","),
        }
        if diario == "servico":
            dados["servico"] = registro.servico
        else:
            dados["tipo_material"] = registro.tipo_material
            dados["material_aplicado"] = registro.material_aplicado
        return dados
    return {"equipe": ordem.equipe or ""}


def _endpoint_diario(diario):
    return "ordens_servico.servicos" if diario == "servico" else "ordens_servico.materiais"


def _render_diario(id_os_interno, diario, apontamento_edicao=None):
    try:
        ordem = buscar_ordem_por_id(id_os_interno, current_user)
    except OrdemServicoConsultaErro:
        flash("Não foi possível consultar a Ordem de Serviço no momento.", "danger")
        return redirect(url_for("ordens_servico.index"))
    if not ordem:
        flash("Ordem de Serviço não encontrada ou sem identificação segura.", "warning")
        return redirect(url_for("ordens_servico.index"))
    if request.method == "POST":
        try:
            if apontamento_edicao:
                apontamento_edicao = editar_registro(request.form.to_dict(), id_os_interno, apontamento_edicao.id_apontamento_diario, request.form.get("versao"), current_user, diario)
            else:
                _, repetido = criar_registro(request.form.to_dict(), id_os_interno, request.form.get("chave_idempotencia"), current_user, diario)
                flash(f"Apontamento de {diario} {'recuperado' if repetido else 'criado'} com sucesso.", "success")
                return redirect(url_for(_endpoint_diario(diario), id_os_interno=id_os_interno))
        except DiarioProducaoErro as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Apontamento de {diario} atualizado com sucesso.", "success")
            return redirect(url_for(_endpoint_diario(diario), id_os_interno=id_os_interno))
    try:
        apontamentos = consultar_registros(id_os_interno, current_user, diario)
        erro_consulta = None
    except DiarioProducaoErro as exc:
        apontamentos, erro_consulta = [], str(exc)
    return render_template(
        "operacao/ordens_servico/diario_producao.html",
        ordem=ordem, diario=diario, apontamentos=apontamentos,
        apontamento_edicao=apontamento_edicao, erro_consulta=erro_consulta,
        dados_diario=request.form.to_dict() if request.method == "POST" else _dados_formulario_diario(ordem, diario, apontamento_edicao),
        servicos_catalogo=OperacaoServicoCatalogo.query.filter_by(ativo=True).order_by(OperacaoServicoCatalogo.nome).all(),
        materiais_catalogo=OperacaoMaterialCatalogo.query.filter_by(ativo=True).order_by(OperacaoMaterialCatalogo.nome).all(),
        opcoes_equipe=OPCOES["equipe"], chave_idempotencia=str(uuid.uuid4()),
        pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "criar"),
        pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "editar"),
    )


@ordens_servico_bp.route("/<string:id_os_interno>/servicos", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "visualizar")
def servicos(id_os_interno):
    return _render_diario(id_os_interno, "servico")


@ordens_servico_bp.route("/<string:id_os_interno>/materiais", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "visualizar")
def materiais(id_os_interno):
    return _render_diario(id_os_interno, "material")


@ordens_servico_bp.route("/<string:id_os_interno>/<string:diario>/<string:id_apontamento_diario>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "editar")
def editar_diario_producao(id_os_interno, diario, id_apontamento_diario):
    if diario not in ("servico", "material"):
        return redirect(url_for("ordens_servico.ficha", id_os_interno=id_os_interno))
    try:
        apontamento = buscar_registro(id_os_interno, id_apontamento_diario, current_user, diario, "editar")
    except DiarioProducaoErro as exc:
        flash(str(exc), "danger")
        return redirect(url_for(_endpoint_diario(diario), id_os_interno=id_os_interno))
    return _render_diario(id_os_interno, diario, apontamento)


def _dados_formulario_circulacao(ordem, apontamento=None):
    if not apontamento:
        return {"equipe": ordem.equipe or ""}
    registro = apontamento.circulacao_trem
    return {
        "data_evento": apontamento.data_evento.isoformat(), "equipe": apontamento.equipe,
        "prefixo": registro.prefixo or "", "via_linha": registro.via_linha or "",
        "operador_ccp_maquinista": registro.operador_ccp_maquinista or "",
        "motivo_paralisacao": registro.motivo_paralisacao or "",
        "hora_inicio": registro.hora_inicio.strftime("%H:%M") if registro.hora_inicio else "",
        "hora_fim": registro.hora_fim.strftime("%H:%M") if registro.hora_fim else "",
        "pedido_corte_composicao": registro.pedido_corte_composicao,
        "corte_composicao": registro.corte_composicao,
    }


def _render_circulacao(id_os_interno, apontamento_edicao=None):
    try:
        ordem = buscar_ordem_por_id(id_os_interno, current_user)
    except OrdemServicoConsultaErro:
        return redirect(url_for("ordens_servico.index"))
    if not ordem:
        return redirect(url_for("ordens_servico.index"))
    if request.method == "POST":
        try:
            if apontamento_edicao:
                editar_circulacao(request.form.to_dict(), id_os_interno, apontamento_edicao.id_apontamento_diario, request.form.get("versao"), current_user)
            else:
                _, repetido = criar_circulacao(request.form.to_dict(), id_os_interno, request.form.get("chave_idempotencia"), current_user)
                flash(f"Circulação de Trens {'recuperada' if repetido else 'criada'} com sucesso.", "success")
                return redirect(url_for("ordens_servico.circulacao", id_os_interno=id_os_interno))
        except CirculacaoErro as exc:
            flash(str(exc), "danger")
        else:
            flash("Circulação de Trens atualizada com sucesso.", "success")
            return redirect(url_for("ordens_servico.circulacao", id_os_interno=id_os_interno))
    try:
        apontamentos, erro_consulta = consultar_circulacoes(id_os_interno, current_user), None
    except CirculacaoErro as exc:
        apontamentos, erro_consulta = [], str(exc)
    return render_template("operacao/ordens_servico/circulacao.html", ordem=ordem, apontamentos=apontamentos, apontamento_edicao=apontamento_edicao, dados_circulacao=request.form.to_dict() if request.method == "POST" else _dados_formulario_circulacao(ordem, apontamento_edicao), opcoes_equipe=OPCOES["equipe"], opcoes_corte=OPCOES_CORTE, opcoes_motivo_paralisacao=OPCOES_MOTIVO_PARALISACAO, chave_idempotencia=str(uuid.uuid4()), erro_consulta=erro_consulta, pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "criar"), pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "editar"))


@ordens_servico_bp.route("/<string:id_os_interno>/circulacao", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "visualizar")
def circulacao(id_os_interno):
    return _render_circulacao(id_os_interno)


@ordens_servico_bp.route("/<string:id_os_interno>/circulacao/<string:id_apontamento_diario>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "editar")
def editar_circulacao_trem(id_os_interno, id_apontamento_diario):
    try:
        apontamento = buscar_circulacao(id_os_interno, id_apontamento_diario, current_user, "editar")
    except CirculacaoErro as exc:
        flash(str(exc), "danger")
        return redirect(url_for("ordens_servico.circulacao", id_os_interno=id_os_interno))
    return _render_circulacao(id_os_interno, apontamento)


def _render_intervencoes(id_os_interno, apontamento_edicao=None):
    try: ordem = buscar_ordem_por_id(id_os_interno, current_user)
    except OrdemServicoConsultaErro: return redirect(url_for("ordens_servico.index"))
    if not ordem: return redirect(url_for("ordens_servico.index"))
    if request.method == "POST":
        try:
            if apontamento_edicao: editar_intervencao(request.form.to_dict(), id_os_interno, apontamento_edicao.id_apontamento_diario, request.form.get("versao"), current_user)
            else:
                _, repetido = criar_intervencao(request.form.to_dict(), id_os_interno, request.form.get("chave_idempotencia"), current_user)
                flash(f"Intervenção adversa {'recuperada' if repetido else 'criada'} com sucesso.", "success"); return redirect(url_for("ordens_servico.intervencoes", id_os_interno=id_os_interno))
        except IntervencaoErro as exc: flash(str(exc), "danger")
        else: flash("Intervenção adversa atualizada com sucesso.", "success"); return redirect(url_for("ordens_servico.intervencoes", id_os_interno=id_os_interno))
    try: apontamentos, erro = consultar_intervencoes(id_os_interno, current_user), None
    except IntervencaoErro as exc: apontamentos, erro = [], str(exc)
    dados = request.form.to_dict() if request.method == "POST" else ({"data_evento": apontamento_edicao.data_evento.isoformat(), "equipe": apontamento_edicao.equipe, "hora_inicio": apontamento_edicao.intervencao_adversa.hora_inicio.strftime("%H:%M") if apontamento_edicao and apontamento_edicao.intervencao_adversa.hora_inicio else "", "hora_fim": apontamento_edicao.intervencao_adversa.hora_fim.strftime("%H:%M") if apontamento_edicao and apontamento_edicao.intervencao_adversa.hora_fim else "", "intervencao": apontamento_edicao.intervencao_adversa.intervencao, "categoria": apontamento_edicao.intervencao_adversa.categoria} if apontamento_edicao else {"equipe": ordem.equipe or ""})
    return render_template("operacao/ordens_servico/intervencoes.html", ordem=ordem, apontamentos=apontamentos, apontamento_edicao=apontamento_edicao, dados=dados, opcoes_equipe=OPCOES["equipe"], categorias=CATEGORIAS, chave_idempotencia=str(uuid.uuid4()), erro_consulta=erro, pode_criar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "criar"), pode_editar=usuario_tem_permissao(current_user, DEPARTAMENTO, MODULO, "editar"))


@ordens_servico_bp.route("/<string:id_os_interno>/intervencoes", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "visualizar")
def intervencoes(id_os_interno): return _render_intervencoes(id_os_interno)


@ordens_servico_bp.route("/<string:id_os_interno>/intervencoes/<string:id_apontamento_diario>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "editar")
def editar_intervencao_adversa(id_os_interno, id_apontamento_diario):
    try: apontamento = buscar_intervencao(id_os_interno, id_apontamento_diario, current_user, "editar")
    except IntervencaoErro as exc: flash(str(exc), "danger"); return redirect(url_for("ordens_servico.intervencoes", id_os_interno=id_os_interno))
    return _render_intervencoes(id_os_interno, apontamento)


@ordens_servico_bp.route("/nova", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "criar")
def nova():
    dados = request.form.to_dict() if request.method == "POST" else {}
    chave_idempotencia = dados.get("chave_idempotencia") or str(uuid.uuid4())
    if request.method == "POST":
        try:
            ordem, reutilizada = criar_ordem_servico(dados, chave_idempotencia, current_user)
        except OrdemServicoCadastroErro as exc:
            flash(str(exc), "danger")
        else:
            acao = "recuperada" if reutilizada else "criada"
            flash(f"Ordem de Serviço {ordem.codigo_os_rental} {acao} com sucesso.", "success")
            return redirect(url_for("ordens_servico.ficha", id_os_interno=ordem.id_os_interno))
    return render_template(
        "operacao/ordens_servico/form.html",
        dados=dados,
        chave_idempotencia=chave_idempotencia,
        equipes=Equipe.query.filter_by(ativo=True).order_by(Equipe.nome.asc()).all(),
        supervisores=Colaborador.query.filter(Colaborador.ativo.is_(True), Colaborador.funcao == "SUPERVISOR").order_by(Colaborador.nome.asc()).all(),
        encarregados=Colaborador.query.filter(Colaborador.ativo.is_(True), Colaborador.funcao == "ENCARREGADO").order_by(Colaborador.nome.asc()).all(),
    )


@ordens_servico_bp.route("/<string:id_os_interno>/editar", methods=["GET", "POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "editar")
def editar(id_os_interno):
    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem:
        flash("Ordem de Serviço não encontrada.", "warning")
        return redirect(url_for("ordens_servico.index"))

    dados = request.form.to_dict() if request.method == "POST" else {
        "numero_os_cliente": ordem.numero_os_cliente or "",
        "local": ordem.local or "", "equipe": ordem.equipe or "",
        "data_programada_inicial": ordem.data_programada_inicial.isoformat() if ordem.data_programada_inicial else "",
        "data_programada_final": ordem.data_programada_final.isoformat() if ordem.data_programada_final else "",
        "data_inicial": ordem.data_inicial.isoformat() if ordem.data_inicial else "",
        "data_final": ordem.data_final.isoformat() if ordem.data_final else "",
        "trabalho_previsto": ordem.trabalho_previsto or "", "supervisor": ordem.supervisor or "",
        "encarregado": ordem.encarregado or "",
    }
    if request.method == "POST":
        try:
            ordem = editar_ordem_servico(dados, id_os_interno, current_user)
        except OrdemServicoCadastroErro as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Ordem de Serviço {ordem.codigo_os_rental} atualizada com sucesso.", "success")
            return redirect(url_for("ordens_servico.ficha", id_os_interno=ordem.id_os_interno))

    return render_template(
        "operacao/ordens_servico/form.html", dados=dados, ordem=ordem, em_edicao=True,
        equipes=Equipe.query.filter_by(ativo=True).order_by(Equipe.nome.asc()).all(),
        supervisores=Colaborador.query.filter(Colaborador.ativo.is_(True), Colaborador.funcao == "SUPERVISOR").order_by(Colaborador.nome.asc()).all(),
        encarregados=Colaborador.query.filter(Colaborador.ativo.is_(True), Colaborador.funcao == "ENCARREGADO").order_by(Colaborador.nome.asc()).all(),
    )


@ordens_servico_bp.route("/<string:id_os_interno>/alternar-status", methods=["POST"])
@login_required
@module_permission_required(DEPARTAMENTO, MODULO, "editar")
def alternar_status(id_os_interno):
    ordem = db.session.get(OperacaoOrdemServico, id_os_interno)
    if not ordem:
        flash("Ordem de Serviço não encontrada.", "warning")
        return redirect(url_for("ordens_servico.index"))
    ordem.ativo = not ordem.ativo
    ordem.atualizado_por_usuario_id = current_user.id
    db.session.commit()
    acao = "ativada" if ordem.ativo else "desativada"
    registrar_log("operacao_ordem_servico_status_alterado", f"OS {ordem.codigo_os_rental} {acao}.", usuario=current_user)
    flash(f"Ordem de Serviço {ordem.codigo_os_rental} {acao} com sucesso.", "success")
    return redirect(url_for("ordens_servico.index"))



