from app.extensions import db
from app.models import SuprimentosItem


def executar_seed():
    print("Seed para marcar itens como nao estocaveis iniciado...")

    total_itens = SuprimentosItem.query.count()
    atualizados = (
        SuprimentosItem.query
        .filter(SuprimentosItem.item_estocavel.is_(True))
        .update(
            {SuprimentosItem.item_estocavel: False},
            synchronize_session=False,
        )
    )

    db.session.commit()

    print("Itens encontrados:", total_itens)
    print("Itens alterados para nao estocaveis:", atualizados)
    print("Seed para marcar itens como nao estocaveis concluido com sucesso.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()

    with app.app_context():
        executar_seed()
