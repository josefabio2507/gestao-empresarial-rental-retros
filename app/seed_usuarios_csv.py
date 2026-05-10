import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path

from sqlalchemy import func

from app import create_app
from app.extensions import db
from app.models import Colaborador, NivelAcesso, Usuario


CAMINHO_PADRAO_CSV = Path("instance/imports/cadastro_usuarios.CSV")
CAMPOS_OBRIGATORIOS = {
    "nome",
    "email",
    "nivel_acesso_id",
    "ativo",
    "precisa_trocar_senha",
    "colaborador_id",
}
VALORES_VERDADEIROS = {"1", "s", "sim", "true", "ativo", "yes", "y"}
VALORES_FALSOS = {"0", "n", "nao", "não", "false", "inativo", "no"}


def normalizar_email(valor):
    return (valor or "").strip().lower()


def interpretar_booleano(valor, padrao=True):
    texto = (valor or "").strip().lower()

    if not texto:
        return padrao

    if texto in VALORES_VERDADEIROS:
        return True

    if texto in VALORES_FALSOS:
        return False

    raise ValueError(f"Valor booleano inválido: {valor}")


def converter_inteiro(valor, campo):
    try:
        return int((valor or "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"{campo} inválido.")


def ler_conteudo_csv(caminho_csv):
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return caminho_csv.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "csv",
        b"",
        0,
        1,
        "Não foi possível ler o arquivo CSV com utf-8-sig, utf-8 ou latin-1.",
    )


def carregar_linhas_csv(caminho_csv):
    conteudo = ler_conteudo_csv(caminho_csv)
    leitor = csv.DictReader(StringIO(conteudo), delimiter=";")

    if not leitor.fieldnames:
        raise ValueError("CSV sem cabeçalho.")

    campos = {campo.strip() for campo in leitor.fieldnames}
    campos_ausentes = CAMPOS_OBRIGATORIOS - campos

    if campos_ausentes:
        campos_formatados = ", ".join(sorted(campos_ausentes))
        raise ValueError(f"CSV sem colunas obrigatórias: {campos_formatados}.")

    return list(leitor)


def carregar_colaboradores_por_email():
    colaboradores = (
        Colaborador.query
        .filter(Colaborador.email.isnot(None))
        .all()
    )
    colaboradores_por_email = defaultdict(list)

    for colaborador in colaboradores:
        email = normalizar_email(colaborador.email)

        if email:
            colaboradores_por_email[email].append(colaborador)

    return colaboradores_por_email


def usuario_existente_por_email(email):
    return (
        Usuario.query
        .filter(func.lower(Usuario.email) == email)
        .first()
    )


def nivel_acesso_existe(nivel_acesso_id):
    return NivelAcesso.query.filter_by(id=nivel_acesso_id).first() is not None


def colaborador_ja_vinculado(colaborador_id, usuario_id_ignorado=None):
    query = Usuario.query.filter(
        Usuario.colaborador_id == colaborador_id,
        Usuario.ativo.is_(True),
    )

    if usuario_id_ignorado:
        query = query.filter(Usuario.id != usuario_id_ignorado)

    return (
        query.first()
        is not None
    )


def resolver_colaborador_por_email(email, colaboradores_por_email, usuario_id_ignorado=None):
    colaboradores = colaboradores_por_email.get(email, [])

    if not colaboradores:
        return None, "sem_colaborador"

    if len(colaboradores) > 1:
        return None, "conflito_email_colaborador"

    colaborador = colaboradores[0]

    if not getattr(colaborador, "ativo", True):
        return None, "colaborador_inativo"

    if colaborador_ja_vinculado(colaborador.id, usuario_id_ignorado=usuario_id_ignorado):
        return None, "colaborador_ja_vinculado"

    return colaborador, "vinculado"


def atualizar_vinculo_usuario_existente(usuario, email, colaboradores_por_email):
    if usuario.colaborador_id:
        return {
            "usuario": usuario,
            "criado": False,
            "existente": True,
            "status_vinculo": "vinculo_preservado",
        }

    colaborador, status_vinculo = resolver_colaborador_por_email(
        email,
        colaboradores_por_email,
        usuario_id_ignorado=usuario.id,
    )

    if colaborador:
        usuario.colaborador_id = colaborador.id
        status_vinculo = "usuario_existente_vinculado"

    return {
        "usuario": usuario,
        "criado": False,
        "existente": True,
        "status_vinculo": status_vinculo,
    }


def processar_linha_usuario(linha, senha_padrao, colaboradores_por_email):
    nome = (linha.get("nome") or "").strip()
    email = normalizar_email(linha.get("email"))
    nivel_acesso_id = converter_inteiro(linha.get("nivel_acesso_id"), "nivel_acesso_id")
    ativo = interpretar_booleano(linha.get("ativo"), padrao=True)
    precisa_trocar_senha = interpretar_booleano(
        linha.get("precisa_trocar_senha"),
        padrao=True,
    )

    if not nome:
        raise ValueError("Nome é obrigatório.")

    if not email:
        raise ValueError("E-mail é obrigatório.")

    usuario_existente = usuario_existente_por_email(email)

    if usuario_existente:
        return atualizar_vinculo_usuario_existente(
            usuario_existente,
            email,
            colaboradores_por_email,
        )

    if not nivel_acesso_existe(nivel_acesso_id):
        raise ValueError("Nível de acesso não encontrado.")

    colaborador, status_vinculo = resolver_colaborador_por_email(
        email,
        colaboradores_por_email,
    )

    usuario = Usuario(
        nome=nome,
        email=email,
        nivel_acesso_id=nivel_acesso_id,
        colaborador_id=colaborador.id if colaborador else None,
        ativo=ativo,
        precisa_trocar_senha=precisa_trocar_senha,
    )
    usuario.definir_senha(senha_padrao)
    db.session.add(usuario)

    if status_vinculo == "vinculado":
        status_vinculo = "novo_usuario_vinculado"

    return {
        "usuario": usuario,
        "criado": True,
        "existente": False,
        "status_vinculo": status_vinculo,
    }


def montar_resumo():
    return {
        "total_linhas": 0,
        "usuarios_criados": 0,
        "usuarios_existentes": 0,
        "novos_usuarios_vinculados": 0,
        "usuarios_existentes_vinculados": 0,
        "usuarios_com_vinculo_preservado": 0,
        "usuarios_sem_colaborador": 0,
        "conflitos_colaborador_email": 0,
        "colaboradores_ja_vinculados": 0,
        "linhas_ignoradas": 0,
        "emails_sem_colaborador": [],
        "erros": [],
        "status_vinculo": Counter(),
    }


def importar_usuarios_csv(caminho_csv, senha_padrao):
    caminho_csv = Path(caminho_csv)

    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {caminho_csv}")

    linhas = carregar_linhas_csv(caminho_csv)
    colaboradores_por_email = carregar_colaboradores_por_email()
    resumo = montar_resumo()
    resumo["total_linhas"] = len(linhas)

    try:
        for indice, linha in enumerate(linhas, start=2):
            try:
                resultado = processar_linha_usuario(
                    linha,
                    senha_padrao,
                    colaboradores_por_email,
                )
                usuario = resultado["usuario"]
                status_vinculo = resultado["status_vinculo"]

                if resultado["existente"]:
                    resumo["usuarios_existentes"] += 1

                if resultado["criado"]:
                    resumo["usuarios_criados"] += 1

                resumo["status_vinculo"][status_vinculo] += 1

                if status_vinculo == "novo_usuario_vinculado":
                    resumo["novos_usuarios_vinculados"] += 1
                elif status_vinculo == "usuario_existente_vinculado":
                    resumo["usuarios_existentes_vinculados"] += 1
                elif status_vinculo == "vinculo_preservado":
                    resumo["usuarios_com_vinculo_preservado"] += 1
                elif status_vinculo == "conflito_email_colaborador":
                    resumo["conflitos_colaborador_email"] += 1
                    resumo["usuarios_sem_colaborador"] += 1
                elif status_vinculo == "colaborador_ja_vinculado":
                    resumo["colaboradores_ja_vinculados"] += 1
                    resumo["usuarios_sem_colaborador"] += 1
                else:
                    resumo["usuarios_sem_colaborador"] += 1

                if status_vinculo in {"sem_colaborador", "colaborador_inativo", "colaborador_ja_vinculado"}:
                    resumo["emails_sem_colaborador"].append(usuario.email)

            except Exception as erro_linha:
                resumo["linhas_ignoradas"] += 1
                email = normalizar_email(linha.get("email"))
                resumo["erros"].append(
                    f"Linha {indice}: {email or '-'} - {erro_linha}"
                )

        db.session.commit()
        return resumo

    except Exception:
        db.session.rollback()
        raise


def imprimir_resumo(resumo):
    print("Seed de usuários por CSV concluído.")
    print(f"Total de linhas lidas: {resumo['total_linhas']}")
    print(f"Usuários criados: {resumo['usuarios_criados']}")
    print(f"Usuários já existentes: {resumo['usuarios_existentes']}")
    print(f"Novos usuários vinculados a colaboradores: {resumo['novos_usuarios_vinculados']}")
    print(f"Usuários existentes vinculados nesta execução: {resumo['usuarios_existentes_vinculados']}")
    print(f"Usuários que já tinham vínculo preservado: {resumo['usuarios_com_vinculo_preservado']}")
    print(f"Usuários sem colaborador correspondente: {resumo['usuarios_sem_colaborador']}")
    print(f"Conflitos de colaborador por e-mail duplicado: {resumo['conflitos_colaborador_email']}")
    print(f"Colaboradores já vinculados a outro usuário: {resumo['colaboradores_ja_vinculados']}")
    print(f"Linhas ignoradas por erro: {resumo['linhas_ignoradas']}")

    if resumo["status_vinculo"]:
        print("Resumo de vínculo:")
        for status, quantidade in sorted(resumo["status_vinculo"].items()):
            print(f"- {status}: {quantidade}")

    if resumo["emails_sem_colaborador"]:
        print("E-mails sem colaborador correspondente:")
        for email in resumo["emails_sem_colaborador"][:50]:
            print(f"- {email}")

        if len(resumo["emails_sem_colaborador"]) > 50:
            restante = len(resumo["emails_sem_colaborador"]) - 50
            print(f"- ... mais {restante} e-mails")

    if resumo["erros"]:
        print("Erros por linha:")
        for erro in resumo["erros"]:
            print(f"- {erro}")


def construir_parser():
    parser = argparse.ArgumentParser(
        description="Importa usuários em massa por CSV sem versionar dados pessoais.",
    )
    parser.add_argument(
        "--arquivo",
        default=str(CAMINHO_PADRAO_CSV),
        help=f"Caminho do CSV. Padrão: {CAMINHO_PADRAO_CSV}",
    )
    parser.add_argument(
        "--senha-padrao",
        default=os.getenv("USUARIOS_CSV_SENHA_PADRAO", "123456"),
        help=(
            "Senha inicial dos novos usuários. Também pode ser informada pela "
            "variável USUARIOS_CSV_SENHA_PADRAO."
        ),
    )
    return parser


def main():
    parser = construir_parser()
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        try:
            resumo = importar_usuarios_csv(
                caminho_csv=args.arquivo,
                senha_padrao=args.senha_padrao,
            )
            imprimir_resumo(resumo)
        except Exception as erro:
            db.session.rollback()
            print(f"Erro crítico ao importar usuários: {erro}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
