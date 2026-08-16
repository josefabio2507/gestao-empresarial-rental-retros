import os
import base64
import gzip
import tempfile
import unittest
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from werkzeug.datastructures import FileStorage
from werkzeug.security import check_password_hash

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    FiscalCertificadoA1,
    FiscalControleNSU,
    FiscalDocumento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosOrdemCompra,
    Usuario,
)
from app.services.fiscal_service import (
    buscar_documentos_para_ordem_compra,
    consultar_documentos_sefaz,
    salvar_certificado_a1,
    salvar_xml_documento,
    vincular_documento_ordem_compra,
)


XML_NFE = b"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35260811222333000181550010000001231000001234" versao="4.00">
      <ide>
        <natOp>Venda de mercadoria</natOp>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>123</nNF>
        <dhEmi>2026-08-15T10:30:00-03:00</dhEmi>
      </ide>
      <emit>
        <CNPJ>11222333000181</CNPJ>
        <xNome>Fornecedor Teste LTDA</xNome>
      </emit>
      <dest>
        <CNPJ>44555666000177</CNPJ>
        <xNome>Rental Retros LTDA</xNome>
      </dest>
      <total>
        <ICMSTot>
          <vNF>251.00</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
</nfeProc>
"""


class FiscalDocumentosTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            FISCAL_XML_DIR=os.path.join(self.tmp.name, "xmls"),
            FISCAL_DANFE_DIR=os.path.join(self.tmp.name, "danfes"),
            FISCAL_CERTIFICADOS_DIR=os.path.join(self.tmp.name, "certificados"),
        )

        self.contexto = self.app.app_context()
        self.contexto.push()
        db.drop_all()
        db.create_all()

        admin = NivelAcesso(nome="Administrador", slug="administrador", ativo=True)
        comum = NivelAcesso(nome="Usuario", slug="usuario", ativo=True)
        db.session.add_all([admin, comum])
        db.session.flush()

        self.admin = Usuario(
            nome="Admin",
            email="admin.fiscal@teste.com",
            nivel_acesso=admin,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario = Usuario(
            nome="Comum",
            email="comum.fiscal@teste.com",
            nivel_acesso=comum,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])

        fiscal = Departamento(nome="Fiscal", slug="fiscal", ativo=True, ordem=6)
        suprimentos = Departamento(nome="Suprimentos", slug="suprimentos", ativo=True, ordem=2)
        db.session.add_all([fiscal, suprimentos])
        db.session.flush()

        self.modulo_fiscal = Modulo(
            departamento_id=fiscal.id,
            nome="Documentos Fiscais",
            slug="documentos_fiscais",
            ativo=True,
            ordem=1,
        )
        self.modulo_oc = Modulo(
            departamento_id=suprimentos.id,
            nome="Ordens de Compra",
            slug="ordens_compra",
            ativo=True,
            ordem=9,
        )
        db.session.add_all([self.modulo_fiscal, self.modulo_oc])
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()
        self.tmp.cleanup()

    def _arquivo_xml(self):
        return FileStorage(
            stream=BytesIO(XML_NFE),
            filename="nfe.xml",
            content_type="text/xml",
        )

    def _arquivo_certificado(self):
        return FileStorage(
            stream=BytesIO(b"certificado fake"),
            filename="rental.pfx",
            content_type="application/x-pkcs12",
        )

    def _retorno_distribuicao_dfe(self):
        doc_zip = base64.b64encode(gzip.compress(XML_NFE)).decode()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<retDistDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
  <tpAmb>1</tpAmb>
  <verAplic>TESTE</verAplic>
  <cStat>138</cStat>
  <xMotivo>Documento localizado</xMotivo>
  <dhResp>2026-08-15T22:30:00-03:00</dhResp>
  <ultNSU>101</ultNSU>
  <maxNSU>101</maxNSU>
  <loteDistDFeInt>
    <docZip NSU="101" schema="procNFe_v4.00.xsd">{doc_zip}</docZip>
  </loteDistDFeInt>
</retDistDFeInt>
"""

    class FakePyNFeClient:
        chamadas = []
        resposta = ""

        def __init__(self, certificado_path, senha, uf, homologacao):
            self.__class__.chamadas.append(
                {
                    "certificado_path": certificado_path,
                    "senha": senha,
                    "uf": uf,
                    "homologacao": homologacao,
                }
            )

        def consultar(self, cnpj, ultimo_nsu):
            self.__class__.chamadas[-1]["cnpj"] = cnpj
            self.__class__.chamadas[-1]["ultimo_nsu"] = ultimo_nsu
            return self.__class__.resposta

    def _autenticar(self, usuario):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True

    def _liberar_usuario(self, modulo, **acoes):
        permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=modulo.id,
            pode_visualizar=acoes.get("visualizar", False),
            pode_criar=acoes.get("criar", False),
            pode_editar=acoes.get("editar", False),
            pode_excluir=acoes.get("excluir", False),
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def _criar_ordem_compra_minima(self, cnpj="11222333000181"):
        ordem = SuprimentosOrdemCompra(
            numero="OC-TESTE",
            cotacao_id=1,
            requisicao_id=1,
            fornecedor_id=1,
            criado_por_usuario_id=self.admin.id,
            fornecedor_razao_social_snapshot="FORNECEDOR TESTE LTDA",
            fornecedor_cnpj_cpf_snapshot=cnpj,
            status="Gerada",
        )
        db.session.add(ordem)
        db.session.commit()
        return ordem

    def test_importa_xml_gera_danfe_e_metadados(self):
        sucesso, mensagem, documento = salvar_xml_documento(self._arquivo_xml(), self.admin, "100")

        self.assertTrue(sucesso)
        self.assertEqual("XML armazenado e DANFE gerado com sucesso.", mensagem)
        self.assertEqual("123", documento.numero)
        self.assertEqual("11222333000181", documento.emitente_cnpj)
        self.assertEqual("44555666000177", documento.destinatario_cnpj)
        self.assertTrue(os.path.exists(documento.xml_path))
        self.assertTrue(os.path.exists(documento.danfe_path))
        self.assertEqual(1, FiscalDocumento.query.count())

    def test_vincula_documento_a_ordem_compra_por_cnpj_fornecedor(self):
        _, _, documento = salvar_xml_documento(self._arquivo_xml(), self.admin, "100")
        ordem = self._criar_ordem_compra_minima()

        disponiveis = buscar_documentos_para_ordem_compra(ordem)
        self.assertEqual([documento], disponiveis)

        sucesso, mensagem, vinculado = vincular_documento_ordem_compra(documento.id, ordem, self.admin)

        self.assertTrue(sucesso)
        self.assertEqual("NF-e vinculada à O.C. e DANFE associado automaticamente.", mensagem)
        self.assertEqual(ordem.id, vinculado.ordem_compra_id)
        self.assertEqual("Vinculado", vinculado.status)
        self.assertIsNotNone(vinculado.vinculado_em)
        self.assertEqual([], buscar_documentos_para_ordem_compra(ordem))

    def test_bloqueia_vinculo_com_cnpj_diferente(self):
        _, _, documento = salvar_xml_documento(self._arquivo_xml(), self.admin, "100")
        ordem = self._criar_ordem_compra_minima("99999999000199")

        sucesso, mensagem, vinculado = vincular_documento_ordem_compra(documento.id, ordem, self.admin)

        self.assertFalse(sucesso)
        self.assertEqual("O emitente da NF-e não corresponde ao fornecedor da O.C.", mensagem)
        self.assertIsNone(vinculado)

    def test_salva_certificado_sem_expor_senha(self):
        sucesso, mensagem, certificado = salvar_certificado_a1(
            {
                "cnpj_empresa": "44.555.666/0001-77",
                "razao_social": "Rental Retros LTDA",
                "senha": "segredo",
            },
            self._arquivo_certificado(),
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Certificado A1 cadastrado com segurança.", mensagem)
        self.assertTrue(os.path.exists(certificado.arquivo_path))
        self.assertNotEqual("segredo", certificado.senha_hash)
        self.assertTrue(check_password_hash(certificado.senha_hash, "segredo"))
        self.assertEqual(1, FiscalCertificadoA1.query.count())

    def test_certificado_com_chave_criptografia_invalida_retorna_erro_amigavel(self):
        self.app.config["FISCAL_CERTIFICADO_CRYPTO_KEY"] = "chave-invalida"

        sucesso, mensagem, certificado = salvar_certificado_a1(
            {
                "cnpj_empresa": "44.555.666/0001-77",
                "razao_social": "Rental Retros LTDA",
                "senha": "segredo",
            },
            self._arquivo_certificado(),
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertIn("FISCAL_CERTIFICADO_CRYPTO_KEY invalida", mensagem)
        self.assertIsNone(certificado)
        self.assertEqual(0, FiscalCertificadoA1.query.count())

    def test_consulta_nsu_sem_certificado_orienta_cadastro(self):
        sucesso, mensagem, controle = consultar_documentos_sefaz("44.555.666/0001-77")

        self.assertFalse(sucesso)
        self.assertIn("Cadastre um certificado A1 ativo", mensagem)
        self.assertEqual("44555666000177", controle.cnpj_empresa)
        self.assertEqual("Aguardando certificado", controle.status)
        self.assertEqual(1, FiscalControleNSU.query.count())

    def test_consulta_nsu_com_cliente_pynfe_importa_xml_e_atualiza_controle(self):
        sucesso, _, certificado = salvar_certificado_a1(
            {
                "cnpj_empresa": "44.555.666/0001-77",
                "razao_social": "Rental Retros LTDA",
                "senha": "segredo",
            },
            self._arquivo_certificado(),
            self.admin,
        )
        self.assertTrue(sucesso)
        self.assertIsNotNone(certificado.senha_criptografada)
        self.FakePyNFeClient.chamadas = []
        self.FakePyNFeClient.resposta = self._retorno_distribuicao_dfe()

        sucesso, mensagem, controle = consultar_documentos_sefaz(
            "44.555.666/0001-77",
            cliente_cls=self.FakePyNFeClient,
        )

        self.assertTrue(sucesso)
        self.assertIn("XMLs importados: 1", mensagem)
        self.assertEqual("Consultado", controle.status)
        self.assertEqual("101", controle.ultimo_nsu)
        self.assertEqual("101", controle.max_nsu)
        self.assertEqual(1, FiscalDocumento.query.count())
        chamada = self.FakePyNFeClient.chamadas[0]
        self.assertEqual(certificado.arquivo_path, chamada["certificado_path"])
        self.assertEqual("segredo", chamada["senha"])
        self.assertEqual("sp", chamada["uf"])
        self.assertFalse(chamada["homologacao"])
        self.assertEqual("44555666000177", chamada["cnpj"])
        self.assertEqual("0", chamada["ultimo_nsu"])

    def test_rota_documentos_fiscais_exige_permissao(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/fiscal/documentos")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_rota_documentos_fiscais_com_permissao(self):
        self._liberar_usuario(self.modulo_fiscal, visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/fiscal/documentos")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Documentos Fiscais", resposta.data)


if __name__ == "__main__":
    unittest.main()
