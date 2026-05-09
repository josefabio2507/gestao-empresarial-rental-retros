import re
import unicodedata
from dataclasses import dataclass, field

from flask import current_app

from app.extensions import db
from app.models import Colaborador, HoleriteColaborador
from app.services.google_drive_service import (
    GOOGLE_DRIVE_PDF_MIME_TYPE,
    GoogleDriveConfiguracaoErro,
    criar_google_drive_client,
    listar_itens_da_pasta,
    listar_pastas_da_pasta,
)


PADRAO_PASTA_COLABORADOR = re.compile(r"^\s*(?P<matricula>\d+)")
PADRAO_MATRICULA_ARQUIVO = re.compile(r"^\s*(?P<matricula>\d+)\s*[-_\s]*")
PADROES_COMPETENCIA = [
    re.compile(r"(?<!\d)(?P<mes>0?[1-9]|1[0-2])\s*[./]\s*(?P<ano>19\d{2}|20\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<ano>19\d{2}|20\d{2})\s*-\s*(?P<mes>0?[1-9]|1[0-2])(?!\d)"),
    re.compile(r"(?<!\d)(?P<mes>0?[1-9]|1[0-2])\s+(?P<ano>19\d{2}|20\d{2})(?!\d)"),
]

TIPOS_PONTO_NAO_ACEITOS = [
    "cartao de ponto",
    "cartoes de ponto",
    "espelho de ponto",
    "ponto",
]


@dataclass
class ResumoSincronizacaoHolerites:
    arquivos_encontrados: int = 0
    importados: int = 0
    ja_existentes: int = 0
    pastas_ignoradas: int = 0
    colaboradores_nao_encontrados: int = 0
    arquivos_fora_padrao: int = 0
    arquivos_nao_pdf: int = 0
    ignorados_tipo_nao_aceito: int = 0
    competencia_nao_identificada: int = 0
    colaboradores_inativos: int = 0
    erros: int = 0
    mensagens: list[str] = field(default_factory=list)

    def adicionar_mensagem(self, mensagem):
        if len(self.mensagens) < 50:
            self.mensagens.append(mensagem)

    def como_dict(self):
        return {
            "arquivos_encontrados": self.arquivos_encontrados,
            "importados": self.importados,
            "ja_existentes": self.ja_existentes,
            "pastas_ignoradas": self.pastas_ignoradas,
            "colaboradores_nao_encontrados": self.colaboradores_nao_encontrados,
            "arquivos_fora_padrao": self.arquivos_fora_padrao,
            "arquivos_nao_pdf": self.arquivos_nao_pdf,
            "ignorados_tipo_nao_aceito": self.ignorados_tipo_nao_aceito,
            "competencia_nao_identificada": self.competencia_nao_identificada,
            "colaboradores_inativos": self.colaboradores_inativos,
            "erros": self.erros,
            "mensagens": self.mensagens,
        }


