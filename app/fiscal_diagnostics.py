"""Diagnosticos seguros para integracoes fiscais.

Nao registra XML completo, certificado, assinatura, CNPJ, chave completa ou
conteudo fiscal sensivel. O objetivo e expor apenas a estrutura enviada para
identificar rejeicoes de schema retornadas pela Sefaz.
"""

_PATCH_APLICADO = False

_TAGS_COM_VALOR_SANEADO = {
    "cOrgao",
    "tpAmb",
    "tpEvento",
    "nSeqEvento",
    "verEvento",
    "descEvento",
    "versaoDados",
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
        item = {
            "nivel": len(elemento.xpath("ancestor::*")),
            "tag": qname.localname,
            "ns": qname.namespace or "",
        }
        if elemento.attrib:
            item["attrs"] = _atributos_saneados(elemento.attrib)
        valor = _resumo_valor(elemento, qname.localname)
        if valor is not None:
            item["valor"] = valor
        estrutura.append(item)
    return estrutura[:140]


def aplicar_diagnostico_manifestacao(app):
    global _PATCH_APLICADO
    if _PATCH_APLICADO:
        return

    from app.services import fiscal_service

    adaptador = fiscal_service.SefazManifestacaoDestinatarioAdapter
    etree = fiscal_service.etree
    montar_original = adaptador._montar_xml_evento_assinado
    envelope_original = adaptador._envelope_soap

    def _montar_xml_evento_assinado_com_diagnostico(self, cnpj, chave_acesso, evento_codigo, justificativa=None):
        xml_evento = montar_original(
            self,
            cnpj,
            chave_acesso,
            evento_codigo,
            justificativa=justificativa,
        )
        try:
            app.logger.info(
                "[fiscal_manifestacao_xml_estrutura] chave_len=%s evento=%s estrutura=%s",
                len(chave_acesso or ""),
                evento_codigo,
                _estrutura_xml(fiscal_service, xml_evento),
            )
        except Exception as exc:
            app.logger.warning(
                "[fiscal_manifestacao_xml_estrutura] Nao foi possivel registrar estrutura XML: %s",
                exc,
            )
        return xml_evento

    def _envelope_soap_com_cabecalho_e_diagnostico(self, xml_evento):
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
            app.logger.info(
                "[fiscal_manifestacao_soap_estrutura] estrutura=%s",
                _estrutura_xml(fiscal_service, envelope_xml),
            )
        except Exception as exc:
            app.logger.warning(
                "[fiscal_manifestacao_soap_estrutura] Nao foi possivel registrar estrutura SOAP: %s",
                exc,
            )
        return envelope_xml

    adaptador._montar_xml_evento_assinado = _montar_xml_evento_assinado_com_diagnostico
    adaptador._envelope_soap = _envelope_soap_com_cabecalho_e_diagnostico
    _PATCH_APLICADO = True
    app.logger.info(
        "[fiscal_manifestacao_patch] Diagnostico estrutural explicito da manifestacao fiscal ativo. "
        "Envelope original preservado para referencia: %s",
        getattr(envelope_original, "__name__", "_envelope_soap"),
    )
