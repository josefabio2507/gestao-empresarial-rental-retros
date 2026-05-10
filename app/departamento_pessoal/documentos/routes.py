from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from itsdangerous import BadSignature, URLSafeSerializer

from app.services.logs_service import registrar_log
from app.services.permissoes_service import (
    usuario_eh_administrador,
    usuario_tem_permissao_holerites,
)
from app.departamento_pessoal.documentos.services import (
    buscar_holerite_por_id,
    buscar_holerites_visiveis,
    usuario_deve_ver_apenas_proprios_holerites,
    usuario_pode_acessar_holerite,
)
from app.services.holerites_drive_service import (
    normalizar_competencia_informada,
    sincronizar_holerites_google_drive,
)


documentos_bp = Blueprint("documentos", __name__)

SYNC_CURSOR_SALT = "holerites-google-drive-sync"


def _cursor_serializer():
    return URLSafeSerializer(
        current_app.config["SECRET_KEY"],
        salt=SYNC_CURSOR_SALT,
    )


def codificar_cursor_sincronizacao(estado):
    if not estado:
        return None

    return _cursor_serializer().dumps(estado)


def decodificar_cursor_sincronizacao(token):
    if not token:
        return None

    try:
        return _cursor_serializer().loads(token)
    except BadSignature:
        flash("A continuação da sincronização expirou. Inicie um novo lote.", "warning")
        return None


def pode_visualizar_holerites():
    return usuario_tem_permissao_holerites(current_user, "visualizar")


def pode_exportar_holerites():
    return usuario_tem_permissao_holerites(current_user, "exportar")


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

    cursor = request.form.get("cursor")
    estado = decodificar_cursor_sincronizacao(cursor)
    competencia = None

    if not cursor:
        competencia = normalizar_competencia_informada(
            request.form.get("competencia"),
        )

        if not competencia:
            flash("Informe uma competência válida no formato MM/AAAA.", "warning")
            return renderizar_holerites()

    resumo = sincronizar_holerites_google_drive(
        usuario_id=current_user.id,
        estado=estado,
        competencia_filtro=competencia,
    )
    resumo["proximo_cursor"] = codificar_cursor_sincronizacao(
        resumo.get("proximo_estado"),
    )

    registrar_log(
        "holerites_sincronizados_google_drive",
        (
            f"Usuário ID {current_user.id} sincronizou holerites. "
            f"Lote: {resumo['arquivos_processados_lote']}, "
            f"Competência: {resumo['competencia_processada'] or 'geral'}, "
            f"Importados: {resumo['importados']}, "
            f"já existentes: {resumo['ja_existentes']}, "
            f"erros: {resumo['erros']}, "
            f"concluído: {resumo['concluido']}."
        ),
    )

    if resumo["erros"]:
        flash("Lote de sincronização concluído com pendências.", "warning")
    elif resumo["concluido"]:
        flash("Sincronização concluída.", "success")
    else:
        flash("Lote de sincronização processado. Continue para avançar.", "info")

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
