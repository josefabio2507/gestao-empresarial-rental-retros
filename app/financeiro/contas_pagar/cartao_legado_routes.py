import csv
from io import StringIO

from flask import abort, current_app, flash, jsonify, redirect, render_template, request, Response, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf, validate_csrf
from wtforms.validators import ValidationError

from app.decorators import module_permission_required
from app.extensions import db
from app.financeiro.contas_pagar import financeiro_contas_pagar_bp as bp
from app.models import FinanceiroImportacaoCartao
from app.services import financeiro_cartao_legado_service as service


def _job(job_id):
    job = db.session.get(FinanceiroImportacaoCartao, job_id)
    if not job or job.usuario_id != current_user.id:
        abort(404)
    return job


def _csrf():
    try:
        validate_csrf(request.form.get("csrf_token") or request.headers.get("X-CSRFToken"))
    except ValidationError:
        abort(400, description="Sessão expirada. Atualize a página para continuar.")


@bp.route("/cartoes/importar-legado", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def importar_cartao_legado():
    if request.method == "POST":
        request.max_content_length = 11 * 1024 * 1024
        _csrf()
        arquivo = request.files.get("arquivo")
        try:
            if not arquivo or not arquivo.filename:
                raise ValueError("Selecione a planilha Excel.")
            job = service.criar_importacao(arquivo, current_user)
            return redirect(url_for("financeiro_contas_pagar.previa_cartao_legado", job_id=job.id))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "warning")
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Falha na leitura de planilha de cartao legado")
            flash("Não foi possível analisar o arquivo. Confira se é uma planilha Excel válida e tente novamente.", "warning")
    recentes = FinanceiroImportacaoCartao.query.filter_by(usuario_id=current_user.id).order_by(FinanceiroImportacaoCartao.criado_em.desc()).limit(10).all()
    return render_template("financeiro/contas_pagar/importar_cartao_legado.html", job=None, recentes=recentes, csrf=generate_csrf())


@bp.route("/cartoes/importar-legado/<job_id>", methods=["GET", "POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def previa_cartao_legado(job_id):
    job = _job(job_id)
    if request.method == "POST":
        _csrf()
        try:
            service.atualizar_mapeamento(job, request.form)
            flash("Cartões validados. Confira a prévia antes de importar.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "warning")
        return redirect(url_for("financeiro_contas_pagar.previa_cartao_legado", job_id=job.id))
    return render_template("financeiro/contas_pagar/importar_cartao_legado.html", job=job,
        resumo=service.resumo(job), finais=sorted({r["final"] for r in job.dados}),
        cartoes=service.cartoes_disponiveis(), csrf=generate_csrf(),
        sem_cartao=any(not r.get("cartao_id") for r in job.dados if not r["erros_base"]))


@bp.route("/cartoes/importar-legado/<job_id>/lote", methods=["POST"])
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def lote_cartao_legado(job_id):
    _csrf()
    _job(job_id)
    dados = request.get_json(silent=True) or {}
    try:
        cursor = dados.get("cursor")
        if type(cursor) is not int or cursor < 0:
            raise ValueError("Posição de importação inválida. Atualize a página.")
        return jsonify(service.processar_lote(job_id, current_user.id, cursor))
    except ValueError as exc:
        db.session.rollback()
        return jsonify(erro=str(exc)), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Falha no lote da importacao de cartao %s", job_id)
        return jsonify(erro="Não foi possível concluir este lote. Os lotes anteriores estão salvos. Atualize a página e retome a importação."), 500


@bp.route("/cartoes/importar-legado/<job_id>/pendencias")
@login_required
@module_permission_required("financeiro", "contas_a_pagar", "criar")
def pendencias_cartao_legado(job_id):
    job = _job(job_id)
    saida = StringIO(newline="")
    writer = csv.writer(saida, delimiter=";")
    writer.writerow(["Linha", "ID legado", "Final", "Descrição", "Valor", "Pendências"])
    for linha in job.dados:
        if linha["erros"]:
            valores = [linha["linha"], linha["id_legado"], linha["final"], linha["descricao"], linha.get("valor", ""), " | ".join(linha["erros"])]
            # Evita interpretar conteudo da planilha como formula ao abrir o CSV.
            writer.writerow(["'" + str(v) if str(v).startswith(("=", "+", "-", "@")) else v for v in valores])
    return Response("\ufeff" + saida.getvalue(), mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pendencias_cartao_legado.csv"'})
