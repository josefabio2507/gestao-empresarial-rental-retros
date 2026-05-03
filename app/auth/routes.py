from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import Usuario
from app.extensions import db


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if getattr(current_user, "precisa_trocar_senha", False):
            return redirect(url_for("auth.trocar_senha"))

        return redirect(url_for("main.inicio"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario or not usuario.verificar_senha(senha):
            flash("E-mail ou senha inválidos.", "danger")
            return redirect(url_for("auth.login"))

        if not usuario.ativo:
            flash("Usuário inativo. Procure o administrador.", "warning")
            return redirect(url_for("auth.login"))

        login_user(usuario)

        if usuario.precisa_trocar_senha:
            return redirect(url_for("auth.trocar_senha"))

        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("main.inicio"))

    return render_template("login.html")

@auth_bp.before_app_request
def bloquear_navegacao_com_troca_pendente():
    if not current_user.is_authenticated:
        return None

    if not getattr(current_user, "precisa_trocar_senha", False):
        return None

    rotas_liberadas = [
        "auth.trocar_senha",
        "auth.logout",
        "static",
    ]

    endpoint_atual = request.endpoint or ""

    if endpoint_atual in rotas_liberadas or endpoint_atual.startswith("static"):
        return None

    return redirect(url_for("auth.trocar_senha"))

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("auth.login"))

@auth_bp.route("/trocar-senha", methods=["GET", "POST"])
@login_required
def trocar_senha():
    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nova_senha or not confirmar_senha:
            flash("Informe a nova senha e a confirmação.", "danger")
            return redirect(url_for("auth.trocar_senha"))

        if len(nova_senha) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("auth.trocar_senha"))

        if nova_senha != confirmar_senha:
            flash("A nova senha e a confirmação não conferem.", "danger")
            return redirect(url_for("auth.trocar_senha"))

        current_user.definir_senha(nova_senha)
        current_user.precisa_trocar_senha = False

        db.session.commit()

        flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("main.inicio"))

    return render_template("trocar_senha.html")

@auth_bp.route("/minha-senha", methods=["GET", "POST"])
@login_required
def minha_senha():
    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not senha_atual:
            flash("Informe a senha atual.", "danger")
            return redirect(url_for("auth.minha_senha"))

        if not current_user.verificar_senha(senha_atual):
            flash("Senha atual incorreta.", "danger")
            return redirect(url_for("auth.minha_senha"))

        if not nova_senha or not confirmar_senha:
            flash("Informe a nova senha e a confirmação.", "danger")
            return redirect(url_for("auth.minha_senha"))

        if len(nova_senha) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("auth.minha_senha"))

        if nova_senha != confirmar_senha:
            flash("A nova senha e a confirmação não conferem.", "danger")
            return redirect(url_for("auth.minha_senha"))

        current_user.definir_senha(nova_senha)
        current_user.precisa_trocar_senha = False

        db.session.commit()

        flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("main.inicio"))

    return render_template("minha_senha.html")