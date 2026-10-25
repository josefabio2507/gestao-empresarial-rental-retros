import unittest
import uuid
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    Departamento, LogAcesso, Modulo, NivelAcesso, OperacaoApontamentoDiario,
    OperacaoOrdemServico, PermissaoUsuarioModulo, Usuario,
)
from app.operacao.ordens_servico.diarios_producao_service import (
    DiarioProducaoErro, buscar_registro, consultar_registros, criar_registro,
    editar_registro,
)
from app.operacao.ordens_servico.localizacao_service import OPCOES


class DiariosProducaoDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "SECRET_KEY": "test", "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False, "AUTO_MIGRATE_ON_START": False,
            "AUTO_SEED_MODULES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_UNIDADES_ON_START": False,
            "AUTO_SEED_SUPRIMENTOS_ITENS_ON_START": False, "AUTO_SEED_OPERACAO_VEICULOS_ON_START": False,
            "FISCAL_CONSULTA_AUTOMATICA_ENABLED": False,
        })
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.create_all()
        nivel = NivelAcesso(nome="Usuário", slug="usuario", ativo=True)
        self.usuario = Usuario(nome="Operador", email="diarios@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False)
        self.usuario.definir_senha("teste")
        departamento = Departamento(nome="Operação", slug="operacao", ativo=True)
        modulo = Modulo(departamento=departamento, nome="Ordens de Serviço", slug="ordens_de_servico", ativo=True)
        db.session.add_all([nivel, self.usuario, departamento, modulo])
        db.session.flush()
        self.permissao = PermissaoUsuarioModulo(usuario_id=self.usuario.id, modulo_id=modulo.id, pode_visualizar=True, pode_criar=True, pode_editar=True, ativo=True)
        db.session.add(self.permissao)
        db.session.commit()
        self.ordem = self._nova_os("RR-OS-2026-DIARIOS-1")
        self.outra_ordem = self._nova_os("RR-OS-2026-DIARIOS-2")
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _nova_os(self, codigo):
        ordem = OperacaoOrdemServico(chave_idempotencia=str(uuid.uuid4()), codigo_os_rental=codigo, local="Pátio XI", equipe="TMC AMV", data_programada_inicial=date(2026, 10, 18), data_programada_final=date(2026, 10, 19), status_identificacao="Pendente", status_operacional="Programada", criado_por_usuario_id=self.usuario.id)
        db.session.add(ordem)
        db.session.commit()
        return ordem

    def _dados(self, diario, **campos):
        dados = {"data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0], "quantidade": "2,5"}
        if diario == "servico":
            dados["servico"] = "Serviço ferroviário confirmado"
        else:
            dados.update({"tipo_material": "NOVO", "material_aplicado": "Material ferroviário confirmado"})
        dados.update(campos)
        return dados

    def _autenticar(self):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id)
            sessao["_fresh"] = True

    def test_cria_consulta_e_isola_servico_e_material_por_os(self):
        for diario in ("servico", "material"):
            primeiro, repetido = criar_registro(self._dados(diario), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario, diario)
            criar_registro(self._dados(diario, data_evento="2026-10-19"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario, diario)
            criar_registro(self._dados(diario), self.outra_ordem.id_os_interno, str(uuid.uuid4()), self.usuario, diario)
            self.assertFalse(repetido)
            self.assertEqual(2, len(consultar_registros(self.ordem.id_os_interno, self.usuario, diario)))
            self.assertEqual(self.ordem.id_os_interno, primeiro.id_os_interno)
        self.assertEqual(4, OperacaoApontamentoDiario.query.filter_by(id_os_interno=self.ordem.id_os_interno).count())

    def test_idempotencia_edicao_e_concorrencia(self):
        for diario in ("servico", "material"):
            chave = str(uuid.uuid4())
            apontamento, _ = criar_registro(self._dados(diario), self.ordem.id_os_interno, chave, self.usuario, diario)
            repetido, reenvio = criar_registro(self._dados(diario), self.ordem.id_os_interno, chave, self.usuario, diario)
            self.assertTrue(reenvio)
            self.assertEqual(apontamento.id_apontamento_diario, repetido.id_apontamento_diario)
            editado = editar_registro(self._dados(diario, quantidade="3"), self.ordem.id_os_interno, apontamento.id_apontamento_diario, 1, self.usuario, diario)
            self.assertEqual(2, editado.versao)
            self.assertEqual(self.usuario.id, editado.atualizado_por_usuario_id)
            with self.assertRaises(DiarioProducaoErro):
                editar_registro(self._dados(diario), self.ordem.id_os_interno, apontamento.id_apontamento_diario, 1, self.usuario, diario)
            with self.assertRaises(DiarioProducaoErro):
                buscar_registro(self.outra_ordem.id_os_interno, apontamento.id_apontamento_diario, self.usuario, diario)
        self.assertEqual(2, LogAcesso.query.filter_by(acao="operacao_servico_editado").count() + LogAcesso.query.filter_by(acao="operacao_material_editado").count())

    def test_validacoes_e_rotas_persistem_no_banco(self):
        for diario in ("servico", "material"):
            with self.assertRaises(DiarioProducaoErro):
                criar_registro(self._dados(diario, quantidade="0"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario, diario)
        self._autenticar()
        for rota, diario in (("servicos", "servico"), ("materiais", "material")):
            pagina = self.client.get(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/{rota}")
            envio = self.client.post(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/{rota}", data={**self._dados(diario), "chave_idempotencia": str(uuid.uuid4())})
            self.assertEqual(200, pagina.status_code)
            self.assertEqual(302, envio.status_code)
            apontamento = consultar_registros(self.ordem.id_os_interno, self.usuario, diario)[0]
            edicao = self.client.get(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/{diario}/{apontamento.id_apontamento_diario}/editar")
            self.assertEqual(200, edicao.status_code)

    def test_uuid_invalido_e_edicao_sem_permissao_sao_bloqueados(self):
        self._autenticar()
        self.assertEqual(302, self.client.get("/operacao/ordens-de-servico/invalido/servicos").status_code)
        apontamento, _ = criar_registro(self._dados("material"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario, "material")
        self.permissao.pode_editar = False
        db.session.commit()
        resposta = self.client.get(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/material/{apontamento.id_apontamento_diario}/editar")
        self.assertEqual(302, resposta.status_code)


if __name__ == "__main__":
    unittest.main()
