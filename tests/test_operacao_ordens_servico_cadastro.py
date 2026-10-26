import unittest
import uuid
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    LogAcesso,
    Modulo,
    NivelAcesso,
    OperacaoOrdemServico,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.operacao.ordens_servico.cadastro_service import (
    OrdemServicoCadastroErro,
    criar_ordem_servico,
)


class OperacaoOrdensServicoCadastroTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "SECRET_KEY": "test",
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "AUTO_MIGRATE_ON_START": False,
            "AUTO_SEED_MODULES_ON_START": False,
            "AUTO_SEED_SUPRIMENTOS_UNIDADES_ON_START": False,
            "AUTO_SEED_SUPRIMENTOS_ITENS_ON_START": False,
            "AUTO_SEED_OPERACAO_VEICULOS_ON_START": False,
            "FISCAL_CONSULTA_AUTOMATICA_ENABLED": False,
        })
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()

        nivel = NivelAcesso(nome="Usuário", slug="usuario", ativo=True)
        self.usuario = Usuario(
            nome="Operador",
            email="operador-os@teste.com",
            nivel_acesso=nivel,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario.definir_senha("teste")
        departamento = Departamento(nome="Operação", slug="operacao", ativo=True)
        modulo = Modulo(
            departamento=departamento,
            nome="Ordens de Serviço",
            slug="ordens_de_servico",
            ativo=True,
        )
        db.session.add_all([nivel, self.usuario, departamento, modulo])
        db.session.flush()
        self.permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id,
            modulo_id=modulo.id,
            pode_visualizar=True,
            pode_criar=True,
            ativo=True,
        )
        db.session.add(self.permissao)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _dados(self, **campos):
        dados = {
            "numero_os_cliente": "OS-CLIENTE-77",
            "local": "Pátio XI",
            "equipe": "TMC AMV",
            "data_programada_inicial": "2026-10-18",
            "data_programada_final": "2026-10-19",
            "data_inicial": "",
            "data_final": "",
            "trabalho_previsto": "Manutenção",
            "supervisor": "Supervisor",
            "encarregado": "Encarregado",
        }
        dados.update(campos)
        return dados

    def _autenticar(self):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id)
            sessao["_fresh"] = True

    def test_cria_os_com_numero_cliente_status_e_auditoria(self):
        ordem, reutilizada = criar_ordem_servico(self._dados(), str(uuid.uuid4()), self.usuario)

        self.assertFalse(reutilizada)
        self.assertEqual("Informado", ordem.status_identificacao)
        self.assertEqual("Programada", ordem.status_operacional)
        self.assertEqual(self.usuario.id, ordem.criado_por_usuario_id)
        self.assertEqual(1, OperacaoOrdemServico.query.count())
        self.assertEqual(1, LogAcesso.query.filter_by(acao="operacao_ordem_servico_criada").count())

    def test_cria_os_sem_numero_cliente(self):
        ordem, _ = criar_ordem_servico(
            self._dados(numero_os_cliente=""), str(uuid.uuid4()), self.usuario
        )

        self.assertIsNone(ordem.numero_os_cliente)
        self.assertEqual("Pendente", ordem.status_identificacao)

    def test_reenvio_com_mesma_chave_reutiliza_a_mesma_os(self):
        chave = str(uuid.uuid4())
        primeira, reutilizada = criar_ordem_servico(self._dados(), chave, self.usuario)
        segunda, repetida = criar_ordem_servico(self._dados(), chave, self.usuario)

        self.assertFalse(reutilizada)
        self.assertTrue(repetida)
        self.assertEqual(primeira.id_os_interno, segunda.id_os_interno)
        self.assertEqual(1, OperacaoOrdemServico.query.count())

    def test_banco_bloqueia_chave_idempotente_duplicada(self):
        chave = str(uuid.uuid4())
        ordem, _ = criar_ordem_servico(self._dados(), chave, self.usuario)
        db.session.add(
            OperacaoOrdemServico(
                chave_idempotencia=chave,
                codigo_os_rental="RR-OS-2026-CODIGO-DUPLICADO",
                local=ordem.local,
                equipe=ordem.equipe,
                data_programada_inicial=ordem.data_programada_inicial,
                data_programada_final=ordem.data_programada_final,
                criado_por_usuario_id=self.usuario.id,
            )
        )

        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_validacao_falha_sem_persistir_registro(self):
        with self.assertRaises(OrdemServicoCadastroErro):
            criar_ordem_servico(self._dados(local=""), str(uuid.uuid4()), self.usuario)
        self.assertEqual(0, OperacaoOrdemServico.query.count())

    def test_rollback_em_falha_de_transacao(self):
        with patch("app.operacao.ordens_servico.cadastro_service.db.session.commit", side_effect=IntegrityError("falha", {}, None)):
            with self.assertRaises(OrdemServicoCadastroErro):
                criar_ordem_servico(self._dados(), str(uuid.uuid4()), self.usuario)
        self.assertEqual(0, OperacaoOrdemServico.query.count())

    def test_rota_de_criacao_persiste_no_banco_operacional(self):
        self._autenticar()
        dados = self._dados(chave_idempotencia=str(uuid.uuid4()))
        resposta = self.client.post("/operacao/ordens-de-servico/nova", data=dados)

        self.assertEqual(302, resposta.status_code)
        self.assertEqual(1, OperacaoOrdemServico.query.count())

    def test_rota_bloqueia_usuario_sem_permissao_de_criar(self):
        self.permissao.pode_criar = False
        db.session.commit()
        self._autenticar()

        resposta = self.client.post(
            "/operacao/ordens-de-servico/nova",
            data=self._dados(chave_idempotencia=str(uuid.uuid4())),
        )

        self.assertEqual(302, resposta.status_code)
        self.assertEqual(0, OperacaoOrdemServico.query.count())


if __name__ == "__main__":
    unittest.main()
