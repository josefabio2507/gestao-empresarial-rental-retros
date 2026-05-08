from app.models import Departamento, Modulo, PermissaoUsuarioModulo
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

DEPARTAMENTO_PESSOAL_SLUG = "departamento_pessoal"
DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG = "documentos_pessoais"
MODULO_HOLERITES_SLUG = "holerites"


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

def usuario_eh_administrador(usuario):
    """
    Verifica se o usuário possui perfil de administrador.
    Administrador tem acesso total ao sistema.
    """

    if not usuario:
        return False

    if not getattr(usuario, "is_authenticated", False):
        return False

    if getattr(usuario, "is_admin", False):
        return True

    nivel_acesso = getattr(usuario, "nivel_acesso", None)

    if nivel_acesso and (nivel_acesso.slug or "").lower() == "administrador":
        return True

    return False


def usuario_tem_permissao(usuario, departamento_slug, modulo_slug, acao="visualizar"):
    """
    Verifica se o usuário possui permissão para acessar uma ação em um módulo.
    Administrador possui acesso total.
    """

    if not usuario or not usuario.is_authenticated:
        return False

    if not usuario.ativo:
        return False

    if usuario_eh_administrador(usuario):
        return True

    acoes_validas = {
        "visualizar": "pode_visualizar",
        "criar": "pode_criar",
        "editar": "pode_editar",
        "excluir": "pode_excluir",
        "aprovar": "pode_aprovar",
        "exportar": "pode_exportar",
    }

    campo_acao = acoes_validas.get(acao)

    if not campo_acao:
        return False

    departamento = Departamento.query.filter_by(
        slug=departamento_slug,
        ativo=True,
    ).first()

    if not departamento:
        return False

    modulo = Modulo.query.filter_by(
        departamento_id=departamento.id,
        slug=modulo_slug,
        ativo=True,
    ).first()

    if not modulo:
        return False

    permissao = PermissaoUsuarioModulo.query.filter_by(
        usuario_id=usuario.id,
        modulo_id=modulo.id,
        ativo=True,
    ).first()

    if not permissao:
        return False

    return bool(getattr(permissao, campo_acao, False))


def buscar_departamentos_liberados(usuario):
    """
    Retorna os departamentos que o usuário pode visualizar.
    Administrador vê todos os departamentos ativos.
    Usuário comum vê apenas departamentos com pelo menos um módulo liberado.
    """

    if not usuario or not usuario.is_authenticated or not usuario.ativo:
        return []

    if usuario.is_admin:
        return (
            Departamento.query
            .filter(
                Departamento.ativo.is_(True),
                Departamento.slug != DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG,
            )
            .order_by(Departamento.ordem.asc(), Departamento.nome.asc())
            .all()
        )

    permissoes = (
        PermissaoUsuarioModulo.query
        .join(Modulo)
        .join(Departamento)
        .filter(
            PermissaoUsuarioModulo.usuario_id == usuario.id,
            PermissaoUsuarioModulo.ativo.is_(True),
            PermissaoUsuarioModulo.pode_visualizar.is_(True),
            Modulo.ativo.is_(True),
            Departamento.ativo.is_(True),
            Departamento.slug != DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG,
        )
        .order_by(Departamento.ordem.asc(), Departamento.nome.asc())
        .all()
    )

    departamentos = []
    ids_adicionados = set()

    for permissao in permissoes:
        departamento = permissao.modulo.departamento

        if departamento.id not in ids_adicionados:
            departamentos.append(departamento)
            ids_adicionados.add(departamento.id)

    if usuario_tem_permissao(
        usuario,
        DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG,
        MODULO_HOLERITES_SLUG,
    ):
        departamento_pessoal = Departamento.query.filter_by(
            slug=DEPARTAMENTO_PESSOAL_SLUG,
            ativo=True,
        ).first()

        if (
            departamento_pessoal
            and departamento_pessoal.id not in ids_adicionados
        ):
            departamentos.append(departamento_pessoal)

    departamentos.sort(key=lambda departamento: (departamento.ordem, departamento.nome))

    return departamentos


