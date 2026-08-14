from app import create_app
from app.services.operacao_veiculos_service import (
    executar_carga_inicial,
    imprimir_resumo_carga,
)


def executar_seed():
    resumo = executar_carga_inicial()
    imprimir_resumo_carga(resumo)
    return resumo


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        executar_seed()
