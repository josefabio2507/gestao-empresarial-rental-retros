from datetime import date, timedelta
import hashlib
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import NamedTemporaryFile

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.decorators import module_permission_required
from app.extensions import db
from app.models import (
    Colaborador,
    Equipe,
    PedidoTicketPedido,
    PedidoTicketEvento,
    PedidoTicketBeneficiario,
    PedidoTicketCadastroBeneficiario,
    PedidoTicketEmpresa,
    PedidoTicketUnidadeEntrega,
)
from app.departamento_pessoal.pedido_tiquete.excel_service import gerar_planilha_pedido
from app.departamento_pessoal.pedido_tiquete.portal_service import PortalTicketError, enviar_planilha_para_portal
from app.services.permissoes_service import usuario_tem_permissao
from app.departamento_pessoal.colaboradores.services import formatar_cpf


pedido_tiquete_bp = Blueprint("pedido_tiquete", __name__)
PRODUTOS = ("TAE", "TRE", "TKE", "TFE")
LIMITE_BENEFICIARIOS_PEDIDO = 245
TRANSICOES_HISTORICO = {
    "rascunho": {"cancelado"},
    "enviando": {"processado", "rejeitado", "falha"},
    "enviado": {"processado", "rejeitado", "falha"},
    "falha": {"processado", "rejeitado", "rascunho"},
}
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


def _get_por_parametro(modelo, nome_parametro):
    registro_id = request.args.get(nome_parametro, type=int)
    return db.session.get(modelo, registro_id) if registro_id is not None else None


def _pode(acao):
    return usuario_tem_permissao(current_user, "departamento_pessoal", "pedido_tiquete", acao)


def _exigir_feature_ativa():
    if not current_app.config.get("PEDIDO_TICKET_ENABLED", False):
        abort(404)


def _registrar_evento(numero_pedido, tipo, descricao, *, pedido=None, status_anterior=None, status_novo=None, protocolo=None, arquivo_sha256=None, quantidade_beneficiarios=None, valor_total=None):
    db.session.add(PedidoTicketEvento(
        pedido_id=pedido.id if pedido else None,
        numero_pedido=numero_pedido,
        tipo=tipo,
        descricao=descricao,
        status_anterior=status_anterior,
        status_novo=status_novo,
        protocolo=protocolo,
        arquivo_sha256=arquivo_sha256,
        quantidade_beneficiarios=quantidade_beneficiarios,
        valor_total=valor_total,
        usuario_id=current_user.id if current_user.is_authenticated else None,
    ))


