"""Ajustes de inicializacao do runtime Python.

Este arquivo e carregado automaticamente pelo Python quando o projeto esta no
PYTHONPATH. Mantem uma correcao pontual para a Missao 16 enquanto o modulo
fiscal concentra a integracao direta com a Sefaz.
"""

import builtins
import sys

_ORIGINAL_IMPORT = builtins.__import__
_PATCH_APLICADO = False


def _aplicar_patch_manifestacao_fiscal():
    global _PATCH_APLICADO
    if _PATCH_APLICADO:
        return

    fiscal_service = sys.modules.get("app.services.fiscal_service")
    if fiscal_service is None:
        return

    adaptador = getattr(fiscal_service, "SefazManifestacaoDestinatarioAdapter", None)
    etree = getattr(fiscal_service, "etree", None)
    if adaptador is None or etree is None:
        return

    def _envelope_soap_com_cabecalho(self, xml_evento):
        envelope = etree.Element(
            etree.QName(fiscal_service.NAMESPACE_SOAP12, "Envelope"),
            nsmap={"soap12": fiscal_service.NAMESPACE_SOAP12},
        )
        header = etree.SubElement(envelope, etree.QName(fiscal_service.NAMESPACE_SOAP12, "Header"))
        cabecalho = etree.SubElement(
            header,
            etree.QName(fiscal_service.NAMESPACE_RECEPCAO_EVENTO, "nfeCabecMsg"),
        )
        etree.SubElement(
            cabecalho,
            etree.QName(fiscal_service.NAMESPACE_RECEPCAO_EVENTO, "cUF"),
        ).text = fiscal_service.CODIGO_ORGAO_MANIFESTACAO_DESTINATARIO
        etree.SubElement(
            cabecalho,
            etree.QName(fiscal_service.NAMESPACE_RECEPCAO_EVENTO, "versaoDados"),
        ).text = fiscal_service.VERSAO_ENVIO_EVENTO

        body = etree.SubElement(envelope, etree.QName(fiscal_service.NAMESPACE_SOAP12, "Body"))
        dados = etree.SubElement(
            body,
            etree.QName(fiscal_service.NAMESPACE_RECEPCAO_EVENTO, "nfeDadosMsg"),
        )
        dados.append(etree.fromstring(xml_evento))
        return etree.tostring(envelope, encoding="utf-8", xml_declaration=True)

    adaptador._envelope_soap = _envelope_soap_com_cabecalho
    _PATCH_APLICADO = True


def _import_hook(name, globals=None, locals=None, fromlist=(), level=0):
    modulo = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    if name == "app.services.fiscal_service" or name.startswith("app.services") or name == "app":
        _aplicar_patch_manifestacao_fiscal()
    return modulo


builtins.__import__ = _import_hook
_aplicar_patch_manifestacao_fiscal()
