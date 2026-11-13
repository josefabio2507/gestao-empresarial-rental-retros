import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO, StringIO

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.decorators import module_permission_required
from app.extensions import db
from app.models import Colaborador, FeriasColaborador
from app.services.permissoes_service import usuario_tem_permissao
from app.services.logs_service import registrar_log
from app.utils.datas import agora_brasil

ferias_bp = Blueprint("ferias", __name__)


def data_limite_concessao(registro):
    return registro.periodo_aquisitivo_fim + timedelta(days=365)


def situacao_prazo(registro, hoje=None):
    hoje = hoje or date.today()
    if registro.status in ("concluida", "cancelada"):
        return "encerrado"
    limite = data_limite_concessao(registro)
    if hoje > limite:
        return "vencido"
    if limite <= hoje + timedelta(days=90):
        return "proximo"
    return "no_prazo"


def _data(nome):
    return datetime.strptime(request.form.get(nome, ""), "%Y-%m-%d").date()


def _dados_formulario():
    inicio = _data("inicio_ferias")
    fim = _data("fim_ferias")
    aquisitivo_inicio = _data("periodo_aquisitivo_inicio")
    aquisitivo_fim = _data("periodo_aquisitivo_fim")
    dias = int(request.form.get("dias", "0"))
    if fim < inicio or aquisitivo_fim < aquisitivo_inicio or dias < 1 or dias > 30:
        raise ValueError
    return {"colaborador_id": int(request.form["colaborador_id"]), "periodo_aquisitivo_inicio": aquisitivo_inicio, "periodo_aquisitivo_fim": aquisitivo_fim, "inicio_ferias": inicio, "fim_ferias": fim, "dias": dias, "abono_pecuniario": request.form.get("abono_pecuniario") == "on", "status": request.form.get("status", "programada"), "observacoes": request.form.get("observacoes", "").strip()}


def _possui_sobreposicao(dados, ignorar_id=None):
    query = FeriasColaborador.query.filter(FeriasColaborador.colaborador_id == dados["colaborador_id"], FeriasColaborador.status != "cancelada", FeriasColaborador.inicio_ferias <= dados["fim_ferias"], FeriasColaborador.fim_ferias >= dados["inicio_ferias"])
    if ignorar_id:
        query = query.filter(FeriasColaborador.id != ignorar_id)
    return query.first() is not None


