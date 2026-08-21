import unittest
from io import BytesIO
from datetime import date
from decimal import Decimal

from PIL import Image
from werkzeug.datastructures import FileStorage

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    SuprimentosAlcadaAprovacao,
    SuprimentosCategoriaItem,
    SuprimentosFornecedor,
    SuprimentosFornecedorItem,
    SuprimentosItem,
    SuprimentosMovimentacaoEstoque,
    SuprimentosOrdemCompra,
    SuprimentosOrdemCompraItemEvidencia,
    SuprimentosOrdemCompraParcela,
    SuprimentosUnidadeMedida,
    Usuario,
)
from app.services.suprimentos_service import (
    STATUS_COTACAO_APROVADA,
    STATUS_FINANCEIRO_CANCELADO,
    STATUS_FINANCEIRO_PENDENTE,
    STATUS_FINANCEIRO_PREPARADO,
    STATUS_FINANCEIRO_PROVISIONADO,
    STATUS_ORDEM_COMPRA_CANCELADA,
    STATUS_ORDEM_COMPRA_GERADA,
    STATUS_ORDEM_COMPRA_PARCIAL,
    STATUS_ORDEM_COMPRA_RECEBIDA,
    adicionar_item_requisicao,
    aprovar_cotacao,
    buscar_ordens_aguardando_financeiro,
    cancelar_ordem_compra,
    enviar_cotacao_para_aprovacao,
    enviar_requisicao_compra,
    gerar_ordens_compra_cotacao,
    preparar_financeiro_ordem_compra,
    provisionar_financeiro_ordem_compra,
    registrar_entrada_estoque_recebimento_item,
    registrar_recebimento_ordem_compra,
    salvar_evidencia_item_ordem_compra,
    salvar_cotacao,
    salvar_proposta_cotacao,
    salvar_requisicao_compra,
    selecionar_proposta_vencedora,
    status_evidencia_item_oc,
)


class FakeDriveCreateRequest:
    def __init__(self, resposta):
        self.resposta = resposta

    def execute(self):
        return self.resposta


class FakeDriveErroCotaRequest:
    def execute(self):
        raise RuntimeError("storageQuotaExceeded: Service Accounts do not have storage quota.")


class FakeDriveFiles:
    def __init__(self, falhar_cota=False):
        self.uploads = []
        self.falhar_cota = falhar_cota

    def create(self, body, media_body, fields, supportsAllDrives):
        if self.falhar_cota:
            return FakeDriveErroCotaRequest()
        self.uploads.append(
            {
                "body": body,
                "media_body": media_body,
                "fields": fields,
                "supportsAllDrives": supportsAllDrives,
            }
        )
        indice = len(self.uploads)
        return FakeDriveCreateRequest(
            {
                "id": f"drive-file-{indice}",
                "name": body["name"],
                "webViewLink": f"https://drive.google.com/file/{indice}",
            }
        )


class FakeDriveService:
    def __init__(self, falhar_cota=False):
        self._files = FakeDriveFiles(falhar_cota=falhar_cota)

    def files(self):
        return self._files


