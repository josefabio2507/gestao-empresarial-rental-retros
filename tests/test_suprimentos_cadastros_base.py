import unittest

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosCategoriaItem,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.suprimentos_service import (
    consultar_cnpj_publico,
    salvar_categoria,
    salvar_centro_custo,
    salvar_fornecedor,
    salvar_item,
    salvar_unidade,
    salvar_vinculo_fornecedor_item,
    validar_cnpj,
    validar_cpf,
)


class SuprimentosCadastrosBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
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
            email="admin@teste.com",
            nivel_acesso=admin,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario = Usuario(
            nome="Comum",
            email="comum@teste.com",
            nivel_acesso=comum,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])

        self.departamento = Departamento(
            nome="Suprimentos",
            slug="suprimentos",
            descricao="Teste",
            ativo=True,
            ordem=2,
        )
        db.session.add(self.departamento)
        db.session.flush()

        self.modulos = {}
        for ordem, slug in enumerate(
            [
                "fornecedores",
                "categorias",
                "unidades_medida",
                "itens",
                "centros_custo",
                "fornecedor_itens",
            ],
            start=1,
        ):
            modulo = Modulo(
                departamento_id=self.departamento.id,
                nome=slug.replace("_", " ").title(),
                slug=slug,
                ativo=True,
                ordem=ordem,
            )
            db.session.add(modulo)
            self.modulos[slug] = modulo

        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _autenticar(self, usuario):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True

    def _liberar(self, slug, **acoes):
        permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=self.modulos[slug].id,
            pode_visualizar=acoes.get("visualizar", False),
            pode_criar=acoes.get("criar", False),
            pode_editar=acoes.get("editar", False),
            pode_excluir=acoes.get("excluir", False),
            pode_exportar=acoes.get("exportar", False),
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def _criar_base_item(self):
        categoria = SuprimentosCategoriaItem(
            nome="Pecas",
            slug="pecas",
            ativo=True,
        )
        unidade = SuprimentosUnidadeMedida(
            nome="Unidade",
            sigla="UN",
            ativo=True,
        )
        centro = CentroCusto(nome="Manutencao", codigo="MAN", ativo=True)
        db.session.add_all([categoria, unidade, centro])
        db.session.commit()
        return categoria, unidade, centro

    def test_admin_acessa_hub_suprimentos(self):
        self._autenticar(self.admin)

        resposta = self.client.get("/suprimentos/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Suprimentos", resposta.data)
        self.assertIn(b"Fornecedores", resposta.data)

    def test_usuario_sem_permissao_nao_acessa_rota_direta(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/fornecedores/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_usuario_com_visualizar_acessa_hub_e_fornecedores(self):
        self._liberar("fornecedores", visualizar=True)
        self._autenticar(self.usuario)

        hub = self.client.get("/suprimentos/")
        fornecedores = self.client.get("/suprimentos/fornecedores/")

        self.assertEqual(200, hub.status_code)
        self.assertEqual(200, fornecedores.status_code)
        self.assertIn(b"Fornecedores", hub.data)

    def test_usuario_sem_criar_nao_acessa_novo_fornecedor(self):
        self._liberar("fornecedores", visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/fornecedores/novo")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_cria_edita_e_inativa_fornecedor(self):
        self._autenticar(self.admin)

        resposta = self.client.post(
            "/suprimentos/fornecedores/novo",
            data={
                "razao_social": " Fornecedor Teste Ltda ",
                "tipo_pessoa": "juridica",
                "cnpj_cpf": "11.222.333/0001-81",
                "email": "CONTATO@FORNECEDOR.COM",
                "telefone": "(13) 99123-4567",
            },
            follow_redirects=True,
        )
        fornecedor = SuprimentosFornecedor.query.one()

        self.assertEqual(200, resposta.status_code)
        self.assertEqual("FORNECEDOR TESTE LTDA", fornecedor.razao_social)
        self.assertEqual("11222333000181", fornecedor.cnpj_cpf)
        self.assertEqual("contato@fornecedor.com", fornecedor.email)
        self.assertEqual("5513991234567", fornecedor.telefone)
        self.assertTrue(fornecedor.ativo)

        resposta_duplicado = self.client.post(
            "/suprimentos/fornecedores/novo",
            data={
                "razao_social": "Outro Fornecedor",
                "tipo_pessoa": "juridica",
                "cnpj_cpf": "11.222.333/0001-81",
                "email": "outro@fornecedor.com",
                "telefone": "13988887777",
            },
            follow_redirects=True,
        )

        self.assertEqual(200, resposta_duplicado.status_code)
        self.assertIn("Ja existe fornecedor cadastrado".encode(), resposta_duplicado.data)
        self.assertEqual(1, SuprimentosFornecedor.query.count())

        self.client.post(
            f"/suprimentos/fornecedores/{fornecedor.id}/status",
            follow_redirects=True,
        )
        db.session.refresh(fornecedor)
        self.assertFalse(fornecedor.ativo)

    def test_services_validam_cadastros_base(self):
        sucesso, _, categoria = salvar_categoria({"nome": " EPI "})
        self.assertTrue(sucesso)
        self.assertEqual("epi", categoria.slug)
        self.assertEqual("EPI", categoria.nome)

        sucesso, mensagem, _ = salvar_categoria({"nome": "epi"})
        self.assertFalse(sucesso)
        self.assertIn("Ja existe categoria", mensagem)

        sucesso, _, unidade = salvar_unidade({"nome": "Unidade", "sigla": " un "})
        self.assertTrue(sucesso)
        self.assertEqual("UN", unidade.sigla)

        sucesso, mensagem, _ = salvar_unidade({"nome": "Outra", "sigla": "UN"})
        self.assertFalse(sucesso)
        self.assertIn("Ja existe unidade", mensagem)

        sucesso, _, centro = salvar_centro_custo({"nome": "Operacao", "codigo": "ope"})
        self.assertTrue(sucesso)
        self.assertEqual("OPE", centro.codigo)
        self.assertEqual("OPERACAO", centro.nome)

    def test_valida_cpf_cnpj_e_bloqueia_documento_invalido(self):
        self.assertTrue(validar_cpf("529.982.247-25"))
        self.assertFalse(validar_cpf("111.111.111-11"))
        self.assertTrue(validar_cnpj("11.222.333/0001-81"))
        self.assertFalse(validar_cnpj("11.111.111/1111-11"))

        sucesso, mensagem, _ = salvar_fornecedor(
            {
                "razao_social": "Fornecedor Invalido",
                "tipo_pessoa": "juridica",
                "cnpj_cpf": "11.111.111/1111-11",
                "email": "fornecedor@teste.com",
                "telefone": "13999998888",
            }
        )

        self.assertFalse(sucesso)
        self.assertEqual("CNPJ/CPF invalido.", mensagem)

        sucesso, mensagem, _ = salvar_fornecedor(
            {
                "razao_social": "Fornecedor Sem Telefone",
                "tipo_pessoa": "juridica",
                "cnpj_cpf": "11.222.333/0001-81",
                "email": "fornecedor@teste.com",
            }
        )

        self.assertFalse(sucesso)
        self.assertEqual("Telefone e obrigatorio.", mensagem)

    def test_item_servico_nao_fica_estocavel_e_bloqueia_estoque_negativo(self):
        categoria, unidade, centro = self._criar_base_item()

        sucesso, mensagem, _ = salvar_item(
            {
                "descricao": "Item invalido",
                "categoria_id": str(categoria.id),
                "unidade_medida_id": str(unidade.id),
                "centro_custo_padrao_id": str(centro.id),
                "tipo": "material",
                "estoque_minimo": "-1",
            }
        )

        self.assertFalse(sucesso)
        self.assertIn("Estoque minimo", mensagem)

        sucesso, _, item = salvar_item(
            {
                "codigo_interno": "srv-001",
                "descricao": "Servico de manutencao",
                "categoria_id": str(categoria.id),
                "unidade_medida_id": str(unidade.id),
                "centro_custo_padrao_id": str(centro.id),
                "tipo": "servico",
                "item_estocavel": "on",
            }
        )

        self.assertTrue(sucesso)
        self.assertFalse(item.item_estocavel)
        self.assertEqual("SERVICO DE MANUTENCAO", item.descricao)

    def test_vinculo_fornecedor_item_bloqueia_duplicidade(self):
        categoria, unidade, centro = self._criar_base_item()
        sucesso, _, fornecedor = salvar_fornecedor(
            {
                "razao_social": "Fornecedor Vinculo",
                "tipo_pessoa": "juridica",
                "cnpj_cpf": "11.444.777/0001-61",
                "email": "vinculo@fornecedor.com",
                "telefone": "5513988887777",
            }
        )
        self.assertTrue(sucesso)
        sucesso, _, item = salvar_item(
            {
                "codigo_interno": "PEC-001",
                "descricao": "Filtro",
                "categoria_id": str(categoria.id),
                "unidade_medida_id": str(unidade.id),
                "centro_custo_padrao_id": str(centro.id),
                "tipo": "peca",
            }
        )
        self.assertTrue(sucesso)

        dados = {
            "fornecedor_id": str(fornecedor.id),
            "item_id": str(item.id),
            "preco_referencia": "10,50",
            "prazo_entrega_dias": "5",
            "condicao_pagamento": "30 dias",
        }
        sucesso, _, vinculo = salvar_vinculo_fornecedor_item(dados)
        self.assertTrue(sucesso)
        self.assertEqual(1, SuprimentosFornecedorItem.query.count())

        sucesso, mensagem, _ = salvar_vinculo_fornecedor_item(dados)
        self.assertFalse(sucesso)
        self.assertIn("Ja existe vinculo", mensagem)
        self.assertEqual(vinculo.id, SuprimentosFornecedorItem.query.one().id)

    def test_consulta_cnpj_publico_normaliza_dados(self):
        import app.services.suprimentos_service as service

        class RespostaFake:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return (
                    b'{"razao_social":"Empresa Demo Ltda","nome_fantasia":"Demo",'
                    b'"email":"CONTATO@EXEMPLO.COM","municipio":"Santos","uf":"sp"}'
                )

        urlopen_original = service.urlopen
        service.urlopen = lambda requisicao, timeout=8: RespostaFake()

        try:
            sucesso, mensagem, dados = consultar_cnpj_publico("11.222.333/0001-81")
        finally:
            service.urlopen = urlopen_original

        self.assertTrue(sucesso)
        self.assertEqual("CNPJ consultado com sucesso.", mensagem)
        self.assertEqual("EMPRESA DEMO LTDA", dados["razao_social"])
        self.assertEqual("contato@exemplo.com", dados["email"])
        self.assertEqual("SP", dados["uf"])


if __name__ == "__main__":
    unittest.main()
