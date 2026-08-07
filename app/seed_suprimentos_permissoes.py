from app.extensions import db
from app.models import Departamento, Modulo


SUPRIMENTOS = {
    "nome": "Suprimentos",
    "slug": "suprimentos",
    "descricao": "Cadastro de fornecedores, itens, centros de custo e base do processo de compras.",
    "icone": "compras",
    "ordem": 2,
    "modulos": [
        ("Fornecedores", "fornecedores", "Cadastro e consulta de fornecedores"),
        ("Categorias", "categorias", "Categorias de itens, materiais e servicos"),
        ("Unidades de Medida", "unidades_medida", "Unidades usadas nos itens de compra"),
        ("Itens", "itens", "Materiais, servicos, pecas, EPIs e consumo"),
        ("Centros de Custo", "centros_custo", "Centros de custo para compras e integracao futura"),
        ("Fornecedor x Item", "fornecedor_itens", "Vinculo comercial entre fornecedores e itens"),
        ("Requisicoes de Compra", "requisicoes_compra", "Solicitacao interna de compras e servicos"),
        ("Cotacoes", "cotacoes", "Registro de propostas de fornecedores para requisicoes enviadas"),
    ],
}


def executar_seed():
    print("Seed de Suprimentos iniciado...")

    departamento = Departamento.query.filter_by(slug=SUPRIMENTOS["slug"]).first()
    departamento_criado = False

    if not departamento:
        departamento = Departamento(slug=SUPRIMENTOS["slug"])
        db.session.add(departamento)
        departamento_criado = True

    departamento.nome = SUPRIMENTOS["nome"]
    departamento.descricao = SUPRIMENTOS["descricao"]
    departamento.icone = SUPRIMENTOS["icone"]
    departamento.ordem = SUPRIMENTOS["ordem"]
    departamento.ativo = True
    db.session.flush()

    modulos_criados = 0
    modulos_preservados = 0

    for ordem, dados_modulo in enumerate(SUPRIMENTOS["modulos"], start=1):
        nome, slug, descricao = dados_modulo
        modulo = Modulo.query.filter_by(
            departamento_id=departamento.id,
            slug=slug,
        ).first()

        if not modulo:
            modulo = Modulo(departamento_id=departamento.id, slug=slug)
            db.session.add(modulo)
            modulos_criados += 1
        else:
            modulos_preservados += 1

        modulo.nome = nome
        modulo.descricao = descricao
        modulo.ordem = ordem
        modulo.ativo = True

    db.session.commit()

    print("Departamento criado:", 1 if departamento_criado else 0)
    print("Departamento atualizado/preservado:", 0 if departamento_criado else 1)
    print("Modulos criados:", modulos_criados)
    print("Modulos atualizados/preservados:", modulos_preservados)
    print("Seed de Suprimentos concluido com sucesso.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()

    with app.app_context():
        executar_seed()
