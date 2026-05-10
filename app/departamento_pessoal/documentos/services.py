import re

from app.models import HoleriteColaborador
from app.services.permissoes_service import usuario_eh_administrador


def chave_ordenacao_competencia(competencia):
    texto = str(competencia or "").strip()
    correspondencia = re.search(
        r"(?P<mes>0?[1-9]|1[0-2])\s*[./-]\s*(?P<ano>19\d{2}|20\d{2})",
        texto,
    )

    if not correspondencia:
        correspondencia = re.search(
            r"(?P<ano>19\d{2}|20\d{2})\s*-\s*(?P<mes>0?[1-9]|1[0-2])",
            texto,
        )

    if not correspondencia:
        return (0, 0)

    return (
        int(correspondencia.group("ano")),
        int(correspondencia.group("mes")),
    )


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

    holerites = (
        query
        .order_by(HoleriteColaborador.id.desc())
        .all()
    )

    return sorted(
        holerites,
        key=lambda holerite: (
            chave_ordenacao_competencia(holerite.competencia),
            getattr(holerite, "criado_em", None),
            holerite.id,
        ),
        reverse=True,
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
