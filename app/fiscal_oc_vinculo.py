import os

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.models import FiscalDocumento
from app.services import fiscal_service
from app.utils.datas import agora_brasil


def _cnpj_fornecedor_ordem(ordem):
    return fiscal_service.somente_digitos(ordem.fornecedor_cnpj_cpf_snapshot)


def _documento_pode_aparecer_para_ordem(documento, ordem, cnpj_fornecedor):
    if not documento.tem_xml_completo or not documento.xml_path:
        return False
    if documento.ordem_compra_id not in (None, ordem.id):
        return False
    return fiscal_service.somente_digitos(documento.emitente_cnpj) == cnpj_fornecedor


def buscar_documentos_para_ordem_compra(ordem):
    cnpj_fornecedor = _cnpj_fornecedor_ordem(ordem)
    if not cnpj_fornecedor:
        return []

    documentos_candidatos = (
        FiscalDocumento.query
        .filter(
            FiscalDocumento.tem_xml_completo.is_(True),
            FiscalDocumento.xml_path.isnot(None),
            or_(
                FiscalDocumento.ordem_compra_id.is_(None),
                FiscalDocumento.ordem_compra_id == ordem.id,
            ),
        )
        .order_by(FiscalDocumento.data_emissao.desc(), FiscalDocumento.id.desc())
        .all()
    )
    documentos = [
        documento
        for documento in documentos_candidatos
        if _documento_pode_aparecer_para_ordem(documento, ordem, cnpj_fornecedor)
    ]

    current_app.logger.info(
        "[fiscal_oc_vinculo] Busca NF-e para OC %s. CNPJ fornecedor: %s. Candidatas: %s. Encontradas: %s.",
        ordem.numero,
        cnpj_fornecedor,
        len(documentos_candidatos),
        len(documentos),
    )
    return documentos


def vincular_documento_ordem_compra(documento_id, ordem, usuario):
    try:
        documento_id = int(documento_id)
    except (TypeError, ValueError):
        return False, "Documento fiscal não encontrado.", None

    documento = db.session.get(FiscalDocumento, documento_id)
    cnpj_fornecedor = _cnpj_fornecedor_ordem(ordem)

    if not documento:
        return False, "Documento fiscal não encontrado.", None
    if ordem.status == "Cancelada":
        return False, "O.C. cancelada não pode receber vínculo fiscal.", None
    if documento.ordem_compra_id and documento.ordem_compra_id != ordem.id:
        return False, "Documento fiscal já vinculado a outra O.C.", None
    if not documento.tem_xml_completo or not documento.xml_path:
        return False, "A NF-e ainda nao possui XML completo disponivel para vinculo com O.C.", None
    if fiscal_service.somente_digitos(documento.emitente_cnpj) != cnpj_fornecedor:
        return False, "O emitente da NF-e não corresponde ao fornecedor da O.C.", None

    if not documento.danfe_path or not os.path.exists(documento.danfe_path):
        documento.danfe_path = fiscal_service.gerar_danfe_pdf(documento)

    documento.ordem_compra_id = ordem.id
    documento.vinculado_por_usuario_id = usuario.id
    documento.vinculado_em = agora_brasil()
    documento.status = fiscal_service.STATUS_VINCULADO_OC
    db.session.commit()
    return True, "NF-e vinculada à O.C. e DANFE associado automaticamente.", documento


def aplicar_busca_documentos_oc(_app=None):
    fiscal_service.buscar_documentos_para_ordem_compra = buscar_documentos_para_ordem_compra
    fiscal_service.vincular_documento_ordem_compra = vincular_documento_ordem_compra
