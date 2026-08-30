import os
from datetime import date
from decimal import Decimal
from io import BytesIO

from sqlalchemy import inspect as sa_inspect
from werkzeug.datastructures import FileStorage

from app import create_app
from app.extensions import db
from app.models import (
    CentroCusto,
    Departamento,
    Equipe,
    FinanceiroContaReceberBaixa,
    FinanceiroContaReceberLoteBaixa,
    FinanceiroContaReceberTitulo,
    FinanceiroContratoCliente,
    FinanceiroContratoMedicao,
    FinanceiroNotaFiscalEmitida,
    Modulo,
    NivelAcesso,
    PermissaoUsuarioModulo,
    Usuario,
)
from app.services.financeiro_contas_receber_service import (
    cancelar_recebimento_titulo,
    preparar_baixa_em_massa,
    recalcular_recebimento_titulo,
    registrar_recebimento_em_massa,
    registrar_recebimento_titulo,
    salvar_contrato_cliente,
    salvar_medicao_contrato,
    salvar_nota_emitida,
    salvar_titulo_receber,
    gerar_titulos_da_medicao,
    gerar_titulos_da_nota,
    vincular_medicao_a_nota,
)


USUARIO_DEMO_EMAIL = "financeiro.receber.demo@rentalretros.local"
USUARIO_DEMO_SENHA = "Demo@12345"

CLIENTES_TESTE_CR = [
    ("Cliente TESTE CR - Santos Logística Ltda", "12345678000190", "financeiro@santoslogistica.test", "1333330001"),
    ("Cliente TESTE CR - Porto Serviços Integrados Ltda", "23456789000180", "financeiro@portoservicos.test", "1333330002"),
    ("Cliente TESTE CR - Guarujá Manutenção Ferroviária Ltda", "34567890000170", "financeiro@guarujamf.test", "1333330003"),
    ("Cliente TESTE CR - Terminal Atlântico Operações S.A.", "45678901000160", "financeiro@terminalatlantico.test", "1333330004"),
    ("Cliente TESTE CR - Baixada Infraestrutura Ltda", "56789012000150", "financeiro@baixadainfra.test", "1333330005"),
]

TITULOS_TESTE_CR = [
    ("CR-TESTE-0001", 0, "TESTE CR - Prestação de serviço operacional - Agosto/2026", "900001", "Manual", "2026-08", "2026-08-01", "2026-08-10", "15000.00", "Agendado"),
    ("CR-TESTE-0002", 0, "TESTE CR - Apoio operacional adicional", "900002", "Manual", "2026-08", "2026-08-02", "2026-08-15", "8500.00", "Agendado"),
    ("CR-TESTE-0003", 1, "TESTE CR - Serviços de limpeza industrial", "900003", "Nota Fiscal Emitida", "2026-08", "2026-08-03", "2026-08-20", "22000.00", "Faturado"),
    ("CR-TESTE-0004", 1, "TESTE CR - Medição parcial de contrato", "900004", "Medição", "2026-08", "2026-08-05", "2026-08-25", "12750.00", "Faturado"),
    ("CR-TESTE-0005", 2, "TESTE CR - Manutenção ferroviária corretiva", "900005", "Manual", "2026-07", "2026-07-01", "2026-07-15", "18400.00", "Agendado"),
    ("CR-TESTE-0006", 2, "TESTE CR - Serviço emergencial de via permanente", "900006", "Manual", "2026-07", "2026-07-10", "2026-07-25", "9600.00", "Agendado"),
    ("CR-TESTE-0007", 3, "TESTE CR - Locação de equipe operacional", "900007", "Contrato", "2026-09", "2026-09-01", "2026-09-10", "30000.00", "A vencer"),
    ("CR-TESTE-0008", 3, "TESTE CR - Reembolso de materiais operacionais", "900008", "Reembolso", "2026-09", "2026-09-03", "2026-09-18", "4200.00", "A vencer"),
    ("CR-TESTE-0009", 4, "TESTE CR - Serviços administrativos compartilhados", "900009", "Manual", "2026-08", "2026-08-07", "2026-08-28", "6700.00", "Agendado"),
    ("CR-TESTE-0010", 4, "TESTE CR - Mobilização de equipe", "900010", "Manual", "2026-08", "2026-08-08", "2026-08-30", "11300.00", "Agendado"),
    ("CR-TESTE-0011", 0, "TESTE CR - Título parcialmente recebido para teste", "900011", "Manual", "2026-08", "2026-08-01", "2026-08-12", "10000.00", "Faturado"),
    ("CR-TESTE-0012", 1, "TESTE CR - Título recebido para bloqueio de nova baixa", "900012", "Manual", "2026-08", "2026-08-01", "2026-08-12", "5000.00", "Faturado"),
    ("CR-TESTE-0013", 2, "TESTE CR - Título cancelado para teste de bloqueio", "900013", "Manual", "2026-08", "2026-08-01", "2026-08-12", "7500.00", "Cancelado"),
    ("CR-TESTE-0014", 3, "TESTE CR - Título sem comprovante após baixa", "900014", "Manual", "2026-08", "2026-08-04", "2026-08-14", "8800.00", "Agendado"),
    ("CR-TESTE-0015", 4, "TESTE CR - Título para baixa em massa parcial", "900015", "Manual", "2026-09", "2026-09-02", "2026-09-20", "14200.00", "A vencer"),
]