class SuprimentosOrdensCompraTestCase(unittest.TestCase):
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
            nome="Ordens de Compra",
            slug="ordens_compra",
            ativo=True,
            ordem=9,
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
        db.session.add_all([self.item, self.fornecedor])
        db.session.flush()

        self.vinculo = SuprimentosFornecedorItem(
            fornecedor_id=self.fornecedor.id,
            item_id=self.item.id,
            ativo=True,
            fornecedor_preferencial=True,
        )
        db.session.add(self.vinculo)
        db.session.commit()

        self.alcada = SuprimentosAlcadaAprovacao(
            usuario_aprovador_id=self.admin.id,
            valor_minimo=Decimal("0.00"),
            valor_maximo=None,
            ativo=True,
        )
        db.session.add(self.alcada)
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
            ativo=True,
        )
        permissao.garantir_visualizacao()
        db.session.add(permissao)
        db.session.commit()

    def _criar_cotacao_aprovada(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id), "observacoes": "Rodada inicial"},
            self.admin,
        )
        _, _, proposta = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(self.requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "125,50",
                "prazo_entrega_dias": "3",
                "condicao_pagamento": "30 dias",
                "observacoes": "entrega parcial nao autorizada",
            },
            cotacao,
        )
        selecionar_proposta_vencedora({"proposta_id": str(proposta.id)}, cotacao, self.admin)
        enviar_cotacao_para_aprovacao(cotacao, self.admin)
        aprovar_cotacao(cotacao, self.admin, {"observacoes_aprovacao": "aprovado"})
        db.session.refresh(cotacao)
        self.assertEqual(STATUS_COTACAO_APROVADA, cotacao.status)
        return cotacao

    def _criar_ordem_compra(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        return ordens[0]

    def _arquivo_imagem(self, nome="foto.png", tamanho=(1200, 900), cor=(20, 120, 40)):
        buffer = BytesIO()
        imagem = Image.new("RGB", tamanho, cor)
        imagem.save(buffer, format="PNG")
        buffer.seek(0)
        return FileStorage(stream=buffer, filename=nome, content_type="image/png")

    def test_gera_ordem_compra_a_partir_de_cotacao_aprovada(self):
        cotacao = self._criar_cotacao_aprovada()

        sucesso, mensagem, ordens = gerar_ordens_compra_cotacao(
            cotacao,
            self.admin,
            {"observacoes": "comprar conforme aprovado"},
        )

        self.assertTrue(sucesso)
        self.assertEqual("Ordem de compra gerada com sucesso.", mensagem)
        self.assertEqual(1, len(ordens))

        ordem = ordens[0]
        self.assertTrue(ordem.numero.startswith("OC-"))
        self.assertEqual(STATUS_ORDEM_COMPRA_GERADA, ordem.status)
        self.assertEqual(self.fornecedor.id, ordem.fornecedor_id)
        self.assertEqual("FORNECEDOR TESTE LTDA", ordem.fornecedor_razao_social_snapshot)
        self.assertEqual("30 DIAS", ordem.condicao_pagamento_snapshot)
        self.assertEqual("COMPRAR CONFORME APROVADO", ordem.observacoes)
        self.assertEqual(1, len(ordem.itens))
        self.assertEqual(Decimal("251.00"), ordem.valor_total)
        self.assertEqual(STATUS_FINANCEIRO_PENDENTE, ordem.status_financeiro)
        self.assertEqual(1, ordem.quantidade_parcelas)
        self.assertEqual([], ordem.parcelas_financeiras)

    def test_gera_ordem_compra_com_preparacao_financeira(self):
        cotacao = self._criar_cotacao_aprovada()

        sucesso, mensagem, ordens = gerar_ordens_compra_cotacao(
            cotacao,
            self.admin,
            {
                "observacoes": "comprar conforme aprovado",
                "previsao_vencimento": "2026-09-10",
                "quantidade_parcelas": "2",
                "observacoes_financeiras": "pagar apos recebimento",
            },
        )

        self.assertTrue(sucesso)
        self.assertEqual("Ordem de compra gerada com sucesso.", mensagem)
        ordem = ordens[0]
        self.assertEqual(STATUS_FINANCEIRO_PREPARADO, ordem.status_financeiro)
        self.assertEqual(date(2026, 9, 10), ordem.previsao_vencimento)
        self.assertEqual(2, ordem.quantidade_parcelas)
        self.assertEqual("PAGAR APOS RECEBIMENTO", ordem.observacoes_financeiras)
        self.assertIsNotNone(ordem.preparado_financeiro_em)
        self.assertEqual(2, len(ordem.parcelas_financeiras))
        self.assertEqual(Decimal("125.50"), ordem.parcelas_financeiras[0].valor_previsto)
        self.assertEqual(Decimal("125.50"), ordem.parcelas_financeiras[1].valor_previsto)
        self.assertEqual(date(2026, 9, 10), ordem.parcelas_financeiras[0].data_vencimento)
        self.assertEqual(date(2026, 10, 10), ordem.parcelas_financeiras[1].data_vencimento)

    def test_prepara_e_provisiona_financeiro_da_ordem_compra(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]

        sucesso, mensagem = provisionar_financeiro_ordem_compra(ordem)
        self.assertFalse(sucesso)
        self.assertEqual("Prepare as parcelas financeiras antes de provisionar.", mensagem)

        sucesso, mensagem = preparar_financeiro_ordem_compra(
            ordem,
            {
                "previsao_vencimento": "2026-09-15",
                "quantidade_parcelas": "3",
                "observacoes_financeiras": "parcelar compra",
            },
        )

        self.assertTrue(sucesso)
        self.assertEqual("Dados financeiros preparados com sucesso.", mensagem)
        self.assertEqual(STATUS_FINANCEIRO_PREPARADO, ordem.status_financeiro)
        self.assertEqual(3, SuprimentosOrdemCompraParcela.query.filter_by(ordem_compra_id=ordem.id).count())
        self.assertEqual(Decimal("83.67"), ordem.parcelas_financeiras[0].valor_previsto)
        self.assertEqual(Decimal("83.67"), ordem.parcelas_financeiras[1].valor_previsto)
        self.assertEqual(Decimal("83.66"), ordem.parcelas_financeiras[2].valor_previsto)

        sucesso, mensagem = provisionar_financeiro_ordem_compra(ordem)

        self.assertTrue(sucesso)
        self.assertEqual("Ordem de compra provisionada para o futuro Financeiro.", mensagem)
        self.assertEqual(STATUS_FINANCEIRO_PROVISIONADO, ordem.status_financeiro)
        self.assertIsNotNone(ordem.provisionado_financeiro_em)

    def test_listagem_de_ordens_aguardando_financeiro(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]

        aguardando = buscar_ordens_aguardando_financeiro()

        self.assertIn(ordem, aguardando)

        preparar_financeiro_ordem_compra(
            ordem,
            {"previsao_vencimento": "2026-09-15", "quantidade_parcelas": "1"},
        )
        provisionar_financeiro_ordem_compra(ordem)

        aguardando = buscar_ordens_aguardando_financeiro()
        self.assertNotIn(ordem, aguardando)

    def test_nao_gera_ordem_compra_duplicada_para_mesma_cotacao(self):
        cotacao = self._criar_cotacao_aprovada()
        gerar_ordens_compra_cotacao(cotacao, self.admin)

        sucesso, mensagem, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)

        self.assertFalse(sucesso)
        self.assertEqual("Esta cotacao ja possui ordem de compra gerada.", mensagem)
        self.assertEqual(1, len(ordens))
        self.assertEqual(1, SuprimentosOrdemCompra.query.count())

    def test_nao_gera_ordem_compra_para_cotacao_nao_aprovada(self):
        _, _, cotacao = salvar_cotacao(
            {"requisicao_id": str(self.requisicao.id)},
            self.admin,
        )

        sucesso, mensagem, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)

        self.assertFalse(sucesso)
        self.assertEqual("Somente cotacoes aprovadas podem gerar ordem de compra.", mensagem)
        self.assertEqual([], ordens)

    def test_cancela_ordem_compra(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]

        sucesso, mensagem = cancelar_ordem_compra(ordem, "erro de emissao")

        self.assertTrue(sucesso)
        self.assertEqual("Ordem de compra cancelada com sucesso.", mensagem)
        self.assertEqual(STATUS_ORDEM_COMPRA_CANCELADA, ordem.status)
        self.assertEqual(STATUS_FINANCEIRO_CANCELADO, ordem.status_financeiro)
        self.assertEqual("ERRO DE EMISSAO", ordem.motivo_cancelamento)

    def test_cancelamento_cancela_parcelas_financeiras(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(
            cotacao,
            self.admin,
            {"previsao_vencimento": "2026-09-10", "quantidade_parcelas": "2"},
        )
        ordem = ordens[0]

        sucesso, mensagem = cancelar_ordem_compra(ordem, "erro de emissao")

        self.assertTrue(sucesso)
        self.assertEqual("Ordem de compra cancelada com sucesso.", mensagem)
        self.assertEqual(STATUS_FINANCEIRO_CANCELADO, ordem.status_financeiro)
        self.assertEqual(["Cancelada", "Cancelada"], [parcela.status for parcela in ordem.parcelas_financeiras])

    def test_registra_recebimento_parcial_e_total_da_ordem(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        item = ordem.itens[0]

        sucesso, mensagem, recebimento = registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Nota Fiscal",
                "numero_documento": "nf 123",
                "data_documento": "2026-08-08",
                "observacoes": "recebimento parcial",
                f"quantidade_recebida_{item.id}": "1",
            },
            ordem,
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Recebimento registrado com sucesso.", mensagem)
        self.assertTrue(recebimento.numero.startswith("REC-"))
        self.assertEqual("Nota Fiscal", recebimento.tipo_documento)
        self.assertEqual("NF 123", recebimento.numero_documento)
        self.assertEqual("2026-08-08", recebimento.data_documento.isoformat())
        self.assertEqual("RECEBIMENTO PARCIAL", recebimento.observacoes)
        self.assertEqual(STATUS_ORDEM_COMPRA_PARCIAL, ordem.status)
        self.assertEqual(Decimal("1.000"), item.quantidade_recebida)
        self.assertEqual(Decimal("1.000"), item.saldo_receber)
        self.assertEqual(1, SuprimentosMovimentacaoEstoque.query.count())
        self.assertEqual(Decimal("1.000"), self.item.saldo_estoque)

        sucesso, mensagem, recebimento = registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Romaneio",
                "numero_documento": "rom 55",
                "data_documento": "2026-08-09",
                f"quantidade_recebida_{item.id}": "1",
            },
            ordem,
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertEqual(STATUS_ORDEM_COMPRA_RECEBIDA, ordem.status)
        self.assertEqual(Decimal("2.000"), item.quantidade_recebida)
        self.assertEqual(Decimal("0.000"), item.saldo_receber)
        self.assertEqual(2, SuprimentosMovimentacaoEstoque.query.count())
        self.assertEqual(Decimal("2.000"), self.item.saldo_estoque)

    def test_nao_duplica_entrada_estoque_do_mesmo_item_recebido(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        item = ordem.itens[0]
        _, _, recebimento = registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Nota Fiscal",
                "numero_documento": "nf 123",
                "data_documento": "2026-08-08",
                f"quantidade_recebida_{item.id}": "2",
            },
            ordem,
            self.admin,
        )
        recebimento_item = recebimento.itens[0]
        movimento = recebimento_item.movimentacao_estoque

        movimento_reprocessado = registrar_entrada_estoque_recebimento_item(recebimento_item)
        db.session.commit()

        self.assertEqual(movimento.id, movimento_reprocessado.id)
        self.assertEqual(1, SuprimentosMovimentacaoEstoque.query.count())
        self.assertEqual(Decimal("2.000"), self.item.saldo_estoque)

    def test_nao_movimenta_estoque_para_item_nao_estocavel(self):
        item_servico = SuprimentosItem(
            codigo_interno="SRV-001",
            descricao="SERVICO DE CALIBRAGEM",
            categoria_id=self.categoria.id,
            unidade_medida_id=self.unidade.id,
            centro_custo_padrao_id=self.centro.id,
            tipo="servico",
            item_estocavel=False,
            ativo=True,
        )
        db.session.add(item_servico)
        db.session.flush()
        db.session.add(
            SuprimentosFornecedorItem(
                fornecedor_id=self.fornecedor.id,
                item_id=item_servico.id,
                ativo=True,
                fornecedor_preferencial=False,
            )
        )
        db.session.commit()

        _, _, requisicao = salvar_requisicao_compra(
            {"centro_custo_id": str(self.centro.id), "justificativa": "Contratar servico"},
            self.admin,
        )
        adicionar_item_requisicao(
            {"item_id": str(item_servico.id), "quantidade": "1"},
            requisicao,
        )
        enviar_requisicao_compra(requisicao)
        requisicao_item = requisicao.itens[0]
        _, _, cotacao = salvar_cotacao({"requisicao_id": str(requisicao.id)}, self.admin)
        _, _, proposta = salvar_proposta_cotacao(
            {
                "requisicao_item_id": str(requisicao_item.id),
                "fornecedor_id": str(self.fornecedor.id),
                "preco_unitario": "50",
            },
            cotacao,
        )
        selecionar_proposta_vencedora({"proposta_id": str(proposta.id)}, cotacao, self.admin)
        enviar_cotacao_para_aprovacao(cotacao, self.admin)
        aprovar_cotacao(cotacao, self.admin, {"observacoes_aprovacao": "aprovado"})
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        ordem_item = ordem.itens[0]

        sucesso, _, recebimento = registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Outro",
                "numero_documento": "serv 1",
                "data_documento": "2026-08-08",
                f"quantidade_recebida_{ordem_item.id}": "1",
            },
            ordem,
            self.admin,
        )

        self.assertTrue(sucesso)
        self.assertIsNone(recebimento.itens[0].movimentacao_estoque)
        self.assertEqual(0, SuprimentosMovimentacaoEstoque.query.count())
        self.assertEqual(0, item_servico.saldo_estoque)

    def test_bloqueia_recebimento_acima_do_saldo(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        item = ordem.itens[0]

        sucesso, mensagem, recebimento = registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Cupom Fiscal",
                "numero_documento": "cf 1",
                "data_documento": "2026-08-08",
                f"quantidade_recebida_{item.id}": "3",
            },
            ordem,
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Quantidade recebida nao pode ser maior que o saldo do item.", mensagem)
        self.assertIsNone(recebimento)
        self.assertEqual(STATUS_ORDEM_COMPRA_GERADA, ordem.status)

    def test_exige_tipo_e_numero_documento_no_recebimento(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        item = ordem.itens[0]

        sucesso, mensagem, recebimento = registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Nota Fiscal",
                "data_documento": "2026-08-08",
                f"quantidade_recebida_{item.id}": "1",
            },
            ordem,
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Numero do documento e obrigatorio.", mensagem)
        self.assertIsNone(recebimento)

        sucesso, mensagem, recebimento = registrar_recebimento_ordem_compra(
            {
                "numero_documento": "doc 1",
                "data_documento": "2026-08-08",
                f"quantidade_recebida_{item.id}": "1",
            },
            ordem,
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Tipo de documento e obrigatorio.", mensagem)
        self.assertIsNone(recebimento)

        sucesso, mensagem, recebimento = registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Nota Fiscal",
                "numero_documento": "doc 1",
                f"quantidade_recebida_{item.id}": "1",
            },
            ordem,
            self.admin,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Data de recebimento e obrigatoria.", mensagem)
        self.assertIsNone(recebimento)

    def test_nao_cancela_ordem_com_recebimento(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        item = ordem.itens[0]
        registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Outro",
                "numero_documento": "doc 1",
                "data_documento": "2026-08-08",
                f"quantidade_recebida_{item.id}": "1",
            },
            ordem,
            self.admin,
        )

        sucesso, mensagem = cancelar_ordem_compra(ordem, "erro")

        self.assertFalse(sucesso)
        self.assertEqual("Ordem de compra com recebimento nao pode ser cancelada.", mensagem)
        self.assertEqual(STATUS_ORDEM_COMPRA_PARCIAL, ordem.status)

    def test_usuario_sem_permissao_nao_acessa_ordens_compra(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/ordens-compra/")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_usuario_com_visualizar_acessa_listagem(self):
        self._liberar_usuario(visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/suprimentos/ordens-compra/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Ordens de Compra", resposta.data)
        self.assertIn(b"Aguardando financeiro", resposta.data)

    def test_rota_aguardando_financeiro_exibe_ordem_pendente(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        self._autenticar(self.admin)

        resposta = self.client.get("/suprimentos/ordens-compra/aguardando-financeiro")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"OCs aguardando financeiro", resposta.data)
        self.assertIn(ordem.numero.encode(), resposta.data)

    def test_rota_gerar_exige_permissao_de_criar(self):
        cotacao = self._criar_cotacao_aprovada()
        self._liberar_usuario(visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.post(f"/suprimentos/ordens-compra/gerar/cotacao/{cotacao.id}")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_rota_receber_exige_permissao_de_editar(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        self._liberar_usuario(visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get(f"/suprimentos/ordens-compra/{ordem.id}/receber")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_rota_detalhes_exibe_ordem_recebida(self):
        cotacao = self._criar_cotacao_aprovada()
        _, _, ordens = gerar_ordens_compra_cotacao(cotacao, self.admin)
        ordem = ordens[0]
        item = ordem.itens[0]
        registrar_recebimento_ordem_compra(
            {
                "tipo_documento": "Nota Fiscal",
                "numero_documento": "nf 123",
                "data_documento": "2026-08-08",
                f"quantidade_recebida_{item.id}": "2",
            },
            ordem,
            self.admin,
        )
        self._autenticar(self.admin)

        resposta = self.client.get(f"/suprimentos/ordens-compra/{ordem.id}")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Recebimentos", resposta.data)
        self.assertIn(b"Entradas de Estoque", resposta.data)
        self.assertIn(b"Preparacao Financeira", resposta.data)
        self.assertIn(b"NF 123", resposta.data)
        self.assertIn(b"Recebida", resposta.data)

    def test_salva_evidencia_item_ordem_compra_com_foto(self):
        ordem = self._criar_ordem_compra()
        item = ordem.itens[0]
        self.app.config["GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID"] = "pasta-drive"
        drive = FakeDriveService()

        sucesso, mensagem, evidencia = salvar_evidencia_item_ordem_compra(
            ordem,
            item,
            {
                "data_evidencia": "2026-08-10",
                "destino_real": "Aplicado na retro R01",
                "observacao": "foto no recebimento",
            },
            {"foto_1": self._arquivo_imagem()},
            self.admin,
            drive_service=drive,
        )

        self.assertTrue(sucesso)
        self.assertEqual("Evidencia salva com sucesso.", mensagem)
        self.assertEqual("Evidenciado", evidencia.status)
        self.assertEqual("APLICADO NA RETRO R01", evidencia.destino_real)
        self.assertEqual("drive-file-1", evidencia.foto_1_drive_file_id)
        self.assertEqual("Evidenciado", status_evidencia_item_oc(item))
        self.assertEqual(1, SuprimentosOrdemCompraItemEvidencia.query.count())
        self.assertEqual(1, len(drive.files().uploads))
        self.assertIn("OC-", evidencia.foto_1_nome_arquivo)
        self.assertTrue(evidencia.foto_1_nome_arquivo.endswith(".jpg"))

    def test_rota_detalhes_exibe_fotos_anexadas_da_evidencia(self):
        ordem = self._criar_ordem_compra()
        item = ordem.itens[0]
        self.app.config["GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID"] = "pasta-drive"
        salvar_evidencia_item_ordem_compra(
            ordem,
            item,
            {
                "data_evidencia": "2026-08-10",
                "destino_real": "Aplicado na retro R01",
                "observacao": "foto no recebimento",
            },
            {"foto_1": self._arquivo_imagem()},
            self.admin,
            drive_service=FakeDriveService(),
        )
        self._autenticar(self.admin)

        resposta = self.client.get(f"/suprimentos/ordens-compra/{ordem.id}")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Fotos anexadas a Ordem de Compra", resposta.data)
        self.assertIn(b"Foto 1", resposta.data)
        self.assertIn(b"Foto 2", resposta.data)
        self.assertIn(b"thumbnail?id=drive-file-1", resposta.data)
        self.assertIn(b"Nenhuma foto 2 anexada", resposta.data)

    def test_exibe_mensagem_clara_quando_drive_recusa_cota_da_conta_servico(self):
        ordem = self._criar_ordem_compra()
        item = ordem.itens[0]
        self.app.config["GOOGLE_DRIVE_EVIDENCIAS_OC_FOLDER_ID"] = "pasta-drive"

        sucesso, mensagem, evidencia = salvar_evidencia_item_ordem_compra(
            ordem,
            item,
            {
                "data_evidencia": "2026-08-10",
                "destino_real": "Aplicado na retro R01",
            },
            {"foto_1": self._arquivo_imagem()},
            self.admin,
            drive_service=FakeDriveService(falhar_cota=True),
        )

        self.assertFalse(sucesso)
        self.assertIn("conta de servico nao possui cota", mensagem)
        self.assertIn("Drive compartilhado", mensagem)
        self.assertIsNone(evidencia)
        self.assertEqual(0, SuprimentosOrdemCompraItemEvidencia.query.count())

    def test_nao_salva_evidencia_sem_foto_nova(self):
        ordem = self._criar_ordem_compra()
        item = ordem.itens[0]

        sucesso, mensagem, evidencia = salvar_evidencia_item_ordem_compra(
            ordem,
            item,
            {
                "data_evidencia": "2026-08-10",
                "destino_real": "Aplicado na retro R01",
            },
            {},
            self.admin,
            drive_service=FakeDriveService(),
        )

        self.assertFalse(sucesso)
        self.assertEqual("Envie ao menos uma foto para registrar a evidencia.", mensagem)
        self.assertIsNone(evidencia)
        self.assertEqual(0, SuprimentosOrdemCompraItemEvidencia.query.count())

    def test_bloqueia_arquivo_que_nao_e_imagem(self):
        ordem = self._criar_ordem_compra()
        item = ordem.itens[0]
        arquivo = FileStorage(
            stream=BytesIO(b"texto"),
            filename="foto.txt",
            content_type="text/plain",
        )

        sucesso, mensagem, evidencia = salvar_evidencia_item_ordem_compra(
            ordem,
            item,
            {
                "data_evidencia": "2026-08-10",
                "destino_real": "Aplicado na retro R01",
            },
            {"foto_1": arquivo},
            self.admin,
            drive_service=FakeDriveService(),
        )

        self.assertFalse(sucesso)
        self.assertIn("JPG, JPEG, PNG ou WEBP", mensagem)
        self.assertIsNone(evidencia)

    def test_rota_evidencias_ordem_exibe_status_dos_itens(self):
        ordem = self._criar_ordem_compra()
        self._autenticar(self.admin)

        resposta = self.client.get(f"/suprimentos/ordens-compra/{ordem.id}/evidencias")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Evidencias", resposta.data)
        self.assertIn(b"Pendente", resposta.data)
        self.assertIn(ordem.numero.encode(), resposta.data)

    def test_rota_evidencia_item_exige_permissao_editar(self):
        ordem = self._criar_ordem_compra()
        item = ordem.itens[0]
        self._liberar_usuario(visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get(f"/suprimentos/ordens-compra/{ordem.id}/itens/{item.id}/evidencia")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])


if __name__ == "__main__":
    unittest.main()
