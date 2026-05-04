import re


MENSAGEM_TELEFONE_INVALIDO = (
    "Telefone invalido. Informe DDD + numero ou 55 + DDD + numero."
)


def somente_numeros(valor):
    if valor is None:
        return ""

    return re.sub(r"\D", "", str(valor))


def normalizar_telefone_brasil(valor):
    telefone = somente_numeros(valor)

    if not telefone:
        return None

    if not telefone.startswith("55") and len(telefone) in (10, 11):
        telefone = f"55{telefone}"

    if not telefone.startswith("55"):
        raise ValueError(MENSAGEM_TELEFONE_INVALIDO)

    if len(telefone) not in (12, 13):
        raise ValueError(MENSAGEM_TELEFONE_INVALIDO)

    return telefone


def formatar_cpf_completo(cpf):
    cpf = somente_numeros(cpf)

    if not cpf:
        return "-"

    if len(cpf) != 11:
        return cpf

    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def mascarar_cpf(cpf):
    cpf = somente_numeros(cpf)

    if not cpf:
        return "-"

    if len(cpf) != 11:
        return "***"

    return f"***.{cpf[3:6]}.{cpf[6:9]}-**"


def formatar_telefone_completo(telefone):
    telefone = somente_numeros(telefone)

    if not telefone:
        return "-"

    if len(telefone) == 13 and telefone.startswith("55"):
        return f"+{telefone[:2]} ({telefone[2:4]}) {telefone[4:9]}-{telefone[9:]}"

    if len(telefone) == 12 and telefone.startswith("55"):
        return f"+{telefone[:2]} ({telefone[2:4]}) {telefone[4:8]}-{telefone[8:]}"

    if len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"

    if len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"

    return telefone


def mascarar_telefone(telefone):
    telefone = somente_numeros(telefone)

    if not telefone:
        return "-"

    try:
        telefone = normalizar_telefone_brasil(telefone)
    except ValueError:
        return "***"

    if len(telefone) == 13:
        return f"+{telefone[:2]} ({telefone[2:4]}) {telefone[4]}****-{telefone[9:]}"

    return f"+{telefone[:2]} ({telefone[2:4]}) ****-{telefone[8:]}"


def mascarar_email(email):
    if not email:
        return "-"

    email = str(email).strip().lower()

    if not email:
        return "-"

    if "@" not in email:
        return f"{email[:1]}****"

    usuario, dominio = email.split("@", 1)

    if not usuario:
        return f"****@{dominio}"

    return f"{usuario[:1]}****@{dominio}"


def formatar_email_completo(email):
    if not email:
        return "-"

    email = str(email).strip().lower()
    return email or "-"


def exibir_cpf(cpf, pode_ver_dados_sensiveis=False):
    if pode_ver_dados_sensiveis:
        return formatar_cpf_completo(cpf)

    return mascarar_cpf(cpf)


def exibir_telefone(telefone, pode_ver_dados_sensiveis=False):
    if pode_ver_dados_sensiveis:
        return formatar_telefone_completo(telefone)

    return mascarar_telefone(telefone)


def exibir_email(email, pode_ver_dados_sensiveis=False):
    if pode_ver_dados_sensiveis:
        return formatar_email_completo(email)

    return mascarar_email(email)


def pode_ver_dados_sensiveis(usuario, modulo_slug="colaboradores"):
    if not usuario or not getattr(usuario, "is_authenticated", False):
        return False

    if not getattr(usuario, "ativo", False):
        return False

    if getattr(usuario, "is_admin", False):
        return True

    from app.services.permissoes_service import usuario_tem_permissao

    return usuario_tem_permissao(
        usuario,
        "departamento_pessoal",
        modulo_slug,
        "editar",
    )
