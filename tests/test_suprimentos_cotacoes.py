import unittest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosCategoriaItem,
    SuprimentosCotacao,
    SuprimentosCotacaoProposta,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.suprimentos_service import (
    STATUS_COTACAO_ABERTA,
    STATUS_COTACAO_APROVADA,
    STATUS_COTACAO_CANCELADA,
    STATUS_COTACAO_EM_APROVACAO,
    STATUS_COTACAO_ENCERRADA,
    STATUS_COTACAO_REPROVADA,
    STATUS_REQUISICAO_APROVADA,
    STATUS_REQUISICAO_CANCELADA,
    STATUS_REQUISICAO_ENVIADA,
    adicionar_item_requisicao,
    aprovar_cotacao,
    cancelar_cotacao,
    encerrar_cotacao,
    enviar_cotacao_para_aprovacao,
    formatar_moeda_brl,
    enviar_requisicao_compra,
    montar_mapa_comparativo_cotacao,
    reprovar_cotacao,
    salvar_cotacao,
    salvar_proposta_cotacao,
    salvar_requisicao_compra,
    selecionar_proposta_vencedora,
)


class SuprimentosCotacoesTestCase(unittest.TestCase):
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

        departamento = Departamento(
            nome="Suprimentos",
            slug="suprimentos",
            ativo=True,
            ordem=2,
        )
        db.session.add(departamento)
        db.session.flush()

        self.modulo = Modulo(
            departamento_id=departamento.id,
            nome="Cotacoes",
            slug="cotacoes",
            ativo=True,
            ordem=8,
        )
        db.session.add(self.modulo)

        self.centro = CentroCusto(codigo="MAN", nome="MANUTENCAO", ativo=True)
        self.categoria = SuprimentosCategoriaItem(nome="PECAS", slug="pecas", ativo=True)
        self.unidade = SuprimentosUnidadeMedida(nome="UNIDADE", sigla="UN", ativo=True)
        db.session.add_all([self.centro, self.categoria, self.unidade])
        db.session.flush()

        self.item = SuprimentosItem(
            codigo_interno="PEC-001",
            descricao="FILTRO DE OLEO",
            categoria_id=self.categoria.id,
            unidade_medida_id=self.unidade.id,
            centro_custo_padrao_id=self.centro.id,
            tipo="peca",
            item_estocavel=True,
            ativo=True,
        )
        self.fornecedor = SuprimentosFornecedor(
            razao_social="FORNECEDOR TESTE LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="11222333000181",
            email="fornecedor@teste.com",
            telefone="5513999998888",
            ativo=True,
        )
        self.fornecedor_b = SuprimentosFornecedor(
            razao_social="FORNECEDOR B LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="11444777000161",
            email="fornecedorb@teste.com",
            telefone="551388887777",
            ativo=True,
        )
        db.session.add_all([self.item, self.fornecedor, self.fornecedor_b])
        db.session.flush()

        self.vinculo = SuprimentosFornecedorItem(
            fornecedor_id=self.fornecedor.id,
            item_id=self.item.id,
            ativo=True,
            fornecedor_preferencial=True,
        )
        self.vinculo_b = SuprimentosFornecedorItem(
            fornecedor_id=self.fornecedor_b.id,
            item_id=self.item.id,
            ativo=True,
            fornecedor_preferencial=False,
        )
        db.session.add_all([self.vinculo, self.vinculo_b])
        db.session.commit()

        _, _, self.requisicao = salvar_requisicao_compra(
            {"centro_custo_id": str(self.centro.id), "justificativa": "Comprar filtros"},
            self.admin,
        )
        adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "2"},
            self.requisicao,
        )
        enviar_requisicao_compra(self.requisicao)
        db.session.refresh(self.requisicao)
        self.requisicao_item = self.requisicao.itens[0]

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _autenticar(self, usuario):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True

    def _liberar_usuario(self, **acoes):
        permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=self.modulo.id,
            pode_visualizar=acoes.get("visualizar", False),
            pode_criar=acoes.get("criar", False),
            pode_editar=acoes.get("editar", False),
            pode_excluir=acoes.get("excluir", False),
            pode_aprovar=acoes.get("aprovar", False),
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def test_usuario_sem_permissao_nao_acessa_cotacoes(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/cotacoes/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_usuario_com_visualizar_acessa_listagem(self):
        self._liberar_usuario(visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/cotacoes/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Cotacoes", resposta.data)

    def test_cria_cotacao_apenas_para_requisicao_enviada(self):
        self.assertEqual(STATUS_REQUISICAO_ENVIADA, self.requisicao.status)

        sucesso, mensagem, cotacao = salvar_cotacao(
            {
                "requisicao_id": str(self.requisicao.id),
                "observacoes": " rodada inicial ",
            },
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Cotacao salva com sucesso.", mensagem)
        self.assertEqual(STATUS_COTACAO_ABERTA, cotacao.status)
        self.assertEqual(STATUS_REQUISICAO_ENVIADA, self.requisicao.status)
        self.assertEqual("RODADA INICIAL", cotacao.observacoes)
        self.assertTrue(cotacao.numero.startswith("COT-"))

    def test_nao_cria_cotacao_para_requisicao_rascunho(self):
        _, _, rascunho = salvar_requisicao_compra(
            {"justificativa": "Ainda em rascunho"},
            self.admin,
        )

        sucesso, mensagem, cotacao = salvar_cotacao(
            {"requisicao_id": str(rascunho.id)},
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Somente requisicoes enviadas para analise podem iniciar cotacao.", mensagem)
        self.assertIsNone(cotacao)

    def test_registra_proposta_com_fornecedor_vinculado_e_bloqueia_duplicado(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )

        dados = {
            "requisicao_item_id": str(self.requisicao_item.id),
            "fornecedor_id": str(self.fornecedor.id),
            "preco_unitario": "R$ 15,50",
            "prazo_entrega_dias": "3",
            "condicao_pagamento": "30 dias",
            "observacoes": "entrega parcial",
        }
        sucesso, mensagem, proposta = salvar_proposta_cotacao(dados, cotacao)

        self.assertTrue(sucesso)
        self.assertEqual("Proposta registrada com sucesso.", mensagem)
        self.assertEqual("FORNECEDOR TESTE LTDA", proposta.fornecedor_razao_social_snapshot)
        self.assertEqual("FILTRO DE OLEO", proposta.item_descricao_snapshot)
        self.assertEqual("R$ 15,50", formatar_moeda_brl(proposta.preco_unitario))
        self.assertEqual("R$ 31,00", formatar_moeda_brl(proposta.valor_total))
        self.assertEqual("30 DIAS", proposta.condicao_pagamento)
        self.assertEqual("ENTREGA PARCIAL", proposta.observacoes)

        sucesso, mensagem, _ = salvar_proposta_cotacao(dados, cotacao)

        self.assertFalse(sucesso)
        self.assertEqual("Ja existe proposta deste fornecedor para este item.", mensagem)
        self.assertEqual(1, SuprimentosCotacaoProposta.query.count())

    def test_bloqueia_fornecedor_sem_vinculo_com_item(self):
        fornecedor_sem_vinculo = SuprimentosFornecedor(
            razao_social="SEM VINCULO LTDA",
            tipo_pessoa="juridica",
            cnpj_cpf="50873397000156",
            email="sem@vinculo.com",
            telefone="551388887777",
            ativo=True,
        )
        db.session.add(fornecedor_sem_vinculo)
        db.session.commit()
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )

        sucesso, mensagem, _ = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(fornecedor_sem_vinculo.id),
                "preco_unitario": "10",
            },
            cotacao,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Fornecedor nao esta vinculado ao item selecionado.", mensagem)

    def test_nao_encerra_sem_proposta_e_encerra_com_proposta(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )

        sucesso, mensagem = encerrar_cotacao(cotacao)

        self.assertFalse(sucesso)
        self.assertEqual("Registre ao menos uma proposta antes de encerrar.", mensagem)

        salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15",
            },
            cotacao,
        )
        sucesso, mensagem = encerrar_cotacao(cotacao)

        self.assertTrue(sucesso)
        self.assertEqual("Cotacao encerrada com sucesso.", mensagem)
        self.assertEqual(STATUS_COTACAO_ENCERRADA, cotacao.status)
        self.assertEqual(STATUS_REQUISICAO_APROVADA, cotacao.requisicao.status)

    def test_cancela_cotacao(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )

        sucesso, mensagem = cancelar_cotacao(cotacao)

        self.assertTrue(sucesso)
        self.assertEqual("Cotacao cancelada com sucesso.", mensagem)
        self.assertEqual(STATUS_COTACAO_CANCELADA, cotacao.status)
        self.assertEqual(STATUS_REQUISICAO_CANCELADA, cotacao.requisicao.status)

    def test_detalhes_mostra_preco_unitario_com_simbolo_real(self):
        self._liberar_usuario(visualizar=True, editar=True)
        self._autenticar(self.usuario)
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
            },
            cotacao,
        )

        resposta = self.client.get(f"/suprimentos/cotacoes/{cotacao.id}")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"R$", resposta.data)
        self.assertIn(b"R$ 15,50", resposta.data)
        self.assertIn(b"R$ 31,00", resposta.data)

    def test_monta_mapa_comparativo_destacando_melhores_criterios(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
                "prazo_entrega_dias": "5",
            },
            cotacao,
        )
        salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor_b.id),
                "preco_unitario": "14,00",
                "prazo_entrega_dias": "8",
            },
            cotacao,
        )

        mapa = montar_mapa_comparativo_cotacao(cotacao)
        grupo = mapa["grupos"][0]

        self.assertEqual(1, mapa["totais"]["itens"])
        self.assertEqual(1, mapa["totais"]["itens_com_proposta"])
        self.assertEqual(2, mapa["totais"]["propostas"])
        self.assertEqual(Decimal("14.00"), grupo["menor_preco"])
        self.assertEqual(Decimal("28.00000"), grupo["menor_total"])
        self.assertEqual(5, grupo["menor_prazo"])

        linha_fornecedor_b = next(
            linha
            for linha in grupo["propostas"]
            if linha["proposta"].fornecedor_id == self.fornecedor_b.id
        )
        linha_fornecedor_a = next(
            linha
            for linha in grupo["propostas"]
            if linha["proposta"].fornecedor_id == self.fornecedor.id
        )

        self.assertTrue(linha_fornecedor_b["menor_preco"])
        self.assertTrue(linha_fornecedor_b["menor_total"])
        self.assertFalse(linha_fornecedor_b["menor_prazo"])
        self.assertTrue(linha_fornecedor_a["menor_prazo"])

    def test_mapa_comparativo_renderiza_destaques_sem_escolher_vencedor(self):
        self._liberar_usuario(visualizar=True)
        self._autenticar(self.usuario)
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
                "prazo_entrega_dias": "5",
            },
            cotacao,
        )

        resposta = self.client.get(f"/suprimentos/cotacoes/{cotacao.id}/mapa-comparativo")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Mapa comparativo", resposta.data)
        self.assertIn(b"Menor preco", resposta.data)
        self.assertIn(b"Menor total", resposta.data)
        self.assertIn(b"Enviar para aprovacao", resposta.data)

    def test_seleciona_vencedor_e_exige_justificativa_quando_nao_e_menor_preco(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        _, _, proposta_a = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
            },
            cotacao,
        )
        _, _, proposta_b = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor_b.id),
                "preco_unitario": "14,00",
            },
            cotacao,
        )

        sucesso, mensagem, _ = selecionar_proposta_vencedora(
            {"proposta_id": str(proposta_a.id)},
            cotacao,
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Informe a justificativa para escolher proposta acima do menor preco.", mensagem)

        sucesso, mensagem, proposta = selecionar_proposta_vencedora(
            {
                "proposta_id": str(proposta_a.id),
                "justificativa_selecao": "melhor prazo de entrega",
            },
            cotacao,
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Proposta vencedora selecionada com sucesso.", mensagem)
        self.assertTrue(proposta.selecionada)
        self.assertEqual("MELHOR PRAZO DE ENTREGA", proposta.justificativa_selecao)
        self.assertFalse(proposta_b.selecionada)

    def test_envia_para_aprovacao_somente_com_vencedor_em_todos_os_itens(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        _, _, proposta = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
            },
            cotacao,
        )

        sucesso, mensagem = enviar_cotacao_para_aprovacao(cotacao, self.admin)

        self.assertFalse(sucesso)
        self.assertEqual(
            "Selecione uma proposta vencedora para todos os itens antes de enviar para aprovacao.",
            mensagem,
        )

        selecionar_proposta_vencedora({"proposta_id": str(proposta.id)}, cotacao, self.admin)
        sucesso, mensagem = enviar_cotacao_para_aprovacao(cotacao, self.admin)

        self.assertTrue(sucesso)
        self.assertEqual("Cotacao enviada para aprovacao com sucesso.", mensagem)
        self.assertEqual(STATUS_COTACAO_EM_APROVACAO, cotacao.status)
        self.assertEqual(STATUS_REQUISICAO_ENVIADA, cotacao.requisicao.status)
        self.assertIsNotNone(cotacao.enviada_aprovacao_em)

    def test_aprova_cotacao_sem_gerar_ordem_de_compra(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        _, _, proposta = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
            },
            cotacao,
        )
        selecionar_proposta_vencedora({"proposta_id": str(proposta.id)}, cotacao, self.admin)
        enviar_cotacao_para_aprovacao(cotacao, self.admin)

        sucesso, mensagem = aprovar_cotacao(
            cotacao,
            self.admin,
            {"observacoes_aprovacao": "aprovado dentro da alcada"},
        )

        self.assertTrue(sucesso)
        self.assertEqual("Cotacao aprovada com sucesso.", mensagem)
        self.assertEqual(STATUS_COTACAO_APROVADA, cotacao.status)
        self.assertEqual(STATUS_REQUISICAO_APROVADA, cotacao.requisicao.status)
        self.assertEqual(self.admin.id, cotacao.aprovada_por_usuario_id)
        self.assertEqual("APROVADO DENTRO DA ALCADA", cotacao.observacoes_aprovacao)

    def test_reprova_cotacao_e_libera_para_ajustes(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        _, _, proposta = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
            },
            cotacao,
        )
        selecionar_proposta_vencedora({"proposta_id": str(proposta.id)}, cotacao, self.admin)
        enviar_cotacao_para_aprovacao(cotacao, self.admin)

        sucesso, mensagem = reprovar_cotacao(cotacao, self.admin, {})

        self.assertFalse(sucesso)
        self.assertEqual("Informe a justificativa da reprovacao.", mensagem)

        sucesso, mensagem = reprovar_cotacao(
            cotacao,
            self.admin,
            {"observacoes_aprovacao": "negociar prazo"},
        )

        self.assertTrue(sucesso)
        self.assertEqual("Cotacao reprovada e liberada para ajustes.", mensagem)
        self.assertEqual(STATUS_COTACAO_REPROVADA, cotacao.status)
        self.assertEqual(STATUS_REQUISICAO_CANCELADA, cotacao.requisicao.status)
        self.assertTrue(cotacao.pode_editar)

    def test_requisicao_volta_para_enviada_quando_cotacao_reprovada_e_reaberta(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )
        _, _, proposta = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "15,50",
            },
            cotacao,
        )
        selecionar_proposta_vencedora({"proposta_id": str(proposta.id)}, cotacao, self.admin)
        enviar_cotacao_para_aprovacao(cotacao, self.admin)
        reprovar_cotacao(
            cotacao,
            self.admin,
            {"observacoes_aprovacao": "negociar prazo"},
        )

        self.assertEqual(STATUS_REQUISICAO_CANCELADA, cotacao.requisicao.status)

        sucesso, mensagem, _ = selecionar_proposta_vencedora(
            {"proposta_id": str(proposta.id)},
            cotacao,
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Proposta vencedora selecionada com sucesso.", mensagem)
        self.assertEqual(STATUS_COTACAO_ABERTA, cotacao.status)
        self.assertEqual(STATUS_REQUISICAO_ENVIADA, cotacao.requisicao.status)

    def test_rota_aprovacao_exige_permissao_de_aprovar(self):
        self._liberar_usuario(visualizar=True, editar=True)
        self._autenticar(self.usuario)
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )

        resposta = self.client.post(f"/suprimentos/cotacoes/{cotacao.id}/aprovar")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])


if __name__ == "__main__":
    unittest.main()
