from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.decorators import module_permission_required
from app.extensions import db
from app.models import (
    PedidoTicketBeneficiario,
    PedidoTicketEmpresa,
    PedidoTicketUnidadeEntrega,
)
from app.departamento_pessoal.pedido_tiquete.excel_service import gerar_planilha_pedido
from app.services.permissoes_service import usuario_tem_permissao


pedido_tiquete_bp = Blueprint("pedido_tiquete", __name__)
PRODUTOS = ("TAE", "TRE", "TKE", "TFE")
ESTADOS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()


def _digitos(valor):
    return "".join(caractere for caractere in valor if caractere.isdigit())


def _data_form(nome):
    return date.fromisoformat(request.form.get(nome, ""))


def _somar_dias_uteis(inicio, quantidade):
    atual = inicio
    contagem = 0
    while contagem < quantidade:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            contagem += 1
    return atual


def _idade_minima_atendida(nascimento, idade):
    try:
        limite = nascimento.replace(year=nascimento.year + idade)
    except ValueError:
        limite = date(nascimento.year + idade, 3, 1)
    return date.today() >= limite


def _pode(acao):
    return usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_tiquete", acao)


def _exigir_feature_ativa():
    if not current_app.config.get("PEDIDO_TICKET_ENABLED", False):
        abort(404)


@pedido_tiquete_bp.route("/")
@module_permission_required("departamento_pessoal", "pedido_tiquete", "visualizar")
def index():
    _exigir_feature_ativa()
    aba = request.args.get("aba", "empresas")
    if aba not in {"empresas", "unidades", "beneficiarios"}:
        aba = "empresas"
    return render_template(
        "departamento_pessoal/pedido_tiquete/index.html",
        aba=aba,
        empresas=PedidoTicketEmpresa.query.order_by(PedidoTicketEmpresa.criado_em.desc()).limit(100).all(),
        empresas_ativas=PedidoTicketEmpresa.query.filter_by(ativo=True).order_by(PedidoTicketEmpresa.numero_pedido.desc(), PedidoTicketEmpresa.nome_empresa).limit(100).all(),
        editar_empresa=db.session.get(PedidoTicketEmpresa, request.args.get("editar_empresa", type=int)),
        unidades=PedidoTicketUnidadeEntrega.query.order_by(PedidoTicketUnidadeEntrega.nome_unidade).limit(100).all(),
        beneficiarios=PedidoTicketBeneficiario.query.order_by(PedidoTicketBeneficiario.nome).limit(100).all(),
        pedidos=[linha[0] for linha in PedidoTicketBeneficiario.query.with_entities(
            PedidoTicketBeneficiario.numero_pedido
        ).distinct().order_by(PedidoTicketBeneficiario.numero_pedido.desc()).limit(100).all()],
        produtos=PRODUTOS,
        estados=ESTADOS,
        pode_criar=_pode("criar"),
        pode_editar=_pode("editar"),
    )


