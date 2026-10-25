import unittest
import uuid

from app import create_app
from app.extensions import db
from app.models import Departamento, LogAcesso, Modulo, NivelAcesso, OperacaoOrdemServico, PermissaoUsuarioModulo, Usuario
from app.operacao.ordens_servico.cadastro_service import criar_ordem_servico
from app.operacao.ordens_servico.circulacao_service import criar_circulacao
from app.operacao.ordens_servico.consulta_service import consultar_ordens
from app.operacao.ordens_servico.diarios_producao_service import DiarioProducaoErro, criar_registro, editar_registro
from app.operacao.ordens_servico.intervencoes_service import criar_intervencao
from app.operacao.ordens_servico.localizacao_service import OPCOES, criar_apontamento
from app.operacao.ordens_servico.monitoramento_service import obter_monitoramento


class HomologacaoIntegradaOrdensServicoTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"SECRET_KEY": "test", "TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SQLALCHEMY_TRACK_MODIFICATIONS": False, "AUTO_MIGRATE_ON_START": False, "AUTO_SEED_MODULES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_UNIDADES_ON_START": False, "AUTO_SEED_SUPRIMENTOS_ITENS_ON_START": False, "AUTO_SEED_OPERACAO_VEICULOS_ON_START": False, "FISCAL_CONSULTA_AUTOMATICA_ENABLED": False})
        self.contexto = self.app.app_context(); self.contexto.push(); db.create_all()
        nivel = NivelAcesso(nome="Usuário", slug="usuario", ativo=True)
        self.usuario = Usuario(nome="Homologador", email="homologacao-os@teste.com", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False); self.usuario.definir_senha("teste")
        departamento = Departamento(nome="Operação", slug="operacao", ativo=True); modulo = Modulo(departamento=departamento, nome="Ordens de Serviço", slug="ordens_de_servico", ativo=True)
        db.session.add_all([nivel, self.usuario, departamento, modulo]); db.session.flush(); db.session.add(PermissaoUsuarioModulo(usuario_id=self.usuario.id, modulo_id=modulo.id, pode_visualizar=True, pode_criar=True, pode_editar=True, ativo=True)); db.session.commit()

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.contexto.pop()

    def _dados_os(self, **campos):
        dados = {"numero_os_cliente": "", "local": "Pátio de homologação", "equipe": OPCOES["equipe"][0], "data_programada_inicial": "2026-10-18", "data_programada_final": "2026-10-19", "trabalho_previsto": "Manutenção sintética", "supervisor": "Supervisor", "encarregado": "Encarregado"}; dados.update(campos); return dados

    def test_fluxo_integrado_completo_em_banco_isolado(self):
        ordem, reenvio = criar_ordem_servico(self._dados_os(), str(uuid.uuid4()), self.usuario)
        self.assertFalse(reenvio); self.assertEqual("Programada", ordem.status_operacional); self.assertEqual("Pendente", ordem.status_identificacao); self.assertEqual(36, len(ordem.id_os_interno))
        self.assertEqual(ordem.id_os_interno, consultar_ordens({"codigo_os_rental": ordem.codigo_os_rental}, 1, self.usuario).itens[0].id_os_interno)

        localizacao, _ = criar_apontamento({"data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0], "encarregado": OPCOES["encarregado"][0], "chefe_boletim": OPCOES["chefe_boletim"][0], "local": "Pátio de homologação"}, ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        servico_dados = {"data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0], "servico": "Serviço sintético", "quantidade": "2"}
        servico_chave = str(uuid.uuid4()); servico, _ = criar_registro(servico_dados, ordem.id_os_interno, servico_chave, self.usuario, "servico")
        repetido, foi_reenvio = criar_registro(servico_dados, ordem.id_os_interno, servico_chave, self.usuario, "servico")
        material, _ = criar_registro({"data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0], "tipo_material": "NOVO", "material_aplicado": "Material sintético", "quantidade": "1"}, ordem.id_os_interno, str(uuid.uuid4()), self.usuario, "material")
        circulacao, _ = criar_circulacao({"data_evento": "2026-10-18", "equipe": OPCOES["equipe"][0], "via_linha": "Linha sintética", "pedido_corte_composicao": "SIM", "corte_composicao": "NÃO"}, ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        intervencao, _ = criar_intervencao({"data_evento": "2026-10-19", "equipe": OPCOES["equipe"][0], "intervencao": "Evento sintético", "categoria": "Categoria ainda livre"}, ordem.id_os_interno, str(uuid.uuid4()), self.usuario)
        self.assertTrue(foi_reenvio); self.assertEqual(servico.id_apontamento_diario, repetido.id_apontamento_diario)

        editado = editar_registro({**servico_dados, "quantidade": "3"}, ordem.id_os_interno, servico.id_apontamento_diario, 1, self.usuario, "servico")
        self.assertEqual(2, editado.versao)
        with self.assertRaises(DiarioProducaoErro): editar_registro(servico_dados, ordem.id_os_interno, servico.id_apontamento_diario, 1, self.usuario, "servico")

        resumo = obter_monitoramento(ordem.id_os_interno, self.usuario)
        self.assertEqual((1, 1, 1, 1, 1), (resumo.localizacoes, resumo.servicos, resumo.materiais, resumo.circulacoes, resumo.intervencoes))
        self.assertEqual(5, resumo.total_apontamentos)
        outra, _ = criar_ordem_servico(self._dados_os(local="Outro pátio"), str(uuid.uuid4()), self.usuario)
        self.assertEqual(0, obter_monitoramento(outra.id_os_interno, self.usuario).total_apontamentos)
        self.assertEqual("Programada", ordem.status_operacional)
        self.assertGreaterEqual(LogAcesso.query.filter_by(usuario_id=self.usuario.id).count(), 7)
        self.assertEqual(2, OperacaoOrdemServico.query.count())
        self.assertEqual(5, len({localizacao.id_apontamento_diario, servico.id_apontamento_diario, material.id_apontamento_diario, circulacao.id_apontamento_diario, intervencao.id_apontamento_diario}))


if __name__ == "__main__": unittest.main()
