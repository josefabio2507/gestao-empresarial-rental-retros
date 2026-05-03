from app.extensions import db
from app.models import Usuario, NivelAcesso


def normalizar_email(email):
    return email.strip().lower() if email else ""


def buscar_usuarios():
    return (
        Usuario.query
        .join(NivelAcesso)
        .order_by(Usuario.nome.asc())
        .all()
    )


def buscar_usuario_por_id(usuario_id):
    return Usuario.query.get(usuario_id)


def buscar_niveis_ativos():
    return NivelAcesso.query.filter_by(ativo=True).order_by(NivelAcesso.nome.asc()).all()


def email_ja_existe(email, usuario_id_ignorado=None):
    email_normalizado = normalizar_email(email)

    query = Usuario.query.filter_by(email=email_normalizado)

    if usuario_id_ignorado:
        query = query.filter(Usuario.id != usuario_id_ignorado)

    return query.first() is not None


def criar_usuario(nome, email, senha, nivel_acesso_id, ativo=True):
    nome = nome.strip()
    email = normalizar_email(email)

    if not nome:
        return False, "Nome é obrigatório."

    if not email:
        return False, "E-mail é obrigatório."

    if not senha:
        return False, "Senha inicial é obrigatória."

    if not nivel_acesso_id:
        return False, "Nível de acesso é obrigatório."

    if email_ja_existe(email):
        return False, "E-mail já cadastrado."

    usuario = Usuario(
        nome=nome,
        email=email,
        nivel_acesso_id=nivel_acesso_id,
        ativo=ativo,
        precisa_trocar_senha=True
    )
    usuario.definir_senha(senha)

    db.session.add(usuario)
    db.session.commit()

    return True, "Usuário criado com sucesso."


def atualizar_usuario(usuario, nome, email, nivel_acesso_id, ativo=True, nova_senha=None):
    nome = nome.strip()
    email = normalizar_email(email)

    if not nome:
        return False, "Nome é obrigatório."

    if not email:
        return False, "E-mail é obrigatório."

    if not nivel_acesso_id:
        return False, "Nível de acesso é obrigatório."

    if email_ja_existe(email, usuario_id_ignorado=usuario.id):
        return False, "E-mail já cadastrado para outro usuário."

    usuario.nome = nome
    usuario.email = email
    usuario.nivel_acesso_id = nivel_acesso_id
    usuario.ativo = ativo

    if nova_senha:
        usuario.definir_senha(nova_senha)
        usuario.precisa_trocar_senha = True

    db.session.commit()

    return True, "Usuário atualizado com sucesso."


def contar_administradores_ativos():
    return (
        Usuario.query
        .join(NivelAcesso)
        .filter(
            Usuario.ativo.is_(True),
            NivelAcesso.slug == "administrador"
        )
        .count()
    )


def pode_inativar_usuario(usuario_alvo, usuario_logado):
    if usuario_alvo.id == usuario_logado.id:
        return False, "Você não pode inativar seu próprio usuário."

    if usuario_alvo.nivel_acesso and usuario_alvo.nivel_acesso.slug == "administrador":
        total_admins_ativos = contar_administradores_ativos()

        if total_admins_ativos <= 1:
            return False, "Não é possível inativar o último administrador ativo."

    return True, ""


def alterar_status_usuario(usuario_alvo, usuario_logado):
    if usuario_alvo.ativo:
        permitido, mensagem = pode_inativar_usuario(usuario_alvo, usuario_logado)

        if not permitido:
            return False, mensagem

        usuario_alvo.ativo = False
        db.session.commit()
        return True, "Usuário inativado com sucesso."

    usuario_alvo.ativo = True
    db.session.commit()
    return True, "Usuário ativado com sucesso."