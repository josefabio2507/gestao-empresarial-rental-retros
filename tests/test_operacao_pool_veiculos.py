import unittest

from app import create_app
from app.extensions import db
from app.models import (
    Colaborador,
    Departamento,
    Equipe,
    Modulo,
    NivelAcesso,
    OperacaoLeituraAtivo,
    OperacaoVeiculoEquipamento,
    OperacaoVeiculoResponsavel,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.services.operacao_pool_service import (
    STATUS_DISPONIVEL,
    STATUS_EM_USO,
    STATUS_INDISPONIVEL,
    STATUS_VINCULO_ATIVO,
    STATUS_VINCULO_ENCERRADO,
    STATUS_VINCULO_RETIFICADO,
    alterar_indisponibilidade_veiculo,
    corrigir_vinculo,
    registrar_leitura,
    salvar_veiculo_equipamento,
    veiculos_vinculados_ao_colaborador,
    vincular_responsavel,
)


class OperacaoPoolVeiculosTestCase(unittest.TestCase):
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

        self.admin = Usuario(nome="Admin", email="admin@teste.com", nivel_acesso=admin, ativo=True, precisa_trocar_senha=False)
        self.usuario = Usuario(nome="Comum", email="comum@teste.com", nivel_acesso=comum, ativo=True, precisa_trocar_senha=False)
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])

        self.departamento = Departamento(nome="Operacao", slug="operacao", descricao="Teste", ativo=True, ordem=2)
        db.session.add(self.departamento)
        db.session.flush()
        self.modulo = Modulo(
            departamento_id=self.departamento.id,
            nome="Gestao de Veiculos e EGPs",
            slug="gestao_veiculos_epgs",
            ativo=True,
            ordem=1,
        )
        db.session.add(self.modulo)

        self.equipe = Equipe(nome="Operacao", slug="operacao", ativo=True)
        db.session.add(self.equipe)
        db.session.flush()
        self.motorista = Colaborador(
            matricula="M001",
            nome="Motorista Um",
            cpf="11111111111",
            equipe_id=self.equipe.id,
            ativo=True,
        )
        self.operador = Colaborador(
            matricula="M002",
            nome="Operador Dois",
            cpf="22222222222",
            equipe_id=self.equipe.id,
            ativo=True,
        )
        db.session.add_all([self.motorista, self.operador])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _criar_veiculo(self, identificacao="ABC1D23", descricao="FIAT MOBI"):
        sucesso, _, veiculo = salvar_veiculo_equipamento(
            {
                "identificacao": identificacao,
                "placa": identificacao,
                "descricao": descricao,
                "situacao_aquisicao": "Quitado",
                "tipo": "Veiculo leve",
            }
        )
        self.assertTrue(sucesso)
        return veiculo

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

    def test_cria_vinculo_e_registra_leitura_do_pool(self):
        veiculo = self._criar_veiculo()

        sucesso, mensagem, vinculo = vincular_responsavel(
            {
                "colaborador_id": str(self.motorista.id),
                "tipo_leitura": "odometro",
                "leitura_inicial": "1000,50",
            },
            usuario=self.admin,
            veiculo=veiculo,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(STATUS_VINCULO_ATIVO, vinculo.status)
        self.assertEqual(STATUS_EM_USO, veiculo.status_operacional)
        self.assertEqual(1, OperacaoLeituraAtivo.query.filter_by(veiculo_id=veiculo.id, origem="pool").count())

    def test_troca_automatica_preserva_historico(self):
        veiculo = self._criar_veiculo()
        _, _, primeiro = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )

        sucesso, mensagem, segundo = vincular_responsavel(
            {
                "colaborador_id": str(self.operador.id),
                "tipo_leitura": "odometro",
                "leitura_inicial": "25",
                "leitura_final_anterior": "20",
            },
            usuario=self.admin,
            veiculo=veiculo,
        )
        db.session.refresh(primeiro)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(STATUS_VINCULO_ENCERRADO, primeiro.status)
        self.assertIsNotNone(primeiro.encerrado_em)
        self.assertEqual(STATUS_VINCULO_ATIVO, segundo.status)
        self.assertEqual(2, OperacaoVeiculoResponsavel.query.filter_by(veiculo_id=veiculo.id).count())

    def test_motorista_pode_ter_multiplos_veiculos_ativos(self):
        veiculo_um = self._criar_veiculo("CAR001", "CAMINHAO")
        veiculo_dois = self._criar_veiculo("CAR002", "MAQUINA")

        self.assertTrue(vincular_responsavel({"colaborador_id": str(self.motorista.id)}, usuario=self.admin, veiculo=veiculo_um)[0])
        self.assertTrue(vincular_responsavel({"colaborador_id": str(self.motorista.id)}, usuario=self.admin, veiculo=veiculo_dois)[0])

        vinculados = veiculos_vinculados_ao_colaborador(self.motorista.id)
        self.assertEqual({veiculo_um.id, veiculo_dois.id}, {veiculo.id for veiculo in vinculados})

    def test_correcao_auditavel_nao_apaga_original_e_cria_novo(self):
        veiculo = self._criar_veiculo()
        _, _, vinculo = vincular_responsavel({"colaborador_id": str(self.motorista.id)}, usuario=self.admin, veiculo=veiculo)

        sucesso, mensagem, novo = corrigir_vinculo(
            vinculo,
            {
                "motivo_correcao": "Lancamento no operador incorreto",
                "status_correcao": STATUS_VINCULO_RETIFICADO,
                "criar_novo_vinculo": "1",
                "colaborador_id": str(self.operador.id),
            },
            usuario=self.admin,
        )
        db.session.refresh(vinculo)

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(STATUS_VINCULO_RETIFICADO, vinculo.status)
        self.assertEqual("Lancamento no operador incorreto", vinculo.motivo_correcao)
        self.assertEqual(self.admin.id, vinculo.corrigido_por_usuario_id)
        self.assertIsNotNone(vinculo.corrigido_em)
        self.assertEqual(self.operador.id, novo.colaborador_id)
        self.assertEqual(2, OperacaoVeiculoResponsavel.query.filter_by(veiculo_id=veiculo.id).count())

    def test_bloqueia_regressao_de_leitura_exceto_correcao_auditavel(self):
        veiculo = self._criar_veiculo()
        self.assertTrue(registrar_leitura(veiculo, "odometro", "100", usuario=self.admin)[0])

        sucesso, mensagem, _ = registrar_leitura(veiculo, "odometro", "90", usuario=self.admin)
        self.assertFalse(sucesso)
        self.assertEqual("Leitura menor que a ultima valida do ativo.", mensagem)

        sucesso, _, leitura = registrar_leitura(
            veiculo,
            "odometro",
            "90",
            origem="correcao",
            usuario=self.admin,
            permitir_regressao=True,
            motivo_correcao="Leitura anterior lancada com erro",
        )
        self.assertTrue(sucesso)
        self.assertEqual("correcao", leitura.origem)
        self.assertEqual("Leitura anterior lancada com erro", leitura.motivo_correcao)

    def test_status_disponivel_em_uso_e_indisponivel(self):
        veiculo = self._criar_veiculo()
        self.assertEqual(STATUS_DISPONIVEL, veiculo.status_operacional)

        vincular_responsavel({"colaborador_id": str(self.motorista.id)}, usuario=self.admin, veiculo=veiculo)
        self.assertEqual(STATUS_EM_USO, veiculo.status_operacional)

        sucesso, _ = alterar_indisponibilidade_veiculo(veiculo, indisponivel=True, motivo="Oficina")
        self.assertTrue(sucesso)
        self.assertEqual(STATUS_INDISPONIVEL, veiculo.status_operacional)

    def test_permissao_visualizar_rota_pool(self):
        self._autenticar(self.usuario)
        resposta = self.client.get("/operacao/pool-veiculos")
        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

        self._liberar_usuario(visualizar=True)
        resposta = self.client.get("/operacao/pool-veiculos")
        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Pool de Veiculos", resposta.data)


if __name__ == "__main__":
    unittest.main()

