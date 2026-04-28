from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.models import Usuario


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
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
        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("main.inicio"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("auth.login"))