def normalizar_texto(valor):
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = re.sub(r"[_\-]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar_matricula(valor):
    matricula = re.sub(r"\D+", "", str(valor or ""))

    if not matricula:
        return ""

    return matricula.lstrip("0") or "0"


def matriculas_equivalentes(matricula_a, matricula_b):
    return normalizar_matricula(matricula_a) == normalizar_matricula(matricula_b)


def extrair_matricula_pasta(nome_pasta):
    correspondencia = PADRAO_PASTA_COLABORADOR.match(nome_pasta or "")

    if not correspondencia:
        return None

    return correspondencia.group("matricula").strip()


def buscar_colaborador_por_matricula(matricula):
    colaborador = Colaborador.query.filter_by(matricula=matricula).first()

    if colaborador:
        return colaborador

    matricula_normalizada = normalizar_matricula(matricula)

    if not matricula_normalizada:
        return None

    colaboradores = Colaborador.query.all()

    for colaborador in colaboradores:
        if normalizar_matricula(colaborador.matricula) == matricula_normalizada:
            return colaborador

    return None


def extrair_matricula_arquivo(nome_base):
    correspondencia = PADRAO_MATRICULA_ARQUIVO.match(nome_base or "")

    if not correspondencia:
        return None

    return correspondencia.group("matricula").strip()


def normalizar_competencia(mes, ano):
    return f"{int(mes):02d}/{ano}"


def extrair_competencia(nome_base):
    for padrao in PADROES_COMPETENCIA:
        correspondencia = padrao.search(nome_base or "")

        if correspondencia:
            return normalizar_competencia(
                correspondencia.group("mes"),
                correspondencia.group("ano"),
            )

    return None


def normalizar_tipo_documento(nome_base):
    texto = normalizar_texto(nome_base)

    if any(tipo in texto for tipo in TIPOS_PONTO_NAO_ACEITOS):
        return None

    if "adiantamento" in texto:
        return "Adiantamento Salarial"

    if "holerite" in texto or "holerites" in texto:
        return "Holerite Mensal"

    return None


def analisar_nome_arquivo_holerite(nome_arquivo):
    nome_arquivo = nome_arquivo or ""

    if not nome_arquivo.lower().endswith(".pdf"):
        return {
            "valido": False,
            "motivo": "nao_pdf",
        }

    nome_base = re.sub(r"\.pdf\s*$", "", nome_arquivo, flags=re.IGNORECASE).strip()
    matricula = extrair_matricula_arquivo(nome_base)
    tipo = normalizar_tipo_documento(nome_base)

    if not tipo:
        return {
            "valido": False,
            "motivo": "tipo_nao_aceito",
            "matricula": matricula,
        }

    competencia = extrair_competencia(nome_base)

    if not competencia:
        return {
            "valido": False,
            "motivo": "competencia_nao_identificada",
            "matricula": matricula,
            "tipo": tipo,
        }

    return {
        "valido": True,
        "matricula": matricula,
        "tipo": tipo,
        "competencia": competencia,
        "nome": nome_base,
    }


def interpretar_nome_arquivo_holerite(nome_arquivo):
    resultado = analisar_nome_arquivo_holerite(nome_arquivo)

    if not resultado.get("valido"):
        return None

    return {
        "matricula": resultado.get("matricula"),
        "tipo": resultado["tipo"],
        "competencia": resultado["competencia"],
        "nome": resultado["nome"],
    }


def holerite_ja_importado(colaborador_id, dados_arquivo, arquivo_drive):
    google_drive_file_id = arquivo_drive.get("id")

    if google_drive_file_id:
        existente = HoleriteColaborador.query.filter_by(
            google_drive_file_id=google_drive_file_id,
        ).first()

        if existente:
            return True

    return (
        HoleriteColaborador.query
        .filter_by(
            colaborador_id=colaborador_id,
            competencia=dados_arquivo["competencia"],
            tipo=dados_arquivo["tipo"],
            nome_arquivo=arquivo_drive.get("name"),
        )
        .first()
        is not None
    )


def criar_holerite(colaborador, dados_arquivo, arquivo_drive, usuario_id=None):
    holerite = HoleriteColaborador(
        colaborador_id=colaborador.id,
        competencia=dados_arquivo["competencia"],
        tipo=dados_arquivo["tipo"],
        nome_arquivo=arquivo_drive.get("name"),
        origem_arquivo="google_drive",
        google_drive_file_id=arquivo_drive.get("id"),
        google_drive_url=arquivo_drive.get("webViewLink"),
        ativo=True,
        criado_por_usuario_id=usuario_id,
    )
    db.session.add(holerite)
    return holerite


def sincronizar_holerites_google_drive(usuario_id=None, drive_service=None, folder_id=None):
    resumo = ResumoSincronizacaoHolerites()
    folder_id = folder_id or current_app.config.get("GOOGLE_DRIVE_HOLERITES_FOLDER_ID")

    if not folder_id:
        resumo.erros += 1
        resumo.adicionar_mensagem("Pasta principal de Holerites não configurada.")
        return resumo.como_dict()

    try:
        service = drive_service or criar_google_drive_client()
        pastas = listar_pastas_da_pasta(service, folder_id)
    except GoogleDriveConfiguracaoErro as exc:
        resumo.erros += 1
        resumo.adicionar_mensagem(str(exc))
        return resumo.como_dict()
    except Exception:
        resumo.erros += 1
        resumo.adicionar_mensagem("Não foi possível acessar a pasta principal de Holerites.")
        return resumo.como_dict()

    for pasta in pastas:
        nome_pasta = pasta.get("name") or ""
        matricula = extrair_matricula_pasta(nome_pasta)

        if not matricula:
            resumo.pastas_ignoradas += 1
            resumo.adicionar_mensagem(f"Pasta ignorada fora do padrão: {nome_pasta}")
            continue

        colaborador = buscar_colaborador_por_matricula(matricula)

        if not colaborador:
            resumo.colaboradores_nao_encontrados += 1
            resumo.adicionar_mensagem(f"Colaborador não encontrado para matrícula {matricula}.")
            continue

        if hasattr(colaborador, "ativo") and not colaborador.ativo:
            resumo.colaboradores_inativos += 1
            resumo.adicionar_mensagem(f"Colaborador inativo ignorado. Matrícula: {matricula}.")
            continue

        try:
            arquivos = listar_itens_da_pasta(service, pasta.get("id"))
        except Exception:
            resumo.erros += 1
            resumo.adicionar_mensagem(f"Não foi possível ler a pasta da matrícula {matricula}.")
            continue

        for arquivo in arquivos:
            nome_arquivo = arquivo.get("name") or ""
            resumo.arquivos_encontrados += 1

            if (
                arquivo.get("mimeType") != GOOGLE_DRIVE_PDF_MIME_TYPE
                and not nome_arquivo.lower().endswith(".pdf")
            ):
                resumo.arquivos_nao_pdf += 1
                continue

            analise_arquivo = analisar_nome_arquivo_holerite(nome_arquivo)

            if analise_arquivo.get("motivo") == "tipo_nao_aceito":
                resumo.ignorados_tipo_nao_aceito += 1
                resumo.adicionar_mensagem(f"Tipo não aceito: {nome_arquivo}")
                continue

            if analise_arquivo.get("motivo") == "competencia_nao_identificada":
                resumo.competencia_nao_identificada += 1
                resumo.adicionar_mensagem(f"Competência não identificada: {nome_arquivo}")
                continue

            if not analise_arquivo.get("valido"):
                resumo.arquivos_fora_padrao += 1
                resumo.adicionar_mensagem(f"Arquivo fora do padrão: {nome_arquivo}")
                continue

            dados_arquivo = {
                "matricula": analise_arquivo.get("matricula"),
                "tipo": analise_arquivo["tipo"],
                "competencia": analise_arquivo["competencia"],
                "nome": analise_arquivo["nome"],
            }

            if holerite_ja_importado(colaborador.id, dados_arquivo, arquivo):
                resumo.ja_existentes += 1
                continue

            criar_holerite(
                colaborador,
                dados_arquivo,
                arquivo,
                usuario_id=usuario_id,
            )
            resumo.importados += 1

    db.session.commit()
    return resumo.como_dict()
