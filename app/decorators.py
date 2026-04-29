from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Faça login para acessar o sistema.", "warning")
            return redirect(url_for("auth.login"))

        if not current_user.nivel_acesso:
            flash("Você não tem permissão para acessar esta área.", "danger")
            return redirect(url_for("main.acesso_negado"))

        if current_user.nivel_acesso.slug != "administrador":
            flash("Você não tem permissão para acessar esta área.", "danger")
            return redirect(url_for("main.acesso_negado"))

        return func(*args, **kwargs)

    return wrapper

def module_permission_required(departamento_slug, modulo_slug, acao="visualizar"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Faça login para acessar o sistema.", "warning")
                return redirect(url_for("auth.login"))

            from app.services.permissoes_service import usuario_tem_permissao

            if not usuario_tem_permissao(
                current_user,
                departamento_slug,
                modulo_slug,
                acao,
            ):
                flash("Você não tem permissão para acessar esta área.", "danger")
                return redirect(url_for("main.acesso_negado"))

            return func(*args, **kwargs)

        return wrapper

    return decorator