@pedido_tiquete_bp.route("/")
@module_permission_required("departamento_pessoal", "pedido_tiquete", "visualizar")
def index():
    _exigir_feature_ativa()
    abas = {"empresas", "unidades", "beneficiarios", "cadastro_beneficiarios", "novo_pedido", "pedidos"}
    aba = request.args.get("aba", "empresas")
    if aba not in abas:
        aba = "empresas"
    busca_colaborador = request.args.get("busca", "").strip()[:80]
    colaboradores = []
    cadastros_beneficiarios = []
    if aba in {"novo_pedido", "cadastro_beneficiarios"}:
        consulta_colaboradores = Colaborador.query.join(Equipe).filter(
            Colaborador.ativo.is_(True),
            Equipe.ativo.is_(True),
        )
        if busca_colaborador:
            termo = f"%{busca_colaborador}%"
            consulta_colaboradores = consulta_colaboradores.filter(or_(
                Colaborador.nome.ilike(termo),
                Colaborador.matricula.ilike(termo),
                Colaborador.cpf.ilike(termo),
            ))
        colaboradores = consulta_colaboradores.order_by(Colaborador.nome).limit(LIMITE_BENEFICIARIOS_PEDIDO).all()
        if aba == "cadastro_beneficiarios":
            cadastros_beneficiarios = PedidoTicketCadastroBeneficiario.query.join(Colaborador).order_by(Colaborador.nome, PedidoTicketCadastroBeneficiario.tipo_beneficio).limit(500).all()

    pedido_edicao = _get_por_parametro(PedidoTicketPedido, "pedido_id")
    if pedido_edicao and pedido_edicao.status != "rascunho":
        pedido_edicao = None
    empresas_para_pedido = PedidoTicketEmpresa.query.filter_by(ativo=True)
    if pedido_edicao:
        empresas_para_pedido = empresas_para_pedido.filter_by(numero_pedido=pedido_edicao.numero_pedido)
    empresas_para_pedido = empresas_para_pedido.order_by(PedidoTicketEmpresa.numero_pedido.desc(), PedidoTicketEmpresa.nome_empresa).limit(100).all()
    pedido_selecionado = _get_por_parametro(PedidoTicketPedido, "ver_pedido")
    beneficiarios_do_pedido = []
    colaboradores_no_pedido = set()
    if pedido_selecionado:
        beneficiarios_do_pedido = PedidoTicketBeneficiario.query.filter_by(
            pedido_id=pedido_selecionado.id
        ).order_by(PedidoTicketBeneficiario.nome).all()
    if pedido_edicao:
        colaboradores_no_pedido = {
            row[0] for row in PedidoTicketBeneficiario.query.with_entities(
                PedidoTicketBeneficiario.colaborador_id
            ).filter_by(pedido_id=pedido_edicao.id).all() if row[0] is not None
        }

    unidades_ativas = PedidoTicketUnidadeEntrega.query.filter_by(ativo=True).order_by(PedidoTicketUnidadeEntrega.nome_unidade).limit(245).all()
    return render_template(
        "departamento_pessoal/pedido_tiquete/index.html",
        aba=aba,
        empresas=PedidoTicketEmpresa.query.order_by(PedidoTicketEmpresa.criado_em.desc()).limit(100).all(),
        empresas_ativas=PedidoTicketEmpresa.query.filter_by(ativo=True).order_by(PedidoTicketEmpresa.numero_pedido.desc(), PedidoTicketEmpresa.nome_empresa).limit(100).all(),
        empresas_para_pedido=empresas_para_pedido,
        editar_empresa=_get_por_parametro(PedidoTicketEmpresa, "editar_empresa"),
        empresas_unidades=PedidoTicketEmpresa.query.order_by(PedidoTicketEmpresa.nome_empresa, PedidoTicketEmpresa.numero_contrato).limit(100).all(),
        empresas_unidades_ativas=PedidoTicketEmpresa.query.filter_by(ativo=True).order_by(PedidoTicketEmpresa.nome_empresa, PedidoTicketEmpresa.numero_contrato).limit(100).all(),
        unidades=PedidoTicketUnidadeEntrega.query.order_by(PedidoTicketUnidadeEntrega.nome_unidade).limit(100).all(),
        unidades_ativas=unidades_ativas,
        editar_unidade=_get_por_parametro(PedidoTicketUnidadeEntrega, "editar_unidade"),
        beneficiarios=PedidoTicketBeneficiario.query.order_by(PedidoTicketBeneficiario.nome).limit(100).all(),
        pedidos=[linha[0] for linha in PedidoTicketBeneficiario.query.with_entities(
            PedidoTicketBeneficiario.numero_pedido
        ).distinct().order_by(PedidoTicketBeneficiario.numero_pedido.desc()).limit(100).all()],
        pedidos_ticket=PedidoTicketPedido.query.order_by(PedidoTicketPedido.criado_em.desc()).limit(100).all(),
        pedido_edicao=pedido_edicao,
        pedido_selecionado=pedido_selecionado,
        beneficiarios_do_pedido=beneficiarios_do_pedido,
        colaboradores=colaboradores,
        colaboradores_cadastro=colaboradores if aba == "cadastro_beneficiarios" else [],
        cadastros_beneficiarios=cadastros_beneficiarios,
        formatar_cpf=formatar_cpf,
        busca_colaborador=busca_colaborador,
        colaboradores_no_pedido=colaboradores_no_pedido,
        unidades_pedido=unidades_ativas,
        produtos=PRODUTOS,
        estados=ESTADOS,
        pode_criar=_pode("criar"),
        pode_editar=_pode("editar"),
        limite_beneficiarios=LIMITE_BENEFICIARIOS_PEDIDO,
        data_hoje=date.today().isoformat(),
        ticket_upload_habilitado=current_app.config.get("PEDIDO_TICKET_UPLOAD_ENABLED", False),
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

    pedido = PedidoTicketPedido.query.filter_by(numero_pedido=numero_pedido).first()
    arquivo.seek(0)
    arquivo_sha256 = hashlib.sha256(arquivo.getvalue()).hexdigest()
    arquivo.seek(0)
    _registrar_evento(
        numero_pedido,
        "arquivo_gerado",
        "Planilha Excel gerada para download.",
        pedido=pedido,
        status_novo="arquivo_gerado",
        arquivo_sha256=arquivo_sha256,
        quantidade_beneficiarios=len(beneficiarios),
        valor_total=sum((item.valor_mensal for item in beneficiarios), Decimal("0.00")),
    )
    db.session.commit()
    resposta = send_file(
        arquivo,
        as_attachment=True,
        download_name=f"pedido_tiquete_{numero_pedido}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        max_age=0,
    )
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


@pedido_tiquete_bp.route("/pedidos/<int:pedido_id>/enviar-ticket", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def enviar_pedido_ticket(pedido_id):
    _exigir_feature_ativa()
    if not current_app.config.get("PEDIDO_TICKET_UPLOAD_ENABLED", False):
        abort(404)
    if request.form.get("confirmacao_envio") != "sim":
        abort(400)

    pedido = db.session.get(PedidoTicketPedido, pedido_id)
    if not pedido or pedido.status != "rascunho":
        abort(404)

    empresas = PedidoTicketEmpresa.query.filter_by(
        numero_pedido=pedido.numero_pedido
    ).order_by(PedidoTicketEmpresa.id).all()
    beneficiarios = PedidoTicketBeneficiario.query.filter_by(
        pedido_id=pedido.id
    ).order_by(PedidoTicketBeneficiario.id).all()
    if not empresas or not beneficiarios:
        flash("O pedido precisa ter contrato e beneficiários antes do envio.", "warning")
        return redirect(url_for("pedido_tiquete.index", aba="pedidos"))

    cnpjs = {empresa.cnpj for empresa in empresas}
    unidades = PedidoTicketUnidadeEntrega.query.filter(
        PedidoTicketUnidadeEntrega.cnpj.in_(cnpjs)
    ).order_by(PedidoTicketUnidadeEntrega.id).all()
    modelo = Path(__file__).with_name("modelo_pedido_ticket.xlsx")
    if not modelo.is_file():
        flash("O modelo oficial do Excel não está disponível.", "danger")
        return redirect(url_for("pedido_tiquete.index", aba="pedidos"))

    try:
        arquivo = gerar_planilha_pedido(
            modelo, pedido.numero_pedido, empresas, unidades, beneficiarios
        )
        arquivo_sha256 = hashlib.sha256(arquivo.getvalue()).hexdigest()
        arquivo.seek(0)
        with NamedTemporaryFile(suffix=".xlsx", delete=False) as temporario:
            temporario.write(arquivo.read())
            caminho = Path(temporario.name)

        simulacao = current_app.config.get("PEDIDO_TICKET_SIMULATION", False)
        if not simulacao:
            atualizado = PedidoTicketPedido.query.filter_by(
                id=pedido.id, status="rascunho"
            ).update({"status": "enviando"}, synchronize_session=False)
            if not atualizado:
                db.session.rollback()
                flash("Este pedido já está sendo enviado ou não está mais em rascunho.", "warning")
                return redirect(url_for("pedido_tiquete.index", aba="pedidos"))
            _registrar_evento(
                pedido.numero_pedido,
                "envio_iniciado",
                "Envio confirmado pelo operador e iniciado no Portal Ticket.",
                pedido=pedido,
                status_anterior="rascunho",
                status_novo="enviando",
                arquivo_sha256=arquivo_sha256,
                quantidade_beneficiarios=pedido.quantidade_beneficiarios,
                valor_total=pedido.valor_total,
            )
            db.session.commit()

        resultado = enviar_planilha_para_portal(
            caminho,
            operador_id=str(current_user.get_id()),
            confirmado=True,
            settings=current_app.config,
        )
        if resultado.status == "upload_iniciado":
            pedido.status = "enviado"
            _registrar_evento(
                pedido.numero_pedido,
                "upload_iniciado",
                "Portal Ticket confirmou o início do upload; processamento ainda pendente.",
                pedido=pedido,
                status_anterior="enviando",
                status_novo="enviado",
                protocolo=resultado.protocolo,
                arquivo_sha256=arquivo_sha256,
                quantidade_beneficiarios=pedido.quantidade_beneficiarios,
                valor_total=pedido.valor_total,
            )
            db.session.commit()
            flash(
                "Upload iniciado no Portal Ticket. O processamento do pedido ainda precisa ser confirmado no portal.",
                "info",
            )
        else:
            _registrar_evento(
                pedido.numero_pedido,
                "envio_simulado" if resultado.status == "simulado" else "retorno_portal",
                resultado.mensagem[:255],
                pedido=pedido,
                status_anterior="rascunho" if simulacao else "enviando",
                status_novo=resultado.status[:20],
                protocolo=resultado.protocolo,
                quantidade_beneficiarios=pedido.quantidade_beneficiarios,
                valor_total=pedido.valor_total,
            )
            db.session.commit()
            flash(resultado.mensagem, "info")
        return redirect(url_for("pedido_tiquete.index", aba="pedidos"))
    except PortalTicketError as erro:
        db.session.rollback()
        pedido_atual = db.session.get(PedidoTicketPedido, pedido_id)
        if pedido_atual and pedido_atual.status == "enviando":
            pedido_atual.status = "falha"
            _registrar_evento(
                pedido_atual.numero_pedido,
                "falha_envio",
                f"Portal Ticket interrompeu o envio ({type(erro).__name__}).",
                pedido=pedido_atual,
                status_anterior="enviando",
                status_novo="falha",
            )
            db.session.commit()
        flash(str(erro), "warning")
        return redirect(url_for("pedido_tiquete.index", aba="pedidos"))
    except ValueError as erro:
        db.session.rollback()
        pedido_atual = db.session.get(PedidoTicketPedido, pedido_id)
        if pedido_atual and pedido_atual.status == "enviando":
            pedido_atual.status = "falha"
            _registrar_evento(
                pedido_atual.numero_pedido,
                "falha_envio",
                f"Portal Ticket interrompeu o envio ({type(erro).__name__}).",
                pedido=pedido_atual,
                status_anterior="enviando",
                status_novo="falha",
            )
            db.session.commit()
        flash(str(erro), "warning")
        return redirect(url_for("pedido_tiquete.index", aba="pedidos"))
    finally:
        if "caminho" in locals():
            caminho.unlink(missing_ok=True)


def _proximo_numero_pedido(empresa):
    existentes = PedidoTicketEmpresa.query.filter(
        PedidoTicketEmpresa.id != empresa.id
    ).with_entities(
        PedidoTicketEmpresa.id,
        PedidoTicketEmpresa.numero_pedido,
    ).all()
    numeros = [
        int(numero) for _, numero in existentes
        if str(numero).isdigit()
    ]
    maior_numero = max(numeros, default=0)
    maior_id = max((registro_id for registro_id, _ in existentes), default=0)
    deslocamento = max(maior_numero - maior_id, 0)
    proximo = deslocamento + empresa.id
    if proximo > 9_999_999_999:
        raise ValueError("O limite de numeração de pedidos foi atingido.")
    return f"{proximo:010d}"


def _dados_empresa_form(empresa=None):
    numero_pedido = empresa.numero_pedido if empresa else None
    cnpj = request.form.get("cnpj", "").strip().upper()
    nome = request.form.get("nome_empresa", "").strip()
    contrato = _digitos(request.form.get("numero_contrato", ""))
    produto = request.form.get("produto", "").strip().upper()
    data_credito = _data_form("data_credito")

    if not (1 <= len(cnpj) <= 14 and cnpj.isalnum()):
        raise ValueError("Confira o CNPJ/CPF da empresa.")
    if not nome or len(nome) > 26 or not (1 <= len(contrato) <= 10) or produto not in PRODUTOS:
        raise ValueError("Confira o nome, o contrato e o produto da empresa.")

    duplicado = PedidoTicketEmpresa.query.filter_by(
        cnpj=cnpj, numero_contrato=contrato, produto=produto, data_credito=data_credito
    )
    if empresa:
        duplicado = duplicado.filter(PedidoTicketEmpresa.id != empresa.id)
    if duplicado.first():
        raise ValueError("Esse contrato e produto já foram cadastrados para a mesma data de crédito.")

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

    dados = {
        "cnpj": cnpj,
        "nome_empresa": nome,
        "numero_contrato": contrato,
        "produto": produto,
        "data_credito": data_credito,
        "ativo": True if empresa is None else request.form.get("ativo") == "on",
    }
    if empresa:
        dados["numero_pedido"] = empresa.numero_pedido
    return dados


@pedido_tiquete_bp.route("/empresas", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_empresa():
    _exigir_feature_ativa()
    try:
        empresa = PedidoTicketEmpresa(numero_pedido="", **_dados_empresa_form())
        db.session.add(empresa)
        db.session.flush()
        empresa.numero_pedido = _proximo_numero_pedido(empresa)
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

def _dados_unidade_form(unidade=None):
    empresa_id = request.form.get("empresa_id", type=int)
    empresa = db.session.get(PedidoTicketEmpresa, empresa_id) if empresa_id else None
    dados = {campo: request.form.get(campo, "").strip() for campo in (
        "codigo_unidade", "nome_unidade", "tipo_logradouro", "logradouro", "numero",
        "complemento", "bairro", "estado", "cidade", "cep", "interlocutor", "cpf_interlocutor",
        "rg_interlocutor", "ddd", "telefone", "ramal",
    )}
    dados["estado"] = dados["estado"].upper()
    if not empresa or (not empresa.ativo and (unidade is None or empresa.cnpj != unidade.cnpj)):
        raise ValueError("Selecione uma empresa ou contrato ativo.")
    limites = {"codigo_unidade": 6, "nome_unidade": 26, "tipo_logradouro": 4, "logradouro": 50,
               "numero": 6, "complemento": 10, "bairro": 15, "cidade": 25, "cep": 8,
               "interlocutor": 50, "cpf_interlocutor": 11, "rg_interlocutor": 10, "ddd": 3,
               "telefone": 9, "ramal": 5}
    for campo, limite in limites.items():
        if len(dados[campo]) > limite:
            raise ValueError(f"O campo {campo} excede o limite da planilha.")
    obrigatorios = ("codigo_unidade", "nome_unidade", "tipo_logradouro", "logradouro", "numero", "bairro", "cidade", "cep", "interlocutor")
    if any(not dados[campo] for campo in obrigatorios):
        raise ValueError("Preencha os campos obrigatórios.")
    if not dados["codigo_unidade"].isalnum() or dados["estado"] not in ESTADOS or len(_digitos(dados["cep"])) != 8:
        raise ValueError("Confira o código da unidade, o estado e o CEP.")
    duplicada = PedidoTicketUnidadeEntrega.query.filter_by(cnpj=empresa.cnpj, codigo_unidade=dados["codigo_unidade"])
    if unidade:
        duplicada = duplicada.filter(PedidoTicketUnidadeEntrega.id != unidade.id)
    if duplicada.first():
        raise ValueError("Já existe uma unidade com esse código para a empresa.")
    for campo, tamanho in (("cpf_interlocutor", 11), ("ddd", 2)):
        if dados[campo] and len(_digitos(dados[campo])) != tamanho:
            raise ValueError(f"Confira o formato do campo {campo}.")
    if dados["telefone"] and len(_digitos(dados["telefone"])) not in (8, 9):
        raise ValueError("Confira o telefone do interlocutor.")
    dados["cnpj"] = empresa.cnpj
    dados["ativo"] = request.form.get("ativo") == "on" if unidade else True
    dados["cep"] = _digitos(dados["cep"])
    for campo in ("cpf_interlocutor", "ddd", "telefone", "rg_interlocutor", "ramal", "numero"):
        if dados[campo]:
            dados[campo] = _digitos(dados[campo])
    return dados


@pedido_tiquete_bp.route("/unidades", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_unidade():
    _exigir_feature_ativa()
    try:
        db.session.add(PedidoTicketUnidadeEntrega(**_dados_unidade_form()))
        db.session.commit()
        flash("Unidade de entrega cadastrada com sucesso.", "success")
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Não foi possível cadastrar. Confira a empresa, os campos e a unicidade do código.", "danger")
    return redirect(url_for("pedido_tiquete.index", aba="unidades"))


@pedido_tiquete_bp.route("/unidades/<int:unidade_id>/editar", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "editar")
def editar_unidade(unidade_id):
    _exigir_feature_ativa()
    unidade = db.session.get(PedidoTicketUnidadeEntrega, unidade_id)
    if not unidade:
        abort(404)
    if request.method == "GET":
        return redirect(url_for("pedido_tiquete.index", aba="unidades", editar_unidade=unidade.id))
    try:
        dados = _dados_unidade_form(unidade)
        chave_mudou = (
            dados["cnpj"] != unidade.cnpj
            or dados["codigo_unidade"] != unidade.codigo_unidade
            or dados["nome_unidade"] != unidade.nome_unidade
        )
        referencia_antiga = f"{unidade.codigo_unidade} - {unidade.nome_unidade}"
        beneficiario_vinculado = PedidoTicketBeneficiario.query.filter_by(unidade_entrega=referencia_antiga).first()
        if unidade.ativo and not dados["ativo"] and beneficiario_vinculado:
            raise ValueError("Esta unidade está vinculada a beneficiários e não pode ser desativada.")
        if chave_mudou and beneficiario_vinculado:
            raise ValueError("Não altere empresa, código ou nome: há beneficiários vinculados a esta unidade.")
        for campo, valor in dados.items():
            setattr(unidade, campo, valor)
        db.session.commit()
        flash("Unidade de entrega atualizada com sucesso.", "success")
    except (ValueError, TypeError):
        db.session.rollback()
        flash("Não foi possível atualizar. Confira os dados, os vínculos e a unicidade do código.", "danger")
    return redirect(url_for("pedido_tiquete.index", aba="unidades"))


@pedido_tiquete_bp.route("/unidades/<int:unidade_id>/status", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "editar")
def alternar_status_unidade(unidade_id):
    _exigir_feature_ativa()
    unidade = db.session.get(PedidoTicketUnidadeEntrega, unidade_id)
    if not unidade:
        abort(404)
    if unidade.ativo:
        referencia = f"{unidade.codigo_unidade} - {unidade.nome_unidade}"
        if PedidoTicketBeneficiario.query.filter_by(unidade_entrega=referencia).first():
            flash("Esta unidade está vinculada a beneficiários e não pode ser desativada.", "warning")
            return redirect(url_for("pedido_tiquete.index", aba="unidades"))
    unidade.ativo = not unidade.ativo
    db.session.commit()
    flash("Unidade ativada." if unidade.ativo else "Unidade desativada.", "success")
    return redirect(url_for("pedido_tiquete.index", aba="unidades"))


@pedido_tiquete_bp.route("/pedidos", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_pedido_rascunho():
    _exigir_feature_ativa()
    pedido = None
    try:
        empresa_id = request.form.get("empresa_id", type=int)
        unidade_id = request.form.get("unidade_id", type=int)
        empresa = db.session.get(PedidoTicketEmpresa, empresa_id) if empresa_id else None
        unidade = db.session.get(PedidoTicketUnidadeEntrega, unidade_id) if unidade_id else None
        if not empresa or not empresa.ativo:
            raise ValueError("Selecione uma empresa ou contrato ativo.")
        if not unidade or not unidade.ativo or unidade.cnpj != empresa.cnpj:
            raise ValueError("Selecione uma unidade ativa vinculada à empresa escolhida.")

        ids_texto = request.form.getlist("colaborador_ids")
        if not ids_texto:
            raise ValueError("Selecione ao menos um colaborador.")
        try:
            ids_recebidos = [int(item) for item in ids_texto]
        except (ValueError, TypeError):
            raise ValueError("A seleção de colaboradores contém um identificador inválido.")
        if len(ids_recebidos) != len(set(ids_recebidos)):
            raise ValueError("Há colaboradores repetidos na seleção.")
        if len(ids_recebidos) > LIMITE_BENEFICIARIOS_PEDIDO:
            raise ValueError(f"O modelo aceita no máximo {LIMITE_BENEFICIARIOS_PEDIDO} beneficiários por pedido.")

        colaboradores = Colaborador.query.join(Equipe).filter(
            Colaborador.id.in_(ids_recebidos),
            Colaborador.ativo.is_(True),
            Equipe.ativo.is_(True),
        ).all()
        if len(colaboradores) != len(ids_recebidos):
            raise ValueError("Um ou mais colaboradores não estão ativos ou não existem mais no cadastro.")
        pedido_id = request.form.get("pedido_id", type=int)
        rascunho_existente = False
        if pedido_id:
            pedido = db.session.get(PedidoTicketPedido, pedido_id)
            if not pedido or pedido.status != "rascunho":
                raise ValueError("O rascunho não existe ou não está mais aberto.")
            if pedido.numero_pedido != empresa.numero_pedido:
                raise ValueError("A empresa selecionada não pertence ao número deste rascunho.")
            rascunho_existente = True
        else:
            pedido = PedidoTicketPedido.query.filter_by(numero_pedido=empresa.numero_pedido).first()
            if pedido and pedido.status != "rascunho":
                raise ValueError("Este pedido já foi encerrado e não pode receber novos beneficiários.")
            rascunho_existente = pedido is not None

        ja_vinculados = PedidoTicketBeneficiario.query.filter_by(
            numero_pedido=empresa.numero_pedido
        ).with_entities(PedidoTicketBeneficiario.cpf).all()
        cpfs_existentes = {cpf for (cpf,) in ja_vinculados}
        novos_itens = []
        for colaborador in colaboradores:
            matricula = (colaborador.matricula or "").strip()
            cpf = _digitos(colaborador.cpf or "")
            nome = (colaborador.nome or "").strip()
            departamento = (colaborador.equipe.nome or "").strip()
            if not (1 <= len(matricula) <= 12 and matricula.isalnum()):
                raise ValueError(f"Corrija a matrícula de {nome or 'um colaborador'} no cadastro antes de continuar.")
            if len(cpf) != 11 or not (1 <= len(nome) <= 60):
                raise ValueError(f"Corrija CPF ou nome de {nome or 'um colaborador'} no cadastro antes de continuar.")
            if not departamento or len(departamento) > 50:
                raise ValueError(f"A equipe de {nome} precisa ter um nome de até 50 caracteres.")
            if cpf in cpfs_existentes:
                raise ValueError(f"{nome} já está incluído no pedido {empresa.numero_pedido}.")
            try:
                nascimento = date.fromisoformat(request.form.get(f"data_nascimento_{colaborador.id}", ""))
            except ValueError:
                raise ValueError(f"Informe a data de nascimento de {nome}.")
            if nascimento > date.today():
                raise ValueError(f"A data de nascimento de {nome} não pode estar no futuro.")
            try:
                valor = Decimal(request.form.get(f"valor_mensal_{colaborador.id}", "").replace(",", "."))
                valor_centavos = valor.quantize(Decimal("0.01"))
            except (InvalidOperation, AttributeError):
                raise ValueError(f"Informe um valor mensal válido para {nome}.")
            if valor < 0 or valor != valor_centavos or valor > Decimal("9999999999.99"):
                raise ValueError(f"Confira o valor mensal informado para {nome}.")
            parcelas_texto = request.form.get(f"numero_parcelas_{colaborador.id}", "").strip()
            if parcelas_texto and not parcelas_texto.isdigit():
                raise ValueError(f"Confira o número de parcelas de {nome}.")
            parcelas = int(parcelas_texto) if parcelas_texto else None
            if parcelas is not None and parcelas < 1:
                raise ValueError(f"Confira o número de parcelas de {nome}.")
            novos_itens.append({
                "pedido_id": None,
                "colaborador_id": colaborador.id,
                "numero_pedido": empresa.numero_pedido,
                "matricula": matricula,
                "cpf": cpf,
                "nome": nome,
                "data_nascimento": nascimento,
                "departamento": departamento,
                "unidade_entrega": f"{unidade.codigo_unidade} - {unidade.nome_unidade}",
                "valor_mensal": valor_centavos,
                "contrato_produto": f"{empresa.numero_contrato} - {empresa.produto}",
                "numero_parcelas": parcelas,
            })

        if pedido:
            quantidade_atual = PedidoTicketBeneficiario.query.filter_by(pedido_id=pedido.id).count()
            if quantidade_atual + len(novos_itens) > LIMITE_BENEFICIARIOS_PEDIDO:
                raise ValueError(f"O pedido ultrapassaria o limite de {LIMITE_BENEFICIARIOS_PEDIDO} beneficiários do modelo.")
        else:
            pedido = PedidoTicketPedido(
                numero_pedido=empresa.numero_pedido,
                status="rascunho",
                criado_por_usuario_id=current_user.id,
            )
            db.session.add(pedido)
            db.session.flush()

        for dados in novos_itens:
            dados["pedido_id"] = pedido.id
            db.session.add(PedidoTicketBeneficiario(**dados))
        db.session.flush()
        itens = PedidoTicketBeneficiario.query.filter_by(pedido_id=pedido.id).all()
        pedido.quantidade_beneficiarios = len(itens)
        pedido.valor_total = sum((item.valor_mensal for item in itens), Decimal("0.00"))
        _registrar_evento(
            pedido.numero_pedido,
            "rascunho_atualizado" if rascunho_existente else "rascunho_criado",
            f"Rascunho {'atualizado' if rascunho_existente else 'criado'} com {pedido.quantidade_beneficiarios} beneficiário(s).",
            pedido=pedido,
            status_anterior="rascunho" if rascunho_existente else None,
            status_novo="rascunho",
            quantidade_beneficiarios=pedido.quantidade_beneficiarios,
            valor_total=pedido.valor_total,
        )
        db.session.commit()
        flash("Rascunho salvo. Confira colaboradores, quantidade e valor total antes da próxima etapa.", "success")
        return redirect(url_for("pedido_tiquete.index", aba="pedidos", ver_pedido=pedido.id))
    except (ValueError, TypeError, InvalidOperation) as erro:
        db.session.rollback()
        flash(str(erro) or "Não foi possível salvar o rascunho. Confira os dados selecionados.", "danger")
    except IntegrityError:
        db.session.rollback()
        flash("O pedido mudou durante o salvamento. Atualize a tela e tente novamente.", "danger")
    destino = {"aba": "novo_pedido"}
    if pedido and pedido.id:
        destino["pedido_id"] = pedido.id
    return redirect(url_for("pedido_tiquete.index", **destino))


@pedido_tiquete_bp.route("/cadastro-beneficiarios", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_cadastro_beneficiario():
    _exigir_feature_ativa()
    colaborador_id = request.form.get("colaborador_id", type=int)
    tipo_beneficio = request.form.get("tipo_beneficio", "").strip().upper()
    colaborador = db.session.get(Colaborador, colaborador_id) if colaborador_id else None
    if not colaborador or not colaborador.ativo or not colaborador.equipe or not colaborador.equipe.ativo:
        flash("Selecione um colaborador ativo do Cadastro de Colaboradores.", "danger")
        return redirect(url_for("pedido_tiquete.index", aba="cadastro_beneficiarios"))
    if tipo_beneficio not in PRODUTOS:
        flash("Selecione um tipo de benefício válido.", "danger")
        return redirect(url_for("pedido_tiquete.index", aba="cadastro_beneficiarios"))

    cadastro = PedidoTicketCadastroBeneficiario.query.filter_by(
        colaborador_id=colaborador.id,
        tipo_beneficio=tipo_beneficio,
    ).first()
    if cadastro:
        flash("Este colaborador já possui cadastro para esse benefício. Reative o existente se estiver inativo.", "warning")
        return redirect(url_for("pedido_tiquete.index", aba="cadastro_beneficiarios"))

    db.session.add(PedidoTicketCadastroBeneficiario(colaborador_id=colaborador.id, tipo_beneficio=tipo_beneficio))
    try:
        db.session.commit()
        flash("Beneficiário cadastrado com sucesso.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("O cadastro já existe. Atualize a página e confira a lista.", "warning")
    return redirect(url_for("pedido_tiquete.index", aba="cadastro_beneficiarios"))


@pedido_tiquete_bp.route("/cadastro-beneficiarios/<int:cadastro_id>/status", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "editar")
def alternar_status_cadastro_beneficiario(cadastro_id):
    _exigir_feature_ativa()
    cadastro = db.session.get(PedidoTicketCadastroBeneficiario, cadastro_id)
    if not cadastro:
        abort(404)
    cadastro.ativo = not cadastro.ativo
    db.session.commit()
    flash("Cadastro de benefício ativado." if cadastro.ativo else "Cadastro de benefício inativado.", "success")
    return redirect(url_for("pedido_tiquete.index", aba="cadastro_beneficiarios"))


@pedido_tiquete_bp.route("/beneficiarios", methods=["POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "criar")
def criar_beneficiario():
    _exigir_feature_ativa()
    flash("Os beneficiários agora são selecionados do cadastro de colaboradores na aba Novo Pedido.", "warning")
    return redirect(url_for("pedido_tiquete.index", aba="novo_pedido"))

@pedido_tiquete_bp.route("/pedidos/<int:pedido_id>/historico", methods=["GET", "POST"])
@module_permission_required("departamento_pessoal", "pedido_tiquete", "visualizar")
def historico_pedido(pedido_id):
    _exigir_feature_ativa()
    pedido = db.session.get(PedidoTicketPedido, pedido_id)
    if not pedido:
        abort(404)
    if request.method == "POST":
        if not _pode("editar"):
            abort(403)
        status_novo = request.form.get("status", "").strip().lower()
        protocolo = request.form.get("protocolo", "").strip() or None
        descricao = request.form.get("descricao", "").strip()
        if status_novo not in TRANSICOES_HISTORICO.get(pedido.status, set()):
            flash("A atualização não é permitida a partir do status atual do pedido.", "warning")
        elif status_novo == "rascunho" and request.form.get("portal_sem_processamento") != "sim":
            flash("Para reabrir o envio, confirme que o pedido não foi processado no Portal Ticket.", "warning")
        elif len(descricao) > 255 or (protocolo and len(protocolo) > 100):
            flash("Confira a descrição (até 255 caracteres) e o protocolo (até 100 caracteres).", "danger")
        else:
            status_anterior = pedido.status
            pedido.status = status_novo
            _registrar_evento(
                pedido.numero_pedido,
                "retorno_portal" if status_novo != "cancelado" else "pedido_cancelado",
                descricao or f"Status atualizado manualmente para {status_novo}.",
                pedido=pedido,
                status_anterior=status_anterior,
                status_novo=status_novo,
                protocolo=protocolo,
                quantidade_beneficiarios=pedido.quantidade_beneficiarios,
                valor_total=pedido.valor_total,
            )
            db.session.commit()
            flash("Histórico do pedido atualizado.", "success")
        return redirect(url_for("pedido_tiquete.historico_pedido", pedido_id=pedido_id))
    tipo_filtro = request.args.get("tipo", "").strip()[:30]
    status_filtro = request.args.get("status", "").strip()[:20]
    consulta = PedidoTicketEvento.query.filter_by(pedido_id=pedido.id)
    if tipo_filtro:
        consulta = consulta.filter_by(tipo=tipo_filtro)
    if status_filtro:
        consulta = consulta.filter(
            (PedidoTicketEvento.status_anterior == status_filtro)
            | (PedidoTicketEvento.status_novo == status_filtro)
        )
    eventos = consulta.order_by(
        PedidoTicketEvento.criado_em.desc(), PedidoTicketEvento.id.desc()
    ).limit(200).all()
    return render_template(
        "departamento_pessoal/pedido_tiquete/historico.html",
        pedido=pedido,
        eventos=eventos,
        pode_editar=_pode("editar"),
        status_opcoes=TRANSICOES_HISTORICO.get(pedido.status, set()),
        tipo_filtro=tipo_filtro,
        status_filtro=status_filtro,
    )
