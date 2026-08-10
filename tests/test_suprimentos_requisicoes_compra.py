import unittest

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Equipe,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosCategoriaItem,
    SuprimentosComprador,
    SuprimentosItem,
    SuprimentosRequisicaoCompra,
    SuprimentosRequisicaoCompraItem,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.suprimentos_service import (
    STATUS_REQUISICAO_CANCELADA,
    STATUS_REQUISICAO_ENVIADA,
    STATUS_REQUISICAO_RASCUNHO,
    adicionar_item_requisicao,
    cancelar_requisicao_compra,
    enviar_requisicao_compra,
    enviar_email_requisicao_compra,
    gerar_link_whatsapp_requisicao_compra,
    gerar_mensagem_whatsapp_requisicao_compra,
    salvar_comprador_suprimentos,
    salvar_requisicao_compra,
)


class SuprimentosRequisicoesCompraTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            BASE_URL="https://app.rentalretros.test",
            OUTLOOK_CLASSIC_EMAIL_ENABLED="false",
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

        self.modulo = Modulo(
            departamento_id=self.departamento.id,
            nome="Requisicoes de Compra",
            slug="requisicoes_compra",
            ativo=True,
            ordem=7,
        )
        db.session.add(self.modulo)

        self.centro = CentroCusto(
            codigo="MAN",
            nome="MANUTENCAO",
            ativo=True,
        )
        self.equipe = Equipe(
            nome="EQUIPE CAMPO",
            slug="equipe-campo",
            ativo=True,
        )
        self.categoria = SuprimentosCategoriaItem(
            nome="PECAS",
            slug="pecas",
            ativo=True,
        )
        self.unidade = SuprimentosUnidadeMedida(
            nome="UNIDADE",
            sigla="UN",
            ativo=True,
        )
        db.session.add_all([self.centro, self.equipe, self.categoria, self.unidade])
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
        db.session.add(self.item)
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

    def _liberar_usuario(self, **acoes):
        permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=self.modulo.id,
            pode_visualizar=acoes.get("visualizar", False),
            pode_criar=acoes.get("criar", False),
            pode_editar=acoes.get("editar", False),
            pode_excluir=acoes.get("excluir", False),
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def test_usuario_sem_permissao_nao_acessa_requisicoes(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/requisicoes/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_usuario_com_visualizar_acessa_listagem(self):
        self._liberar_usuario(visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/requisicoes/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Requisicoes de Compra", resposta.data)

    def test_cria_requisicao_em_rascunho(self):
        sucesso, mensagem, requisicao = salvar_requisicao_compra(
            {
                "centro_custo_id": str(self.centro.id),
                "equipe_id": str(self.equipe.id),
                "veiculo_placa": "abc1d23",
                "justificativa": " comprar filtros ",
                "observacoes": " manutencao preventiva ",
            },
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Requisicao salva com sucesso.", mensagem)
        self.assertEqual(STATUS_REQUISICAO_RASCUNHO, requisicao.status)
        self.assertEqual(self.equipe.id, requisicao.equipe_id)
        self.assertEqual("ABC1D23", requisicao.veiculo_placa)
        self.assertEqual("COMPRAR FILTROS", requisicao.justificativa)
        self.assertTrue(requisicao.numero.startswith("RC-"))

    def test_nao_aceita_equipe_inativa_na_requisicao(self):
        self.equipe.ativo = False
        db.session.commit()

        sucesso, mensagem, requisicao = salvar_requisicao_compra(
            {
                "equipe_id": str(self.equipe.id),
                "justificativa": "Comprar filtros",
            },
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Equipe nao encontrada ou inativa.", mensagem)
        self.assertIsNone(requisicao)

    def test_nao_cria_requisicao_sem_justificativa(self):
        sucesso, mensagem, requisicao = salvar_requisicao_compra({}, self.admin)

        self.assertFalse(sucesso)
        self.assertEqual("Justificativa e obrigatoria.", mensagem)
        self.assertIsNone(requisicao)

    def test_adiciona_item_com_snapshot_e_bloqueia_duplicado(self):
        _, _, requisicao = salvar_requisicao_compra(
            {"justificativa": "Comprar item"},
            self.admin,
        )

        sucesso, mensagem, requisicao_item = adicionar_item_requisicao(
            {
                "item_id": str(self.item.id),
                "quantidade": "2,5",
                "observacoes": "urgente",
            },
            requisicao,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Item adicionado com sucesso.", mensagem)
        self.assertEqual("PEC-001", requisicao_item.item_codigo_snapshot)
        self.assertEqual("FILTRO DE OLEO", requisicao_item.item_descricao_snapshot)
        self.assertEqual("UN", requisicao_item.unidade_medida_snapshot)
        self.assertEqual("URGENTE", requisicao_item.observacoes)

        sucesso, mensagem, _ = adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "1"},
            requisicao,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Este item ja foi adicionado a requisicao.", mensagem)
        self.assertEqual(1, SuprimentosRequisicaoCompraItem.query.count())

    def test_quantidade_deve_ser_maior_que_zero(self):
        _, _, requisicao = salvar_requisicao_compra(
            {"justificativa": "Comprar item"},
            self.admin,
        )

        sucesso, mensagem, _ = adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "0"},
            requisicao,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Quantidade deve ser maior que zero.", mensagem)

    def test_nao_envia_requisicao_sem_item(self):
        _, _, requisicao = salvar_requisicao_compra(
            {"justificativa": "Comprar item"},
            self.admin,
        )

        sucesso, mensagem = enviar_requisicao_compra(requisicao)

        self.assertFalse(sucesso)
        self.assertEqual("Adicione ao menos um item antes de enviar.", mensagem)
        self.assertEqual(STATUS_REQUISICAO_RASCUNHO, requisicao.status)

    def test_envia_requisicao_com_item_e_bloqueia_edicao(self):
        _, _, requisicao = salvar_requisicao_compra(
            {"justificativa": "Comprar item"},
            self.admin,
        )
        adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "1"},
            requisicao,
        )

        sucesso, mensagem = enviar_requisicao_compra(requisicao)

        self.assertTrue(sucesso)
        self.assertEqual("Requisicao enviada para analise.", mensagem)
        self.assertEqual(STATUS_REQUISICAO_ENVIADA, requisicao.status)
        self.assertIsNotNone(requisicao.enviada_em)

        sucesso, mensagem, _ = salvar_requisicao_compra(
            {"justificativa": "Alterar"},
            self.admin,
            requisicao,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Somente requisicoes em rascunho podem ser editadas.", mensagem)

    def test_salva_comprador_para_envio_por_whatsapp(self):
        sucesso, mensagem, comprador = salvar_comprador_suprimentos(
            {
                "nome": " comprador suprimentos ",
                "telefone_whatsapp": "(13) 99999-0001",
                "email": "COMPRAS@RENTALRETROS.COM.BR",
                "centro_custo_id": str(self.centro.id),
                "ativo": "on",
                "observacoes": " recebe requisicoes ",
            }
        )

        self.assertTrue(sucesso)
        self.assertEqual("Comprador salvo com sucesso.", mensagem)
        self.assertEqual("COMPRADOR SUPRIMENTOS", comprador.nome)
        self.assertEqual("5513999990001", comprador.telefone_whatsapp)
        self.assertEqual("compras@rentalretros.com.br", comprador.email)
        self.assertEqual("RECEBE REQUISICOES", comprador.observacoes)

    def test_gera_link_whatsapp_requisicao_enviada_para_comprador(self):
        _, _, requisicao = salvar_requisicao_compra(
            {
                "centro_custo_id": str(self.centro.id),
                "justificativa": "Comprar item",
            },
            self.admin,
        )
        adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "1"},
            requisicao,
        )
        db.session.add(
            SuprimentosComprador(
                nome="COMPRADOR",
                telefone_whatsapp="5513999990001",
                centro_custo_id=self.centro.id,
                ativo=True,
            )
        )
        db.session.commit()
        enviar_requisicao_compra(requisicao)

        mensagem = gerar_mensagem_whatsapp_requisicao_compra(requisicao)
        sucesso, texto_mensagem, link = gerar_link_whatsapp_requisicao_compra(requisicao)

        self.assertIn("*Rental Retros - Nova Requisicao Aberta*", mensagem)
        self.assertIn(f"Requisicao: {requisicao.numero}", mensagem)
        self.assertIn("Solicitante: Admin", mensagem)
        self.assertIn("Centro de custo: MANUTENCAO", mensagem)
        self.assertTrue(sucesso)
        self.assertEqual("Link do WhatsApp gerado com sucesso.", texto_mensagem)
        self.assertTrue(link.startswith("https://wa.me/5513999990001?text="))

    def test_rota_enviar_requisicao_abre_whatsapp_do_comprador(self):
        _, _, requisicao = salvar_requisicao_compra(
            {
                "centro_custo_id": str(self.centro.id),
                "justificativa": "Comprar item",
            },
            self.admin,
        )
        adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "1"},
            requisicao,
        )
        db.session.add(
            SuprimentosComprador(
                nome="COMPRADOR",
                telefone_whatsapp="5513999990001",
                ativo=True,
            )
        )
        db.session.commit()
        self._autenticar(self.admin)

        resposta = self.client.post(f"/suprimentos/requisicoes/{requisicao.id}/enviar")

        self.assertEqual(302, resposta.status_code)
        self.assertTrue(resposta.headers["Location"].startswith("https://wa.me/5513999990001?text="))
        db.session.refresh(requisicao)
        self.assertEqual(STATUS_REQUISICAO_ENVIADA, requisicao.status)

    def test_rota_enviar_requisicao_por_email_abre_outlook_sem_smtp(self):
        _, _, requisicao = salvar_requisicao_compra(
            {
                "centro_custo_id": str(self.centro.id),
                "justificativa": "Comprar item",
            },
            self.admin,
        )
        adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "1"},
            requisicao,
        )
        db.session.add(
            SuprimentosComprador(
                nome="COMPRADOR",
                telefone_whatsapp="5513999990001",
                email="compras@rentalretros.com.br",
                ativo=True,
            )
        )
        db.session.commit()
        self._autenticar(self.admin)

        resposta = self.client.post(f"/suprimentos/requisicoes/{requisicao.id}/enviar-email")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Abrir e-mail no Outlook", resposta.data)
        self.assertIn(b"mailto:compras@rentalretros.com.br?", resposta.data)
        self.assertIn(b"Nova%20Requisicao%20de%20Compra", resposta.data)
        db.session.refresh(requisicao)
        self.assertEqual(STATUS_REQUISICAO_ENVIADA, requisicao.status)

    def test_reenvia_email_requisicao_ja_enviada_sem_erro(self):
        _, _, requisicao = salvar_requisicao_compra(
            {
                "centro_custo_id": str(self.centro.id),
                "justificativa": "Comprar item",
            },
            self.admin,
        )
        adicionar_item_requisicao(
            {"item_id": str(self.item.id), "quantidade": "1"},
            requisicao,
        )
        db.session.add(
            SuprimentosComprador(
                nome="COMPRADOR",
                telefone_whatsapp="5513999990001",
                email="compras@rentalretros.com.br",
                ativo=True,
            )
        )
        db.session.commit()
        enviar_requisicao_compra(requisicao)
        self._autenticar(self.admin)

        resposta = self.client.post(f"/suprimentos/requisicoes/{requisicao.id}/enviar-email")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Abrir e-mail no Outlook", resposta.data)
        self.assertNotIn(b"Somente requisicoes em rascunho podem ser enviadas.", resposta.data)

    def test_envia_email_requisicao_automaticamente_quando_smtp_configurado(self):
        _, _, requisicao = salvar_requisicao_compra(
            {
                "centro_custo_id": str(self.centro.id),
                "justificativa": "Comprar item",
            },
            self.admin,
        )
        db.session.add(
            SuprimentosComprador(
                nome="COMPRADOR",
                telefone_whatsapp="5513999990001",
                email="compras@rentalretros.com.br",
                ativo=True,
            )
        )
        db.session.commit()

        import app.services.suprimentos_service as service

        smtp_original = service.smtp_configurado
        enviar_original = service.enviar_email
        chamados = []
        service.smtp_configurado = lambda: True
        service.enviar_email = lambda destinatario, assunto, corpo: chamados.append(
            (destinatario, assunto, corpo)
        ) or (True, None)

        try:
            sucesso, mensagem, link = enviar_email_requisicao_compra(requisicao)
        finally:
            service.smtp_configurado = smtp_original
            service.enviar_email = enviar_original

        self.assertTrue(sucesso)
        self.assertEqual("E-mail enviado automaticamente ao comprador.", mensagem)
        self.assertIsNone(link)
        self.assertEqual("compras@rentalretros.com.br", chamados[0][0])
        self.assertIn(requisicao.numero, chamados[0][1])
        self.assertIn("Centro de custo: MANUTENCAO", chamados[0][2])

    def test_cancela_requisicao(self):
        _, _, requisicao = salvar_requisicao_compra(
            {"justificativa": "Comprar item"},
            self.admin,
        )

        sucesso, mensagem = cancelar_requisicao_compra(requisicao, "erro de cadastro")

        self.assertTrue(sucesso)
        self.assertEqual("Requisicao cancelada com sucesso.", mensagem)
        self.assertEqual(STATUS_REQUISICAO_CANCELADA, requisicao.status)
        self.assertEqual("ERRO DE CADASTRO", requisicao.motivo_cancelamento)


if __name__ == "__main__":
    unittest.main()
