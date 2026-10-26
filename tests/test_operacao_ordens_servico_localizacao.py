import unittest
import uuid
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    LogAcesso,
    Modulo,
    NivelAcesso,
    OperacaoApontamentoDiario,
    OperacaoOrdemServico,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.operacao.ordens_servico.localizacao_service import (
    OPCOES,
    LocalizacaoErro,
    consultar_apontamentos,
    criar_apontamento,
    editar_apontamento,
)


class LocalizacaoDatabaseTestCase(unittest.TestCase):
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
        self.usuario = Usuario(nome="Operador", email="localizacao@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False)
        self.usuario.definir_senha("teste")
        departamento = Departamento(nome="Operação", slug="operacao", ativo=True)
        modulo = Modulo(departamento=departamento, nome="Ordens de Serviço", slug="ordens_de_servico", ativo=True)
        db.session.add_all([nivel, self.usuario, departamento, modulo])
        db.session.flush()
        self.permissao = PermissaoUsuarioModulo(
            usuario_id=self.usuario.id, modulo_id=modulo.id,
            pode_visualizar=True, pode_criar=True, pode_editar=True, ativo=True,
        )
        db.session.add(self.permissao)
        db.session.commit()
        self.ordem = self._nova_os("RR-OS-2026-LOCAL-1")
        self.outra_ordem = self._nova_os("RR-OS-2026-LOCAL-2")
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _nova_os(self, codigo):
        ordem = OperacaoOrdemServico(
            chave_idempotencia=str(uuid.uuid4()), codigo_os_rental=codigo,
            numero_os_cliente=None, local="Pátio XI", equipe="TMC AMV",
            encarregado=OPCOES["encarregado"][0],
            data_programada_inicial=date(2026, 10, 18), data_programada_final=date(2026, 10, 19),
            status_identificacao="Pendente", status_operacional="Programada",
            criado_por_usuario_id=self.usuario.id,
        )
        db.session.add(ordem)
        db.session.commit()
        return ordem

    def _dados(self, **campos):
        dados = {
            "data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0],
            "encarregado": OPCOES["encarregado"][0], "chefe_boletim": OPCOES["chefe_boletim"][0],
            "local": "Pátio XI", "amv": "AMV-1", "sub": "SUB-1", "km_inicio": "1+000",
            "km_fim": "1+100", "intervalo_inicio": "08:00", "intervalo_fim": "09:00",
            "pedido_liberacao_ccp": "07:50", "liberacao_embandeiramento": "08:00",
            "termino_embandeiramento": "09:10", "observacao": "Registro inicial",
        }
        dados.update(campos)
        return dados

    def _autenticar(self):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id)
            sessao["_fresh"] = True

    def test_cria_apontamento_com_os_opcional_e_auditoria(self):
        apontamento, repetido = criar_apontamento(self._dados(), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)

        self.assertFalse(repetido)
        self.assertEqual(self.ordem.id_os_interno, apontamento.id_os_interno)
        self.assertEqual("Pátio XI", apontamento.diario_localizacao.local)
        self.assertEqual(1, LogAcesso.query.filter_by(acao="operacao_localizacao_criada").count())

    def test_permite_multiplos_apontamentos_e_consulta_somente_da_os(self):
        criar_apontamento(self._dados(data_evento="2026-10-18"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        criar_apontamento(self._dados(data_evento="2026-10-19"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        criar_apontamento(self._dados(), self.outra_ordem.id_os_interno, str(uuid.uuid4()), self.usuario)

        registros = consultar_apontamentos(self.ordem.id_os_interno, self.usuario)
        self.assertEqual(2, len(registros))
        self.assertEqual([date(2026, 10, 19), date(2026, 10, 18)], [registro.data_evento for registro in registros])

    def test_reenvio_reutiliza_registro_e_chave_duplicada_eh_bloqueada(self):
        chave = str(uuid.uuid4())
        primeiro, repetido = criar_apontamento(self._dados(), self.ordem.id_os_interno, chave, self.usuario)
        segundo, reenvio = criar_apontamento(self._dados(), self.ordem.id_os_interno, chave, self.usuario)

        self.assertFalse(repetido)
        self.assertTrue(reenvio)
        self.assertEqual(primeiro.id_apontamento_diario, segundo.id_apontamento_diario)
        self.assertEqual(1, OperacaoApontamentoDiario.query.filter_by(id_os_interno=self.ordem.id_os_interno).count())

    def test_validacao_e_os_inexistente_nao_gravam(self):
        with self.assertRaises(LocalizacaoErro):
            criar_apontamento(self._dados(equipe="Inválida"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        with self.assertRaises(LocalizacaoErro):
            criar_apontamento(self._dados(), str(uuid.uuid4()), str(uuid.uuid4()), self.usuario)
        self.assertEqual(0, OperacaoApontamentoDiario.query.count())

    def test_edicao_registra_usuario_e_bloqueia_versao_desatualizada(self):
        apontamento, _ = criar_apontamento(self._dados(), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        editado = editar_apontamento(
            self._dados(local="Pátio Corrigido"), self.ordem.id_os_interno,
            apontamento.id_apontamento_diario, apontamento.versao, self.usuario,
        )
        self.assertEqual("Pátio Corrigido", editado.diario_localizacao.local)
        self.assertEqual(2, editado.versao)
        self.assertEqual(self.usuario.id, editado.atualizado_por_usuario_id)
        with self.assertRaises(LocalizacaoErro):
            editar_apontamento(self._dados(), self.ordem.id_os_interno, apontamento.id_apontamento_diario, 1, self.usuario)
        self.assertEqual(1, LogAcesso.query.filter_by(acao="operacao_localizacao_editada").count())

    def test_rota_preenche_os_e_persiste_apontamento(self):
        self._autenticar()
        pagina = self.client.get(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/localizacao")
        envio = self.client.post(
            f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/localizacao",
            data={**self._dados(), "chave_idempotencia": str(uuid.uuid4())},
        )

        self.assertEqual(200, pagina.status_code)
        self.assertIn("Pátio XI".encode("utf-8"), pagina.data)
        self.assertEqual(302, envio.status_code)
        self.assertEqual(1, len(consultar_apontamentos(self.ordem.id_os_interno, self.usuario)))

    def test_rotas_bloqueiam_uuid_invalido_e_edicao_sem_permissao(self):
        self._autenticar()
        invalida = self.client.get("/operacao/ordens-de-servico/invalido/localizacao")
        self.assertEqual(302, invalida.status_code)
        apontamento, _ = criar_apontamento(self._dados(), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        self.permissao.pode_editar = False
        db.session.commit()
        bloqueada = self.client.get(
            f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/localizacao/{apontamento.id_apontamento_diario}/editar"
        )
        self.assertEqual(302, bloqueada.status_code)


if __name__ == "__main__":
    unittest.main()
