from app import create_app
from app.extensions import db
from app.models import NivelAcesso


NIVEIS = [
    {
        "nome": "Administrador",
        "slug": "administrador",
        "descricao": "Acesso administrativo completo ao sistema.",
    },
    {
        "nome": "Gestor",
        "slug": "gestor",
        "descricao": "Acesso gerencial aos módulos liberados.",
    },
    {
        "nome": "Operador",
        "slug": "operador",
        "descricao": "Acesso operacional aos módulos liberados.",
    },
    {
        "nome": "Visualizador",
        "slug": "visualizador",
        "descricao": "Acesso somente para consulta aos módulos liberados.",
    },
]


def executar_seed():
    criados = 0
    atualizados = 0
    processados = []

    print("Seed de níveis de acesso iniciado...")

    for dados in NIVEIS:
        nivel = NivelAcesso.query.filter_by(slug=dados["slug"]).first()

        if nivel:
            nivel.nome = dados["nome"]
            nivel.descricao = dados["descricao"]
            nivel.ativo = True
            atualizados += 1
        else:
            nivel = NivelAcesso(
                nome=dados["nome"],
                slug=dados["slug"],
                descricao=dados["descricao"],
                ativo=True,
            )
            db.session.add(nivel)
            criados += 1

        processados.append(dados["nome"])

    db.session.commit()

    print("Seed de níveis de acesso concluído com sucesso.")
    print(f"Criados: {criados}")
    print(f"Atualizados: {atualizados}")
    print("Níveis processados:")

    for nome in processados:
        print(f"- {nome}")


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        executar_seed()