NOTAS_TESTE_CR = [
    ("NFS-e", "NFSE-TESTE-1001", "", "Cliente TESTE CR - Santos Logística Ltda", "12345678000190", "financeiro@santoslogistica.test", "1333330001", "2026-08-01", "2026-08", "TESTE CR - Prestação de serviço operacional", "15000.00", "2026-08-10", "1", "Emitida", "Não integrado"),
    ("NFS-e", "NFSE-TESTE-1002", "", "Cliente TESTE CR - Porto Serviços Integrados Ltda", "23456789000180", "financeiro@portoservicos.test", "1333330002", "2026-08-03", "2026-08", "TESTE CR - Serviços de limpeza industrial", "22000.00", "2026-08-20", "2", "Emitida", "Não integrado"),
    ("NFS-e", "NFSE-TESTE-1003", "", "Cliente TESTE CR - Guarujá Manutenção Ferroviária Ltda", "34567890000170", "financeiro@guarujamf.test", "1333330003", "2026-07-01", "2026-07", "TESTE CR - Manutenção ferroviária corretiva", "18400.00", "2026-07-15", "1", "Emitida", "Não integrado"),
    ("Fatura", "FAT-TESTE-2001", "A", "Cliente TESTE CR - Terminal Atlântico Operações S.A.", "45678901000160", "financeiro@terminalatlantico.test", "1333330004", "2026-09-01", "2026-09", "TESTE CR - Locação de equipe operacional", "30000.00", "2026-09-10", "3", "Emitida", "Não integrado"),
    ("NFS-e", "NFSE-TESTE-1004", "", "Cliente TESTE CR - Baixada Infraestrutura Ltda", "56789012000150", "financeiro@baixadainfra.test", "1333330005", "2026-08-07", "2026-08", "TESTE CR - Serviços administrativos compartilhados", "6700.00", "2026-08-28", "1", "Emitida", "Não integrado"),
    ("NFS-e", "NFSE-TESTE-1005", "", "Cliente TESTE CR - Santos Logística Ltda", "12345678000190", "financeiro@santoslogistica.test", "1333330001", "2026-08-09", "2026-08", "TESTE CR - Nota já integrada", "2500.00", "2026-08-31", "1", "Emitida", "Não integrado"),
    ("NFS-e", "NFSE-TESTE-1006", "", "Cliente TESTE CR - Porto Serviços Integrados Ltda", "23456789000180", "financeiro@portoservicos.test", "1333330002", "2026-08-11", "2026-08", "TESTE CR - Nota cancelada para bloqueio", "1200.00", "2026-08-30", "1", "Cancelada", "Cancelado"),
]


