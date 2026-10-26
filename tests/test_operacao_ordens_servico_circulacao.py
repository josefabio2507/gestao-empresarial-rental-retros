import unittest
import uuid
from datetime import date

from app import create_app
from app.extensions import db
from app.models import Departamento, LogAcesso, Modulo, NivelAcesso, OperacaoOrdemServico, PermissaoUsuarioModulo, Usuario
from app.operacao.ordens_servico.circulacao_service import CirculacaoErro, buscar_circulacao, consultar_circulacoes, criar_circulacao, editar_circulacao
from app.operacao.ordens_servico.localizacao_service import OPCOES


class CirculacaoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"SECRET_KEY": "test", "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SQLALCHEMY_TRACK_MODIFICATIONS": False, "AUTO_MIGRATE_ON_START": False, "AUTO_SEED_MODULES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_UNIDADES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_ITENS_ON_START": False, "AUTO_SEED_OPERACAO_VEICULOS_ON_START": False, "FISCAL_CONSULTA_AUTOMATICA_ENABLED": False})
        self.ctx = self.app.app_context(); self.ctx.push(); db.create_all()
        nivel = NivelAcesso(nome="Usuário", slug="usuario", ativo=True)
        self.usuario = Usuario(nome="Operador", email="circulacao@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False); self.usuario.definir_senha("teste")
        departamento = Departamento(nome="Operação", slug="operacao", ativo=True); modulo = Modulo(departamento=departamento, nome="Ordens de Serviço", slug="ordens_de_servico", ativo=True)
        db.session.add_all([nivel, self.usuario, departamento, modulo]); db.session.flush(); db.session.add(PermissaoUsuarioModulo(usuario_id=self.usuario.id, modulo_id=modulo.id, pode_visualizar=True, pode_criar=True, pode_editar=True, ativo=True)); db.session.commit()
        self.ordem = self._os("RR-OS-2026-CIRC-1"); self.outra_ordem = self._os("RR-OS-2026-CIRC-2"); self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()

    def _os(self, codigo):
        ordem = OperacaoOrdemServico(chave_idempotencia=str(uuid.uuid4()), codigo_os_rental=codigo, local="Pátio XI", equipe="TMC AMV", data_programada_inicial=date(2026, 10, 18), data_programada_final=date(2026, 10, 19), status_identificacao="Pendente", status_operacional="Programada", criado_por_usuario_id=self.usuario.id); db.session.add(ordem); db.session.commit(); return ordem

    def _dados(self, **campos):
        dados = {"data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0], "prefixo": "MRS-100", "hora_inicio": "08:00", "hora_fim": "08:30", "via_linha": "Linha 1", "pedido_corte_composicao": "SIM", "corte_composicao": "NÃO"}; dados.update(campos); return dados

    def test_criacao_idempotencia_consulta_e_edicao_concorrente(self):
        chave = str(uuid.uuid4()); primeiro, _ = criar_circulacao(self._dados(), self.ordem.id_os_interno, chave, self.usuario); repetido, reenvio = criar_circulacao(self._dados(), self.ordem.id_os_interno, chave, self.usuario)
        self.assertTrue(reenvio); self.assertEqual(primeiro.id_apontamento_diario, repetido.id_apontamento_diario)
        criar_circulacao(self._dados(prefixo="MRS-101"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario); criar_circulacao(self._dados(), self.outra_ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        self.assertEqual(2, len(consultar_circulacoes(self.ordem.id_os_interno, self.usuario)))
        editado = editar_circulacao(self._dados(via_linha="Linha 2"), self.ordem.id_os_interno, primeiro.id_apontamento_diario, 1, self.usuario); self.assertEqual(2, editado.versao)
        with self.assertRaises(CirculacaoErro): editar_circulacao(self._dados(), self.ordem.id_os_interno, primeiro.id_apontamento_diario, 1, self.usuario)
        with self.assertRaises(CirculacaoErro): buscar_circulacao(self.outra_ordem.id_os_interno, primeiro.id_apontamento_diario, self.usuario)
        self.assertEqual(1, LogAcesso.query.filter_by(acao="operacao_circulacao_editada").count())

    def test_validacoes_e_rotas(self):
        with self.assertRaises(CirculacaoErro): criar_circulacao(self._dados(via_linha=""), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        with self.assertRaises(CirculacaoErro): criar_circulacao(self._dados(pedido_corte_composicao="TALVEZ"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        with self.client.session_transaction() as sessao: sessao["_user_id"] = str(self.usuario.id); sessao["_fresh"] = True
        self.assertEqual(200, self.client.get(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/circulacao").status_code)
        self.assertEqual(302, self.client.post(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}/circulacao", data={**self._dados(), "chave_idempotencia": str(uuid.uuid4())}).status_code)
        self.assertEqual(302, self.client.get("/operacao/ordens-de-servico/invalido/circulacao").status_code)


if __name__ == "__main__": unittest.main()
