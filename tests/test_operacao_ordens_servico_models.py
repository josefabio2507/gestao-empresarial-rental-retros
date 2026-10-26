import unittest
import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models import (
    NivelAcesso,
    OperacaoApontamentoDiario,
    OperacaoDiarioLocalizacao,
    OperacaoOrdemServico,
    Usuario,
)


class OperacaoOrdensServicoModelsTestCase(unittest.TestCase):
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
        db.session.execute(text("PRAGMA foreign_keys=ON"))

        nivel = NivelAcesso(nome="Administrador", slug="administrador", ativo=True)
        self.usuario = Usuario(
            nome="Admin",
            email="admin-os@teste.com",
            nivel_acesso=nivel,
            ativo=True,
            precisa_trocar_senha=False,
        )
        self.usuario.definir_senha("teste")
        db.session.add_all([nivel, self.usuario])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.session.execute(text("PRAGMA foreign_keys=OFF"))
        db.drop_all()
        self.contexto.pop()

    def _nova_os(self, **campos):
        dados = {
            "local": "Pátio XI",
            "equipe": "TMC AMV",
            "data_programada_inicial": date(2026, 10, 18),
            "data_programada_final": date(2026, 10, 19),
            "criado_por_usuario_id": self.usuario.id,
            "chave_idempotencia": str(uuid.uuid4()),
        }
        dados.update(campos)
        return OperacaoOrdemServico(**dados)

    def test_os_gera_identificadores_e_numero_cliente_eh_opcional(self):
        ordem = self._nova_os()
        db.session.add(ordem)
        db.session.commit()

        self.assertEqual(36, len(ordem.id_os_interno))
        self.assertTrue(ordem.codigo_os_rental.startswith("RR-OS-2026-"))
        self.assertIsNone(ordem.numero_os_cliente)
        self.assertEqual("Pendente", ordem.status_identificacao)

    def test_codigo_os_rental_eh_unico(self):
        db.session.add(self._nova_os(codigo_os_rental="RR-OS-2026-UNICA"))
        db.session.commit()
        db.session.add(self._nova_os(codigo_os_rental="RR-OS-2026-UNICA"))

        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_apontamento_exige_os_existente(self):
        apontamento = OperacaoApontamentoDiario(
            id_os_interno="0f0f0f0f-0000-4000-8000-000000000000",
            chave_idempotencia=str(uuid.uuid4()),
            data_evento=date(2026, 10, 18),
            equipe="TMC AMV",
            criado_por_usuario_id=self.usuario.id,
        )
        db.session.add(apontamento)

        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_diario_exige_apontamento_existente_e_os_nao_eh_excluida_com_historico(self):
        db.session.add(
            OperacaoDiarioLocalizacao(
                id_apontamento_diario="0f0f0f0f-0000-4000-8000-000000000000",
                encarregado="Responsável",
                chefe_boletim="Chefe",
                local="Pátio XI",
            )
        )
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        ordem = self._nova_os()
        db.session.add(ordem)
        db.session.flush()
        apontamento = OperacaoApontamentoDiario(
            id_os_interno=ordem.id_os_interno,
            chave_idempotencia=str(uuid.uuid4()),
            data_evento=date(2026, 10, 18),
            equipe="TMC AMV",
            criado_por_usuario_id=self.usuario.id,
        )
        db.session.add(apontamento)
        db.session.flush()
        db.session.add(
            OperacaoDiarioLocalizacao(
                id_apontamento_diario=apontamento.id_apontamento_diario,
                encarregado="Responsável",
                chefe_boletim="Chefe",
                local="Pátio XI",
            )
        )
        db.session.commit()

        db.session.delete(ordem)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()


if __name__ == "__main__":
    unittest.main()
