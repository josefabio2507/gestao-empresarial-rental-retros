from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.services.permissoes_service import usuario_tem_permissao

operacao_bp = Blueprint("operacao", __name__)


@operacao_bp.route("/")
@login_required
def index():
    pode_acessar_gestao_veiculos = usuario_tem_permissao(
        current_user,
        "operacao",
        "gestao_veiculos_epgs",
        "visualizar",
    )

    return render_template(
        "operacao/index.html",
        pode_acessar_gestao_veiculos=pode_acessar_gestao_veiculos,
    )


@operacao_bp.route("/status")
@login_required
def status():
    return "Operação online."