@pedido_tiquete_bp.route("/pedidos/<numero_pedido>/excel", methods=["GET"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "visualizar")
def baixar_excel(numero_pedido):
    _exigir_feature_ativa()
    if not numero_pedido.isdigit() or len(numero_pedido) > 10:
        flash("Número de pedido inválido.", "danger")
        return redirect(url_for("pedido_tiquete.index", aba="empresas"))

    empresas = PedidoTicketEmpresa.query.filter_by(numero_pedido=numero_pedido).order_by(
        PedidoTicketEmpresa.id
    ).all()
    beneficiarios = PedidoTicketBeneficiario.query.filter_by(
        numero_pedido=numero_pedido
    ).order_by(PedidoTicketBeneficiario.id).all()
    cnpjs = {empresa.cnpj for empresa in empresas}
    unidades = PedidoTicketUnidadeEntrega.query.filter(
        PedidoTicketUnidadeEntrega.cnpj.in_(cnpjs)
    ).order_by(PedidoTicketUnidadeEntrega.id).all()
    if not empresas or not beneficiarios:
        flash("Cadastre os contratos e beneficiários do pedido antes de gerar a planilha.", "warning")
        return redirect(url_for("pedido_tiquete.index", aba="empresas"))

    modelo = Path(__file__).with_name("modelo_pedido_ticket.xlsx")
    if not modelo.is_file():
        flash("O modelo oficial do Excel não está disponível.", "danger")
        return redirect(url_for("pedido_tiquete.index", aba="empresas"))

    try:
        arquivo = gerar_planilha_pedido(modelo, numero_pedido, empresas, unidades, beneficiarios)
    except ValueError as erro:
        flash(str(erro), "danger")
        return redirect(url_for("pedido_tiquete.index", aba="empresas"))

    resposta = send_file(
        arquivo,
        as_attachment=True,
        download_name=f"pedido_tiquete_{numero_pedido}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        max_age=0,
    )
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


def _dados_empresa_form(empresa=None):
    numero_pedido = _digitos(request.form.get("numero_pedido", ""))
    cnpj = request.form.get("cnpj", "").strip().upper()
    nome = request.form.get("nome_empresa", "").strip()
    contrato = _digitos(request.form.get("numero_contrato", ""))
    produto = request.form.get("produto", "").strip().upper()
    data_credito = _data_form("data_credito")

    if not (1 <= len(numero_pedido) <= 10 and 1 <= len(cnpj) <= 14 and cnpj.isalnum()):
        raise ValueError("Confira o número do pedido e o CNPJ/CPF da empresa.")
    if not nome or len(nome) > 26 or not (1 <= len(contrato) <= 10) or produto not in PRODUTOS:
        raise ValueError("Confira o nome, o contrato e o produto da empresa.")

    duplicado = PedidoTicketEmpresa.query.filter_by(
        numero_pedido=numero_pedido, numero_contrato=contrato, produto=produto
    )
    if empresa:
        duplicado = duplicado.filter(PedidoTicketEmpresa.id != empresa.id)
    if duplicado.first():
        raise ValueError("Esse contrato e produto já foram incluídos no pedido.")

    if empresa:
        chave_antiga = f"{empresa.numero_contrato} - {empresa.produto}"
        identidade_mudou = (
            numero_pedido != empresa.numero_pedido
            or contrato != empresa.numero_contrato
            or produto != empresa.produto
        )
        if identidade_mudou and PedidoTicketBeneficiario.query.filter_by(
            numero_pedido=empresa.numero_pedido, contrato_produto=chave_antiga
        ).first():
            raise ValueError("Não altere o pedido, contrato ou produto: já há beneficiários vinculados.")
        if cnpj != empresa.cnpj and PedidoTicketUnidadeEntrega.query.filter_by(cnpj=empresa.cnpj).first():
            raise ValueError("Não altere o CNPJ enquanto houver unidades vinculadas a ele.")

    if not empresa or data_credito != empresa.data_credito:
        outros = PedidoTicketEmpresa.query.filter_by(numero_pedido=numero_pedido)
        if empresa:
            outros = outros.filter(PedidoTicketEmpresa.id != empresa.id)
        prazo_dias = 7 if outros.count() == 0 else 3
        if data_credito < _somar_dias_uteis(date.today(), prazo_dias):
            raise ValueError(f"A data de crédito deve respeitar o prazo mínimo de {prazo_dias} dias úteis.")

    return {
        "numero_pedido": numero_pedido,
        "cnpj": cnpj,
        "nome_empresa": nome,
        "numero_contrato": contrato,
        "produto": produto,
        "data_credito": data_credito,
        "ativo": True if empresa is None else request.form.get("ativo") == "on",
    }


@pedido_tiquete_bp.route("/empresas", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_empresa():
    _exigir_feature_ativa()
    try:
        db.session.add(PedidoTicketEmpresa(**_dados_empresa_form()))
        db.session.commit()
        flash("Empresa/contrato cadastrado com sucesso.", "success")
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Não foi possível cadastrar. Confira os campos, a unicidade e o prazo da data de crédito.", "danger")
    return redirect(url_for("pedido_tiquete.index", aba="empresas"))


@pedido_tiquete_bp.route("/empresas/<int:empresa_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "editar")
def editar_empresa(empresa_id):
    _exigir_feature_ativa()
    empresa = db.session.get(PedidoTicketEmpresa, empresa_id)
    if not empresa:
        abort(404)
    if request.method == "GET":
        return redirect(url_for("pedido_tiquete.index", aba="empresas", editar_empresa=empresa.id))
    try:
        for campo, valor in _dados_empresa_form(empresa).items():
            setattr(empresa, campo, valor)
        db.session.commit()
        flash("Empresa/contrato atualizado com sucesso.", "success")
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Não foi possível atualizar. Confira os campos, os vínculos e a unicidade do contrato.", "danger")
    return redirect(url_for("pedido_tiquete.index", aba="empresas"))


@pedido_tiquete_bp.route("/empresas/<int:empresa_id>/status", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "editar")
def alternar_status_empresa(empresa_id):
    _exigir_feature_ativa()
    empresa = db.session.get(PedidoTicketEmpresa, empresa_id)
    if not empresa:
        abort(404)
    empresa.ativo = not empresa.ativo
    db.session.commit()
    flash("Empresa/contrato ativado." if empresa.ativo else "Empresa/contrato desativado.", "success")
    return redirect(url_for("pedido_tiquete.index", aba="empresas"))

@pedido_tiquete_bp.route("/unidades", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_unidade():
    _exigir_feature_ativa()
    try:
        dados = {campo: request.form.get(campo, "").strip() for campo in (
            "cnpj", "codigo_unidade", "nome_unidade", "tipo_logradouro", "logradouro", "numero",
            "complemento", "bairro", "estado", "cidade", "cep", "interlocutor", "cpf_interlocutor",
            "rg_interlocutor", "ddd", "telefone", "ramal",
        )}
        dados["cnpj"] = dados["cnpj"].upper()
        dados["estado"] = dados["estado"].upper()
        if not (dados["cnpj"].isalnum() and len(dados["cnpj"]) <= 14):
            raise ValueError
        limites = {"codigo_unidade": 6, "nome_unidade": 26, "tipo_logradouro": 4, "logradouro": 50,
                   "numero": 6, "complemento": 10, "bairro": 15, "cidade": 25, "cep": 8,
                   "interlocutor": 50, "cpf_interlocutor": 11, "rg_interlocutor": 10, "ddd": 3,
                   "telefone": 9, "ramal": 5}
        for campo, limite in limites.items():
            if len(dados[campo]) > limite:
                raise ValueError
        if any(not dados[campo] for campo in ("codigo_unidade", "nome_unidade", "tipo_logradouro", "logradouro", "numero", "bairro", "cidade", "cep", "interlocutor")):
            raise ValueError
        if dados["estado"] not in ESTADOS or len(_digitos(dados["cep"])) != 8:
            raise ValueError
        if PedidoTicketUnidadeEntrega.query.filter_by(cnpj=dados["cnpj"], codigo_unidade=dados["codigo_unidade"]).first():
            raise ValueError
        for campo, tamanho in (("cpf_interlocutor", 11), ("ddd", 2), ("telefone", 8)):
            if dados[campo] and len(_digitos(dados[campo])) != tamanho and not (campo == "telefone" and len(_digitos(dados[campo])) == 9):
                raise ValueError
        dados["cep"] = _digitos(dados["cep"])
        for campo in ("cpf_interlocutor", "ddd", "telefone", "rg_interlocutor", "ramal", "numero", "codigo_unidade"):
            if dados[campo]:
                dados[campo] = _digitos(dados[campo])
        db.session.add(PedidoTicketUnidadeEntrega(**dados))
        db.session.commit()
        flash("Unidade de entrega cadastrada com sucesso.", "success")
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Não foi possível cadastrar. Confira os campos obrigatórios e os formatos informados.", "danger")
    return redirect(url_for("pedido_tiquete.index", aba="unidades"))


@pedido_tiquete_bp.route("/beneficiarios", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_beneficiario():
    _exigir_feature_ativa()
    try:
        empresa_id = int(request.form.get("empresa_pedido", ""))
        empresa = PedidoTicketEmpresa.query.filter_by(id=empresa_id, ativo=True).first()
        matricula = _digitos(request.form.get("matricula", ""))
        cpf = _digitos(request.form.get("cpf", ""))
        nome = request.form.get("nome", "").strip()
        nascimento = _data_form("data_nascimento")
        departamento = request.form.get("departamento", "").strip()
        unidade_id = int(request.form.get("unidade_entrega", ""))
        unidade = PedidoTicketUnidadeEntrega.query.filter_by(id=unidade_id).first()
        valor = Decimal(request.form.get("valor_mensal", "").replace(",", "."))
        parcelas_texto = _digitos(request.form.get("numero_parcelas", ""))
        parcelas = int(parcelas_texto) if parcelas_texto else None
        if not empresa or not unidade or unidade.cnpj != empresa.cnpj:
            raise ValueError
        if not (1 <= len(matricula) <= 12 and len(cpf) == 11 and 1 <= len(nome) <= 60):
            raise ValueError
        if nascimento > date.today() or not _idade_minima_atendida(nascimento, 14) or not departamento or len(departamento) > 50:
            raise ValueError
        if valor < 0:
            raise ValueError
        if PedidoTicketBeneficiario.query.filter_by(numero_pedido=empresa.numero_pedido, cpf=cpf).first():
            raise ValueError
        if parcelas is not None and parcelas < 1:
            raise ValueError
        db.session.add(PedidoTicketBeneficiario(numero_pedido=empresa.numero_pedido, matricula=matricula, cpf=cpf, nome=nome,
                                                data_nascimento=nascimento, departamento=departamento,
                                                unidade_entrega=f"{unidade.codigo_unidade} - {unidade.nome_unidade}", valor_mensal=valor,
                                                contrato_produto=f"{empresa.numero_contrato} - {empresa.produto}", numero_parcelas=parcelas))
        db.session.commit()
        flash("Beneficiário cadastrado com sucesso.", "success")
    except (ValueError, TypeError, InvalidOperation):
        db.session.rollback()
        flash("Não foi possível cadastrar. Confira os campos obrigatórios e os formatos informados.", "danger")
    return redirect(url_for("pedido_tiquete.index", aba="beneficiarios"))