def _moeda(valor):
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_estimativa(salario, dias, abono=False):
    salario = _moeda(salario)
    dias = int(dias)
    remuneracao = _moeda((salario / Decimal("30")) * dias)
    terco = _moeda(remuneracao / Decimal("3"))
    abono_dias = min(10, dias // 3) if abono else 0
    abono_valor = _moeda((salario / Decimal("30")) * abono_dias)
    abono_terco = _moeda(abono_valor / Decimal("3"))
    total = _moeda(remuneracao + terco + abono_valor + abono_terco)
    return {"salario": salario, "dias": dias, "remuneracao": remuneracao, "terco": terco, "abono_dias": abono_dias, "abono_valor": abono_valor, "abono_terco": abono_terco, "total": total}


@ferias_bp.route("/")
@module_permission_required("departamento_pessoal", "ferias", "visualizar")
def index():
    status = request.args.get("status", "").strip()
    busca = request.args.get("q", "").strip()
    query = FeriasColaborador.query.join(Colaborador).order_by(FeriasColaborador.inicio_ferias.asc())
    if status:
        query = query.filter(FeriasColaborador.status == status)
    if busca:
        query = query.filter(Colaborador.nome.ilike(f"%{busca}%"))
    registros = query.all()
    alertas_prazo = sum(situacao_prazo(item) in ("vencido", "proximo") for item in registros)
    alertas = [
        {"registro": item, "situacao": situacao_prazo(item), "limite": data_limite_concessao(item)}
        for item in registros
        if situacao_prazo(item) in ("vencido", "proximo")
    ]
    alertas.sort(key=lambda alerta: alerta["limite"])
    return render_template("departamento_pessoal/ferias/index.html", registros=registros, alertas=alertas, colaboradores=Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all(), status_selecionado=status, busca=busca, hoje=date.today(), alertas_prazo=alertas_prazo, data_limite_concessao=data_limite_concessao, situacao_prazo=situacao_prazo, pode_criar=usuario_tem_permissao(current_user, "departamento_pessoal", "ferias", "criar"), pode_editar=usuario_tem_permissao(current_user, "departamento_pessoal", "ferias", "editar"), pode_excluir=usuario_tem_permissao(current_user, "departamento_pessoal", "ferias", "excluir"))


@ferias_bp.route("/relatorio.csv")
@module_permission_required("departamento_pessoal", "ferias", "visualizar")
def relatorio_csv():
    registros = FeriasColaborador.query.join(Colaborador).order_by(Colaborador.nome.asc(), FeriasColaborador.inicio_ferias.asc()).all()
    arquivo = StringIO()
    escritor = csv.writer(arquivo, delimiter=";")
    escritor.writerow(["Matr�cula", "Colaborador", "Per�odo aquisitivo in�cio", "Per�odo aquisitivo fim", "F�rias in�cio", "F�rias fim", "Dias", "Prazo concessivo", "Situa��o do prazo", "Status", "Abono pecuni�rio", "Observa��es"])
    for item in registros:
        escritor.writerow([item.colaborador.matricula, item.colaborador.nome, item.periodo_aquisitivo_inicio.strftime("%d/%m/%Y"), item.periodo_aquisitivo_fim.strftime("%d/%m/%Y"), item.inicio_ferias.strftime("%d/%m/%Y"), item.fim_ferias.strftime("%d/%m/%Y"), item.dias, data_limite_concessao(item).strftime("%d/%m/%Y"), situacao_prazo(item), item.status, "Sim" if item.abono_pecuniario else "N�o", item.observacoes or ""])
    dados = arquivo.getvalue().encode("utf-8-sig")
    return send_file(BytesIO(dados), mimetype="text/csv", as_attachment=True, download_name="relatorio_ferias.csv")


@ferias_bp.route("/<int:ferias_id>/calculo")
@module_permission_required("departamento_pessoal", "ferias", "visualizar")
def calculo(ferias_id):
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    resultado = None
    erro = None
    salario = request.args.get("salario", "").strip()
    if salario:
        try:
            resultado = calcular_estimativa(Decimal(salario.replace(".", "").replace(",", ".")), registro.dias, registro.abono_pecuniario)
        except (InvalidOperation, TypeError, ValueError):
            erro = "Informe um sal�rio v�lido para calcular a estimativa."
    return render_template("departamento_pessoal/ferias/calculo.html", registro=registro, resultado=resultado, erro=erro, salario=salario)


@ferias_bp.route("/<int:ferias_id>/historico")
@module_permission_required("departamento_pessoal", "ferias", "visualizar")
def historico(ferias_id):
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    historico_registros = FeriasColaborador.query.filter_by(
        colaborador_id=registro.colaborador_id
    ).order_by(FeriasColaborador.inicio_ferias.desc()).all()
    return render_template(
        "departamento_pessoal/ferias/historico.html",
        colaborador=registro.colaborador,
        registros=historico_registros,
        data_limite_concessao=data_limite_concessao,
        situacao_prazo=situacao_prazo,
    )


def _gerar_documento_ferias(registro, tipo):
    buffer = BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    estilos = getSampleStyleSheet()
    titulo = "AVISO DE F�RIAS" if tipo == "aviso" else "RECIBO DE F�RIAS"
    elementos = [Paragraph("RENTAL RETROS", estilos["Title"]), Spacer(1, 0.5 * cm), Paragraph(titulo, estilos["Heading2"]), Spacer(1, 0.3 * cm), Paragraph("Documento gerado pelo MVP de Controle de F�rias - modelo para confer�ncia.", estilos["Normal"]), Spacer(1, 0.5 * cm)]
    dados = [
        ["Colaborador", registro.colaborador.nome],
        ["Matr�cula", registro.colaborador.matricula],
        ["Cargo", registro.colaborador.cargo or "N�o informado"],
        ["Per�odo aquisitivo", f"{registro.periodo_aquisitivo_inicio.strftime('%d/%m/%Y')} a {registro.periodo_aquisitivo_fim.strftime('%d/%m/%Y')}"],
        ["Per�odo de f�rias", f"{registro.inicio_ferias.strftime('%d/%m/%Y')} a {registro.fim_ferias.strftime('%d/%m/%Y')}"],
        ["Quantidade de dias", str(registro.dias)],
        ["Abono pecuni�rio", "Sim" if registro.abono_pecuniario else "N�o"],
        ["Status", registro.status.replace("_", " ").title()],
    ]
    tabela = Table(dados, colWidths=[5 * cm, 11 * cm])
    tabela.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef3f7")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#061b33")), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d7e0e8")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 8)]))
    elementos.append(tabela)
    elementos.extend([Spacer(1, 1 * cm), Paragraph("Observa��es: " + (registro.observacoes or "N�o informado."), estilos["Normal"]), Spacer(1, 1.2 * cm), Paragraph("Assinatura do colaborador: ______________________________________________", estilos["Normal"]), Spacer(1, 0.7 * cm), Paragraph("Assinatura do respons�vel: ______________________________________________", estilos["Normal"]), Spacer(1, 1 * cm), Paragraph("Este documento � um modelo de confer�ncia e n�o substitui a valida��o do Departamento Pessoal.", estilos["Italic"])])
    documento.build(elementos)
    buffer.seek(0)
    return buffer