CONTRATOS_TESTE_CR = [
    ("CTR-TESTE-CR-001", 0, "TESTE CR - Contrato de prestação de serviços operacionais", "2026-08-01", "2027-07-31", "180000.00", "Medição variável", "Mensal", "10", "Ativo"),
    ("CTR-TESTE-CR-002", 1, "TESTE CR - Contrato de limpeza industrial", "2026-08-01", "2027-07-31", "264000.00", "Valor fixo mensal", "Mensal", "20", "Ativo"),
    ("CTR-TESTE-CR-003", 3, "TESTE CR - Contrato de locação de equipe operacional", "2026-09-01", "2027-08-31", "360000.00", "Medição variável", "Mensal", "10", "Ativo"),
    ("CTR-TESTE-CR-004", 2, "TESTE CR - Contrato cancelado para bloqueio", "2026-07-01", "2026-12-31", "50000.00", "Outro", "Por demanda", "15", "Cancelado"),
]

MEDICOES_TESTE_CR = [
    ("CTR-TESTE-CR-001", "MED-TESTE-CR-001", "2026-08", "2026-08-31", "2026-08-01", "2026-08-31", "TESTE CR - Medição de serviços operacionais agosto", "15000.00", "0.00", "0.00", "0.00", "15000.00", "2026-09-02", "2026-09-10", "Aprovada", "Não integrado", "NFSE-TESTE-1001"),
    ("CTR-TESTE-CR-002", "MED-TESTE-CR-002", "2026-08", "2026-08-31", "2026-08-01", "2026-08-31", "TESTE CR - Medição de limpeza industrial agosto", "22000.00", "0.00", "0.00", "0.00", "22000.00", "2026-09-03", "2026-09-20", "Aprovada", "Não integrado", ""),
    ("CTR-TESTE-CR-003", "MED-TESTE-CR-003", "2026-09", "2026-09-30", "2026-09-01", "2026-09-30", "TESTE CR - Medição de locação de equipe setembro", "30000.00", "0.00", "0.00", "0.00", "30000.00", "2026-10-02", "2026-10-10", "Medida", "Não integrado", ""),
    ("CTR-TESTE-CR-001", "MED-TESTE-CR-004", "2026-08", "2026-08-31", "2026-08-01", "2026-08-31", "TESTE CR - Medição já integrada a título", "2500.00", "0.00", "0.00", "0.00", "2500.00", "2026-08-31", "2026-08-31", "Aprovada", "Não integrado", ""),
    ("CTR-TESTE-CR-002", "MED-TESTE-CR-005", "2026-08", "2026-08-31", "2026-08-01", "2026-08-31", "TESTE CR - Medição cancelada para bloqueio", "1200.00", "0.00", "0.00", "0.00", "1200.00", "2026-08-30", "2026-08-30", "Cancelada", "Cancelado", ""),
]


