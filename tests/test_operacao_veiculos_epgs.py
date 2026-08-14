import unittest
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

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
from app.services.operacao_veiculos_service import (
    executar_carga_inicial,
    salvar_veiculo_equipamento,
)


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
            email="admin.operacao@teste.com",
            nivel_acesso=admin,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario = Usuario(
            nome="Comum",
            email="comum.operacao@teste.com",
            nivel_acesso=comum,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])

        self.departamento = Departamento(
            nome="Operação",
            slug="operacao",
            descricao="Teste",
            ativo=True,
            ordem=3,
        )
        db.session.add(self.departamento)
        db.session.flush()

        self.modulo = Modulo(
            departamento_id=self.departamento.id,
            nome="Gestão de Veículos e EPGs",
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

    def test_usuario_sem_permissao_nao_acessa_rota_direta(self):
        self._autenticar(self.usuario)

        resposta = self.client.get("/operacao/gestao-veiculos-epgs/veiculos-equipamentos")

        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

    def test_admin_acessa_listagem_e_filtro_inicia_oculto(self):
        self._autenticar(self.admin)

        resposta = self.client.get("/operacao/gestao-veiculos-epgs/veiculos-equipamentos")

        self.assertEqual(200, resposta.status_code)
        self.assertIn("Informe um filtro para consultar".encode(), resposta.data)

    def test_salvar_recalcula_centro_custo_e_ignora_valor_manual(self):
        sucesso, mensagem, veiculo = salvar_veiculo_equipamento(
            {
                "identificacao": " abc123 ",
                "placa": "abc123",
                "descricao": " Equipamento Teste ",
                "chassi": "CHASSI001",
                "renavam": "",
                "centro_custo": "VALOR-MANUAL",
                "situacao_aquisicao": "Quitado",
                "tipo": "Equipamento",
            }
        )

        self.assertTrue(sucesso, mensagem)
        self.assertTrue(veiculo.ativo)
        self.assertEqual("abc123-Equipamento Teste", veiculo.centro_custo)

        sucesso, mensagem, veiculo = salvar_veiculo_equipamento(
            {
                "identificacao": "XYZ999",
                "placa": "XYZ999",
                "descricao": "Descricao Atualizada",
                "chassi": "CHASSI001",
                "renavam": "",
                "centro_custo": "OUTRO-VALOR",
                "situacao_aquisicao": "Financiado",
                "tipo": "Máquina",
                "ativo": "1",
            },
            veiculo,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual("XYZ999-Descricao Atualizada", veiculo.centro_custo)
        self.assertEqual(1, OperacaoVeiculoEquipamento.query.count())

    def test_carga_inicial_idempotente_cria_25_registros(self):
        primeiro_resumo = executar_carga_inicial()
        segundo_resumo = executar_carga_inicial()

        self.assertEqual(25, primeiro_resumo["processados"])
        self.assertEqual(25, primeiro_resumo["criados"])
        self.assertEqual(25, OperacaoVeiculoEquipamento.query.count())
        self.assertEqual(0, segundo_resumo["criados"])
        self.assertEqual(25, segundo_resumo["existentes"])
        self.assertEqual(25, OperacaoVeiculoEquipamento.query.count())

        escavadeira = OperacaoVeiculoEquipamento.query.filter_by(
            identificacao="ESC HIDRÁULICA",
        ).one()
        self.assertIsNone(escavadeira.placa)
        self.assertEqual("Financiado", escavadeira.situacao_aquisicao)
        self.assertEqual("ESC HIDRÁULICA-JOHN DEERE - 200G", escavadeira.centro_custo)


if __name__ == "__main__":
    unittest.main()
