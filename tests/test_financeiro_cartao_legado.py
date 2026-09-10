import re
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from openpyxl import Workbook
from werkzeug.datastructures import FileStorage

from config import Config
from app import create_app
from app.extensions import db
from app.models import FinanceiroCartaoCredito, FinanceiroCartaoFatura, FinanceiroContaPagarTitulo, FinanceiroImportacaoCartao, NivelAcesso, Usuario
from app.services import financeiro_cartao_legado_service as svc
from app.services.financeiro_contas_pagar_service import recalcular_pagamento_titulo, salvar_titulo


def planilha(linhas, colunas=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Parcelas"
    sheet.append(colunas or svc.COLUNAS)
    for linha in linhas:
        sheet.append(linha)
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    stream.seek(0)
    return FileStorage(stream=stream, filename="legado.xlsx")


def linha(identificador=1, **campos):
    valores = [identificador, None, None, 903, "Fornecedor Teste", "Compra parcelada", "000123",
        date(2025, 10, 13), 1, 3, 260, None, date(2025, 11, 20), None, "Pago", None]
    for campo, valor in campos.items():
        valores[int(campo)] = valor
    return valores


class ImportacaoCartaoLegadoTest(unittest.TestCase):
    def setUp(self):
        config = {k: False for k in dir(Config) if k.startswith("AUTO_")}
        config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:", SECRET_KEY="test")
        self.config_patch = patch.multiple(Config, **config)
        self.config_patch.start()
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        nivel = NivelAcesso(nome="Administrador", slug="administrador", ativo=True)
        self.usuario = Usuario(nome="Teste", email="legado@test.local", nivel_acesso=nivel, ativo=True, precisa_trocar_senha=False)
        self.usuario.definir_senha("test")
        self.cartao = FinanceiroCartaoCredito(nome="Cartão histórico", banco="Banco Teste", ultimos_4_digitos="0903", dia_fechamento=10, dia_vencimento=20, ativo=True)
        db.session.add_all([self.usuario, self.cartao])
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as sessao:
            sessao["_user_id"] = str(self.usuario.id)
            sessao["_fresh"] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.config_patch.stop()

    def criar(self, linhas):
        return svc.criar_importacao(planilha(linhas), self.usuario)

    def liberar_proximo_lote(self, job):
        job.proximo_lote_em = datetime.utcnow() - timedelta(seconds=1)
        db.session.commit()

    def csrf(self):
        resposta = self.client.get("/financeiro/contas-a-pagar/cartoes/importar-legado")
        self.assertEqual(resposta.status_code, 200)
        return re.search(r'name="csrf_token" value="([^"]+)"', resposta.get_data(as_text=True))[1]

    def test_parcelas_faturas_pagamento_historico_e_reimportacao(self):
        job = self.criar([linha(), linha(2, **{"8": 2, "12": date(2025, 12, 20), "14": None}), linha(3, **{"8": 3, "12": date(2026, 1, 20)})])
        self.assertEqual(svc.resumo(job)["pagas"], 2)
        resultado = svc.processar_lote(job.id, self.usuario.id, 0)
        self.assertEqual(resultado["importados"], 3)
        titulos = FinanceiroContaPagarTitulo.query.order_by(FinanceiroContaPagarTitulo.id).all()
        self.assertEqual([t.competencia_fatura_cartao for t in titulos], [date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1)])
        self.assertTrue(all(t.data_compra_cartao == date(2025, 10, 13) for t in titulos))
        self.assertEqual(titulos[0].valor_pago_legado, Decimal("260"))
        self.assertEqual(titulos[0].numero_documento, "000123")
        self.assertIsNone(titulos[0].data_pagamento)
        self.assertIsNone(titulos[0].centro_custo_id)
        self.assertEqual(titulos[0].origem_lancamento, "Legado")
        self.assertEqual(titulos[1].valor_pago, 0)
        self.assertEqual(titulos[1].status, "Vencido")
        recalcular_pagamento_titulo(titulos[0])
        self.assertEqual(titulos[0].valor_pago, Decimal("260"))
        self.assertEqual(titulos[0].status, "Pago")
        self.assertEqual(titulos[0].baixas, [])
        faturas = FinanceiroCartaoFatura.query.order_by(FinanceiroCartaoFatura.competencia).all()
        self.assertEqual([f.status for f in faturas], ["Paga", "Aberta", "Paga"])
        segundo = self.criar([linha(), linha(2, **{"8": 2, "12": date(2025, 12, 20), "14": None})])
        self.assertEqual(svc.resumo(segundo)["duplicadas"], 2)
        self.assertEqual(svc.processar_lote(segundo.id, self.usuario.id, 0)["ignorados"], 2)
        self.assertEqual(FinanceiroContaPagarTitulo.query.count(), 3)

    def test_ignora_descontos_e_preserva_vencimentos_diferentes(self):
        job = self.criar([linha(), linha(2, **{"12": date(2025, 11, 5)}), linha(3, **{"10": -1.31})])
        self.assertEqual(svc.resumo(job)["pendencias"], 1)
        resultado = svc.processar_lote(job.id, self.usuario.id, 0)
        self.assertEqual(resultado["importados"], 2)
        self.assertEqual(resultado["pendentes"], 1)
        self.assertEqual(FinanceiroCartaoFatura.query.count(), 1)
        self.assertEqual(FinanceiroCartaoFatura.query.one().data_vencimento, date(2025, 11, 20))
        self.assertEqual({t.data_vencimento.day for t in FinanceiroContaPagarTitulo.query.all()}, {5, 20})

    def test_lotes_pausa_repeticao_e_retomada(self):
        job = self.criar([linha(i) for i in range(201)])
        primeiro = svc.processar_lote(job.id, self.usuario.id, 0)
        self.assertEqual(primeiro["importados"], 100)
        self.assertGreaterEqual(job.proximo_lote_em, datetime.utcnow() + timedelta(seconds=9))
        repetido = svc.processar_lote(job.id, self.usuario.id, 0)
        self.assertEqual(repetido["processados"], 100)
        pausado = svc.processar_lote(job.id, self.usuario.id, 100)
        self.assertEqual(pausado["processados"], 100)
        self.liberar_proximo_lote(job)
        self.assertEqual(svc.processar_lote(job.id, self.usuario.id, 100)["importados"], 200)
        self.liberar_proximo_lote(job)
        ultimo = svc.processar_lote(job.id, self.usuario.id, 200)
        self.assertTrue(ultimo["concluido"])
        self.assertEqual(ultimo["importados"], 201)

    def test_lote_falha_reverte_apenas_transacao_atual(self):
        job = self.criar([linha(), linha(2)])
        importar = svc._importar_linha
        def falhar(registro, usuario, cache=None):
            if registro["id_legado"] == "2":
                raise RuntimeError("falha simulada")
            return importar(registro, usuario, cache)
        with patch.object(svc, "_importar_linha", side_effect=falhar):
            with self.assertRaises(RuntimeError):
                svc.processar_lote(job.id, self.usuario.id, 0)
        db.session.rollback()
        self.assertEqual(FinanceiroContaPagarTitulo.query.count(), 0)
        self.assertEqual(job.cursor, 0)
        self.assertEqual(svc.processar_lote(job.id, self.usuario.id, 0)["importados"], 2)

    def test_cartao_ambiguo_exige_vinculo(self):
        outro = FinanceiroCartaoCredito(nome="Outro", banco="Outro", ultimos_4_digitos="0903", dia_fechamento=10, dia_vencimento=20, ativo=False)
        db.session.add(outro)
        db.session.commit()
        job = self.criar([linha()])
        self.assertEqual(svc.resumo(job)["aptas"], 0)
        self.assertEqual(svc.resumo(job)["pendencias"], 1)
        svc.atualizar_mapeamento(job, {"cartao_0903": str(outro.id)})
        svc.processar_lote(job.id, self.usuario.id, 0)
        self.assertEqual(FinanceiroContaPagarTitulo.query.one().cartao_credito_id, outro.id)

    def test_cartao_nao_vinculado_nao_bloqueia_linhas_aptas(self):
        job = self.criar([linha(), linha(2, **{"3": 8887})])
        self.assertEqual(svc.resumo(job)["aptas"], 1)
        resultado = svc.processar_lote(job.id, self.usuario.id, 0)
        self.assertEqual(resultado["importados"], 1)
        self.assertEqual(resultado["pendentes"], 1)
        self.assertTrue(resultado["concluido"])
        self.assertEqual(FinanceiroContaPagarTitulo.query.one().id_legado, "1")

        job_tela = self.criar([linha(3), linha(4, **{"3": 8887})])
        resposta = self.client.get(f"/financeiro/contas-a-pagar/cartoes/importar-legado/{job_tela.id}")
        html = resposta.get_data(as_text=True)
        self.assertIn("As linhas dos cartões ainda não vinculados ficarão nas pendências", html)
        self.assertNotRegex(html, r'id="confirmar"[^>]*disabled')

    def test_fatura_cancelada_nao_recebe_compra(self):
        db.session.add(FinanceiroCartaoFatura(cartao_credito_id=self.cartao.id, competencia=date(2025, 11, 1), data_fechamento=date(2025, 11, 10), data_vencimento=date(2025, 11, 20), status="Cancelada"))
        db.session.commit()
        job = self.criar([linha()])
        self.assertEqual(svc.processar_lote(job.id, self.usuario.id, 0)["pendentes"], 1)
        self.assertEqual(FinanceiroContaPagarTitulo.query.count(), 0)

    def test_confirmacao_sem_reenviar_arquivo_csrf_e_dono(self):
        token = self.csrf()
        arquivo = planilha([linha()])
        resposta = self.client.post("/financeiro/contas-a-pagar/cartoes/importar-legado", data={"csrf_token": token, "arquivo": (arquivo.stream, "legado.xlsx")})
        self.assertEqual(resposta.status_code, 302)
        previa = self.client.get(resposta.location)
        self.assertNotIn('type="file"', previa.get_data(as_text=True))
        self.assertIn("Confirmar importação", previa.get_data(as_text=True))
        lote_url = resposta.location + "/lote"
        self.assertEqual(self.client.post(lote_url, json={"cursor": 0}).status_code, 400)
        confirmado = self.client.post(lote_url, json={"cursor": 0}, headers={"X-CSRFToken": token})
        self.assertEqual(confirmado.status_code, 200)
        self.assertEqual(confirmado.json["importados"], 1)
        job = FinanceiroImportacaoCartao.query.one()
        job.usuario_id = self.usuario.id + 999
        db.session.commit()
        self.assertEqual(self.client.get(resposta.location).status_code, 404)
        self.assertEqual(self.client.get(resposta.location + "/pendencias").status_code, 404)
        self.assertEqual(self.client.post(lote_url, json={"cursor": 0}, headers={"X-CSRFToken": token}).status_code, 404)

    def test_editar_descricao_mantem_fatura_e_pagamento(self):
        job = self.criar([linha()])
        svc.processar_lote(job.id, self.usuario.id, 0)
        titulo = FinanceiroContaPagarTitulo.query.one()
        fatura_id = titulo.fatura_cartao_id
        dados = {"fornecedor_nome_snapshot": "Fornecedor", "descricao": "Descrição corrigida", "valor_original": "260,00", "origem_lancamento": "Legado", "tipo_pagamento": "Cartao de Credito", "forma_pagamento": "Cartao de Credito", "status": "A vencer", "parcela_numero": "1", "total_parcelas": "3", "data_vencimento": "2025-11-20", "data_compra_cartao": "2025-10-13", "cartao_credito_id": str(self.cartao.id)}
        sucesso, mensagem, titulo = salvar_titulo(dados, titulo, self.usuario)
        self.assertTrue(sucesso, mensagem)
        self.assertEqual(titulo.fatura_cartao_id, fatura_id)
        self.assertEqual(titulo.status, "Pago")
        self.assertEqual(titulo.valor_pago, 260)

    def test_formula_datas_status_e_ids_invalidos(self):
        job = self.criar([linha(), linha(), linha(3, **{"7": "errada"}), linha(4, **{"14": "Talvez"}), linha(5, **{"10": "=1+1"})])
        self.assertEqual(svc.resumo(job)["aptas"], 1)
        self.assertEqual(svc.resumo(job)["pendencias"], 4)

    def test_datas_numericas_excel_e_colunas_opcionais_ausentes(self):
        from openpyxl.utils.datetime import to_excel
        valores = linha(**{"7": to_excel(datetime(2025, 10, 13)), "12": to_excel(datetime(2025, 11, 20))})
        manter = [0, 3, 4, 5, 7, 8, 9, 10, 12]
        lidas = svc.ler_planilha(planilha([[valores[i] for i in manter]], [svc.COLUNAS[i] for i in manter]))
        self.assertEqual(lidas[0]["erros_base"], [])
        self.assertEqual(lidas[0]["compra"], "2025-10-13")
        self.assertEqual(lidas[0]["vencimento"], "2025-11-20")
        self.assertFalse(lidas[0]["pago"])


if __name__ == "__main__":
    unittest.main()
