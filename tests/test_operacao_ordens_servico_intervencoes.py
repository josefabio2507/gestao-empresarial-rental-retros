import unittest
import uuid
from datetime import date
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models import Departamento, LogAcesso, Modulo, NivelAcesso, OperacaoApontamentoDiario, OperacaoOrdemServico, PermissaoUsuarioModulo, Usuario
from app.operacao.ordens_servico.intervencoes_service import IntervencaoErro, buscar_intervencao, consultar_intervencoes, criar_intervencao, editar_intervencao
from app.operacao.ordens_servico.localizacao_service import OPCOES


class IntervencoesAdversasTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"SECRET_KEY": "test", "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SQLALCHEMY_TRACK_MODIFICATIONS": False, "AUTO_MIGRATE_ON_START": False, "AUTO_SEED_MODULES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_UNIDADES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_ITENS_ON_START": False, "AUTO_SEED_OPERACAO_VEICULOS_ON_START": False, "FISCAL_CONSULTA_AUTOMATICA_ENABLED": False})
        self.contexto = self.app.app_context(); self.contexto.push(); db.create_all()
        nivel = NivelAcesso(nome="Usuário", slug="usuario", ativo=True)
        self.usuario = Usuario(nome="Operador", email="intervencoes@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False); self.usuario.definir_senha("teste")
        departamento = Departamento(nome="Operação", slug="operacao", ativo=True); modulo = Modulo(departamento=departamento, nome="Ordens de Serviço", slug="ordens_de_servico", ativo=True)
        db.session.add_all([nivel, self.usuario, departamento, modulo]); db.session.flush()
        self.permissao = PermissaoUsuarioModulo(usuario_id=self.usuario.id, modulo_id=modulo.id, pode_visualizar=True, pode_criar=True, pode_editar=True, ativo=True)
        db.session.add(self.permissao); db.session.commit()
        self.ordem = self._nova_os("RR-OS-2026-INT-1"); self.outra_ordem = self._nova_os("RR-OS-2026-INT-2")

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.contexto.pop()

    def _nova_os(self, codigo):
        ordem = OperacaoOrdemServico(chave_idempotencia=str(uuid.uuid4()), codigo_os_rental=codigo, local="Pátio XI", equipe="TMC AMV", data_programada_inicial=date(2026, 10, 18), data_programada_final=date(2026, 10, 19), status_identificacao="Pendente", status_operacional="Programada", criado_por_usuario_id=self.usuario.id)
        db.session.add(ordem); db.session.commit(); return ordem

    def _dados(self, **campos):
        dados = {"data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0], "hora_inicio": "08:00", "hora_fim": "08:30", "intervencao": "Chuva intensa", "categoria": "Clima"}; dados.update(campos); return dados

    def test_criacao_historico_isolamento_idempotencia_e_auditoria(self):
        chave = str(uuid.uuid4())
        primeiro, repetido = criar_intervencao(self._dados(), self.ordem.id_os_interno, chave, self.usuario)
        reenvio, foi_reenvio = criar_intervencao(self._dados(), self.ordem.id_os_interno, chave, self.usuario)
        criar_intervencao(self._dados(data_evento="2026-10-19"), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        criar_intervencao(self._dados(), self.outra_ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        self.assertFalse(repetido); self.assertTrue(foi_reenvio)
        self.assertEqual(primeiro.id_apontamento_diario, reenvio.id_apontamento_diario)
        self.assertEqual(2, len(consultar_intervencoes(self.ordem.id_os_interno, self.usuario)))
        with self.assertRaises(IntervencaoErro): buscar_intervencao(self.outra_ordem.id_os_interno, primeiro.id_apontamento_diario, self.usuario)
        self.assertEqual(3, LogAcesso.query.filter_by(acao="operacao_intervencao_criada").count())

    def test_validacoes_os_inexistente_rollback_e_permissao(self):
        for dados in (self._dados(categoria=""), self._dados(intervencao=""), self._dados(equipe="Outra")):
            with self.assertRaises(IntervencaoErro): criar_intervencao(dados, self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        for identificador in ("invalido", str(uuid.uuid4())):
            with self.assertRaises(IntervencaoErro): criar_intervencao(self._dados(), identificador, str(uuid.uuid4()), self.usuario)
        with patch("app.operacao.ordens_servico.intervencoes_service.db.session.commit", side_effect=IntegrityError("falha", {}, None)):
            with self.assertRaises(IntervencaoErro): criar_intervencao(self._dados(), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        self.assertEqual(0, OperacaoApontamentoDiario.query.filter_by(id_os_interno=self.ordem.id_os_interno).count())
        self.permissao.pode_criar = False; db.session.commit()
        with self.assertRaises(IntervencaoErro): criar_intervencao(self._dados(), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)

    def test_edicao_concorrencia_auditoria_e_permissao(self):
        apontamento, _ = criar_intervencao(self._dados(), self.ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        editado = editar_intervencao(self._dados(categoria="Outra categoria"), self.ordem.id_os_interno, apontamento.id_apontamento_diario, 1, self.usuario)
        self.assertEqual(2, editado.versao); self.assertEqual("Outra categoria", editado.intervencao_adversa.categoria)
        with self.assertRaises(IntervencaoErro): editar_intervencao(self._dados(), self.ordem.id_os_interno, apontamento.id_apontamento_diario, 1, self.usuario)
        self.assertEqual(1, LogAcesso.query.filter_by(acao="operacao_intervencao_editada").count())
        self.permissao.pode_editar = False; db.session.commit()
        with self.assertRaises(IntervencaoErro): editar_intervencao(self._dados(), self.ordem.id_os_interno, apontamento.id_apontamento_diario, 2, self.usuario)


if __name__ == "__main__": unittest.main()
