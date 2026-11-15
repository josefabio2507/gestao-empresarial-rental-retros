from flask import Blueprint, render_template, url_for
from flask_login import login_required

departamento_pessoal_bp = Blueprint("departamento_pessoal", __name__)


@departamento_pessoal_bp.route("/")
@login_required
def index():
    submodulos = [
        {"nome": "Colaboradores", "descricao": "Cadastro e consulta de colaboradores.", "url": url_for("colaboradores.index")},
        {"nome": "Documentos", "descricao": "Documentos e holerites de colaboradores.", "url": url_for("documentos.index")},
        {"nome": "Férias", "descricao": "Programação e acompanhamento de férias.", "url": url_for("ferias.index")},
        {"nome": "Pedido de Refeição", "descricao": "Gestão de pedidos de refeição.", "url": url_for("pedido_refeicoes.index")},
        {"nome": "Vale-Transporte", "descricao": "Pedidos e gestão de vale-transporte.", "url": url_for("vale_transporte.index")},
        {"nome": "Pedido Tícket", "descricao": "Cadastro e acompanhamento de pedidos de tíquete.", "url": url_for("pedido_tiquete.index")},
    ]
    return render_template("departamento_pessoal/index.html", submodulos=submodulos)


@departamento_pessoal_bp.route("/status")
@login_required
def status():
    return "Departamento Pessoal online."