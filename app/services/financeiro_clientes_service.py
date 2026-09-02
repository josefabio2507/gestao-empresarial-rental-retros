from app.extensions import db
from app.models import (
    FinanceiroCliente,
    FinanceiroContaReceberTitulo,
    FinanceiroContratoCliente,
    FinanceiroNotaFiscalEmitida,
)
from app.services.suprimentos_service import (
    consultar_cnpj_publico,
    email_valido,
    somente_digitos,
    texto,
    texto_maiusculo,
    validar_cnpj_cpf,
)
from app.utils.datas import agora_brasil

TIPOS_PESSOA_CLIENTE = ["juridica", "fisica"]


def inteiro_ou_none(valor):
    try:
        return int(valor) if str(valor or "").strip() else None
    except (TypeError, ValueError):
        return None


def cliente_por_id(cliente_id):
    return db.session.get(FinanceiroCliente, cliente_id)


def clientes_ativos():
    return FinanceiroCliente.query.filter_by(ativo=True).order_by(FinanceiroCliente.razao_social.asc()).all()


def cliente_para_json(cliente):
    if not cliente:
        return {}
    return {
        "id": cliente.id,
        "tipo_pessoa": cliente.tipo_pessoa,
        "cnpj_cpf": cliente.cnpj_cpf,
        "cnpj_cpf_normalizado": cliente.cnpj_cpf_normalizado,
        "razao_social": cliente.razao_social,
        "nome_fantasia": cliente.nome_fantasia or "",
        "email_financeiro": cliente.email_financeiro or "",
        "telefone_principal": cliente.telefone_principal or "",
        "condicao_recebimento_padrao": cliente.condicao_recebimento_padrao or "",
        "prazo_vencimento_padrao": cliente.prazo_vencimento_padrao or "",
    }


def buscar_clientes(filtros=None):
    filtros = filtros or {}
    query = FinanceiroCliente.query
    razao = texto(filtros.get("razao_social"))
    fantasia = texto(filtros.get("nome_fantasia"))
    documento = somente_digitos(filtros.get("cnpj_cpf"))
    cidade = texto(filtros.get("cidade"))
    uf = texto(filtros.get("uf")).upper()[:2]
    email = texto(filtros.get("email")).lower()
    telefone = somente_digitos(filtros.get("telefone"))
    status = texto(filtros.get("status"))

    if razao:
        query = query.filter(FinanceiroCliente.razao_social.ilike(f"%{razao}%"))
    if fantasia:
        query = query.filter(FinanceiroCliente.nome_fantasia.ilike(f"%{fantasia}%"))
    if documento:
        query = query.filter(FinanceiroCliente.cnpj_cpf_normalizado.ilike(f"%{documento}%"))
    if cidade:
        query = query.filter(FinanceiroCliente.cidade.ilike(f"%{cidade}%"))
    if uf:
        query = query.filter(FinanceiroCliente.uf == uf)
    if email:
        query = query.filter(
            (FinanceiroCliente.email_financeiro.ilike(f"%{email}%"))
            | (FinanceiroCliente.email_alternativo.ilike(f"%{email}%"))
        )
    if telefone:
        query = query.filter(
            (FinanceiroCliente.telefone_principal.ilike(f"%{telefone}%"))
            | (FinanceiroCliente.telefone_alternativo.ilike(f"%{telefone}%"))
        )
    if status == "ativos":
        query = query.filter(FinanceiroCliente.ativo.is_(True))
    elif status == "inativos":
        query = query.filter(FinanceiroCliente.ativo.is_(False))

    return query.order_by(FinanceiroCliente.razao_social.asc()).all()


def documento_cliente_ja_existe(documento, cliente_id_ignorado=None):
    documento = somente_digitos(documento)
    if not documento:
        return False
    query = FinanceiroCliente.query.filter_by(cnpj_cpf_normalizado=documento)
    if cliente_id_ignorado:
        query = query.filter(FinanceiroCliente.id != cliente_id_ignorado)
    return query.first() is not None


def dados_cliente(form_data):
    return {
        "tipo_pessoa": texto(form_data.get("tipo_pessoa")) or "juridica",
        "cnpj_cpf": texto(form_data.get("cnpj_cpf")),
        "cnpj_cpf_normalizado": somente_digitos(form_data.get("cnpj_cpf")),
        "razao_social": texto_maiusculo(form_data.get("razao_social")),
        "nome_fantasia": texto_maiusculo(form_data.get("nome_fantasia")) or None,
        "inscricao_estadual": texto_maiusculo(form_data.get("inscricao_estadual")) or None,
        "inscricao_municipal": texto_maiusculo(form_data.get("inscricao_municipal")) or None,
        "email_financeiro": texto(form_data.get("email_financeiro")).lower() or None,
        "email_alternativo": texto(form_data.get("email_alternativo")).lower() or None,
        "telefone_principal": somente_digitos(form_data.get("telefone_principal")) or None,
        "telefone_alternativo": somente_digitos(form_data.get("telefone_alternativo")) or None,
        "contato_responsavel": texto_maiusculo(form_data.get("contato_responsavel")) or None,
        "cargo_contato": texto_maiusculo(form_data.get("cargo_contato")) or None,
        "endereco": texto_maiusculo(form_data.get("endereco")) or None,
        "numero": texto(form_data.get("numero")) or None,
        "complemento": texto_maiusculo(form_data.get("complemento")) or None,
        "bairro": texto_maiusculo(form_data.get("bairro")) or None,
        "cidade": texto_maiusculo(form_data.get("cidade")) or None,
        "uf": texto(form_data.get("uf")).upper()[:2] or None,
        "cep": somente_digitos(form_data.get("cep")) or None,
        "condicao_recebimento_padrao": texto(form_data.get("condicao_recebimento_padrao")) or None,
        "prazo_vencimento_padrao": inteiro_ou_none(form_data.get("prazo_vencimento_padrao")),
        "observacoes": texto_maiusculo(form_data.get("observacoes")) or None,
        "ativo": form_data.get("ativo") in {"1", "true", "on", "sim"},
    }


