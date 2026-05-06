from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.models import Usuario
from app.extensions import db
from app.services.email_service import enviar_email_recuperacao_senha
from app.services.logs_service import registrar_log
from app.services.recuperacao_senha_service import (
    buscar_token_valido,
    gerar_token_recuperacao,
    redefinir_senha_por_token,
)


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
        registrar_log(
            "login_sucesso",
            f"Login realizado com sucesso. Usuario ID: {usuario.id}.",
            usuario=usuario,
        )

        if usuario.precisa_trocar_senha:
            return redirect(url_for("auth.trocar_senha"))

        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("main.inicio"))

    return render_template("login.html")

MENSAGEM_RECUPERACAO_NEUTRA = (
    "Se o e-mail informado estiver cadastrado, enviaremos as instruções de recuperação."
)


def obter_ip_requisicao():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    if ip and "," in ip:
        ip = ip.split(",", 1)[0].strip()

    return ip


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        registrar_log(
            "recuperacao_senha_solicitada",
            "Solicitação de recuperação de senha recebida.",
        )

        usuario = Usuario.query.filter_by(email=email, ativo=True).first() if email else None

        if usuario:
            token, _registro = gerar_token_recuperacao(
                usuario,
                ip=obter_ip_requisicao(),
                user_agent=request.user_agent.string if request.user_agent else None,
            )
            link_recuperacao = (
                f"{current_app.config.get('BASE_URL')}"
                f"{url_for('auth.redefinir_senha', token=token)}"
            )

            enviar_email_recuperacao_senha(usuario, link_recuperacao)
            registrar_log(
                "recuperacao_senha_token_gerado",
                f"Token de recuperação gerado para usuário ID {usuario.id}.",
                usuario=usuario,
            )

        flash(MENSAGEM_RECUPERACAO_NEUTRA, "info")
        return redirect(url_for("auth.esqueci_senha"))

    return render_template("recuperar_senha.html")


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))

    registro, erro = buscar_token_valido(token)

    if erro:
        registrar_log(
            "recuperacao_senha_token_invalido",
            "Tentativa de uso de token inválido, expirado ou já utilizado.",
        )
        return render_template("redefinir_senha.html", token_valido=False, erro=erro)

    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nova_senha or not confirmar_senha:
            flash("Informe a nova senha e a confirmação.", "danger")
            return redirect(url_for("auth.redefinir_senha", token=token))

        if len(nova_senha) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("auth.redefinir_senha", token=token))

        if nova_senha != confirmar_senha:
            flash("A nova senha e a confirmação não conferem.", "danger")
            return redirect(url_for("auth.redefinir_senha", token=token))

        sucesso, mensagem, usuario = redefinir_senha_por_token(token, nova_senha)

        if sucesso:
            registrar_log(
                "recuperacao_senha_redefinida",
                f"Senha redefinida via recuperação para usuário ID {usuario.id}.",
                usuario=usuario,
            )
            flash(mensagem, "success")
            return redirect(url_for("auth.login"))

        flash(mensagem, "danger")
        return redirect(url_for("auth.redefinir_senha", token=token))

    return render_template(
        "redefinir_senha.html",
        token_valido=True,
        erro=None,
        usuario=registro.usuario,
    )

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
    usuario = current_user
    registrar_log(
        "logout",
        f"Logout realizado. Usuario ID: {usuario.id}.",
        usuario=usuario,
    )
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
