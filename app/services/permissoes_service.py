from app.extensions import db
from app.models import (
    Usuario,
    Departamento,
    Modulo,
    PermissaoUsuarioModulo,
)


ACOES_PERMISSAO = [
    "visualizar",
    "criar",
    "editar",
    "excluir",
    "aprovar",
    "exportar",
]


def buscar_usuario_com_permissoes(usuario_id):
    return Usuario.query.get(usuario_id)


def buscar_departamentos_com_modulos():
    return (
        Departamento.query
        .filter_by(ativo=True)
        .order_by(Departamento.ordem.asc(), Departamento.nome.asc())
        .all()
    )


def buscar_permissoes_usuario(usuario_id):
    permissoes = (
        PermissaoUsuarioModulo.query
        .filter_by(usuario_id=usuario_id)
        .all()
    )

    return {permissao.modulo_id: permissao for permissao in permissoes}


def buscar_permissoes_ativas_usuario(usuario_id):
    permissoes = (
        PermissaoUsuarioModulo.query
        .join(Modulo)
        .join(Departamento)
        .filter(
            PermissaoUsuarioModulo.usuario_id == usuario_id,
            PermissaoUsuarioModulo.ativo.is_(True),
            PermissaoUsuarioModulo.pode_visualizar.is_(True),
            Modulo.ativo.is_(True),
            Departamento.ativo.is_(True),
        )
        .order_by(
            Departamento.ordem.asc(),
            Modulo.ordem.asc(),
        )
        .all()
    )

    return permissoes


def extrair_acoes_do_formulario(form_data, modulo_id):
    return {
        "pode_visualizar": f"modulo_{modulo_id}_visualizar" in form_data,
        "pode_criar": f"modulo_{modulo_id}_criar" in form_data,
        "pode_editar": f"modulo_{modulo_id}_editar" in form_data,
        "pode_excluir": f"modulo_{modulo_id}_excluir" in form_data,
        "pode_aprovar": f"modulo_{modulo_id}_aprovar" in form_data,
        "pode_exportar": f"modulo_{modulo_id}_exportar" in form_data,
    }


def garantir_visualizacao(acoes):
    alguma_acao_marcada = (
        acoes["pode_criar"]
        or acoes["pode_editar"]
        or acoes["pode_excluir"]
        or acoes["pode_aprovar"]
        or acoes["pode_exportar"]
    )

    if alguma_acao_marcada:
        acoes["pode_visualizar"] = True

    return acoes


def existe_alguma_acao(acoes):
    return any(acoes.values())


def salvar_permissoes_usuario(usuario_id, form_data):
    usuario = Usuario.query.get(usuario_id)

    if not usuario:
        return False, "Usuário não encontrado."

    modulos = Modulo.query.filter_by(ativo=True).all()

    for modulo in modulos:
        acoes = extrair_acoes_do_formulario(form_data, modulo.id)
        acoes = garantir_visualizacao(acoes)

        ativo = existe_alguma_acao(acoes)

        permissao = PermissaoUsuarioModulo.query.filter_by(
            usuario_id=usuario.id,
            modulo_id=modulo.id,
        ).first()

        if not permissao:
            permissao = PermissaoUsuarioModulo(
                usuario_id=usuario.id,
                modulo_id=modulo.id,
            )
            db.session.add(permissao)

        permissao.pode_visualizar = acoes["pode_visualizar"]
        permissao.pode_criar = acoes["pode_criar"]
        permissao.pode_editar = acoes["pode_editar"]
        permissao.pode_excluir = acoes["pode_excluir"]
        permissao.pode_aprovar = acoes["pode_aprovar"]
        permissao.pode_exportar = acoes["pode_exportar"]
        permissao.ativo = ativo

    db.session.commit()

    return True, "Permissões salvas com sucesso."


def permissoes_por_departamento(usuario_id):
    permissoes_ativas = buscar_permissoes_ativas_usuario(usuario_id)

    dados = {}

    for permissao in permissoes_ativas:
        departamento = permissao.modulo.departamento

        if departamento.id not in dados:
            dados[departamento.id] = {
                "departamento": departamento,
                "permissoes": [],
            }

        dados[departamento.id]["permissoes"].append(permissao)

    return dados.values()


def listar_acoes_liberadas(permissao):
    acoes = []

    if permissao.pode_visualizar:
        acoes.append("Visualizar")

    if permissao.pode_criar:
        acoes.append("Criar")

    if permissao.pode_editar:
        acoes.append("Editar")

    if permissao.pode_excluir:
        acoes.append("Excluir")

    if permissao.pode_aprovar:
        acoes.append("Aprovar")

    if permissao.pode_exportar:
        acoes.append("Exportar")

    return acoes