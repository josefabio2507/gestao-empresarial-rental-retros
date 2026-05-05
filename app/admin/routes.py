from flask import render_template, request
from flask_login import login_required

from app.admin import admin_bp
from app.decorators import admin_required
from app.services.logs_service import buscar_logs, buscar_usuarios_com_logs


@admin_bp.route("/")
@login_required
@admin_required
def index():
    return render_template("admin/index.html")


@admin_bp.route("/logs")
@login_required
@admin_required
def logs():
    usuario_id = request.args.get("usuario_id", "").strip()
    acao = request.args.get("acao", "").strip()
    data_inicial = request.args.get("data_inicial", "").strip()
    data_final = request.args.get("data_final", "").strip()

    logs_lista = buscar_logs(
        usuario_id=usuario_id if usuario_id else None,
        acao=acao if acao else None,
        data_inicial=data_inicial if data_inicial else None,
        data_final=data_final if data_final else None,
        limite=500,
    )
    usuarios = buscar_usuarios_com_logs()

    return render_template(
        "admin/logs.html",
        logs=logs_lista,
        usuarios=usuarios,
        filtros={
            "usuario_id": usuario_id,
            "acao": acao,
            "data_inicial": data_inicial,
            "data_final": data_final,
        },
    )
