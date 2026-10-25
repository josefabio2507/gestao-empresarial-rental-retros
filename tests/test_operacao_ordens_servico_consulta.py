import unittest
import uuid
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    Modulo,
    NivelAcesso,
    OperacaoOrdemServico,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.operacao.ordens_servico.cadastro_service import criar_ordem_servico
from app.operacao.ordens_servico.consulta_service import (
    OrdemServicoConsultaErro,
    buscar_ordem_por_id,
    consultar_ordens,
)


class OperacaoOrdensServicoConsultaTestCase(unittest.TestCase):
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
            nome="Consultor",
            email="consulta-os@teste.com",
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
        self.ordens = [
            self._criar_os("RR-OS-2026-AAA", "CLIENTE-1", "Pátio XI", "TMC AMV", date(2026, 10, 18), "Informado"),
            self._criar_os("RR-OS-2026-BBB", None, "Pátio XII", "TMC LIMPEZA", date(2026, 10, 20), "Pendente"),
            self._criar_os("RR-OS-2026-CCC", "CLIENTE-3", "Pátio XI", "TMC AMV", date(2026, 10, 22), "Informado"),
        ]

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _criar_os(self, codigo, numero, local, equipe, inicio, identificacao):
        ordem = OperacaoOrdemServico(
            chave_idempotencia=str(uuid.uuid4()),
            codigo_os_rental=codigo,
            numero_os_cliente=numero,
            local=local,
            equipe=equipe,
            trabalho_previsto="Manutenção",
            data_programada_inicial=inicio,
            data_programada_final=inicio,
            status_identificacao=identificacao,
            status_operacional="Programada",
            criado_por_usuario_id=self.usuario.id,
        )
        db.session.add(ordem)
        db.session.commit()
        return ordem

    def _autenticar(self):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id)
            sessao["_fresh"] = True

    def test_consulta_aplica_filtros_no_banco(self):
        self.assertEqual(1, consultar_ordens({"codigo_os_rental": "BBB"}, 1, self.usuario).total)
        self.assertEqual(1, consultar_ordens({"numero_os_cliente": "CLIENTE-1"}, 1, self.usuario).total)
        self.assertEqual(2, consultar_ordens({"local": "Pátio XI", "equipe": "TMC AMV"}, 1, self.usuario).total)
        self.assertEqual(2, consultar_ordens({"status_identificacao": "Informado", "status_operacional": "Programada"}, 1, self.usuario).total)
        self.assertEqual(
            2,
            consultar_ordens(
                {"periodo_inicial": "2026-10-19", "periodo_final": "2026-10-23"},
                1,
                self.usuario,
            ).total,
        )

    def test_paginacao_e_ordenacao_sao_deterministicas(self):
        primeira = consultar_ordens({}, "invalida", self.usuario, tamanho_pagina=1)
        segunda = consultar_ordens({}, 2, self.usuario, tamanho_pagina=1)

        self.assertEqual(3, primeira.total)
        self.assertEqual(3, primeira.total_paginas)
        self.assertEqual(1, primeira.pagina)
        self.assertEqual("RR-OS-2026-CCC", primeira.itens[0].codigo_os_rental)
        self.assertEqual("RR-OS-2026-BBB", segunda.itens[0].codigo_os_rental)

    def test_ficha_consulta_por_uuid_e_rejeita_identificador_invalido(self):
        encontrada = buscar_ordem_por_id(self.ordens[0].id_os_interno, self.usuario)
        self.assertEqual(self.ordens[0].codigo_os_rental, encontrada.codigo_os_rental)
        with self.assertRaises(OrdemServicoConsultaErro):
            buscar_ordem_por_id("invalido", self.usuario)

    def test_rotas_usam_banco_operacional(self):
        self._autenticar()
        central = self.client.get("/operacao/ordens-de-servico/?local=Pátio+XI")
        ficha = self.client.get(f"/operacao/ordens-de-servico/{self.ordens[0].id_os_interno}")

        self.assertEqual(200, central.status_code)
        self.assertEqual(200, ficha.status_code)
        self.assertIn(b"RR-OS-2026-AAA", central.data)
        self.assertIn(b"RR-OS-2026-AAA", ficha.data)

    def test_cadastro_redireciona_para_ficha_disponivel_imediatamente(self):
        self._autenticar()
        resposta = self.client.post(
            "/operacao/ordens-de-servico/nova",
            data={
                "chave_idempotencia": str(uuid.uuid4()),
                "numero_os_cliente": "CLIENTE-NOVO",
                "local": "Pátio Novo",
                "equipe": "TMC AMV",
                "data_programada_inicial": "2026-10-24",
                "data_programada_final": "2026-10-25",
            },
        )

        self.assertEqual(302, resposta.status_code)
        criada = OperacaoOrdemServico.query.filter_by(numero_os_cliente="CLIENTE-NOVO").one()
        self.assertIn(criada.id_os_interno, resposta.headers["Location"])
        self.assertEqual(200, self.client.get(resposta.headers["Location"]).status_code)

    def test_rotas_preservam_bloqueio_por_permissao_e_nao_encontrada(self):
        self._autenticar()
        inexistente = self.client.get(f"/operacao/ordens-de-servico/{uuid.uuid4()}")
        self.assertEqual(302, inexistente.status_code)

        self.permissao.pode_visualizar = False
        db.session.commit()
        bloqueada = self.client.get("/operacao/ordens-de-servico/")
        self.assertEqual(302, bloqueada.status_code)


if __name__ == "__main__":
    unittest.main()
