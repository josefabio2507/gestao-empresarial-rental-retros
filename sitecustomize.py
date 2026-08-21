"""Ajustes de inicializacao do runtime Python.

Este arquivo e carregado automaticamente pelo Python quando o projeto esta no
PYTHONPATH. Mantem correcoes pontuais para a Missao 16 enquanto o modulo fiscal
concentra a integracao direta com a Sefaz.
"""

import builtins
import sys

_ORIGINAL_IMPORT = builtins.__import__
_PATCH_APLICADO = False

_TAGS_COM_VALOR_SANEADO = {
    "cOrgao",
    "tpAmb",
    "tpEvento",
    "nSeqEvento",
    "verEvento",
    "descEvento",
}

_ATRIBUTOS_PERMITIDOS = {"versao", "Algorithm", "URI"}


def _resumo_valor(elemento, nome):
    texto = (elemento.text or "").strip()
    if not texto:
        return None
    if nome in _TAGS_COM_VALOR_SANEADO:
        return texto
    return f"len:{len(texto)}"


def _atributos_saneados(atributos):
    saneados = {}
    for chave, valor in atributos.items():
        nome = str(chave).split("}")[-1]
        if nome in _ATRIBUTOS_PERMITIDOS:
            saneados[nome] = valor
        elif nome == "Id":
            saneados[nome] = f"prefix:{str(valor)[:8]} len:{len(str(valor))}"
        else:
            saneados[nome] = f"len:{len(str(valor))}"
    return saneados


def _estrutura_xml(fiscal_service, xml_bytes):
    etree = fiscal_service.etree
    raiz = etree.fromstring(xml_bytes)
    estrutura = []
    for elemento in raiz.iter():
        qname = etree.QName(elemento)
        profundidade = len(elemento.xpath("ancestor::*"))
        item = {
            "nivel": profundidade,
            "tag": qname.localname,
            "ns": qname.namespace or "",
        }
        if elemento.attrib:
            item["attrs"] = _atributos_saneados(elemento.attrib)
        valor = _resumo_valor(elemento, qname.localname)
        if valor is not None:
            item["valor"] = valor
        estrutura.append(item)
    return estrutura[:120]


def _aplicar_patch_manifestacao_fiscal():
    global _PATCH_APLICADO
    if _PATCH_APLICADO:
        return

    fiscal_service = sys.modules.get("app.services.fiscal_service")
    if fiscal_service is None:
        return

    adaptador = getattr(fiscal_service, "SefazManifestacaoDestinatarioAdapter", None)
    etree = getattr(fiscal_service, "etree", None)
    current_app = getattr(fiscal_service, "current_app", None)
    if adaptador is None or etree is None or current_app is None:
        return

    montar_original = adaptador._montar_xml_evento_assinado

    def _montar_xml_evento_assinado_com_diagnostico(self, cnpj, chave_acesso, evento_codigo, justificativa=None):
        xml_evento = montar_original(
            self,
            cnpj,
            chave_acesso,
            evento_codigo,
            justificativa=justificativa,
        )
        try:
            current_app.logger.info(
                "[fiscal_manifestacao_xml_estrutura] NF-e len=%s evento=%s estrutura=%s",
                len(chave_acesso or ""),
                evento_codigo,
                _estrutura_xml(fiscal_service, xml_evento),
            )
        except Exception as exc:
            current_app.logger.warning(
                "[fiscal_manifestacao_xml_estrutura] Nao foi possivel registrar estrutura XML: %s",
                exc,
            )
        return xml_evento

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
        envelope_xml = etree.tostring(envelope, encoding="utf-8", xml_declaration=True)
        try:
            current_app.logger.info(
                "[fiscal_manifestacao_soap_estrutura] estrutura=%s",
                _estrutura_xml(fiscal_service, envelope_xml),
            )
        except Exception as exc:
            current_app.logger.warning(
                "[fiscal_manifestacao_soap_estrutura] Nao foi possivel registrar estrutura SOAP: %s",
                exc,
            )
        return envelope_xml

    adaptador._montar_xml_evento_assinado = _montar_xml_evento_assinado_com_diagnostico
    adaptador._envelope_soap = _envelope_soap_com_cabecalho
    _PATCH_APLICADO = True
    try:
        current_app.logger.info("[fiscal_manifestacao_patch] Diagnostico estrutural da manifestacao fiscal ativo.")
    except Exception:
        pass


def _import_hook(name, globals=None, locals=None, fromlist=(), level=0):
    modulo = _ORIGINAL_IMPORT(name, globals, locals, fromlist, level)
    if name == "app.services.fiscal_service" or name.startswith("app.services") or name == "app":
        _aplicar_patch_manifestacao_fiscal()
    return modulo


builtins.__import__ = _import_hook
_aplicar_patch_manifestacao_fiscal()
