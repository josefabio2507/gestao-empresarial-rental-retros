import unittest
import uuid
from datetime import date
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Departamento, Modulo, NivelAcesso, OperacaoOrdemServico, PermissaoUsuarioModulo, Usuario


class OperacaoOrdensServicoTestCase(unittest.TestCase):
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
        usuario_comum = NivelAcesso(nome="Usuário", slug="usuario", ativo=True)
        db.session.add_all([admin, usuario_comum])
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
            nivel_acesso=usuario_comum,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.admin.definir_senha("teste")
        self.usuario.definir_senha("teste")
        db.session.add_all([self.admin, self.usuario])

        departamento = Departamento(nome="Operação", slug="operacao", ativo=True)
        self.modulo = Modulo(
            departamento=departamento,
            nome="Ordens de Serviço",
            slug="ordens_de_servico",
            ativo=True,
        )
        self.outro_modulo = Modulo(
            departamento=departamento,
            nome="Pool de Veículos",
            slug="pool_veiculos",
            ativo=True,
        )
        db.session.add_all([departamento, self.modulo, self.outro_modulo])
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

    def _liberar_visualizacao(self):
        db.session.add(
            PermissaoUsuarioModulo(
                usuario_id=self.usuario.id,
                modulo_id=self.modulo.id,
                pode_visualizar=True,
                ativo=True,
            )
        )
        db.session.commit()

    def test_usuario_autorizado_visualiza_cartao_e_acessa_pagina_inicial(self):
        self._liberar_visualizacao()
        self._autenticar(self.usuario)

        resposta_menu = self.client.get("/departamentos/operacao")
        resposta_modulo = self.client.get("/operacao/ordens-de-servico/")

        self.assertEqual(200, resposta_menu.status_code)
        self.assertIn(b'href="/operacao/ordens-de-servico/"', resposta_menu.data)
        self.assertEqual(200, resposta_modulo.status_code)
        self.assertIn("Gestão de Ordens de Serviço".encode("utf-8"), resposta_modulo.data)
        self.assertIn("Registros consultados diretamente na base operacional.".encode("utf-8"), resposta_modulo.data)
        self.assertIn(b'href="/departamentos/operacao"', resposta_modulo.data)

    def test_usuario_sem_permissao_nao_visualiza_cartao_nem_acessa_rota(self):
        db.session.add(
            PermissaoUsuarioModulo(
                usuario_id=self.usuario.id,
                modulo_id=self.outro_modulo.id,
                pode_visualizar=True,
                ativo=True,
            )
        )
        db.session.commit()
        self._autenticar(self.usuario)

        resposta_menu = self.client.get("/departamentos/operacao")
        resposta_modulo = self.client.get("/operacao/ordens-de-servico/")

        self.assertEqual(200, resposta_menu.status_code)
        self.assertNotIn(b'href="/operacao/ordens-de-servico/"', resposta_menu.data)
        self.assertEqual(302, resposta_modulo.status_code)
        self.assertIn("/acesso-negado", resposta_modulo.headers["Location"])

    def test_administrador_acessa_modulo_sem_permissao_individual(self):
        self._autenticar(self.admin)

        resposta = self.client.get("/operacao/ordens-de-servico/")

        self.assertEqual(200, resposta.status_code)
        self.assertIn("Registros consultados diretamente na base operacional.".encode("utf-8"), resposta.data)

    def test_central_exibe_detalhe_para_os_persistida(self):
        self._liberar_visualizacao()
        self._autenticar(self.usuario)
        ordem = self._criar_ordem("RR-OS-2026-ABC", "Pátio XI", "TMC")
        resposta = self.client.get("/operacao/ordens-de-servico/?local=Pátio")
        self.assertEqual(200, resposta.status_code)
        self.assertIn(f"/operacao/ordens-de-servico/{ordem.id_os_interno}".encode("utf-8"), resposta.data)
        self.assertNotIn(b"RR-OS-2026-ABC", resposta.data)

    def test_ficha_exige_identificador_interno_existente(self):
        self._liberar_visualizacao()
        self._autenticar(self.usuario)
        with patch("app.operacao.ordens_servico.routes.buscar_ordem_por_id", return_value=None):
            resposta = self.client.get("/operacao/ordens-de-servico/id-inexistente")
        self.assertEqual(302, resposta.status_code)
        self.assertIn("/operacao/ordens-de-servico/", resposta.headers["Location"])

    def test_relatorio_pdf_inclui_cronograma_da_os(self):
        self._liberar_visualizacao()
        self._autenticar(self.usuario)
        ordem = self._criar_ordem("RR-OS-2026-PDF", "Pátio XI", "TMC")

        resposta = self.client.get(f"/operacao/ordens-de-servico/{ordem.id_os_interno}/relatorio-pdf")

        self.assertEqual(200, resposta.status_code)
        self.assertEqual("application/pdf", resposta.mimetype)
        self.assertTrue(resposta.data.startswith(b"%PDF"))

    def test_localizacao_reutiliza_dados_da_os_e_exige_permissao_de_criacao(self):
        self._liberar_visualizacao()
        permissao = PermissaoUsuarioModulo.query.filter_by(
            usuario_id=self.usuario.id, modulo_id=self.modulo.id
        ).one()
        permissao.pode_criar = True
        db.session.commit()
        self._autenticar(self.usuario)
        ordem = self._criar_ordem("RR-OS-2026-LOCAL", "Pátio XI", "TMC AMV", "Maria")
        resposta = self.client.get(f"/operacao/ordens-de-servico/{ordem.id_os_interno}/localizacao")
        self.assertEqual(200, resposta.status_code)
        self.assertIn("Pátio XI".encode("utf-8"), resposta.data)
        self.assertIn("Maria".encode("utf-8"), resposta.data)
        permissao.pode_criar = False
        db.session.commit()
        envio = self.client.post(f"/operacao/ordens-de-servico/{ordem.id_os_interno}/localizacao")
        self.assertEqual(302, envio.status_code)
        self.assertIn("/acesso-negado", envio.headers["Location"])

    def _criar_ordem(self, codigo, local, equipe, encarregado=None):
        ordem = OperacaoOrdemServico(
            chave_idempotencia=str(uuid.uuid4()), codigo_os_rental=codigo, local=local,
            equipe=equipe, encarregado=encarregado,
            data_programada_inicial=date(2026, 10, 18), data_programada_final=date(2026, 10, 19),
            status_identificacao="Pendente", status_operacional="Programada", criado_por_usuario_id=self.usuario.id,
        )
        db.session.add(ordem); db.session.commit()
        return ordem


if __name__ == "__main__":
    unittest.main()
