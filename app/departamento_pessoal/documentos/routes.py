from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.services.logs_service import registrar_log
from app.services.permissoes_service import usuario_eh_administrador, usuario_tem_permissao
from app.departamento_pessoal.documentos.services import (
    buscar_holerite_por_id,
    buscar_holerites_visiveis,
    usuario_deve_ver_apenas_proprios_holerites,
    usuario_pode_acessar_holerite,
)
from app.services.holerites_drive_service import sincronizar_holerites_google_drive


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


def pode_sincronizar_holerites():
    return usuario_eh_administrador(current_user)


def renderizar_holerites(resumo_sincronizacao=None):
    holerites_lista = buscar_holerites_visiveis(current_user)
    apenas_proprios = usuario_deve_ver_apenas_proprios_holerites(current_user)

    return render_template(
        "departamento_pessoal/documentos/holerites.html",
        holerites=holerites_lista,
        pode_exportar=pode_exportar_holerites(),
        pode_sincronizar=pode_sincronizar_holerites(),
        apenas_proprios=apenas_proprios,
        resumo_sincronizacao=resumo_sincronizacao,
    )


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

    registrar_log(
        "holerites_visualizados",
        f"Usuário ID {current_user.id} acessou módulo Holerites.",
    )

    return renderizar_holerites()


@documentos_bp.route("/holerites/sincronizar", methods=["POST"])
@login_required
def sincronizar_holerites():
    bloqueio = bloquear_sem_visualizacao()

    if bloqueio:
        return bloqueio

    if not pode_sincronizar_holerites():
        flash("A sincronização de holerites é restrita ao administrador.", "danger")
        return redirect(url_for("main.acesso_negado"))

    resumo = sincronizar_holerites_google_drive(usuario_id=current_user.id)

    registrar_log(
        "holerites_sincronizados_google_drive",
        (
            f"Usuário ID {current_user.id} sincronizou holerites. "
            f"Importados: {resumo['importados']}, "
            f"já existentes: {resumo['ja_existentes']}, "
            f"erros: {resumo['erros']}."
        ),
    )

    if resumo["erros"]:
        flash("Sincronização concluída com pendências.", "warning")
    else:
        flash("Sincronização concluída.", "success")

    return renderizar_holerites(resumo_sincronizacao=resumo)


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