def buscar_departamento_por_slug(slug_departamento):
    return Departamento.query.filter_by(
        slug=slug_departamento,
        ativo=True,
    ).first()


def buscar_modulos_liberados(usuario, departamento_slug):
    """
    Retorna os módulos liberados dentro de um departamento.
    Administrador vê todos os módulos ativos.
    Usuário comum vê apenas módulos com pode_visualizar=True.
    """

    if not usuario or not usuario.is_authenticated or not usuario.ativo:
        return []

    departamento = buscar_departamento_por_slug(departamento_slug)

    if not departamento:
        return []

    if usuario.is_admin:
        return (
            Modulo.query
            .filter_by(
                departamento_id=departamento.id,
                ativo=True,
            )
            .order_by(Modulo.ordem.asc(), Modulo.nome.asc())
            .all()
        )

    permissoes = (
        PermissaoUsuarioModulo.query
        .join(Modulo)
        .filter(
            PermissaoUsuarioModulo.usuario_id == usuario.id,
            PermissaoUsuarioModulo.ativo.is_(True),
            PermissaoUsuarioModulo.pode_visualizar.is_(True),
            Modulo.departamento_id == departamento.id,
            Modulo.ativo.is_(True),
        )
        .order_by(Modulo.ordem.asc(), Modulo.nome.asc())
        .all()
    )

    modulos = [permissao.modulo for permissao in permissoes]

    if (
        departamento_slug == DEPARTAMENTO_PESSOAL_SLUG
        and usuario_tem_permissao(
            usuario,
            DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG,
            MODULO_HOLERITES_SLUG,
        )
    ):
        modulo_documentos = Modulo.query.filter_by(
            departamento_id=departamento.id,
            slug="documentos",
            ativo=True,
        ).first()

        if (
            modulo_documentos
            and all(modulo.id != modulo_documentos.id for modulo in modulos)
        ):
            modulos.append(modulo_documentos)

    return modulos

def buscar_departamentos_liberados_usuario(usuario):
    """
    Retorna os departamentos liberados para o usuário.

    Administrador:
        retorna todos os departamentos ativos.

    Usuário comum:
        retorna apenas departamentos que possuem módulos com permissão ativa.
    """

    if not usuario or not usuario.is_authenticated:
        return []

    if not usuario.ativo:
        return []

    if usuario_eh_administrador(usuario):
        return (
            Departamento.query
            .filter(
                Departamento.ativo == True,
                Departamento.slug != DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG,
            )
            .order_by(Departamento.nome)
            .all()
        )

    departamentos = (
        Departamento.query
        .join(Modulo, Modulo.departamento_id == Departamento.id)
        .join(PermissaoUsuarioModulo, PermissaoUsuarioModulo.modulo_id == Modulo.id)
        .filter(
            Departamento.ativo == True,
            Departamento.slug != DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG,
            Modulo.ativo == True,
            PermissaoUsuarioModulo.usuario_id == usuario.id,
            PermissaoUsuarioModulo.ativo == True,
            PermissaoUsuarioModulo.pode_visualizar == True,
        )
        .distinct()
        .order_by(Departamento.nome)
        .all()
    )

    if usuario_tem_permissao(
        usuario,
        DEPARTAMENTO_DOCUMENTOS_PESSOAIS_SLUG,
        MODULO_HOLERITES_SLUG,
    ):
        departamento_pessoal = Departamento.query.filter_by(
            slug=DEPARTAMENTO_PESSOAL_SLUG,
            ativo=True,
        ).first()

        if (
            departamento_pessoal
            and all(departamento.id != departamento_pessoal.id for departamento in departamentos)
        ):
            departamentos.append(departamento_pessoal)

    departamentos.sort(key=lambda departamento: (departamento.ordem, departamento.nome))

    return departamentos    
