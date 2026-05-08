from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_tem_permissao
from app.departamento_pessoal.documentos.services import (
    buscar_holerite_por_id,
    buscar_holerites_visiveis,
    usuario_deve_ver_apenas_proprios_holerites,
    usuario_pode_acessar_holerite,
)


documentos_bp = Blueprint("documentos", __name__)

DEPARTAMENTO_DOCUMENTOS_PESSOAIS = "documentos_pessoais"
MODULO_HOLERITES = "holerites"


def pode_visualizar_holerites():
    return usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_DOCUMENTOS_PESSOAIS,
        MODULO_HOLERITES,
        "visualizar",
    )


def pode_exportar_holerites():
    return usuario_tem_permissao(
        current_user,
        DEPARTAMENTO_DOCUMENTOS_PESSOAIS,
        MODULO_HOLERITES,
        "exportar",
    )


def bloquear_sem_visualizacao():
    if pode_visualizar_holerites():
        return None

    flash("Você não possui permissão para acessar Holerites.", "danger")
    return redirect(url_for("main.acesso_negado"))


@documentos_bp.route("/")
@login_required
def index():
    bloqueio = bloquear_sem_visualizacao()

    if bloqueio:
        return bloqueio

    return render_template(
        "departamento_pessoal/documentos/index.html",
        pode_visualizar_holerites=True,
    )


@documentos_bp.route("/holerites")
@login_required
def holerites():
    bloqueio = bloquear_sem_visualizacao()

    if bloqueio:
        return bloqueio

    holerites_lista = buscar_holerites_visiveis(current_user)
    apenas_proprios = usuario_deve_ver_apenas_proprios_holerites(current_user)

    registrar_log(
        "holerites_visualizados",
        f"Usuário ID {current_user.id} acessou módulo Holerites.",
    )

    return render_template(
        "departamento_pessoal/documentos/holerites.html",
        holerites=holerites_lista,
        pode_exportar=pode_exportar_holerites(),
        apenas_proprios=apenas_proprios,
    )


@documentos_bp.route("/holerites/<int:holerite_id>/exportar")
@login_required
def exportar_holerite(holerite_id):
    if not pode_exportar_holerites():
        flash("Você não possui permissão para exportar holerites.", "danger")
        return redirect(url_for("main.acesso_negado"))

    holerite = buscar_holerite_por_id(holerite_id)

    if not usuario_pode_acessar_holerite(current_user, holerite):
        flash("Holerite não encontrado ou indisponível para o seu usuário.", "warning")
        return redirect(url_for("documentos.holerites"))

    registrar_log(
        "holerite_exportado",
        f"Usuário ID {current_user.id} exportou holerite ID {holerite.id}.",
    )

    if holerite.google_drive_url:
        return redirect(holerite.google_drive_url)

    flash(
        "Arquivo preparado para integração. A exportação será habilitada quando o documento estiver vinculado.",
        "info",
    )
    return redirect(url_for("documentos.holerites"))
