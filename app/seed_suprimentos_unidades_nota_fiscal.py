import json
from pathlib import Path

from sqlalchemy import func

from app.extensions import db
from app.models import SuprimentosUnidadeMedida


ARQUIVO_ITENS = Path(__file__).resolve().parent / "data" / "suprimentos_itens_nota_fiscal.json"


def normalizar_texto(valor):
    if valor is None:
        return ""
    return " ".join(str(valor).strip().upper().split())


def carregar_unidades_unicas():
    with ARQUIVO_ITENS.open("r", encoding="utf-8") as arquivo:
        itens = json.load(arquivo)

    unidades = {
        normalizar_texto(item.get("unidade")) or "UN"
        for item in itens
    }
    return sorted(unidades)


def buscar_unidade_por_sigla(sigla):
    return SuprimentosUnidadeMedida.query.filter(
        func.upper(func.trim(SuprimentosUnidadeMedida.sigla)) == sigla
    ).first()


def executar_seed():
    print("Seed de unidades de nota fiscal iniciado...")

    unidades = carregar_unidades_unicas()
    criadas = 0
    atualizadas = 0
    ignoradas = 0

    for sigla in unidades:
        if not sigla:
            ignoradas += 1
            continue

        unidade = buscar_unidade_por_sigla(sigla)

        if not unidade:
            unidade = SuprimentosUnidadeMedida(
                nome=sigla,
                sigla=sigla,
                descricao="UNIDADE IMPORTADA DA BASE DE ITENS DE NOTA FISCAL.",
                ativo=True,
            )
            db.session.add(unidade)
            criadas += 1
        else:
            unidade.nome = unidade.nome or sigla
            unidade.ativo = True
            atualizadas += 1

    db.session.commit()

    print("Unidades unicas lidas da base de itens:", len(unidades))
    print("Unidades criadas:", criadas)
    print("Unidades atualizadas/preservadas:", atualizadas)
    print("Unidades ignoradas:", ignoradas)
    print("Seed de unidades de nota fiscal concluido com sucesso.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()

    with app.app_context():
        executar_seed()
