import unittest
from io import BytesIO

from PIL import Image
from werkzeug.datastructures import FileStorage, MultiDict

from app import create_app
from app.extensions import db
from app.models import (
    Colaborador,
    Departamento,
    Equipe,
    Modulo,
    NivelAcesso,
    OperacaoAbastecimento,
    OperacaoAbastecimentoCustoExtra,
    OperacaoImpostoTaxa,
    OperacaoLeituraAtivo,
    OperacaoMultaTransito,
    OperacaoVeiculoEquipamento,
    OperacaoVeiculoResponsavel,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.services.operacao_abastecimento_service import TIPOS_COMBUSTIVEL, cancelar_custo_extra_abastecimento, salvar_abastecimento
from app.services.operacao_impostos_taxas_service import salvar_impostos_taxas
from app.services.operacao_multas_transito_service import salvar_multa_transito
from app.services.operacao_pool_service import (
    STATUS_DISPONIVEL,
    STATUS_EM_USO,
    STATUS_INDISPONIVEL,
    STATUS_VINCULO_ATIVO,
    STATUS_VINCULO_ENCERRADO,
    STATUS_VINCULO_RETIFICADO,
    alterar_indisponibilidade_veiculo,
    buscar_veiculos_pool,
    corrigir_vinculo,
    encerrar_vinculo,
    registrar_leitura,
    salvar_veiculo_equipamento,
    veiculos_vinculados_ao_colaborador,
    vincular_responsavel,
)



class FakeDriveCreateRequest:
    def __init__(self, resposta):
        self.resposta = resposta

    def execute(self):
        return self.resposta


class FakeDriveFiles:
    def __init__(self):
        self.uploads = []

    def create(self, body, media_body, fields, supportsAllDrives):
        self.uploads.append(
            {
                "body": body,
                "media_body": media_body,
                "fields": fields,
                "supportsAllDrives": supportsAllDrives,
            }
        )
        indice = len(self.uploads)
        return FakeDriveCreateRequest(
            {
                "id": f"drive-cupom-{indice}",
                "name": body["name"],
                "webViewLink": f"https://drive.google.com/cupom/{indice}",
            }
        )


class FakeDriveService:
    def __init__(self):
        self._files = FakeDriveFiles()

    def files(self):
        return self._files

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
        self.modulos = {}
        for ordem, (nome, slug) in enumerate(
            [
                ("Veiculos e Equipamentos", "veiculos_equipamentos"),
                ("Pool de Veiculos", "pool_veiculos"),
                ("Abastecimento", "abastecimento"),
                ("Multas de Transito", "multas_transito"),
                ("Impostos e Taxas", "impostos_taxas"),
                ("Central de Custos", "central_custos"),
            ],
            start=1,
        ):
            modulo = Modulo(
                departamento_id=self.departamento.id,
                nome=nome,
                slug=slug,
                ativo=True,
                ordem=ordem,
            )
            self.modulos[slug] = modulo
            db.session.add(modulo)
        self.modulo = self.modulos["pool_veiculos"]

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

    def _criar_veiculo(self, identificacao="ABC1D23", descricao="FIAT MOBI", tipo="Veiculo leve"):
        sucesso, _, veiculo = salvar_veiculo_equipamento(
            {
                "identificacao": identificacao,
                "placa": identificacao,
                "descricao": descricao,
                "situacao_aquisicao": "Quitado",
                "tipo": tipo,
            }
        )
        self.assertTrue(sucesso)
        return veiculo

    def _autenticar(self, usuario):
        with self.client.session_transaction() as sessao:
            sessao.clear()
            sessao["_user_id"] = str(usuario.id)
            sessao["_fresh"] = True


    def _arquivo_imagem(self, nome="cupom.png", tamanho=(800, 600), cor=(30, 90, 150)):
        buffer = BytesIO()
        imagem = Image.new("RGB", tamanho, cor)
        imagem.save(buffer, format="PNG")
        buffer.seek(0)
        return FileStorage(stream=buffer, filename=nome, content_type="image/png")
    def _liberar_usuario(self, modulo_slug="pool_veiculos", **acoes):
        modulo = self.modulos[modulo_slug]
        permissao = PermissaoUsuarioModulo.query.filter_by(usuario_id=self.usuario.id, modulo_id=modulo.id).first()
        if not permissao:
            permissao = PermissaoUsuarioModulo(
                usuario_id=self.usuario.id,
                modulo_id=modulo.id,
            )
            db.session.add(permissao)
        permissao.pode_visualizar = acoes.get("visualizar", False)
        permissao.pode_criar = acoes.get("criar", False)
        permissao.pode_editar = acoes.get("editar", False)
        permissao.pode_excluir = acoes.get("excluir", False)
        permissao.ativo = True
        permissao.garantir_visualizacao()
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

    def test_encerrar_vinculo_deixa_veiculo_disponivel_para_novo_usuario(self):
        veiculo = self._criar_veiculo("POOL001", "CAMINHAO POOL")
        _, _, primeiro = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        veiculo.status_operacional = STATUS_INDISPONIVEL
        veiculo.motivo_indisponibilidade = "Sinistro"
        db.session.commit()

        sucesso_encerrar, mensagem_encerrar = encerrar_vinculo(primeiro, usuario=self.admin)
        self.assertTrue(sucesso_encerrar, mensagem_encerrar)
        self.assertEqual(STATUS_DISPONIVEL, veiculo.status_operacional)
        self.assertIsNone(veiculo.motivo_indisponibilidade)

        sucesso, mensagem, segundo = vincular_responsavel(
            {"colaborador_id": str(self.operador.id), "tipo_leitura": "odometro", "leitura_inicial": "20"},
            usuario=self.admin,
            veiculo=veiculo,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(STATUS_VINCULO_ATIVO, segundo.status)
        self.assertEqual(STATUS_EM_USO, veiculo.status_operacional)

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

        self.assertTrue(vincular_responsavel({"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"}, usuario=self.admin, veiculo=veiculo_um)[0])
        self.assertTrue(vincular_responsavel({"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "20"}, usuario=self.admin, veiculo=veiculo_dois)[0])

        vinculados = veiculos_vinculados_ao_colaborador(self.motorista.id)
        self.assertEqual({veiculo_um.id, veiculo_dois.id}, {veiculo.id for veiculo in vinculados})

    def test_correcao_auditavel_nao_apaga_original_e_cria_novo(self):
        veiculo = self._criar_veiculo()
        _, _, vinculo = vincular_responsavel({"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"}, usuario=self.admin, veiculo=veiculo)

        sucesso, mensagem, novo = corrigir_vinculo(
            vinculo,
            {
                "motivo_correcao": "Lancamento no operador incorreto",
                "status_correcao": STATUS_VINCULO_RETIFICADO,
                "criar_novo_vinculo": "1",
                "colaborador_id": str(self.operador.id),
                "tipo_leitura": "odometro",
                "leitura_inicial": "30",
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

        vincular_responsavel({"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"}, usuario=self.admin, veiculo=veiculo)
        self.assertEqual(STATUS_EM_USO, veiculo.status_operacional)

        sucesso, mensagem = alterar_indisponibilidade_veiculo(veiculo, indisponivel=True, motivo="Manutencao")
        self.assertFalse(sucesso)
        self.assertEqual("Veiculo/equipamento com responsavel ativo deve permanecer Em uso.", mensagem)
        self.assertEqual(STATUS_EM_USO, veiculo.status_operacional)

    def test_indisponivel_somente_por_manutencao_ou_sinistro_sem_vinculo_ativo(self):
        veiculo = self._criar_veiculo()

        sucesso, mensagem = alterar_indisponibilidade_veiculo(veiculo, indisponivel=True, motivo="Oficina")
        self.assertFalse(sucesso)
        self.assertEqual("Indisponibilidade permitida apenas por manutencao ou sinistro.", mensagem)
        self.assertEqual(STATUS_DISPONIVEL, veiculo.status_operacional)

        sucesso, _ = alterar_indisponibilidade_veiculo(veiculo, indisponivel=True, motivo="Sinistro")
        self.assertTrue(sucesso)
        self.assertEqual(STATUS_INDISPONIVEL, veiculo.status_operacional)
        self.assertEqual("Sinistro", veiculo.motivo_indisponibilidade)

    def test_listagem_recalcula_status_indisponivel_sem_motivo_valido(self):
        veiculo = self._criar_veiculo("QXN5F52", "FIAT MOBI LIKE")
        veiculo.status_operacional = STATUS_INDISPONIVEL
        veiculo.motivo_indisponibilidade = "Indisponivel operacionalmente."
        db.session.commit()

        veiculos = buscar_veiculos_pool()
        db.session.refresh(veiculo)

        self.assertIn(veiculo, veiculos)
        self.assertEqual(STATUS_DISPONIVEL, veiculo.status_operacional)
        self.assertIsNone(veiculo.motivo_indisponibilidade)

    def test_historico_oculta_corrigir_para_usuario_comum(self):
        veiculo = self._criar_veiculo()
        _, _, vinculo = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        encerrar_vinculo(vinculo, usuario=self.admin)

        self._autenticar(self.usuario)
        self._liberar_usuario(visualizar=True)
        resposta_usuario = self.client.get(f"/operacao/pool-veiculos/ativos/{veiculo.id}/historico")
        self.assertEqual(200, resposta_usuario.status_code)
        self.assertNotIn(b"Corrigir", resposta_usuario.data)

    def test_historico_mostra_corrigir_para_admin(self):
        veiculo = self._criar_veiculo()
        _, _, vinculo = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        encerrar_vinculo(vinculo, usuario=self.admin)

        self._autenticar(self.admin)
        resposta_admin = self.client.get(f"/operacao/pool-veiculos/ativos/{veiculo.id}/historico")
        self.assertEqual(200, resposta_admin.status_code)
        self.assertIn(b"Corrigir", resposta_admin.data)

    def test_corrigir_vinculo_restrito_a_admin_para_usuario_comum(self):
        veiculo = self._criar_veiculo()
        _, _, vinculo = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        encerrar_vinculo(vinculo, usuario=self.admin)

        self._autenticar(self.usuario)
        self._liberar_usuario(excluir=True)
        resposta_usuario = self.client.get(f"/operacao/pool-veiculos/vinculos/{vinculo.id}/corrigir")
        self.assertEqual(302, resposta_usuario.status_code)
        self.assertIn("/acesso-negado", resposta_usuario.headers["Location"])

    def test_corrigir_vinculo_admin_usa_motorista_do_vinculo(self):
        veiculo = self._criar_veiculo()
        _, _, vinculo = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        encerrar_vinculo(vinculo, usuario=self.admin)

        self._autenticar(self.admin)
        resposta_admin = self.client.get(f"/operacao/pool-veiculos/vinculos/{vinculo.id}/corrigir")
        self.assertEqual(200, resposta_admin.status_code)
        self.assertIn(b"Motorista Um", resposta_admin.data)
        self.assertNotIn(b"Operador Dois", resposta_admin.data)
        self.assertNotIn(b"<select id=\"colaborador_id\"", resposta_admin.data)

    def test_permissao_visualizar_rota_pool(self):
        self._autenticar(self.usuario)
        resposta = self.client.get("/operacao/pool-veiculos")
        self.assertEqual(302, resposta.status_code)
        self.assertIn("/acesso-negado", resposta.headers["Location"])

        self._criar_veiculo()
        self._liberar_usuario(visualizar=True)
        resposta = self.client.get("/operacao/pool-veiculos")
        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Pool de Veiculos", resposta.data)
        self.assertIn(b"href=\"/operacao/gestao-veiculos-epgs/\"", resposta.data)
        self.assertIn(b"Vincular", resposta.data)
        self.assertNotIn(b"Editar", resposta.data)
        self.assertNotIn(b"/editar", resposta.data)

    def test_rota_vincular_usa_colaborador_logado_e_leitura_final_anterior(self):
        veiculo = self._criar_veiculo()
        _, _, primeiro = vincular_responsavel(
            {
                "colaborador_id": str(self.motorista.id),
                "tipo_leitura": "odometro",
                "leitura_inicial": "50",
            },
            usuario=self.admin,
            veiculo=veiculo,
        )
        self.usuario.colaborador_id = self.operador.id
        db.session.commit()
        self._liberar_usuario(editar=True)
        self._autenticar(self.usuario)

        resposta_get = self.client.get(f"/operacao/pool-veiculos/ativos/{veiculo.id}/vincular")
        self.assertEqual(200, resposta_get.status_code)
        self.assertIn(b"Operador Dois", resposta_get.data)
        self.assertIn(b"Operacao", resposta_get.data)
        self.assertIn(b"50,00", resposta_get.data)
        self.assertIn(b"value=\"odometro\"", resposta_get.data)
        self.assertNotIn(b"<select id=\"tipo_leitura\"", resposta_get.data)

        resposta_post = self.client.post(
            f"/operacao/pool-veiculos/ativos/{veiculo.id}/vincular",
            data={"tipo_leitura": "odometro", "leitura_inicial": "80"},
            follow_redirects=False,
        )
        self.assertEqual(302, resposta_post.status_code)
        db.session.refresh(primeiro)
        novo = OperacaoVeiculoResponsavel.query.order_by(OperacaoVeiculoResponsavel.id.desc()).first()
        self.assertEqual("50.00", str(primeiro.leitura_final))
        self.assertEqual(self.operador.id, novo.colaborador_id)
        self.assertEqual(self.equipe.id, novo.equipe_id)

    def test_rota_vincular_maquina_usa_horimetro_automatico(self):
        veiculo = self._criar_veiculo("MAQ001", "ESCAVADEIRA", tipo="Maquina")
        self.usuario.colaborador_id = self.operador.id
        db.session.commit()
        self._liberar_usuario(editar=True)
        self._autenticar(self.usuario)

        resposta_get = self.client.get(f"/operacao/pool-veiculos/ativos/{veiculo.id}/vincular")
        self.assertEqual(200, resposta_get.status_code)
        self.assertIn(b"value=\"horimetro\"", resposta_get.data)
        self.assertNotIn(b"<select id=\"tipo_leitura\"", resposta_get.data)

        resposta_post = self.client.post(
            f"/operacao/pool-veiculos/ativos/{veiculo.id}/vincular",
            data={"tipo_leitura": "odometro", "leitura_inicial": "80"},
            follow_redirects=False,
        )
        self.assertEqual(302, resposta_post.status_code)
        vinculo = OperacaoVeiculoResponsavel.query.order_by(OperacaoVeiculoResponsavel.id.desc()).first()
        self.assertEqual("horimetro", vinculo.tipo_leitura)


    def test_salva_abastecimento_com_cupom_no_drive(self):
        veiculo = self._criar_veiculo("RET001", "RETROESCAVADEIRA")
        self.usuario.colaborador_id = self.motorista.id
        db.session.commit()
        _, _, vinculo = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "horimetro", "leitura_inicial": "100"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        self.app.config["GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID"] = "pasta-cupons"
        drive = FakeDriveService()

        sucesso, mensagem, abastecimento = salvar_abastecimento(
            {
                "data_abastecimento": "2026-08-23",
                "tipo_combustivel": "Diesel S10",
                "qtd_litros": "12,50",
                "preco": "345,67",
                "observacoes": "cupom fiscal fotografado",
            },
            {"cupom_fiscal": self._arquivo_imagem()},
            self.usuario,
            veiculo=veiculo,
            drive_service=drive,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual("Abastecimento salvo com sucesso.", mensagem)
        self.assertEqual(veiculo.id, abastecimento.veiculo_id)
        self.assertEqual(vinculo.id, abastecimento.vinculo_id)
        self.assertEqual(self.motorista.id, abastecimento.colaborador_id)
        self.assertEqual(self.equipe.id, abastecimento.equipe_id)
        self.assertEqual("12.500", str(abastecimento.qtd_litros))
        self.assertEqual("345.67", str(abastecimento.preco))
        self.assertEqual("drive-cupom-1", abastecimento.cupom_drive_file_id)
        self.assertEqual("pasta-cupons", drive.files().uploads[0]["body"]["parents"][0])
        self.assertTrue(abastecimento.cupom_nome_arquivo.startswith("ABAST-RET001-20260823-"))
        self.assertEqual(1, OperacaoAbastecimento.query.count())

    def test_salva_abastecimento_com_custos_extras_e_conferencia_nf(self):
        veiculo = self._criar_veiculo("RET777", "RETRO COM EXTRAS")
        self.usuario.colaborador_id = self.motorista.id
        db.session.commit()
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "horimetro", "leitura_inicial": "100"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        self.app.config["GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID"] = "pasta-cupons"

        form = MultiDict(
            [
                ("data_abastecimento", "2026-08-29"),
                ("tipo_combustivel", "Diesel S10"),
                ("qtd_litros", "20,00"),
                ("preco", "15,00"),
                ("numero_nota_fiscal", "NF-123"),
                ("chave_acesso_nfe", "12345678901234567890123456789012345678901234"),
                ("valor_total_nota_fiscal", "362,50"),
                ("observacoes_conferencia", "Conferencia com itens extras"),
                ("custo_extra_categoria", "Arla"),
                ("custo_extra_descricao", "Arla 32"),
                ("custo_extra_quantidade", "2"),
                ("custo_extra_valor_unitario", "25,00"),
                ("custo_extra_observacoes", "Galões"),
                ("custo_extra_id", ""),
                ("custo_extra_categoria", "Lavagem"),
                ("custo_extra_descricao", "Lavagem simples"),
                ("custo_extra_quantidade", "1"),
                ("custo_extra_valor_unitario", "12,50"),
                ("custo_extra_observacoes", ""),
                ("custo_extra_id", ""),
            ]
        )

        sucesso, mensagem, abastecimento = salvar_abastecimento(
            form,
            {"cupom_fiscal": self._arquivo_imagem()},
            self.usuario,
            veiculo=veiculo,
            drive_service=FakeDriveService(),
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(2, OperacaoAbastecimentoCustoExtra.query.filter_by(abastecimento_id=abastecimento.id).count())
        self.assertEqual("300.00", str(abastecimento.valor_total_combustivel))
        self.assertEqual("62.50", str(abastecimento.valor_total_custos_extras))
        self.assertEqual("362.50", str(abastecimento.valor_total_geral))
        self.assertEqual("0.00", str(abastecimento.diferenca_nota_fiscal))
        self.assertEqual("Conferido", abastecimento.status_conferencia_nota_fiscal)

        custo_arla = OperacaoAbastecimentoCustoExtra.query.filter_by(descricao="Arla 32").first()
        sucesso, mensagem, _ = cancelar_custo_extra_abastecimento(custo_arla.id, self.usuario, "Lancado em duplicidade")

        self.assertTrue(sucesso, mensagem)
        db.session.refresh(abastecimento)
        self.assertEqual("Cancelado", custo_arla.status)
        self.assertEqual("12.50", str(abastecimento.valor_total_custos_extras))
        self.assertEqual("Divergente", abastecimento.status_conferencia_nota_fiscal)

    def test_rota_abastecimentos_lista_apenas_veiculos_vinculados_ao_usuario(self):
        veiculo_vinculado = self._criar_veiculo("CAR101", "CAMINHAO DO USUARIO")
        veiculo_outro = self._criar_veiculo("CAR202", "CAMINHAO DE OUTRO MOTORISTA")
        self.usuario.colaborador_id = self.motorista.id
        db.session.commit()
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo_vinculado,
        )
        vincular_responsavel(
            {"colaborador_id": str(self.operador.id), "tipo_leitura": "odometro", "leitura_inicial": "20"},
            usuario=self.admin,
            veiculo=veiculo_outro,
        )
        self._liberar_usuario("abastecimento", visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/operacao/abastecimentos")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"CAR101", resposta.data)
        self.assertNotIn(b"CAR202", resposta.data)

    def test_admin_visualiza_todos_veiculos_em_abastecimento_sem_vinculo(self):
        veiculo_um = self._criar_veiculo("ADM101", "CAMINHAO ADMIN UM")
        veiculo_dois = self._criar_veiculo("ADM202", "CAMINHAO ADMIN DOIS")
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo_um,
        )
        self._autenticar(self.admin)

        resposta = self.client.get("/operacao/abastecimentos")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(veiculo_um.identificacao.encode(), resposta.data)
        self.assertIn(veiculo_dois.identificacao.encode(), resposta.data)
        self.assertNotIn(b">Abastecer</a>", resposta.data)

    def test_formulario_abastecimento_usa_camera_do_celular_para_cupom(self):
        veiculo = self._criar_veiculo("CAR303", "CAMINHAO ABASTECIMENTO")
        self.usuario.colaborador_id = self.motorista.id
        db.session.commit()
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        self._liberar_usuario("abastecimento", criar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get(f"/operacao/abastecimentos/veiculos/{veiculo.id}/novo")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b'accept="image/*"', resposta.data)
        self.assertIn(b'capture="environment"', resposta.data)
        self.assertIn(b'value="Diesel S10"', resposta.data)
        self.assertIn(b'value="Etanol aditivado"', resposta.data)
        self.assertIn(b'value="Gasolina Premium"', resposta.data)
        self.assertNotIn(b'value="Diesel"', resposta.data)
        self.assertNotIn(b'value="Gasolina"', resposta.data)
        self.assertNotIn(b'value="Arla 32"', resposta.data)
        self.assertIn(b"Motorista Um", resposta.data)
        self.assertIn(b"Operacao", resposta.data)

    def test_bloqueia_combustivel_fora_da_lista(self):
        veiculo = self._criar_veiculo("CAR404", "CAMINHAO COMBUSTIVEL")
        self.usuario.colaborador_id = self.motorista.id
        db.session.commit()
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )

        sucesso, mensagem, abastecimento = salvar_abastecimento(
            {
                "data_abastecimento": "2026-08-23",
                "tipo_combustivel": "Diesel",
                "qtd_litros": "10,00",
                "preco": "50,00",
            },
            {},
            self.usuario,
            veiculo=veiculo,
        )

        self.assertFalse(sucesso)
        self.assertEqual("Tipo de combustivel invalido.", mensagem)
        self.assertIsNone(abastecimento)
        self.assertNotIn("Diesel", TIPOS_COMBUSTIVEL)

    def test_central_custos_filtra_ativos_por_padrao(self):
        veiculo_ativo = self._criar_veiculo("CAR501", "CAMINHAO ATIVO")
        veiculo_inativo = self._criar_veiculo("CAR502", "CAMINHAO INATIVO")
        veiculo_inativo.ativo = False
        db.session.commit()
        self._liberar_usuario("central_custos", visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get("/operacao/central-custos")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Central de Custos", resposta.data)
        self.assertIn(veiculo_ativo.identificacao.encode(), resposta.data)
        self.assertNotIn(veiculo_inativo.identificacao.encode(), resposta.data)

    def test_central_custos_veiculo_totaliza_abastecimento_e_exibe_detalhe(self):
        veiculo = self._criar_veiculo("CAR503", "CAMINHAO CENTRAL")
        self.usuario.colaborador_id = self.motorista.id
        db.session.commit()
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        self.app.config["GOOGLE_DRIVE_CUPONS_ABASTECIMENTO_FOLDER_ID"] = "pasta-cupons"
        sucesso, mensagem, abastecimento = salvar_abastecimento(
            {
                "data_abastecimento": "2026-08-23",
                "tipo_combustivel": "Gasolina comum",
                "qtd_litros": "20,00",
                "preco": "123,45",
            },
            {"cupom_fiscal": self._arquivo_imagem()},
            self.usuario,
            veiculo=veiculo,
            drive_service=FakeDriveService(),
        )
        self.assertTrue(sucesso, mensagem)
        self._liberar_usuario("central_custos", visualizar=True)
        self._liberar_usuario("abastecimento", visualizar=True)
        self._autenticar(self.usuario)

        resposta = self.client.get(f"/operacao/central-custos/veiculos/{veiculo.id}")

        self.assertEqual(200, resposta.status_code)
        self.assertIn(b"Abastecimento", resposta.data)
        self.assertIn(b"Manuten", resposta.data)
        self.assertIn(b"Multas", resposta.data)
        self.assertIn(b"Impostos e Taxas", resposta.data)
        self.assertIn(b"Gasolina comum", resposta.data)
        self.assertIn(b"R$ 2.469,00", resposta.data)
        self.assertIn(b"Ver", resposta.data)

        detalhe = self.client.get(f"/operacao/abastecimentos/{abastecimento.id}/ver")
        self.assertEqual(200, detalhe.status_code)
        self.assertIn(b"Detalhes do abastecimento", detalhe.data)
        self.assertIn(b"Ver cupom fiscal", detalhe.data)
        self.assertIn(b"https://drive.google.com/cupom/1", detalhe.data)

    def test_salva_multa_transito_com_motorista_vinculado_e_custo_total(self):
        veiculo = self._criar_veiculo("MLT001", "CAMINHAO MULTA")
        sucesso, mensagem, _ = vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        self.assertTrue(sucesso, mensagem)

        sucesso, mensagem, multa = salvar_multa_transito(
            {
                "data_infracao": "2026-08-26",
                "hora_infracao": "14:30",
                "veiculo_id": str(veiculo.id),
                "numero_auto_infracao": "AUTO-001",
                "local_infracao": "Av. Principal, 100",
                "cidade": "SANTOS",
                "descricao_infracao": "Excesso de velocidade",
                "valor_multa": "195,23",
                "data_vencimento": "2026-09-10",
                "motorista_indicado_nome": "Condutor Informado",
                "gravidade": "Grave",
                "pontuacao": "5",
                "data_vencimento_segunda_cobranca": "2026-10-10",
                "valor_segunda_cobranca": "390,46",
            },
            self.admin,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(self.motorista.id, multa.motorista_vinculado_id)
        self.assertIsNone(multa.motorista_indicado_id)
        self.assertEqual("Condutor Informado", multa.motorista_indicado_nome)
        self.assertEqual("585.69", str(multa.custo_total))
        self.assertEqual(1, OperacaoMultaTransito.query.count())

    def test_rota_multas_transito_e_central_de_custos_exibem_multa(self):
        veiculo = self._criar_veiculo("MLT002", "CAMINHAO CENTRAL MULTA")
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo,
        )
        sucesso, mensagem, multa = salvar_multa_transito(
            {
                "data_infracao": "2026-08-26",
                "hora_infracao": "08:15",
                "veiculo_id": str(veiculo.id),
                "numero_auto_infracao": "AUTO-002",
                "local_infracao": "Rodovia Anchieta",
                "cidade": "CUBATAO",
                "descricao_infracao": "Transitar em faixa exclusiva",
                "valor_multa": "100,00",
                "data_vencimento": "2026-09-01",
                "gravidade": "Media",
                "pontuacao": "4",
            },
            self.admin,
        )
        self.assertTrue(sucesso, mensagem)
        self._liberar_usuario("multas_transito", visualizar=True, criar=True)
        self._liberar_usuario("central_custos", visualizar=True)
        self._autenticar(self.usuario)

        lista = self.client.get("/operacao/multas-transito")
        self.assertEqual(200, lista.status_code)
        self.assertIn(b"Multas de Tr", lista.data)
        self.assertIn(b"AUTO-002", lista.data)

        detalhe = self.client.get(f"/operacao/multas-transito/{multa.id}/ver")
        self.assertEqual(200, detalhe.status_code)
        self.assertIn(b"Detalhes da multa", detalhe.data)
        self.assertIn(b"AUTO-002", detalhe.data)

        central = self.client.get(f"/operacao/central-custos/veiculos/{veiculo.id}")
        self.assertEqual(200, central.status_code)
        self.assertIn(b"Transitar em faixa exclusiva", central.data)
        self.assertIn(b"R$ 100,00", central.data)
        self.assertIn(b"Ver", central.data)

    def test_filtros_multas_transito_por_periodo_placa_e_motorista(self):
        veiculo_motorista = self._criar_veiculo("FLT001", "CAMINHAO FILTRO UM")
        veiculo_operador = self._criar_veiculo("FLT999", "CAMINHAO FILTRO DOIS")
        vincular_responsavel(
            {"colaborador_id": str(self.motorista.id), "tipo_leitura": "odometro", "leitura_inicial": "10"},
            usuario=self.admin,
            veiculo=veiculo_motorista,
        )
        vincular_responsavel(
            {"colaborador_id": str(self.operador.id), "tipo_leitura": "odometro", "leitura_inicial": "20"},
            usuario=self.admin,
            veiculo=veiculo_operador,
        )
        salvar_multa_transito(
            {
                "data_infracao": "2026-08-25",
                "hora_infracao": "08:15",
                "veiculo_id": str(veiculo_motorista.id),
                "numero_auto_infracao": "AUTO-FLT-001",
                "local_infracao": "Av. Teste",
                "cidade": "SANTOS",
                "descricao_infracao": "Multa filtravel um",
                "valor_multa": "100,00",
                "data_vencimento": "2026-09-01",
                "gravidade": "Media",
                "pontuacao": "4",
            },
            self.admin,
        )
        salvar_multa_transito(
            {
                "data_infracao": "2026-08-26",
                "hora_infracao": "09:30",
                "veiculo_id": str(veiculo_operador.id),
                "numero_auto_infracao": "AUTO-FLT-999",
                "local_infracao": "Rua Teste",
                "cidade": "SANTOS",
                "descricao_infracao": "Multa filtravel dois",
                "valor_multa": "80,00",
                "data_vencimento": "2026-09-05",
                "gravidade": "Leve",
                "pontuacao": "3",
            },
            self.admin,
        )
        self._liberar_usuario("multas_transito", visualizar=True)
        self._autenticar(self.usuario)

        filtro_periodo = self.client.get("/operacao/multas-transito?data_inicio=2026-08-25&data_fim=2026-08-25")
        self.assertEqual(200, filtro_periodo.status_code)
        self.assertIn(b"AUTO-FLT-001", filtro_periodo.data)
        self.assertNotIn(b"AUTO-FLT-999", filtro_periodo.data)

        filtro_placa = self.client.get("/operacao/multas-transito?placa=FLT001")
        self.assertEqual(200, filtro_placa.status_code)
        self.assertIn(b"AUTO-FLT-001", filtro_placa.data)
        self.assertNotIn(b"AUTO-FLT-999", filtro_placa.data)

        filtro_motorista = self.client.get(f"/operacao/multas-transito?motorista_vinculado_id={self.motorista.id}")
        self.assertEqual(200, filtro_motorista.status_code)
        self.assertIn(b"AUTO-FLT-001", filtro_motorista.data)
        self.assertNotIn(b"AUTO-FLT-999", filtro_motorista.data)

    def test_impostos_taxas_salva_parcelas_e_integra_central_custos(self):
        veiculo = self._criar_veiculo("IPV001", "CAMINHAO IPVA")
        sucesso, mensagem, lancamentos = salvar_impostos_taxas(
            MultiDict(
                [
                    ("veiculo_id", str(veiculo.id)),
                    ("tipo_custo", "IPVA"),
                    ("data_vencimento", "2026-09-10"),
                    ("numero_parcela", "1a"),
                    ("valor", "100,00"),
                    ("data_vencimento", "2026-10-10"),
                    ("numero_parcela", "2a"),
                    ("valor", "150,50"),
                ]
            ),
            self.admin,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertEqual(2, len(lancamentos))
        self.assertEqual(2, OperacaoImpostoTaxa.query.count())
        self._liberar_usuario("impostos_taxas", visualizar=True, criar=True)
        self._liberar_usuario("central_custos", visualizar=True)
        self._autenticar(self.usuario)

        lista = self.client.get("/operacao/impostos-taxas")
        self.assertEqual(200, lista.status_code)
        self.assertIn(b"Impostos e Taxas", lista.data)
        self.assertIn(b"IPVA", lista.data)
        self.assertIn(b"R$ 150,50", lista.data)

        detalhe = self.client.get(f"/operacao/impostos-taxas/{lancamentos[0].id}/ver")
        self.assertEqual(200, detalhe.status_code)
        self.assertIn(b"Detalhes da parcela", detalhe.data)
        self.assertIn(b"IPVA", detalhe.data)

        central = self.client.get(f"/operacao/central-custos/veiculos/{veiculo.id}")
        self.assertEqual(200, central.status_code)
        self.assertIn(b"Impostos e Taxas", central.data)
        self.assertIn(b"R$ 250,50", central.data)
        self.assertIn(b"Ver", central.data)
if __name__ == "__main__":
    unittest.main()
