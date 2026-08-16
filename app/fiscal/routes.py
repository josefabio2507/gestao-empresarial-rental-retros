from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.decorators import module_permission_required
from app.fiscal import fiscal_bp
from app.models import FiscalDocumento
from app.services.fiscal_service import (
    buscar_certificados,
    buscar_controles_nsu,
    buscar_documentos_fiscais,
    consultar_documentos_sefaz,
    salvar_certificado_a1,
    salvar_xml_documento,
)
from app.services.logs_service import registrar_log


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


@fiscal_bp.route("/documentos/<int:documento_id>/xml")
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "visualizar")
def baixar_xml(documento_id):
    documento = FiscalDocumento.query.get_or_404(documento_id)
    return send_file(documento.xml_path, as_attachment=True, download_name=f"{documento.chave_acesso}.xml")


@fiscal_bp.route("/documentos/<int:documento_id>/danfe")
@login_required
@module_permission_required("fiscal", "documentos_fiscais", "visualizar")
def baixar_danfe(documento_id):
    documento = FiscalDocumento.query.get_or_404(documento_id)
    return send_file(documento.danfe_path, as_attachment=True, download_name=f"{documento.chave_acesso}.pdf")
