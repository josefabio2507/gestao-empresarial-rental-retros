from app.services.permissoes_service import usuario_tem_permissao

DEPARTAMENTO_OPERACAO = "operacao"
MODULO_GESTAO_VEICULOS_EPGS = "gestao_veiculos_epgs"
MODULO_VEICULOS_EQUIPAMENTOS = "veiculos_equipamentos"
MODULO_POOL_VEICULOS = "pool_veiculos"
MODULO_ABASTECIMENTO = "abastecimento"
MODULO_MULTAS_TRANSITO = "multas_transito"
MODULO_IMPOSTOS_TAXAS = "impostos_taxas"
MODULO_CENTRAL_CUSTOS = "central_custos"

SUBMODULOS_GESTAO_VEICULOS = [
    MODULO_VEICULOS_EQUIPAMENTOS,
    MODULO_POOL_VEICULOS,
    MODULO_ABASTECIMENTO,
    MODULO_MULTAS_TRANSITO,
    MODULO_IMPOSTOS_TAXAS,
    MODULO_CENTRAL_CUSTOS,
]


def usuario_tem_permissao_operacao(usuario, modulo_slug, acao="visualizar"):
    return usuario_tem_permissao(usuario, DEPARTAMENTO_OPERACAO, modulo_slug, acao)


def usuario_tem_algum_submodulo_gestao(usuario, acao="visualizar"):
    return any(
        usuario_tem_permissao_operacao(usuario, modulo_slug, acao)
        for modulo_slug in SUBMODULOS_GESTAO_VEICULOS
    )


def permissoes_cards_gestao(usuario):
    return {
        "veiculos_equipamentos": usuario_tem_permissao_operacao(usuario, MODULO_VEICULOS_EQUIPAMENTOS),
        "pool_veiculos": usuario_tem_permissao_operacao(usuario, MODULO_POOL_VEICULOS),
        "abastecimento": usuario_tem_permissao_operacao(usuario, MODULO_ABASTECIMENTO),
        "multas_transito": usuario_tem_permissao_operacao(usuario, MODULO_MULTAS_TRANSITO),
        "impostos_taxas": usuario_tem_permissao_operacao(usuario, MODULO_IMPOSTOS_TAXAS),
        "central_custos": usuario_tem_permissao_operacao(usuario, MODULO_CENTRAL_CUSTOS),
    }
