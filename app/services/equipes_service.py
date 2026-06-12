import re
import unicodedata

from sqlalchemy import func

from app.extensions import db
from app.models import Equipe


def normalizar_nome_equipe(nome):
    return nome.strip() if nome else ""


def gerar_slug_equipe(nome):
    texto = unicodedata.normalize("NFKD", nome)
    texto = "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )
    slug = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    return slug or "equipe"


def buscar_equipes(nome=None):
    query = Equipe.query
    nome = normalizar_nome_equipe(nome)

    if nome:
        query = query.filter(Equipe.nome.ilike(f"%{nome}%"))

    return query.order_by(Equipe.nome.asc()).all()


def buscar_equipe_por_id(equipe_id):
    return Equipe.query.get(equipe_id)


def nome_equipe_ja_existe(nome, equipe_id_ignorado=None):
    nome = normalizar_nome_equipe(nome)

    if not nome:
        return False

    query = Equipe.query.filter(func.lower(Equipe.nome) == nome.lower())

    if equipe_id_ignorado is not None:
        query = query.filter(Equipe.id != equipe_id_ignorado)

    return query.first() is not None


def gerar_slug_unico(nome, equipe_id_ignorado=None):
    slug_base = gerar_slug_equipe(nome)
    slug = slug_base
    sufixo = 2

    while True:
        query = Equipe.query.filter_by(slug=slug)

        if equipe_id_ignorado is not None:
            query = query.filter(Equipe.id != equipe_id_ignorado)

        if query.first() is None:
            return slug

        slug = f"{slug_base}-{sufixo}"
        sufixo += 1


def criar_equipe(nome):
    nome = normalizar_nome_equipe(nome)

    if not nome:
        return False, "Nome da equipe é obrigatório.", None

    if nome_equipe_ja_existe(nome):
        return False, "Já existe uma equipe cadastrada com este nome.", None

    equipe = Equipe(
        nome=nome,
        slug=gerar_slug_unico(nome),
        ativo=True,
    )
    db.session.add(equipe)
    db.session.commit()

    return True, "Equipe criada com sucesso.", equipe


def atualizar_equipe(equipe, nome):
    nome = normalizar_nome_equipe(nome)

    if not nome:
        return False, "Nome da equipe é obrigatório."

    if nome_equipe_ja_existe(nome, equipe_id_ignorado=equipe.id):
        return False, "Já existe uma equipe cadastrada com este nome."

    equipe.nome = nome
    equipe.slug = gerar_slug_unico(nome, equipe_id_ignorado=equipe.id)
    db.session.commit()

    return True, "Equipe atualizada com sucesso."


def alterar_status_equipe(equipe):
    equipe.ativo = not equipe.ativo
    db.session.commit()

    if equipe.ativo:
        return True, "Equipe reativada com sucesso."

    return True, "Equipe inativada com sucesso."
