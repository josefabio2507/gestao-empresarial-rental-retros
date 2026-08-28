import os

from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.fiscal import fiscal_bp
from app.fiscal_drive_storage import MIME_PDF, MIME_XML, baixar_arquivo_fiscal_drive
from app.models import FiscalDocumento
from app.services.fiscal_service import (
    baixar_xml_completo_documento,
    buscar_certificados,
    buscar_controles_nsu,
    buscar_documentos_fiscais,
    consultar_documentos_sefaz,
    eventos_manifestacao_disponiveis,
    manifestar_documento_fiscal,
    rotulos_status_documento,
    salvar_certificado_a1,
    salvar_xml_documento,
)
from app.services.logs_service import registrar_log
from app.services.financeiro_contas_pagar_service import status_financeiro_xml, titulos_ativos_documento_fiscal


@fiscal_bp.route("/")
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "visualizar")
def index():
    return redirect(url_for("fiscal.documentos"))


@fiscal_bp.route("/documentos")
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "visualizar")
def documentos():
    return render_template(
        "fiscal/documentos.html",
        documentos=buscar_documentos_fiscais(request.args),
        filtros=request.args,
        certificados=buscar_certificados(),
        controles_nsu=buscar_controles_nsu(),
        status_documentos=rotulos_status_documento(),
        eventos_manifestacao=eventos_manifestacao_disponiveis(),
        status_financeiro_xml=status_financeiro_xml,
        titulos_ativos_documento_fiscal=titulos_ativos_documento_fiscal,
    )


@fiscal_bp.route("/documentos/importar-xml", methods=["POST"])
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "criar")
def importar_xml():
    sucesso, mensagem, documento = salvar_xml_documento(
        request.files.get("xml"),
        current_user,
        request.form.get("nsu"),
    )

    if sucesso and documento:
        registrar_log("fiscal_xml_importado", f"XML fiscal importado. Documento ID: {documento.id}.")

    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("fiscal.documentos"))


@fiscal_bp.route("/certificado", methods=["GET", "POST"])
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "editar")
def certificado():
    if request.method == "POST":
        sucesso, mensagem, certificado_a1 = salvar_certificado_a1(
            request.form,
            request.files.get("certificado"),
            current_user,
        )
        if sucesso and certificado_a1:
            registrar_log(
                "fiscal_certificado_a1_cadastrado",
                f"Certificado A1 cadastrado. ID: {certificado_a1.id}. CNPJ: {certificado_a1.cnpj_empresa}.",
            )
        flash(mensagem, "success" if sucesso else "danger")
        return redirect(url_for("fiscal.documentos"))

    return render_template("fiscal/certificado.html", certificados=buscar_certificados())


@fiscal_bp.route("/consultar-sefaz", methods=["POST"])
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "criar")
def consultar_sefaz():
    sucesso, mensagem, controle = consultar_documentos_sefaz(request.form.get("cnpj_empresa"))
    if controle:
        registrar_log("fiscal_consulta_nsu", f"Consulta fiscal registrada. Controle NSU ID: {controle.id}.")
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("fiscal.documentos"))


@fiscal_bp.route("/documentos/<int:documento_id>/manifestar", methods=["POST"])
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "editar")
def manifestar(documento_id):
    sucesso, mensagem, documento = manifestar_documento_fiscal(
        documento_id,
        request.form.get("evento"),
        current_user,
        request.form.get("justificativa"),
    )
    if documento:
        registrar_log(
            "fiscal_manifestacao_destinatario",
            f"Manifestacao registrada. Documento ID: {documento.id}. Evento: {request.form.get('evento')}.",
        )
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("fiscal.documentos"))


@fiscal_bp.route("/documentos/<int:documento_id>/baixar-xml-completo", methods=["POST"])
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "criar")
def baixar_xml_completo(documento_id):
    sucesso, mensagem, documento = baixar_xml_completo_documento(documento_id, current_user)
    if documento:
        registrar_log(
            "fiscal_xml_completo_baixado",
            f"Tentativa de download do XML completo. Documento ID: {documento.id}.",
        )
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for("fiscal.documentos"))


def _caminho_local_existente(caminho):
    if not caminho:
        return ""
    caminho_absoluto = caminho if os.path.isabs(caminho) else os.path.abspath(caminho)
    return caminho_absoluto if os.path.exists(caminho_absoluto) else ""


def _baixar_arquivo_documento_fiscal(documento, caminho, sufixo, chave_config_pasta, mime_type):
    nome_arquivo = f"{documento.chave_acesso}.{sufixo}"
    caminho_local = _caminho_local_existente(caminho)
    if caminho_local:
        return send_file(caminho_local, as_attachment=True, download_name=nome_arquivo)

    arquivo_drive = baixar_arquivo_fiscal_drive(nome_arquivo, chave_config_pasta, mime_type)
    if arquivo_drive:
        return send_file(
            arquivo_drive,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype=mime_type,
        )

    flash("Arquivo fiscal nao encontrado no servidor nem na pasta do Google Drive configurada.", "warning")
    return redirect(url_for("fiscal.documentos"))


@fiscal_bp.route("/documentos/<int:documento_id>/xml")
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "visualizar")
def baixar_xml(documento_id):
    documento = FiscalDocumento.query.get_or_404(documento_id)
    if not documento.xml_path:
        flash("XML completo ainda nao esta disponivel para esta NF-e.", "warning")
        return redirect(url_for("fiscal.documentos"))
    return _baixar_arquivo_documento_fiscal(
        documento,
        documento.xml_path,
        "xml",
        "FISCAL_XML_DIR",
        MIME_XML,
    )


@fiscal_bp.route("/documentos/<int:documento_id>/danfe")
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "visualizar")
def baixar_danfe(documento_id):
    documento = FiscalDocumento.query.get_or_404(documento_id)
    if not documento.danfe_path:
        flash("DANFE ainda nao foi gerado para esta NF-e.", "warning")
        return redirect(url_for("fiscal.documentos"))
    return _baixar_arquivo_documento_fiscal(
        documento,
        documento.danfe_path,
        "pdf",
        "FISCAL_DANFE_DIR",
        MIME_PDF,
    )