@ferias_bp.route("/<int:ferias_id>/documento/<tipo>")
@module_permission_required("departamento_pessoal", "ferias", "visualizar")
def documento(ferias_id, tipo):
    if tipo not in ("aviso", "recibo"):
        return redirect(url_for("ferias.index"))
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    arquivo = _gerar_documento_ferias(registro, tipo)
    nome = f"{tipo}_ferias_{registro.colaborador.matricula}.pdf"
    return send_file(arquivo, mimetype="application/pdf", as_attachment=True, download_name=nome)


@ferias_bp.route("/<int:ferias_id>/aprovar", methods=["POST"])
@module_permission_required("departamento_pessoal", "ferias", "editar")
def aprovar(ferias_id):
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    registro.aprovacao_status = "aprovada"
    registro.aprovado_por_usuario_id = current_user.id
    registro.aprovado_em = agora_brasil()
    registro.motivo_reprovacao = None
    db.session.commit()
    registrar_log("ferias_aprovadas", f"F�rias aprovadas. Registro: {registro.id}; colaborador: {registro.colaborador.nome}.")
    flash("Programa��o de f�rias aprovada.", "success")
    return redirect(url_for("ferias.index"))


@ferias_bp.route("/<int:ferias_id>/reprovar", methods=["POST"])
@module_permission_required("departamento_pessoal", "ferias", "editar")
def reprovar(ferias_id):
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    motivo = request.form.get("motivo_reprovacao", "").strip()
    if not motivo:
        flash("Informe o motivo da reprova��o.", "danger")
        return redirect(url_for("ferias.index"))
    registro.aprovacao_status = "reprovada"
    registro.aprovado_por_usuario_id = current_user.id
    registro.aprovado_em = agora_brasil()
    registro.motivo_reprovacao = motivo
    db.session.commit()
    registrar_log("ferias_reprovadas", f"F�rias reprovadas. Registro: {registro.id}; colaborador: {registro.colaborador.nome}.")
    flash("Programa��o de f�rias reprovada.", "warning")
    return redirect(url_for("ferias.index"))


@ferias_bp.route("/novo", methods=["POST"])
@module_permission_required("departamento_pessoal", "ferias", "criar")
def novo():
    try:
        dados = _dados_formulario()
        if _possui_sobreposicao(dados):
            raise RuntimeError("J� existe f�rias cadastrada para este colaborador no per�odo informado.")
        db.session.add(FeriasColaborador(**dados))
        db.session.commit()
        flash("F�rias cadastradas com sucesso.", "success")
    except RuntimeError as erro:
        db.session.rollback()
        flash(str(erro), "danger")
    except (KeyError, TypeError, ValueError):
        db.session.rollback()
        flash("Confira os campos obrigat�rios e as datas informadas.", "danger")
    return redirect(url_for("ferias.index"))


@ferias_bp.route("/<int:ferias_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "ferias", "editar")
def editar(ferias_id):
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    if request.method == "POST":
        try:
            dados = _dados_formulario()
            if _possui_sobreposicao(dados, ignorar_id=registro.id):
                raise RuntimeError("J� existe f�rias cadastrada para este colaborador no per�odo informado.")
            for campo, valor in dados.items():
                setattr(registro, campo, valor)
            db.session.commit()
            flash("F�rias atualizadas com sucesso.", "success")
            return redirect(url_for("ferias.index"))
        except RuntimeError as erro:
            db.session.rollback()
            flash(str(erro), "danger")
        except (KeyError, TypeError, ValueError):
            db.session.rollback()
            flash("Confira os campos obrigat�rios e as datas informadas.", "danger")
    return render_template("departamento_pessoal/ferias/editar.html", registro=registro, colaboradores=Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all())


@ferias_bp.route("/<int:ferias_id>/excluir", methods=["POST"])
@module_permission_required("departamento_pessoal", "ferias", "excluir")
def excluir(ferias_id):
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    registro.status = "cancelada"
    db.session.commit()
    flash("F�rias canceladas com seguran�a. O hist�rico foi preservado.", "success")
    return redirect(url_for("ferias.index"))


@ferias_bp.route("/<int:ferias_id>/status", methods=["POST"])
@module_permission_required("departamento_pessoal", "ferias", "editar")
def alterar_status(ferias_id):
    registro = FeriasColaborador.query.get_or_404(ferias_id)
    registro.status = request.form.get("status", registro.status)
    db.session.commit()
    flash("Status das f�rias atualizado.", "success")
    return redirect(url_for("ferias.index"))
