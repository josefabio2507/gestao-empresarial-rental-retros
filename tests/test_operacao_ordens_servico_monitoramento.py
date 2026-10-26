import unittest
import uuid
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (Departamento, Modulo, NivelAcesso, OperacaoApontamentoDiario,
                        OperacaoCirculacaoTrem, OperacaoDiarioLocalizacao, OperacaoDiarioMaterial,
                        OperacaoDiarioServico, OperacaoIntervencaoAdversa, OperacaoOrdemServico,
                        PermissaoUsuarioModulo, Usuario)
from app.operacao.ordens_servico.monitoramento_service import obter_monitoramento


class MonitoramentoOrdemServicoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"SECRET_KEY": "test", "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SQLALCHEMY_TRACK_MODIFICATIONS": False, "AUTO_MIGRATE_ON_START": False, "AUTO_SEED_MODULES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_UNIDADES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_ITENS_ON_START": False, "AUTO_SEED_OPERACAO_VEICULOS_ON_START": False, "FISCAL_CONSULTA_AUTOMATICA_ENABLED": False})
        self.ctx = self.app.app_context(); self.ctx.push(); db.create_all()
        nivel = NivelAcesso(nome="Usuário", slug="usuario", ativo=True)
        self.usuario = Usuario(nome="Operador", email="monitoramento@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False); self.usuario.definir_senha("teste")
        departamento = Departamento(nome="Operação", slug="operacao", ativo=True); modulo = Modulo(departamento=departamento, nome="Ordens de Serviço", slug="ordens_de_servico", ativo=True)
        db.session.add_all([nivel, self.usuario, departamento, modulo]); db.session.flush(); db.session.add(PermissaoUsuarioModulo(usuario_id=self.usuario.id, modulo_id=modulo.id, pode_visualizar=True, ativo=True)); db.session.commit()
        self.ordem = OperacaoOrdemServico(chave_idempotencia=str(uuid.uuid4()), codigo_os_rental="RR-OS-MON-1", local="Pátio", equipe="TMC AMV", data_programada_inicial=date(2026, 10, 18), data_programada_final=date(2026, 10, 19), status_identificacao="Pendente", status_operacional="Programada", criado_por_usuario_id=self.usuario.id)
        db.session.add(self.ordem); db.session.commit()

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()

    def _apontamento(self, dia):
        item = OperacaoApontamentoDiario(id_os_interno=self.ordem.id_os_interno, chave_idempotencia=str(uuid.uuid4()), data_evento=dia, equipe="TMC AMV", criado_por_usuario_id=self.usuario.id)
        db.session.add(item); db.session.flush(); return item

    def test_consolida_todos_os_diarios_sem_carregar_registros(self):
        local = self._apontamento(date(2026, 10, 18)); db.session.add(OperacaoDiarioLocalizacao(id_apontamento_diario=local.id_apontamento_diario, encarregado="E", chefe_boletim="C", local="Pátio"))
        servico = self._apontamento(date(2026, 10, 19)); db.session.add(OperacaoDiarioServico(id_apontamento_diario=servico.id_apontamento_diario, servico="Serviço", quantidade=1))
        material = self._apontamento(date(2026, 10, 20)); db.session.add(OperacaoDiarioMaterial(id_apontamento_diario=material.id_apontamento_diario, tipo_material="NOVO", material_aplicado="Material", quantidade=1))
        circulacao = self._apontamento(date(2026, 10, 21)); db.session.add(OperacaoCirculacaoTrem(id_apontamento_diario=circulacao.id_apontamento_diario, via_linha="Linha 1", pedido_corte_composicao="SIM", corte_composicao="NÃO"))
        intervencao = self._apontamento(date(2026, 10, 22)); db.session.add(OperacaoIntervencaoAdversa(id_apontamento_diario=intervencao.id_apontamento_diario, intervencao="Chuva", categoria="Clima")); db.session.commit()
        resumo = obter_monitoramento(self.ordem.id_os_interno, self.usuario)
        self.assertEqual((1, 1, 1, 1, 1), (resumo.localizacoes, resumo.servicos, resumo.materiais, resumo.circulacoes, resumo.intervencoes))
        self.assertEqual(5, resumo.total_apontamentos); self.assertEqual(date(2026, 10, 22), resumo.ultimo_apontamento)
        client = self.app.test_client()
        with client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id); sessao["_fresh"] = True
        resposta = client.get(f"/operacao/ordens-de-servico/{self.ordem.id_os_interno}")
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Monitoramento e aderência", resposta.get_data(as_text=True))
        self.assertIn("Intervenções adversas:</strong> 1", resposta.get_data(as_text=True))

    def test_os_sem_apontamentos(self):
        resumo = obter_monitoramento(self.ordem.id_os_interno, self.usuario)
        self.assertEqual(0, resumo.total_apontamentos); self.assertFalse(resumo.possui_apontamentos); self.assertIsNone(resumo.ultimo_apontamento)

    def test_total_conta_apontamento_uma_unica_vez_mesmo_com_filhos_inconsistentes(self):
        apontamento = self._apontamento(date(2026, 10, 18))
        db.session.add(OperacaoDiarioServico(id_apontamento_diario=apontamento.id_apontamento_diario, servico="Serviço", quantidade=1))
        db.session.add(OperacaoDiarioMaterial(id_apontamento_diario=apontamento.id_apontamento_diario, tipo_material="NOVO", material_aplicado="Material", quantidade=1))
        db.session.commit()

        resumo = obter_monitoramento(self.ordem.id_os_interno, self.usuario)

        self.assertEqual(1, resumo.servicos)
        self.assertEqual(1, resumo.materiais)
        self.assertEqual(1, resumo.total_apontamentos)


if __name__ == "__main__": unittest.main()
