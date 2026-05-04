import csv
import io
import re
import unicodedata

from sqlalchemy import func

from app.extensions import db
from app.models import Colaborador, Equipe
from app.utils.mascaras_lgpd import (
    MENSAGEM_TELEFONE_INVALIDO,
    normalizar_telefone_brasil,
)


CABECALHO_ESPERADO = [
    "matricula",
    "nome",
    "cpf",
    "email",
    "telefone",
    "cargo",
    "equipe",
    "ativo",
]

CABECALHO_OBRIGATORIO = [
    "matricula",
    "nome",
    "cpf",
    "equipe",
]

VALORES_VERDADEIROS = {"sim", "s", "1", "true", "ativo"}
VALORES_FALSOS = {"nao", "n", "0", "false", "inativo"}


def normalizar_texto(valor):
    if valor is None:
        return ""

    return str(valor).strip()


def remover_acentos(valor):
    texto = normalizar_texto(valor)
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere))


def normalizar_slug(valor):
    texto = remover_acentos(valor).lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")


def normalizar_cpf(valor):
    return re.sub(r"\D", "", normalizar_texto(valor))


def normalizar_telefone(valor):
    return normalizar_telefone_brasil(valor)


def normalizar_email(valor):
    email = normalizar_texto(valor).lower()
    return email or None


def interpretar_ativo(valor):
    texto = normalizar_slug(valor)

    if not texto:
        return True

    if texto in VALORES_VERDADEIROS:
        return True

    if texto in VALORES_FALSOS:
        return False

    return True


def buscar_equipe_por_nome_ou_slug(nome_equipe):
    nome = normalizar_texto(nome_equipe)
    slug = normalizar_slug(nome)

    if not nome:
        return None

    equipe = (
        Equipe.query
        .filter(func.lower(func.trim(Equipe.nome)) == nome.lower())
        .first()
    )

    if equipe:
        return equipe

    return Equipe.query.filter(func.lower(Equipe.slug) == slug).first()


def decodificar_csv(arquivo_csv):
    conteudo = arquivo_csv.read()

    if isinstance(conteudo, str):
        return conteudo

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue

    return conteudo.decode("latin-1", errors="replace")


def detectar_dialeto_csv(texto_csv):
    amostra = texto_csv[:2048]

    try:
        return csv.Sniffer().sniff(amostra, delimiters=",;")
    except csv.Error:
        primeira_linha = amostra.splitlines()[0] if amostra.splitlines() else ""
        delimitador = ";" if primeira_linha.count(";") >= primeira_linha.count(",") else ","

        class Dialeto(csv.excel):
            delimiter = delimitador

        return Dialeto


def criar_resumo():
    return {
        "total_linhas": 0,
        "criados": 0,
        "atualizados": 0,
        "rejeitados": 0,
        "erros": [],
    }


def validar_cabecalho(cabecalho):
    if not cabecalho:
        return False

    colunas = [normalizar_texto(coluna).lower() for coluna in cabecalho]
    return all(coluna in colunas for coluna in CABECALHO_OBRIGATORIO)


def normalizar_linha(linha):
    return {
        normalizar_texto(chave).lower(): valor
        for chave, valor in linha.items()
        if chave is not None
    }


def rejeitar_linha(resumo, numero_linha, mensagem):
    resumo["rejeitados"] += 1
    resumo["erros"].append(f"Linha {numero_linha}: {mensagem}")


