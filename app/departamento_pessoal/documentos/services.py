from app.models import HoleriteColaborador
from app.services.permissoes_service import usuario_eh_administrador


def usuario_deve_ver_apenas_proprios_holerites(usuario):
    if not usuario:
        return True

    if usuario_eh_administrador(usuario):
        return False

    return bool(getattr(usuario, "colaborador_id", None))


def buscar_holerites_visiveis(usuario):
    query = (
        HoleriteColaborador.query
        .filter(HoleriteColaborador.ativo.is_(True))
    )

    if usuario_deve_ver_apenas_proprios_holerites(usuario):
        colaborador_id = getattr(usuario, "colaborador_id", None)

        if not colaborador_id:
            return []

        query = query.filter(HoleriteColaborador.colaborador_id == colaborador_id)

    return (
        query
        .order_by(
            HoleriteColaborador.competencia.desc(),
            HoleriteColaborador.tipo.asc(),
            HoleriteColaborador.id.desc(),
        )
        .all()
    )


def buscar_holerite_por_id(holerite_id):
    return HoleriteColaborador.query.get(holerite_id)


def usuario_pode_acessar_holerite(usuario, holerite):
    if not usuario or not holerite or not holerite.ativo:
        return False

    if usuario_eh_administrador(usuario):
        return True

    colaborador_id = getattr(usuario, "colaborador_id", None)

    if colaborador_id:
        return holerite.colaborador_id == colaborador_id

    return True