def salvar_cliente(form_data, cliente=None, usuario=None):
    novo = cliente is None
    dados = dados_cliente(form_data)
    if dados["tipo_pessoa"] not in TIPOS_PESSOA_CLIENTE:
        return False, "Tipo de pessoa inválido.", cliente
    if not dados["cnpj_cpf_normalizado"]:
        return False, "CNPJ/CPF é obrigatório.", cliente
    if not validar_cnpj_cpf(dados["cnpj_cpf_normalizado"], dados["tipo_pessoa"]):
        return False, "CNPJ/CPF inválido.", cliente
    if not dados["razao_social"]:
        return False, "Razão Social/Nome é obrigatório.", cliente
    for campo_email in ["email_financeiro", "email_alternativo"]:
        if dados[campo_email] and not email_valido(dados[campo_email]):
            return False, "E-mail inválido.", cliente
    if dados["prazo_vencimento_padrao"] is not None and dados["prazo_vencimento_padrao"] < 0:
        return False, "Prazo padrão de vencimento não pode ser negativo.", cliente
    if documento_cliente_ja_existe(dados["cnpj_cpf_normalizado"], getattr(cliente, "id", None)):
        return False, "CNPJ já cadastrado.", cliente

    cliente = cliente or FinanceiroCliente(ativo=True)
    if novo:
        cliente.criado_por_usuario_id = getattr(usuario, "id", None)
        db.session.add(cliente)
    for campo, valor in dados.items():
        setattr(cliente, campo, valor)
    cliente.atualizado_por_usuario_id = getattr(usuario, "id", None)
    db.session.commit()
    return True, "Cliente cadastrado com sucesso." if novo else "Cliente atualizado com sucesso.", cliente


def alterar_status_cliente(cliente, motivo=None, usuario=None):
    cliente.ativo = not cliente.ativo
    cliente.atualizado_por_usuario_id = getattr(usuario, "id", None)
    if not cliente.ativo:
        cliente.inativado_por_usuario_id = getattr(usuario, "id", None)
        cliente.inativado_em = agora_brasil()
        cliente.motivo_inativacao = texto_maiusculo(motivo) or "INATIVAÇÃO MANUAL"
    else:
        cliente.inativado_por_usuario_id = None
        cliente.inativado_em = None
        cliente.motivo_inativacao = None
    db.session.commit()
    return True, "Cliente reativado com sucesso." if cliente.ativo else "Cliente inativado com sucesso."


def buscar_vinculos_cliente(cliente):
    if not cliente:
        return {"titulos": [], "notas": [], "contratos": [], "medicoes": []}
    documento = cliente.cnpj_cpf_normalizado
    titulos = FinanceiroContaReceberTitulo.query.filter(
        (FinanceiroContaReceberTitulo.cliente_id == cliente.id)
        | (FinanceiroContaReceberTitulo.cliente_cnpj_cpf_snapshot == documento)
    ).order_by(FinanceiroContaReceberTitulo.data_vencimento.desc(), FinanceiroContaReceberTitulo.id.desc()).all()
    notas = FinanceiroNotaFiscalEmitida.query.filter(
        (FinanceiroNotaFiscalEmitida.cliente_id == cliente.id)
        | (FinanceiroNotaFiscalEmitida.cliente_cnpj_cpf_snapshot == documento)
    ).order_by(FinanceiroNotaFiscalEmitida.data_emissao.desc(), FinanceiroNotaFiscalEmitida.id.desc()).all()
    contratos = FinanceiroContratoCliente.query.filter(
        (FinanceiroContratoCliente.cliente_id == cliente.id)
        | (FinanceiroContratoCliente.cliente_cnpj_cpf_snapshot == documento)
    ).order_by(FinanceiroContratoCliente.data_inicio.desc(), FinanceiroContratoCliente.id.desc()).all()
    medicoes = []
    for contrato in contratos:
        medicoes.extend(contrato.medicoes)
    medicoes = sorted(medicoes, key=lambda item: (item.data_medicao, item.id), reverse=True)
    return {"titulos": titulos, "notas": notas, "contratos": contratos, "medicoes": medicoes}


def preencher_snapshots_cliente(registro, form_data, prefixo="cliente"):
    cliente = cliente_por_id(inteiro_ou_none(form_data.get("cliente_id")))
    if not cliente:
        return None
    registro.cliente_id = cliente.id
    registro.cliente_nome_snapshot = cliente.razao_social
    registro.cliente_cnpj_cpf_snapshot = cliente.cnpj_cpf_normalizado
    registro.cliente_email_financeiro_snapshot = cliente.email_financeiro or ""
    registro.cliente_telefone_snapshot = cliente.telefone_principal or ""
    return cliente