def validar_linha(linha, numero_linha, resumo, cpfs_por_matricula):
    matricula = normalizar_texto(linha.get("matricula"))
    nome = normalizar_texto(linha.get("nome"))
    cpf = normalizar_cpf(linha.get("cpf"))
    equipe_nome = normalizar_texto(linha.get("equipe"))

    if not matricula:
        rejeitar_linha(resumo, numero_linha, "Matrícula é obrigatória.")
        return None

    if not nome:
        rejeitar_linha(resumo, numero_linha, "Nome é obrigatório.")
        return None

    if not cpf:
        rejeitar_linha(resumo, numero_linha, "CPF é obrigatório.")
        return None

    if len(cpf) != 11:
        rejeitar_linha(resumo, numero_linha, "CPF inválido. Deve conter 11 dígitos.")
        return None

    matricula_com_mesmo_cpf = cpfs_por_matricula.get(cpf)

    if matricula_com_mesmo_cpf and matricula_com_mesmo_cpf != matricula:
        rejeitar_linha(resumo, numero_linha, "CPF já informado para outra matrícula neste arquivo.")
        return None

    if not equipe_nome:
        rejeitar_linha(resumo, numero_linha, "Equipe é obrigatória.")
        return None

    equipe = buscar_equipe_por_nome_ou_slug(equipe_nome)

    if not equipe:
        rejeitar_linha(resumo, numero_linha, f"Equipe não encontrada: {equipe_nome}")
        return None

    if not equipe.ativo:
        rejeitar_linha(resumo, numero_linha, f"Equipe inativa: {equipe_nome}")
        return None

    colaborador_com_cpf = Colaborador.query.filter_by(cpf=cpf).first()

    if colaborador_com_cpf and colaborador_com_cpf.matricula != matricula:
        rejeitar_linha(resumo, numero_linha, "CPF já cadastrado para outra matrícula.")
        return None

    try:
        telefone = normalizar_telefone(linha.get("telefone"))
    except ValueError:
        rejeitar_linha(resumo, numero_linha, MENSAGEM_TELEFONE_INVALIDO)
        return None

    cpfs_por_matricula[cpf] = matricula

    return {
        "matricula": matricula,
        "nome": nome,
        "cpf": cpf,
        "email": normalizar_email(linha.get("email")),
        "telefone": telefone,
        "cargo": normalizar_texto(linha.get("cargo")) or None,
        "equipe_id": equipe.id,
        "ativo": interpretar_ativo(linha.get("ativo")),
    }


def salvar_colaborador(dados):
    colaborador = Colaborador.query.filter_by(matricula=dados["matricula"]).first()
    criado = colaborador is None

    if criado:
        colaborador = Colaborador(matricula=dados["matricula"])
        db.session.add(colaborador)

    colaborador.nome = dados["nome"]
    colaborador.cpf = dados["cpf"]
    colaborador.email = dados["email"]
    colaborador.telefone = dados["telefone"]
    colaborador.cargo = dados["cargo"]
    colaborador.equipe_id = dados["equipe_id"]
    colaborador.ativo = dados["ativo"]

    return criado


def importar_colaboradores_csv(arquivo_csv):
    resumo = criar_resumo()
    cpfs_por_matricula = {}

    try:
        texto_csv = decodificar_csv(arquivo_csv)
        dialeto = detectar_dialeto_csv(texto_csv)
        leitor = csv.DictReader(io.StringIO(texto_csv), dialect=dialeto)

        if not validar_cabecalho(leitor.fieldnames):
            resumo["erros"].append(
                "Cabeçalho inválido. Colunas obrigatórias: " + ",".join(CABECALHO_OBRIGATORIO)
            )
            return resumo

        for indice, linha in enumerate(leitor, start=2):
            linha = normalizar_linha(linha)

            if not any(normalizar_texto(valor) for valor in linha.values()):
                continue

            resumo["total_linhas"] += 1
            dados = validar_linha(linha, indice, resumo, cpfs_por_matricula)

            if not dados:
                continue

            criado = salvar_colaborador(dados)

            if criado:
                resumo["criados"] += 1
            else:
                resumo["atualizados"] += 1

        db.session.commit()
        return resumo

    except Exception:
        db.session.rollback()
        resumo["erros"].append(
            "Erro crítico ao processar o arquivo. Verifique o CSV e tente novamente."
        )
        return resumo
