import re
import unicodedata

from app import create_app
from app.extensions import db
from app.models import Equipe


EQUIPES = [
    "TMC - INFRAESTRUTURA",
    "TMC - GUARUJA",
    "TMC - FIXA PORTO",
    "TMC - SANTOS",
    "TMC - CALCETARIA",
    "TMC - LIMPEZA II",
    "TMC - FIXA GUARUJA",
    "OPERACAO",
    "ADMINISTRACAO",
    "TMC - LIMPEZA",
    "TMC - AMV",
    "TEG TEAG",
    "TMC - FIXA PARATINGA",
]


def remover_acentos(texto):
    texto_normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(
        caractere
        for caractere in texto_normalizado
        if not unicodedata.combining(caractere)
    )


def gerar_slug(nome):
    texto = remover_acentos(nome).lower()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = re.sub(r"-+", "-", texto)
    return texto.strip("-")


def criar_ou_atualizar_equipe(nome):
    slug = gerar_slug(nome)
    equipe = Equipe.query.filter_by(slug=slug).first()

    if not equipe:
        equipe = Equipe(
            nome=nome,
            slug=slug,
            ativo=True,
        )
        db.session.add(equipe)
        return "criada"

    alterada = False

    if equipe.nome != nome:
        equipe.nome = nome
        alterada = True

    if not equipe.ativo:
        equipe.ativo = True
        alterada = True

    if alterada:
        return "atualizada"

    return "ignorada"


def executar_seed():
    app = create_app()

    with app.app_context():
        criadas = 0
        atualizadas = 0
        ignoradas = 0
        processadas = []

        print("Seed de equipes iniciado...")

        try:
            for nome in EQUIPES:
                resultado = criar_ou_atualizar_equipe(nome)
                processadas.append(nome)

                if resultado == "criada":
                    criadas += 1
                elif resultado == "atualizada":
                    atualizadas += 1
                else:
                    ignoradas += 1

            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

        print(f"Criadas: {criadas}")
        print(f"Atualizadas: {atualizadas}")
        print(f"Ignoradas: {ignoradas}")
        print("Equipes processadas:")

        for nome in processadas:
            print(f"- {nome}")

        print("Seed de equipes concluido com sucesso.")


if __name__ == "__main__":
    executar_seed()
