import smtplib
from email.message import EmailMessage

from flask import current_app


def smtp_configurado():
    return bool(
        current_app.config.get("MAIL_SERVER")
        and current_app.config.get("MAIL_DEFAULT_SENDER")
    )


def enviar_email(destinatario, assunto, corpo_texto):
    if not smtp_configurado():
        base_url = current_app.config.get("BASE_URL", "")

        if base_url.startswith("http://127.0.0.1") or base_url.startswith("http://localhost"):
            print("[RECUPERACAO_SENHA_LOCAL]")
            print(f"Destinatario: {destinatario}")
            print(corpo_texto)

        return False, "SMTP não configurado."

    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    mensagem["To"] = destinatario
    mensagem.set_content(corpo_texto)

    servidor = current_app.config["MAIL_SERVER"]
    porta = current_app.config["MAIL_PORT"]
    usuario = current_app.config.get("MAIL_USERNAME")
    senha = current_app.config.get("MAIL_PASSWORD")
    usar_tls = current_app.config.get("MAIL_USE_TLS", True)
    usar_ssl = current_app.config.get("MAIL_USE_SSL", False)

    try:
        if usar_ssl:
            smtp = smtplib.SMTP_SSL(servidor, porta, timeout=20)
        else:
            smtp = smtplib.SMTP(servidor, porta, timeout=20)

        with smtp:
            if usar_tls and not usar_ssl:
                smtp.starttls()

            if usuario and senha:
                smtp.login(usuario, senha)

            smtp.send_message(mensagem)

        return True, None

    except Exception:
        return False, "Falha ao enviar e-mail."


def enviar_email_recuperacao_senha(usuario, link_recuperacao):
    assunto = "Recuperação de senha - Gestão Empresarial Rental Retros"
    corpo = (
        f"Olá, {usuario.nome}.\n\n"
        "Recebemos uma solicitação de recuperação de senha para sua conta.\n\n"
        "Para redefinir sua senha, acesse o link abaixo:\n"
        f"{link_recuperacao}\n\n"
        "Este link é válido por tempo limitado e pode ser utilizado apenas uma vez.\n\n"
        "Se você não solicitou esta recuperação, ignore este e-mail.\n\n"
        "Rental Retros"
    )

    return enviar_email(usuario.email, assunto, corpo)
