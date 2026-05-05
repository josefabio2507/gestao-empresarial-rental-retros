from datetime import datetime, time

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models import LogAcesso, Usuario


def registrar_log(acao, descricao=None, usuario=None, rota=None):
    try:
        usuario_log = usuario

        if usuario_log is None and has_request_context():
            if getattr(current_user, "is_authenticated", False):
                usuario_log = current_user

        usuario_id = getattr(usuario_log, "id", None)
        rota_log = rota
        ip = None
        user_agent = None

        if has_request_context():
            rota_log = rota_log or request.path
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)

            if ip and "," in ip:
                ip = ip.split(",", 1)[0].strip()

            user_agent = request.user_agent.string if request.user_agent else None

        log = LogAcesso(
            usuario_id=usuario_id,
            acao=acao,
            descricao=descricao,
            rota=rota_log,
            ip=ip,
            user_agent=user_agent,
        )

        db.session.add(log)
        db.session.commit()
        return True

    except Exception:
        db.session.rollback()
        return False


def buscar_logs(usuario_id=None, acao=None, data_inicial=None, data_final=None, limite=500):
    query = LogAcesso.query.outerjoin(Usuario)

    if usuario_id:
        query = query.filter(LogAcesso.usuario_id == usuario_id)

    if acao:
        query = query.filter(LogAcesso.acao.ilike(f"%{acao.strip()}%"))

    if data_inicial:
        try:
            data_inicio = datetime.strptime(data_inicial, "%Y-%m-%d")
            query = query.filter(LogAcesso.criado_em >= data_inicio)
        except ValueError:
            pass

    if data_final:
        try:
            data_fim = datetime.combine(
                datetime.strptime(data_final, "%Y-%m-%d").date(),
                time.max,
            )
            query = query.filter(LogAcesso.criado_em <= data_fim)
        except ValueError:
            pass

    return (
        query
        .order_by(LogAcesso.criado_em.desc())
        .limit(limite)
        .all()
    )


def buscar_usuarios_com_logs():
    return (
        Usuario.query
        .join(LogAcesso)
        .distinct()
        .order_by(Usuario.nome.asc())
        .all()
    )
