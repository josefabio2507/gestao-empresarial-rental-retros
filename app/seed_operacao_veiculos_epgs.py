from app.extensions import db
from app.models import OperacaoVeiculoEquipamento
from app.operacao.veiculos_equipamentos.services import (
    centro_custo_calculado,
    identificar_tipo,
    texto_maiusculo,
)


REGISTROS_INICIAIS = [
    ("STG7D96", "CITROEN JUMPY", "9V7VBYHVERA007070", "", "STG7D96-CITROEN JUMPY", "Quitado"),
    ("RMJ4E07", "M BENZ - ACCELO 1016", "9BM979078LB191211", "", "RMJ4E07-M BENZ - ACCELO 1016", "Quitado"),
    ("QNH0H80", "M BENZ - ACCELO 1016", "9BM979026JB075295", "", "QNH0H80-M BENZ - ACCELO 1016", "Quitado"),
    ("FUV6F90", "FORD - CARGO 816", "9BFVEADS1EBS69487", "", "FUV6F90-FORD - CARGO 816", "Quitado"),
    ("IWQ7F41", "FORD - CARGO 1319", "9BFXEB1B1FBS73432", "", "IWQ7F41-FORD - CARGO 1319", "Quitado"),
    ("SWLC90", "VOLKS - EXPRESS", "95355FTEXPR042128", "", "SWLC90-VOLKS - EXPRESS", "Quitado"),
    ("SUD8D27", "CASE - 580N SERIE 2", "HBZN580NPRAH34224", "", "SUD8D27-CASE - 580N SERIE 2", "Quitado"),
    ("SWO7D00", "CASE - 580N SERIE 2", "HBZN580NJPAH31968", "", "SWO7D00-CASE - 580N SERIE 2", "Quitado"),
    ("FDE3E21", "CASE - 580N TC", "HBZN580NHNAH30415", "", "FDE3E21-CASE - 580N TC", "Quitado"),
    ("FKC0H21", "CASE - 580N TC", "HBZN580NKNAH30413", "", "FKC0H21-CASE - 580N TC", "Quitado"),
    ("FCT4A64", "JOHN DEERE - 310L", "1BZ310LAKJD001386", "", "FCT4A64-JOHN DEERE - 310L", "Quitado"),
    ("EXR7I36", "JOHN DEERE - 310L", "1BZ310LAJKD002105", "", "EXR7I36-JOHN DEERE - 310L", "Quitado"),
    ("TKG7G47", "NEW HOLLAND - B95C", "HBZNB95CTRAH34101", "", "TKG7G47-NEW HOLLAND - B95C", "Quitado"),
    ("DED1G69", "NEW HOLLAND - B95B", "HBZNB95BLGAH15935", "", "DED1G69-NEW HOLLAND - B95B", "Quitado"),
    ("RVP9D49", "FIAT MOBI LIKE", "9BD341ACZPY851075", "", "RVP9D49-FIAT MOBI LIKE", "Quitado"),
    ("RFD7B93", "FIAT MOBI LIKE", "9BD341A5XLY680113", "", "RFD7B93-FIAT MOBI LIKE", "Quitado"),
    ("RFD1D62", "FIAT MOBI LIKE", "9BD341A5XLY680509", "", "RFD1D62-FIAT MOBI LIKE", "Quitado"),
    ("QXN5F52", "FIAT MOBI LIKE", "9BD341A5XLY669544", "", "QXN5F52-FIAT MOBI LIKE", "Quitado"),
    ("SDS7F82", "VOLKS VOYAGE", "9BWDG45U1PT055300", "", "SDS7F82-VOLKS VOYAGE", "Quitado"),
    ("GAG9B93", "VOLKS SAVEIRO", "9BWKB45U5KP017849", "", "GAG9B93-VOLKS SAVEIRO", "Quitado"),
    ("TKS5F97", "CITROEN BASALT", "935CPFCA7SB556035", "", "TKS5F97-CITROEN BASALT", "Quitado"),
    ("ESC HIDRÁULICA", "JOHN DEERE - 200G", "1F9200GXPND020551", "", "ESC HIDRÁULICA-JOHN DEERE - 200G", "Financiado"),
    ("TJF7D14", "VW/EXPRESS DRF 4X2", "95355FTE9SR015706", "", "TJF7D14-VW/EXPRESS DRF 4X2", "Financiado"),
    ("SWU3F73", "VOLKS - DELIVERY 11.180", "9535E6TB4PR054099", "", "SWU3F73-VOLKS - DELIVERY 11.180", "Financiado"),
    ("FJJ3E14", "VOLKS - CONSTELATION 31320", "9536C8TL9SR002684", "", "FJJ3E14-VOLKS - CONSTELATION 31320", "Financiado"),
]


def buscar_existente(identificacao, chassi):
    if chassi:
        existente = OperacaoVeiculoEquipamento.query.filter_by(chassi=chassi).first()
        if existente:
            return existente

    return OperacaoVeiculoEquipamento.query.filter_by(identificacao=identificacao).first()


def executar_seed():
    print("Seed de veículos e EPGs iniciado...")

    processados = 0
    criados = 0
    existentes = 0
    ignorados = 0
    centros_recalculados = 0
    divergencias = 0
    erros = []

    for linha, dados in enumerate(REGISTROS_INICIAIS, start=1):
        processados += 1
        identificacao, descricao, chassi, renavam, centro_planilha, situacao = dados
        identificacao = texto_maiusculo(identificacao)
        descricao = texto_maiusculo(descricao)
        chassi = texto_maiusculo(chassi) or None
        renavam = texto_maiusculo(renavam) or None
        centro_planilha = texto_maiusculo(centro_planilha)
        situacao = situacao.strip()
        centro_calculado = centro_custo_calculado(identificacao, descricao)

        if not identificacao or not descricao:
            ignorados += 1
            erros.append(f"Linha {linha}: identificacao ou descricao ausente.")
            continue

        if centro_planilha != centro_calculado:
            divergencias += 1

        existente = buscar_existente(identificacao, chassi)
        if existente:
            existentes += 1
            continue

        registro = OperacaoVeiculoEquipamento(
            identificacao=identificacao,
            placa=None if " " in identificacao else identificacao,
            descricao=descricao,
            chassi=chassi,
            renavam=renavam,
            situacao_aquisicao=situacao,
            tipo=identificar_tipo(descricao),
            ativo=True,
        )
        registro.recalcular_centro_custo()
        db.session.add(registro)
        criados += 1
        centros_recalculados += 1

    db.session.commit()

    print("Total de registros processados:", processados)
    print("Registros criados:", criados)
    print("Registros ja existentes:", existentes)
    print("Registros ignorados:", ignorados)
    print("Centros de custo recalculados:", centros_recalculados)
    print("Divergencias entre planilha e calculo:", divergencias)
    print("Erros:", len(erros))

    for erro in erros:
        print(f"- {erro}")

    print("Seed de veículos e EPGs concluído com sucesso.")


if __name__ == "__main__":
    from app import create_app

    app = create_app()

    with app.app_context():
        executar_seed()
