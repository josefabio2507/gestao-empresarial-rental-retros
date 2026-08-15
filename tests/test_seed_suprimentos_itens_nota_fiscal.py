import json
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import SuprimentosItem, SuprimentosUnidadeMedida
from app.seed_suprimentos_itens_nota_fiscal import executar_seed
import app.seed_suprimentos_itens_nota_fiscal as seed_itens


class SeedSuprimentosItensNotaFiscalTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            SECRET_KEY="test",
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            AUTO_MIGRATE_ON_START=False,
            AUTO_SEED_MODULES_ON_START=False,
            AUTO_SEED_SUPRIMENTOS_UNIDADES_ON_START=False,
            AUTO_SEED_SUPRIMENTOS_ITENS_ON_START=False,
            AUTO_SEED_OPERACAO_VEICULOS_ON_START=False,
        )
        self.contexto = self.app.app_context()
        self.contexto.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.contexto.pop()

    def _executar_seed_com_dados(self, dados):
        caminho_original = seed_itens.ARQUIVO_DADOS
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as arquivo:
            json.dump(dados, arquivo)
            caminho_temporario = Path(arquivo.name)

        try:
            seed_itens.ARQUIVO_DADOS = caminho_temporario
            executar_seed()
        finally:
            seed_itens.ARQUIVO_DADOS = caminho_original
            caminho_temporario.unlink(missing_ok=True)

    def test_seed_preserva_item_existente_editado_pelo_usuario(self):
        unidade_editada = SuprimentosUnidadeMedida(nome="PAR", sigla="PR", ativo=True)
        db.session.add(unidade_editada)
        db.session.flush()

        item = SuprimentosItem(
            codigo_interno="2002",
            descricao="DESCRICAO EDITADA PELO USUARIO",
            unidade_medida_id=unidade_editada.id,
            tipo="epi",
            item_estocavel=False,
            ncm="99999999",
            observacoes="EDICAO MANUAL",
            ativo=True,
        )
        db.session.add(item)
        db.session.commit()

        self._executar_seed_com_dados(
            [
                {
                    "codigo_interno": "2002",
                    "descricao": "DESCRICAO ORIGINAL DA PLANILHA",
                    "ncm": "12345678",
                    "unidade": "UN",
                }
            ]
        )

        item_atualizado = SuprimentosItem.query.filter_by(codigo_interno="2002").one()
        self.assertEqual("DESCRICAO EDITADA PELO USUARIO", item_atualizado.descricao)
        self.assertEqual(unidade_editada.id, item_atualizado.unidade_medida_id)
        self.assertEqual("epi", item_atualizado.tipo)
        self.assertFalse(item_atualizado.item_estocavel)
        self.assertEqual("99999999", item_atualizado.ncm)
        self.assertEqual("EDICAO MANUAL", item_atualizado.observacoes)

    def test_seed_cria_item_novo_como_nao_estocavel(self):
        self._executar_seed_com_dados(
            [
                {
                    "codigo_interno": "3001",
                    "descricao": "ITEM NOVO DA PLANILHA",
                    "ncm": "12345678",
                    "unidade": "UN",
                }
            ]
        )

        item = SuprimentosItem.query.filter_by(codigo_interno="3001").one()
        self.assertEqual("ITEM NOVO DA PLANILHA", item.descricao)
        self.assertEqual("material", item.tipo)
        self.assertFalse(item.item_estocavel)
        self.assertEqual("12345678", item.ncm)


if __name__ == "__main__":
    unittest.main()
