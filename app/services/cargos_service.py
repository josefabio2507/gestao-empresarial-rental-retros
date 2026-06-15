from sqlalchemy import func

from app.extensions import db
from app.models import Cargo


def normalizar_nome_cargo(nome):
    return nome.strip() if nome else ""


def buscar_cargos(nome=None):
    query = Cargo.query
    nome = normalizar_nome_cargo(nome)

    if nome:
        query = query.filter(Cargo.nome.ilike(f"%{nome}%"))

    return query.order_by(Cargo.nome.asc()).all()


def buscar_cargos_ativos():
    return (
        Cargo.query
        .filter_by(ativo=True)
        .order_by(Cargo.nome.asc())
        .all()
    )


def buscar_cargo_por_id(cargo_id):
    return db.session.get(Cargo, cargo_id)


def nome_cargo_ja_existe(nome, cargo_id_ignorado=None):
    nome = normalizar_nome_cargo(nome)

    if not nome:
        return False

    query = Cargo.query.filter(
        func.lower(func.trim(Cargo.nome)) == nome.lower()
    )

    if cargo_id_ignorado is not None:
        query = query.filter(Cargo.id != cargo_id_ignorado)

    return query.first() is not None


def criar_cargo(nome):
    nome = normalizar_nome_cargo(nome)

    if not nome:
        return False, "Nome do cargo é obrigatório.", None

    if nome_cargo_ja_existe(nome):
        return False, "Já existe um cargo cadastrado com este nome.", None

    cargo = Cargo(nome=nome, ativo=True)
    db.session.add(cargo)
    db.session.commit()

    return True, "Cargo criado com sucesso.", cargo


def atualizar_cargo(cargo, nome):
    nome = normalizar_nome_cargo(nome)

    if not nome:
        return False, "Nome do cargo é obrigatório."

    if nome_cargo_ja_existe(nome, cargo_id_ignorado=cargo.id):
        return False, "Já existe um cargo cadastrado com este nome."

    cargo.nome = nome
    db.session.commit()

    return True, "Cargo atualizado com sucesso."


def alterar_status_cargo(cargo):
    cargo.ativo = not cargo.ativo
    db.session.commit()

    if cargo.ativo:
        return True, "Cargo reativado com sucesso."

    return True, "Cargo inativado com sucesso."
