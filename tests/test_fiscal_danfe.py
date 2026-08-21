import os
import tempfile
import unittest
from types import SimpleNamespace

from app.fiscal_danfe import extrair_dados_danfe, gerar_danfe_pdf_xml


XML_DANFE = b"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35260846198081000187550040000017331693922800" versao="4.00">
      <ide>
        <cUF>35</cUF>
        <natOp>Venda de mercadoria</natOp>
        <mod>55</mod>
        <serie>4</serie>
        <nNF>1733</nNF>
        <dhEmi>2026-08-20T10:13:00-03:00</dhEmi>
        <tpNF>1</tpNF>
      </ide>
      <emit>
        <CNPJ>46198081000187</CNPJ>
        <xNome>COMERCIAL ALVORADA CENTER LTDA</xNome>
        <enderEmit>
          <xLgr>RUA TESTE</xLgr>
          <nro>100</nro>
          <xBairro>CENTRO</xBairro>
          <xMun>SAO PAULO</xMun>
          <UF>SP</UF>
          <CEP>01000000</CEP>
        </enderEmit>
        <IE>123456789</IE>
      </emit>
      <dest>
        <CNPJ>08026664000131</CNPJ>
        <xNome>RENTAL RETROS LOCACAO DE MAQUINAS E SERVICOS LTDA</xNome>
        <enderDest>
          <xLgr>AV RENTAL</xLgr>
          <nro>55</nro>
          <xBairro>INDUSTRIAL</xBairro>
          <xMun>GUARULHOS</xMun>
          <UF>SP</UF>
          <CEP>07000000</CEP>
        </enderDest>
        <IE>ISENTO</IE>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>OLEO01</cProd>
          <xProd>OLEO LUBRIFICANTE HIDRAULICO 68</xProd>
          <NCM>27101932</NCM>
          <CFOP>5102</CFOP>
          <uCom>UN</uCom>
          <qCom>2.0000</qCom>
          <vUnCom>72.2050</vUnCom>
          <vProd>144.41</vProd>
        </prod>
        <imposto>
          <ICMS><ICMS00><vICMS>25.99</vICMS><pICMS>18.00</pICMS></ICMS00></ICMS>
          <IPI><IPITrib><vIPI>0.00</vIPI><pIPI>0.00</pIPI></IPITrib></IPI>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vBC>144.41</vBC>
          <vICMS>25.99</vICMS>
          <vBCST>0.00</vBCST>
          <vST>0.00</vST>
          <vProd>144.41</vProd>
          <vFrete>0.00</vFrete>
          <vSeg>0.00</vSeg>
          <vDesc>0.00</vDesc>
          <vIPI>0.00</vIPI>
          <vNF>144.41</vNF>
        </ICMSTot>
      </total>
      <transp><modFrete>9</modFrete></transp>
      <infAdic><infCpl>Documento gerado para teste fiscal.</infCpl></infAdic>
    </infNFe>
  </NFe>
  <protNFe versao="4.00">
    <infProt>
      <chNFe>35260846198081000187550040000017331693922800</chNFe>
      <dhRecbto>2026-08-20T10:14:00-03:00</dhRecbto>
      <nProt>135260000000000</nProt>
    </infProt>
  </protNFe>
</nfeProc>
"""


class FiscalDanfeTestCase(unittest.TestCase):
    def test_extrai_dados_do_xml_para_danfe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = os.path.join(tmpdir, "nfe.xml")
            with open(xml_path, "wb") as arquivo:
                arquivo.write(XML_DANFE)

            dados = extrair_dados_danfe(xml_path)

        self.assertEqual(dados["numero"], "1733")
        self.assertEqual(dados["serie"], "4")
        self.assertEqual(dados["protocolo"], "135260000000000")
        self.assertEqual(dados["totais"]["nota"], "144,41")
        self.assertEqual(dados["produtos"][0]["descricao"], "OLEO LUBRIFICANTE HIDRAULICO 68")

    def test_gera_pdf_danfe_completo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = os.path.join(tmpdir, "nfe.xml")
            pdf_path = os.path.join(tmpdir, "danfe.pdf")
            with open(xml_path, "wb") as arquivo:
                arquivo.write(XML_DANFE)

            documento = SimpleNamespace(
                chave_acesso="35260846198081000187550040000017331693922800",
                xml_path=xml_path,
            )
            gerar_danfe_pdf_xml(documento, pdf_path)

            self.assertTrue(os.path.exists(pdf_path))
            with open(pdf_path, "rb") as arquivo:
                conteudo = arquivo.read()

        self.assertTrue(conteudo.startswith(b"%PDF"))
        self.assertGreater(len(conteudo), 2000)


if __name__ == "__main__":
    unittest.main()
