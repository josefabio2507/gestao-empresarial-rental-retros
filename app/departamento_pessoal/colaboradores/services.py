import re

from sqlalchemy import or_

from app.extensions import db
from app.models import Colaborador, Equipe
from app.utils.mascaras_lgpd import (
    MENSAGEM_TELEFONE_INVALIDO,
    formatar_cpf_completo,
    formatar_telefone_completo,
    normalizar_telefone_brasil,
)


def limpar_numeros(valor):
    if not valor:
        return ""

    return re.sub(r"\D", "", valor)


def limpar_cpf(cpf):
    return limpar_numeros(cpf)


def limpar_telefone(telefone):
    return limpar_numeros(telefone)


def formatar_cpf(cpf):
    return formatar_cpf_completo(cpf)


def formatar_telefone(telefone):
    return formatar_telefone_completo(telefone)


def normalizar_email(email):
    return email.strip().lower() if email else ""


def buscar_equipes_ativas():
    return (
        Equipe.query
        .filter_by(ativo=True)
        .order_by(Equipe.nome.asc())
        .all()
    )


def buscar_colaborador_por_id(colaborador_id):
    return Colaborador.query.get(colaborador_id)


def buscar_colaboradores(filtro_texto=None, equipe_id=None):
    query = Colaborador.query.join(Equipe)

    if filtro_texto:
        filtro = filtro_texto.strip()
        filtro_numerico = limpar_numeros(filtro)

        condicoes = [
            Colaborador.nome.ilike(f"%{filtro}%"),
            Colaborador.matricula.ilike(f"%{filtro}%"),
        ]

        if filtro_numerico:
            condicoes.append(Colaborador.cpf.ilike(f"%{filtro_numerico}%"))

        query = query.filter(or_(*condicoes))

    if equipe_id:
        query = query.filter(Colaborador.equipe_id == equipe_id)

    return query.order_by(Colaborador.nome.asc()).all()


def matricula_ja_existe(matricula, colaborador_id_ignorado=None):
    matricula = matricula.strip()

    query = Colaborador.query.filter_by(matricula=matricula)

    if colaborador_id_ignorado:
        query = query.filter(Colaborador.id != colaborador_id_ignorado)

    return query.first() is not None


def cpf_ja_existe(cpf, colaborador_id_ignorado=None):
    cpf = limpar_cpf(cpf)

    query = Colaborador.query.filter_by(cpf=cpf)

    if colaborador_id_ignorado:
        query = query.filter(Colaborador.id != colaborador_id_ignorado)

    return query.first() is not None


def validar_dados_colaborador(
    matricula,
    nome,
    cpf,
    equipe_id,
    telefone=None,
    colaborador_id_ignorado=None
):
    matricula = matricula.strip()
    nome = nome.strip()
    cpf_limpo = limpar_cpf(cpf)

    if not matricula:
        return False, "Matrícula é obrigatória."

    if matricula_ja_existe(matricula, colaborador_id_ignorado):
        return False, "Matrícula já cadastrada."

    if not nome:
        return False, "Nome é obrigatório."

    if not cpf_limpo:
        return False, "CPF é obrigatório."

    if len(cpf_limpo) != 11:
        return False, "CPF deve conter 11 números."

    if cpf_ja_existe(cpf_limpo, colaborador_id_ignorado):
        return False, "CPF já cadastrado."

    if not equipe_id:
        return False, "Equipe é obrigatória."

    equipe = Equipe.query.filter_by(id=equipe_id, ativo=True).first()

    if not equipe:
        return False, "Equipe inválida ou inativa."

    try:
        normalizar_telefone_brasil(telefone)
    except ValueError:
        return False, MENSAGEM_TELEFONE_INVALIDO

    return True, ""


def criar_colaborador(
    matricula,
    nome,
    cpf,
    email,
    telefone,
    cargo,
    equipe_id,
    ativo=True
):
    valido, mensagem = validar_dados_colaborador(
        matricula=matricula,
        nome=nome,
        cpf=cpf,
        equipe_id=equipe_id,
        telefone=telefone,
    )

    if not valido:
        return False, mensagem

    colaborador = Colaborador(
        matricula=matricula.strip(),
        nome=nome.strip(),
        cpf=limpar_cpf(cpf),
        email=normalizar_email(email),
        telefone=normalizar_telefone_brasil(telefone),
        cargo=cargo.strip() if cargo else "",
        equipe_id=equipe_id,
        ativo=ativo,
    )

    db.session.add(colaborador)
    db.session.commit()

    return True, "Colaborador criado com sucesso."


def atualizar_colaborador(
    colaborador,
    matricula,
    nome,
    cpf,
    email,
    telefone,
    cargo,
    equipe_id,
    ativo=True
):
    valido, mensagem = validar_dados_colaborador(
        matricula=matricula,
        nome=nome,
        cpf=cpf,
        equipe_id=equipe_id,
        telefone=telefone,
        colaborador_id_ignorado=colaborador.id,
    )

    if not valido:
        return False, mensagem

    colaborador.matricula = matricula.strip()
    colaborador.nome = nome.strip()
    colaborador.cpf = limpar_cpf(cpf)
    colaborador.email = normalizar_email(email)
    colaborador.telefone = normalizar_telefone_brasil(telefone)
    colaborador.cargo = cargo.strip() if cargo else ""
    colaborador.equipe_id = equipe_id
    colaborador.ativo = ativo

    db.session.commit()

    return True, "Colaborador atualizado com sucesso."


def alterar_status_colaborador(colaborador):
    colaborador.ativo = not colaborador.ativo
    db.session.commit()

    if colaborador.ativo:
        return True, "Colaborador ativado com sucesso."

    return True, "Colaborador inativado com sucesso."
