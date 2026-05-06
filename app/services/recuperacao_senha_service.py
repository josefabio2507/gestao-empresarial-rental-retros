import hashlib
import secrets
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import TokenRecuperacaoSenha, Usuario


def gerar_hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invalidar_tokens_usuario(usuario):
    agora = datetime.utcnow()

    tokens_ativos = TokenRecuperacaoSenha.query.filter(
        TokenRecuperacaoSenha.usuario_id == usuario.id,
        TokenRecuperacaoSenha.usado_em.is_(None),
        TokenRecuperacaoSenha.expira_em >= agora,
    ).all()

    for token in tokens_ativos:
        token.usado_em = agora


def gerar_token_recuperacao(usuario, ip=None, user_agent=None):
    invalidar_tokens_usuario(usuario)

    token = secrets.token_urlsafe(48)
    token_hash = gerar_hash_token(token)
    minutos_expiracao = current_app.config.get("RECUPERACAO_SENHA_EXPIRACAO_MINUTOS", 60)

    registro = TokenRecuperacaoSenha(
        usuario_id=usuario.id,
        token_hash=token_hash,
        expira_em=datetime.utcnow() + timedelta(minutes=minutos_expiracao),
        ip_solicitacao=ip,
        user_agent=user_agent,
    )

    db.session.add(registro)
    db.session.commit()

    return token, registro


def buscar_token_valido(token):
    if not token:
        return None, "Token inválido ou expirado."

    token_hash = gerar_hash_token(token)
    registro = TokenRecuperacaoSenha.query.filter_by(token_hash=token_hash).first()

    if not registro:
        return None, "Token inválido ou expirado."

    if registro.foi_usado:
        return None, "Este link já foi utilizado. Solicite uma nova recuperação de senha."

    if registro.expirou:
        return None, "Este link expirou. Solicite uma nova recuperação de senha."

    if not registro.usuario or not registro.usuario.ativo:
        return None, "Token inválido ou expirado."

    return registro, None


def redefinir_senha_por_token(token, nova_senha):
    registro, erro = buscar_token_valido(token)

    if erro:
        return False, erro, None

    usuario = Usuario.query.get(registro.usuario_id)

    if not usuario or not usuario.ativo:
        return False, "Token inválido ou expirado.", None

    agora = datetime.utcnow()
    usuario.definir_senha(nova_senha)
    usuario.precisa_trocar_senha = False
    registro.usado_em = agora

    outros_tokens = TokenRecuperacaoSenha.query.filter(
        TokenRecuperacaoSenha.usuario_id == usuario.id,
        TokenRecuperacaoSenha.id != registro.id,
        TokenRecuperacaoSenha.usado_em.is_(None),
    ).all()

    for token_antigo in outros_tokens:
        token_antigo.usado_em = agora

    db.session.commit()

    return True, "Senha redefinida com sucesso. Acesse o sistema com sua nova senha.", usuario
