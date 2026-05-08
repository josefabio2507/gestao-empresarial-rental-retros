from app import create_app
from app.extensions import db
from app.models import Departamento, Modulo


DEPARTAMENTO_PESSOAL = {
    "nome": "Departamento Pessoal",
    "slug": "departamento_pessoal",
    "descricao": "Gestão de pessoas e rotinas trabalhistas.",
    "icone": "usuarios",
    "ordem": 3,
}

MODULO_DOCUMENTOS_DP = {
    "nome": "Documentos",
    "slug": "documentos",
    "descricao": "Consulta segura de documentos pessoais.",
    "icone": "documentos",
    "ordem": 6,
}

DEPARTAMENTO_DOCUMENTOS_PESSOAIS = {
    "nome": "Documentos Pessoais",
    "slug": "documentos_pessoais",
    "descricao": "Controle de acesso a documentos pessoais dos colaboradores.",
    "icone": "documentos",
    "ordem": 5,
}

MODULO_HOLERITES = {
    "nome": "Holerites",
    "slug": "holerites",
    "descricao": "Documentos > Holerites vinculados aos colaboradores.",
    "icone": "holerite",
    "ordem": 1,
}


def criar_ou_atualizar_departamento(dados):
    departamento = Departamento.query.filter_by(slug=dados["slug"]).first()
    criado = False

    if not departamento:
        departamento = Departamento(slug=dados["slug"])
        db.session.add(departamento)
        criado = True

    departamento.nome = dados["nome"]
    departamento.descricao = dados["descricao"]
    departamento.icone = dados["icone"]
    departamento.ordem = dados["ordem"]
    departamento.ativo = True

    db.session.flush()
    return departamento, criado


def criar_ou_atualizar_modulo(departamento, dados):
    modulo = Modulo.query.filter_by(
        departamento_id=departamento.id,
        slug=dados["slug"],
    ).first()
    criado = False

    if not modulo:
        modulo = Modulo(
            departamento_id=departamento.id,
            slug=dados["slug"],
        )
        db.session.add(modulo)
        criado = True

    modulo.nome = dados["nome"]
    modulo.descricao = dados["descricao"]
    modulo.icone = dados["icone"]
    modulo.ordem = dados["ordem"]
    modulo.ativo = True

    db.session.flush()
    return modulo, criado


def executar_seed():
    print("Seed de Documentos/Holerites iniciado...")

    departamentos_criados = 0
    departamentos_atualizados = 0
    modulos_criados = 0
    modulos_atualizados = 0

    departamento_pessoal, criado = criar_ou_atualizar_departamento(
        DEPARTAMENTO_PESSOAL,
    )

    if criado:
        departamentos_criados += 1
    else:
        departamentos_atualizados += 1

    modulo_documentos, criado = criar_ou_atualizar_modulo(
        departamento_pessoal,
        MODULO_DOCUMENTOS_DP,
    )

    if criado:
        modulos_criados += 1
    else:
        modulos_atualizados += 1

    departamento_documentos, criado = criar_ou_atualizar_departamento(
        DEPARTAMENTO_DOCUMENTOS_PESSOAIS,
    )

    if criado:
        departamentos_criados += 1
    else:
        departamentos_atualizados += 1

    modulo_holerites, criado = criar_ou_atualizar_modulo(
        departamento_documentos,
        MODULO_HOLERITES,
    )

    if criado:
        modulos_criados += 1
    else:
        modulos_atualizados += 1

    db.session.commit()

    print("Seed de Documentos/Holerites concluído com sucesso.")
    print(f"Departamentos criados: {departamentos_criados}")
    print(f"Departamentos atualizados: {departamentos_atualizados}")
    print(f"Módulos criados: {modulos_criados}")
    print(f"Módulos atualizados: {modulos_atualizados}")
    print("Itens processados:")
    print(f"- {departamento_pessoal.nome} > {modulo_documentos.nome}")
    print(f"- {departamento_documentos.nome} > {modulo_holerites.nome}")
    print("Ações consideradas no módulo Holerites: Visualizar e Exportar.")


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        executar_seed()
