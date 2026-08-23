import unittest

from app import create_app
from app.extensions import db
from app.models import (
    Departamento,
    Modulo,
    NivelAcesso,
    OperacaoVeiculoEquipamento,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.operacao.veiculos_equipamentos.services import salvar_veiculo_equipamento
from app.seed_operacao_veiculos_epgs import executar_seed


class OperacaoVeiculosEpgsTestCase(unittest.TestCase):
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
            nome="Operação",
            slug="operacao",
            descricao="Teste",
            ativo=True,
            ordem=3,
        )
        db.session.add(departamento)
        db.session.flush()

        self.modulo = Modulo(
            departamento_id=departamento.id,
            nome="Gestão de Veículos e EGPs",
            slug="gestao_veiculos_epgs",
            ativo=True,
            ordem=1,
        )
        db.session.add(self.modulo)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _autenticar(self, usuario):
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True

    def _liberar(self, **acoes):
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

    def test_admin_acessa_gestao_veiculos_epgs(self):
        self._autenticar(self.admin)

        resposta = self.client.get("/operacao/gestao-veiculos-epgs/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn("Gestão de Veículos e EGPs".encode("utf-8"), resposta.data)
        self.assertIn("Veículos e Equipamentos".encode("utf-8"), resposta.data)
        self.assertIn("Pool de Veículos".encode("utf-8"), resposta.data)

    def test_usuario_sem_permissao_nao_acessa_rota_direta(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/operacao/gestao-veiculos-epgs/veiculos-equipamentos")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_cria_edita_e_inativa_com_centro_custo_calculado(self):
        self._autenticar(self.admin)

        resposta = self.client.post(
            "/operacao/gestao-veiculos-epgs/veiculos-equipamentos/novo",
            data={
                "identificacao": " abc1d23 ",
                "placa": " abc1d23 ",
                "descricao": " fiat mobi like ",
                "chassi": " chassi123 ",
                "renavam": " renavam1 ",
                "centro_custo": "VALOR MANUAL INDEVIDO",
                "situacao_aquisicao": "Quitado",
                "tipo": "Veiculo leve",
            },
            follow_redirects=True,
        )
        registro = OperacaoVeiculoEquipamento.query.one()

        self.assertEqual(200, resposta.status_code)
        self.assertEqual("ABC1D23", registro.identificacao)
        self.assertEqual("ABC1D23-FIAT MOBI LIKE", registro.centro_custo)
        self.assertNotIn("VALOR MANUAL INDEVIDO", registro.centro_custo)

        resposta = self.client.post(
            f"/operacao/gestao-veiculos-epgs/veiculos-equipamentos/{registro.id}/editar",
            data={
                "identificacao": "maq interna",
                "descricao": "john deere - 200g",
                "chassi": "chassi123",
                "situacao_aquisicao": "Financiado",
                "tipo": "Maquina",
                "centro_custo": "OUTRO VALOR",
                "ativo": "on",
            },
            follow_redirects=True,
        )
        db.session.refresh(registro)

        self.assertEqual(200, resposta.status_code)
        self.assertEqual("MAQ INTERNA-JOHN DEERE - 200G", registro.centro_custo)
        self.assertEqual("Financiado", registro.situacao_aquisicao)

        self.client.post(
            f"/operacao/gestao-veiculos-epgs/veiculos-equipamentos/{registro.id}/status",
            follow_redirects=True,
        )
        db.session.refresh(registro)
        self.assertFalse(registro.ativo)

    def test_filtros_consultam_identificacao_chassi_centro_tipo_e_status(self):
        sucesso, _, registro = salvar_veiculo_equipamento(
            {
                "identificacao": "STG7D96",
                "placa": "STG7D96",
                "descricao": "CITROEN JUMPY",
                "chassi": "9V7VBYHVERA007070",
                "situacao_aquisicao": "Quitado",
                "tipo": "Veiculo leve",
            }
        )
        self.assertTrue(sucesso)
        self._autenticar(self.admin)

        for termo in ["STG7D96", "9V7VBYHVERA007070", "STG7D96-CITROEN JUMPY"]:
            resposta = self.client.get(
                "/operacao/gestao-veiculos-epgs/veiculos-equipamentos",
                query_string={"termo": termo, "tipo": "Veiculo leve", "status": "ativos"},
            )
            self.assertEqual(200, resposta.status_code)
            self.assertIn(registro.identificacao.encode(), resposta.data)

    def test_seed_inicial_cria_25_registros_sem_duplicar(self):
        executar_seed()
        self.assertEqual(25, OperacaoVeiculoEquipamento.query.count())
        self.assertEqual(
            "ESC HIDRÁULICA-JOHN DEERE - 200G",
            OperacaoVeiculoEquipamento.query.filter_by(chassi="1F9200GXPND020551").one().centro_custo,
        )

        executar_seed()

        self.assertEqual(25, OperacaoVeiculoEquipamento.query.count())


if __name__ == "__main__":
    unittest.main()