def ambiente_local_liberado(app):
    if os.environ.get("ALLOW_DEV_SEED") != "1":
        return False
    if app.config.get("TESTING"):
        return True
    ambiente = (os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV") or os.environ.get("ENV") or "").lower()
    return ambiente in {"development", "dev", "local"}


def obter_ou_criar(modelo, filtro, dados):
    registro = modelo.query.filter_by(**filtro).first()
    if not registro:
        registro = modelo(**filtro)
        db.session.add(registro)
    for campo, valor in dados.items():
        setattr(registro, campo, valor)
    return registro


def garantir_financeiro_contas_receber():
    departamento = obter_ou_criar(
        Departamento,
        {"slug": "financeiro"},
        {"nome": "Financeiro", "descricao": "Controle financeiro, contas, fluxo de caixa e relatorios.", "icone": "grafico", "ativo": True, "ordem": 1},
    )
    db.session.flush()
    modulo = obter_ou_criar(
        Modulo,
        {"departamento_id": departamento.id, "slug": "contas_a_receber"},
        {"nome": "Contas a Receber", "descricao": "Clientes e recebimentos", "ativo": True, "ordem": 2},
    )
    db.session.flush()
    return departamento, modulo


def criar_usuario_demo(modulo):
    nivel = obter_ou_criar(NivelAcesso, {"slug": "usuario"}, {"nome": "Usuario", "descricao": "Usuario local de testes.", "ativo": True})
    db.session.flush()
    usuario = obter_ou_criar(
        Usuario,
        {"email": USUARIO_DEMO_EMAIL},
        {"nome": "Financeiro Receber Demo", "nivel_acesso_id": nivel.id, "ativo": True, "precisa_trocar_senha": False},
    )
    usuario.definir_senha(USUARIO_DEMO_SENHA)
    permissao = PermissaoUsuarioModulo.query.filter_by(usuario_id=usuario.id, modulo_id=modulo.id).first()
    if not permissao:
        permissao = PermissaoUsuarioModulo(usuario_id=usuario.id, modulo_id=modulo.id)
        db.session.add(permissao)
    permissao.pode_visualizar = True
    permissao.pode_criar = True
    permissao.pode_editar = True
    permissao.pode_excluir = True
    permissao.pode_exportar = True
    permissao.ativo = True
    permissao.garantir_visualizacao()
    return usuario


def criar_cadastros_auxiliares_demo():
    centros = []
    for codigo, nome in [("TESTE-CR-ADM", "TESTE CR - Administrativo"), ("TESTE-CR-OPER", "TESTE CR - Operação"), ("TESTE-CR-LOC", "TESTE CR - Locação")]:
        centros.append(obter_ou_criar(CentroCusto, {"codigo": codigo}, {"nome": nome, "classe": "CENTRO DE CUSTO", "descricao": "Cadastro ficticio local TESTE CR.", "ativo": True}))
    equipes = []
    for slug, nome in [("teste-cr-equipe-operacao", "TESTE CR - Equipe Operação"), ("teste-cr-equipe-medicao", "TESTE CR - Equipe Medição")]:
        equipes.append(obter_ou_criar(Equipe, {"slug": slug}, {"nome": nome, "ativo": True}))
    db.session.flush()
    return centros, equipes


def criar_titulo_demo(item, usuario, centros, equipes):
    documento, cliente_idx, descricao, nf, origem, competencia, emissao, vencimento, valor, status = item
    cliente, cnpj, email, telefone = CLIENTES_TESTE_CR[cliente_idx]
    titulo = FinanceiroContaReceberTitulo.query.filter_by(numero_documento=documento).first()
    if titulo and titulo.baixas:
        recalcular_recebimento_titulo(titulo, usuario=usuario)
        return titulo
    dados = {
        "cliente_nome_snapshot": cliente,
        "cliente_cnpj_cpf_snapshot": cnpj,
        "cliente_email_financeiro_snapshot": email,
        "cliente_telefone_snapshot": telefone,
        "descricao": descricao,
        "numero_documento": documento,
        "numero_nota_fiscal": nf,
        "chave_acesso_nfe_nfse": f"352608{cnpj}550010000{nf}10000{nf}8"[:44],
        "origem_lancamento": origem,
        "competencia": competencia,
        "data_emissao": emissao,
        "data_vencimento": vencimento,
        "valor_original": valor,
        "valor_desconto": "0.00",
        "valor_acrescimo": "0.00",
        "valor_juros_multa": "0.00",
        "valor_recebido": "0.00",
        "parcela_numero": "1",
        "total_parcelas": "1",
        "centro_custo_id": str(centros[cliente_idx % len(centros)].id),
        "sub_centro_custo_equipe_id": str(equipes[cliente_idx % len(equipes)].id),
        "status": status,
        "observacoes": "Dado ficticio local TESTE CR para Missoes 18.1, 18.2 e 18.3.",
    }
    sucesso, mensagem, titulo, _ = salvar_titulo_receber(dados, titulo=titulo, usuario=usuario)
    if not sucesso:
        print(f"Falha ao criar titulo {documento}: {mensagem}")
        return None
    return titulo


def _arquivo_comprovante_demo(nome):
    return FileStorage(stream=BytesIO(f"Comprovante ficticio TESTE CR - {nome}".encode("utf-8")), filename=f"{nome}.pdf", content_type="application/pdf")


def criar_baixa_demo(documento, usuario, valor, forma, conta, observacoes, data_recebimento, com_comprovante=False, estornar=False):
    titulo = FinanceiroContaReceberTitulo.query.filter_by(numero_documento=documento).first()
    if not titulo:
        return None
    existente = FinanceiroContaReceberBaixa.query.filter_by(titulo_id=titulo.id, observacoes=observacoes).first()
    if existente:
        recalcular_recebimento_titulo(titulo, usuario=usuario)
        return existente
    sucesso, mensagem, baixa = registrar_recebimento_titulo(
        titulo,
        {"data_recebimento": data_recebimento, "valor_recebido": valor, "forma_recebimento": forma, "conta_recebimento_descricao": conta, "observacoes": observacoes},
        arquivo=_arquivo_comprovante_demo(documento) if com_comprovante else None,
        usuario=usuario,
    )
    if not sucesso:
        print(f"Falha ao criar baixa {documento}: {mensagem}")
        return None
    if estornar:
        cancelar_recebimento_titulo(baixa, "Baixa cancelada fictícia para testar exclusão de totais", usuario=usuario)
    return baixa


def criar_lote_demo(usuario, inspector):
    if "financeiro_contas_receber_lotes_baixa" not in inspector.get_table_names():
        return None
    existente = FinanceiroContaReceberLoteBaixa.query.filter_by(observacoes="TESTE CR - Lote fictício de baixa em massa").first()
    if existente:
        return existente
    titulos, _ = preparar_baixa_em_massa([
        FinanceiroContaReceberTitulo.query.filter_by(numero_documento="CR-TESTE-0001").one().id,
        FinanceiroContaReceberTitulo.query.filter_by(numero_documento="CR-TESTE-0002").one().id,
        FinanceiroContaReceberTitulo.query.filter_by(numero_documento="CR-TESTE-0003").one().id,
    ])
    dados = {"titulos_ids": [str(titulo.id) for titulo in titulos], "data_recebimento": "2026-08-29", "forma_recebimento": "Pix", "conta_recebimento_descricao": "Banco TESTE CR - Conta Corrente", "observacoes": "TESTE CR - Lote fictício de baixa em massa"}
    valores = {"CR-TESTE-0001": "15000.00", "CR-TESTE-0002": "3000.00", "CR-TESTE-0003": "5000.00"}
    for titulo in titulos:
        dados[f"valor_receber_{titulo.id}"] = valores[titulo.numero_documento]
    sucesso, mensagem, lote = registrar_recebimento_em_massa(dados, arquivo=_arquivo_comprovante_demo("CR-LOTE-TESTE"), usuario=usuario)
    if not sucesso:
        print(f"Falha ao criar lote TESTE CR: {mensagem}")
    return lote



def criar_nota_emitida_demo(item, usuario):
    tipo, numero, serie, cliente, cnpj, email, telefone, emissao, competencia, descricao, valor, vencimento, parcelas, status_fiscal, status_financeiro = item
    nota = FinanceiroNotaFiscalEmitida.query.filter_by(numero_nota=numero, cliente_cnpj_cpf_snapshot=cnpj).first()
    if nota and nota.titulos:
        return nota
    dados = {
        "tipo_nota": tipo,
        "numero_nota": numero,
        "serie": serie,
        "chave_acesso": f"352608{cnpj}550010000{numero[-4:]}10000{numero[-4:]}8"[:44] if tipo == "NF-e" else "",
        "codigo_verificacao_nfse": f"COD-{numero}",
        "cliente_nome_snapshot": cliente,
        "cliente_cnpj_cpf_snapshot": cnpj,
        "cliente_email_financeiro_snapshot": email,
        "cliente_telefone_snapshot": telefone,
        "data_emissao": emissao,
        "competencia": competencia,
        "descricao": descricao,
        "valor_bruto": valor,
        "valor_desconto": "0.00",
        "valor_impostos_retidos": "0.00",
        "valor_liquido": valor,
        "valor_total": valor,
        "data_vencimento_padrao": vencimento,
        "numero_parcelas": parcelas,
        "condicao_recebimento": f"{parcelas} parcela(s)",
        "status_fiscal": status_fiscal,
        "status_financeiro": status_financeiro,
        "observacoes_fiscais": "TESTE CR - nota emitida fictícia local.",
        "observacoes_financeiras": "TESTE CR - preparada para integração com Contas a Receber.",
    }
    sucesso, mensagem, nota = salvar_nota_emitida(dados, nota=nota, usuario=usuario)
    if not sucesso:
        print(f"Falha ao criar nota {numero}: {mensagem}")
        return None
    return nota


def criar_integracao_nota_demo(usuario):
    nota = FinanceiroNotaFiscalEmitida.query.filter_by(numero_nota="NFSE-TESTE-1005").first()
    if nota and not nota.titulos:
        gerar_titulos_da_nota(nota, {"data_primeiro_vencimento": "2026-08-31", "numero_parcelas": "1", "competencia": "2026-08", "descricao": nota.descricao}, usuario=usuario)


def criar_contrato_demo(item, usuario, centros, equipes):
    numero, cliente_idx, objeto, inicio, fim, valor, tipo, periodicidade, dia_vencimento, status = item
    cliente, cnpj, email, telefone = CLIENTES_TESTE_CR[cliente_idx]
    contrato = FinanceiroContratoCliente.query.filter_by(numero_contrato=numero, cliente_cnpj_cpf_snapshot=cnpj).first()
    dados = {
        "numero_contrato": numero,
        "cliente_nome_snapshot": cliente,
        "cliente_cnpj_cpf_snapshot": cnpj,
        "cliente_email_financeiro_snapshot": email,
        "cliente_telefone_snapshot": telefone,
        "descricao_objeto": objeto,
        "data_inicio": inicio,
        "data_fim": fim,
        "valor_contratual": valor,
        "tipo_cobranca": tipo,
        "periodicidade_medicao": periodicidade,
        "dia_padrao_vencimento": dia_vencimento,
        "condicao_recebimento": f"Vencimento dia {dia_vencimento}",
        "centro_custo_id": str(centros[cliente_idx % len(centros)].id),
        "sub_centro_custo_equipe_id": str(equipes[cliente_idx % len(equipes)].id),
        "status": status,
        "observacoes": "TESTE CR - contrato fictício local para Missão 18.5.",
    }
    sucesso, mensagem, contrato = salvar_contrato_cliente(dados, contrato=contrato, usuario=usuario)
    if not sucesso:
        print(f"Falha ao criar contrato {numero}: {mensagem}")
        return None
    return contrato


def criar_medicao_demo(item, usuario):
    numero_contrato, numero_medicao, competencia, data_medicao, periodo_inicio, periodo_fim, descricao, bruto, desconto, acrescimo, retencoes, liquido, faturamento, vencimento, status_medicao, status_financeiro, numero_nota = item
    contrato = FinanceiroContratoCliente.query.filter_by(numero_contrato=numero_contrato).first()
    if not contrato:
        return None
    medicao = FinanceiroContratoMedicao.query.filter_by(contrato_id=contrato.id, numero_medicao=numero_medicao).first()
    nota = FinanceiroNotaFiscalEmitida.query.filter_by(numero_nota=numero_nota).first() if numero_nota else None
    dados = {
        "contrato_id": str(contrato.id),
        "nota_emitida_id": str(nota.id) if nota else "",
        "numero_medicao": numero_medicao,
        "competencia": competencia,
        "data_medicao": data_medicao,
        "periodo_inicio": periodo_inicio,
        "periodo_fim": periodo_fim,
        "descricao": descricao,
        "valor_bruto_medido": bruto,
        "valor_desconto": desconto,
        "valor_acrescimo": acrescimo,
        "valor_retencoes": retencoes,
        "valor_liquido_medido": liquido,
        "data_prevista_faturamento": faturamento,
        "data_prevista_vencimento": vencimento,
        "status_medicao": status_medicao,
        "status_financeiro": status_financeiro,
        "observacoes_tecnicas": "TESTE CR - medição fictícia local.",
        "observacoes_financeiras": "TESTE CR - preparada para integração com Contas a Receber.",
    }
    sucesso, mensagem, medicao = salvar_medicao_contrato(dados, medicao=medicao, usuario=usuario)
    if not sucesso:
        print(f"Falha ao criar medição {numero_medicao}: {mensagem}")
        return None
    return medicao


def criar_integracao_medicao_demo(usuario):
    medicao = FinanceiroContratoMedicao.query.filter_by(numero_medicao="MED-TESTE-CR-004").first()
    if medicao and not medicao.titulos:
        gerar_titulos_da_medicao(medicao, {"data_vencimento": "2026-08-31", "numero_parcelas": "1", "competencia": "2026-08", "descricao": medicao.descricao}, usuario=usuario)
    medicao = FinanceiroContratoMedicao.query.filter_by(numero_medicao="MED-TESTE-CR-001").first()
    nota = FinanceiroNotaFiscalEmitida.query.filter_by(numero_nota="NFSE-TESTE-1001").first()
    if medicao and nota and not medicao.nota_emitida_id:
        vincular_medicao_a_nota(medicao, nota.id, usuario=usuario)

def executar_seed(app=None):
    app = app or create_app()
    if not ambiente_local_liberado(app):
        print("Seed dev de Contas a Receber bloqueado. Use ALLOW_DEV_SEED=1 em ambiente local/desenvolvimento.")
        return False
    with app.app_context():
        inspector = sa_inspect(db.engine)
        if "departamentos" not in inspector.get_table_names():
            db.create_all()
        from app.seed_modulos_base_producao import executar_seed as executar_seed_modulos_base
        executar_seed_modulos_base()
        _, modulo = garantir_financeiro_contas_receber()
        usuario = criar_usuario_demo(modulo)
        centros, equipes = criar_cadastros_auxiliares_demo()
        for item in TITULOS_TESTE_CR:
            criar_titulo_demo(item, usuario, centros, equipes)
        criar_baixa_demo("CR-TESTE-0011", usuario, "4000.00", "Pix", "Banco TESTE CR - Conta Corrente", "Recebimento parcial fictício para teste", "2026-08-13", com_comprovante=True)
        criar_baixa_demo("CR-TESTE-0012", usuario, "5000.00", "Transferência", "Banco TESTE CR - Conta Corrente", "Recebimento total fictício para teste", "2026-08-12", com_comprovante=True)
        criar_baixa_demo("CR-TESTE-0014", usuario, "3000.00", "Boleto", "Banco TESTE CR - Conta Cobrança", "Recebimento parcial sem comprovante para teste", "2026-08-15")
        criar_baixa_demo("CR-TESTE-0009", usuario, "1000.00", "Pix", "Banco TESTE CR - Conta Corrente", "Baixa cancelada fictícia para testar exclusão de totais", "2026-08-20", estornar=True)
        criar_lote_demo(usuario, sa_inspect(db.engine))
        if "financeiro_notas_fiscais_emitidas" in sa_inspect(db.engine).get_table_names():
            for item in NOTAS_TESTE_CR:
                criar_nota_emitida_demo(item, usuario)
            criar_integracao_nota_demo(usuario)
        if "financeiro_contratos_clientes" in sa_inspect(db.engine).get_table_names():
            for item in CONTRATOS_TESTE_CR:
                criar_contrato_demo(item, usuario, centros, equipes)
        if "financeiro_contratos_medicoes" in sa_inspect(db.engine).get_table_names():
            for item in MEDICOES_TESTE_CR:
                criar_medicao_demo(item, usuario)
            criar_integracao_medicao_demo(usuario)
        for titulo in FinanceiroContaReceberTitulo.query.filter(FinanceiroContaReceberTitulo.numero_documento.like("CR-TESTE-%")).all():
            recalcular_recebimento_titulo(titulo, usuario=usuario)
        db.session.commit()
        print("Dados fictícios de Contas a Receber criados com sucesso.")
        print("Dados fictícios já existem. Nenhum registro duplicado foi criado quando aplicável.")
        print(f"Usuario demo: {USUARIO_DEMO_EMAIL}")
        print(f"Senha demo: {USUARIO_DEMO_SENHA}")
        return True


if __name__ == "__main__":
    executar_seed()