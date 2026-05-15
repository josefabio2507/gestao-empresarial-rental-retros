import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

from flask import current_app

from app.extensions import db
from app.models import Colaborador, HoleriteColaborador
from app.utils.datas import BR_TZ, UTC_TZ
from app.services.google_drive_service import (
    GOOGLE_DRIVE_FOLDER_MIME_TYPE,
    GOOGLE_DRIVE_PDF_MIME_TYPE,
    GoogleDriveConfiguracaoErro,
    criar_google_drive_client,
    listar_itens_da_pasta_pagina,
)


TAMANHO_LOTE_PADRAO = 200
TAMANHO_PAGINA_PASTAS = 1
TAMANHO_PAGINA_ARQUIVOS = 100
PADRAO_PASTA_COLABORADOR = re.compile(r"^\s*(?P<matricula>\d+)")
PADRAO_MATRICULA_ARQUIVO = re.compile(r"^\s*(?P<matricula>\d+)\s*[-_\s]*")
PADRAO_DATA_BR = re.compile(r"^\d{2}/\d{2}/\d{4}$")
PADRAO_DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PADROES_COMPETENCIA = [
    re.compile(r"(?<!\d)(?P<mes>0?[1-9]|1[0-2])\s*[./-]\s*(?P<ano>19\d{2}|20\d{2})(?!\d)"),
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
    arquivos_encontrados_data: int = 0
    arquivos_fora_data: int = 0
    importados: int = 0
    ja_existentes: int = 0
    pastas_ignoradas: int = 0
    colaboradores_nao_encontrados: int = 0
    arquivos_fora_padrao: int = 0
    arquivos_nao_pdf: int = 0
    ignorados_tipo_nao_aceito: int = 0
    competencia_nao_identificada: int = 0
    colaboradores_inativos: int = 0
    arquivos_processados_lote: int = 0
    pastas_processadas: int = 0
    tamanho_lote: int = TAMANHO_LOTE_PADRAO
    data_criacao_processada: str | None = None
    concluido: bool = False
    proximo_estado: dict | None = None
    erros: int = 0
    mensagens: list[str] = field(default_factory=list)

    def adicionar_mensagem(self, mensagem):
        if len(self.mensagens) < 50:
            self.mensagens.append(mensagem)

    def como_dict(self):
        return {
            "arquivos_encontrados": self.arquivos_encontrados,
            "arquivos_encontrados_data": self.arquivos_encontrados_data,
            "arquivos_fora_data": self.arquivos_fora_data,
            "importados": self.importados,
            "ja_existentes": self.ja_existentes,
            "pastas_ignoradas": self.pastas_ignoradas,
            "colaboradores_nao_encontrados": self.colaboradores_nao_encontrados,
            "arquivos_fora_padrao": self.arquivos_fora_padrao,
            "arquivos_nao_pdf": self.arquivos_nao_pdf,
            "ignorados_tipo_nao_aceito": self.ignorados_tipo_nao_aceito,
            "competencia_nao_identificada": self.competencia_nao_identificada,
            "colaboradores_inativos": self.colaboradores_inativos,
            "arquivos_processados_lote": self.arquivos_processados_lote,
            "pastas_processadas": self.pastas_processadas,
            "tamanho_lote": self.tamanho_lote,
            "data_criacao_processada": self.data_criacao_processada,
            "concluido": self.concluido,
            "proximo_estado": self.proximo_estado,
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


def normalizar_competencia_informada(valor):
    return extrair_competencia(str(valor or ""))


def normalizar_data_criacao_informada(valor):
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=UTC_TZ)
        return valor.astimezone(BR_TZ).date()

    if isinstance(valor, date):
        return valor

    texto = str(valor or "").strip()

    if PADRAO_DATA_BR.match(texto):
        formato = "%d/%m/%Y"
    elif PADRAO_DATA_ISO.match(texto):
        formato = "%Y-%m-%d"
    else:
        return None

    try:
        return datetime.strptime(texto, formato).date()
    except ValueError:
        return None


def formatar_data_criacao(data_criacao):
    if not data_criacao:
        return None

    return data_criacao.strftime("%d/%m/%Y")


def data_criacao_arquivo_drive(arquivo_drive):
    created_time = (arquivo_drive or {}).get("createdTime")
    texto = str(created_time or "").strip()

    if not texto:
        return None

    try:
        data_hora = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None

    if data_hora.tzinfo is None:
        data_hora = data_hora.replace(tzinfo=UTC_TZ)

    return data_hora.astimezone(BR_TZ).date()


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
    return holerite_ja_importado_com_cache(None, colaborador_id, dados_arquivo, arquivo_drive)


def carregar_cache_holerites_colaborador(colaborador_id):
    holerites = HoleriteColaborador.query.filter_by(
        colaborador_id=colaborador_id,
    ).all()

    return {
        "google_drive_file_ids": {
            holerite.google_drive_file_id
            for holerite in holerites
            if holerite.google_drive_file_id
        },
        "chaves_fallback": {
            (holerite.competencia, holerite.tipo, holerite.nome_arquivo)
            for holerite in holerites
        },
    }


def registrar_holerite_no_cache(cache, dados_arquivo, arquivo_drive):
    if cache is None:
        return

    google_drive_file_id = arquivo_drive.get("id")

    if google_drive_file_id:
        cache["google_drive_file_ids"].add(google_drive_file_id)

    cache["chaves_fallback"].add(
        (
            dados_arquivo["competencia"],
            dados_arquivo["tipo"],
            arquivo_drive.get("name"),
        )
    )


def holerite_ja_importado_com_cache(cache, colaborador_id, dados_arquivo, arquivo_drive):
    google_drive_file_id = arquivo_drive.get("id")

    if cache is not None:
        if google_drive_file_id:
            return google_drive_file_id in cache["google_drive_file_ids"]

        return (
            dados_arquivo["competencia"],
            dados_arquivo["tipo"],
            arquivo_drive.get("name"),
        ) in cache["chaves_fallback"]

    if google_drive_file_id:
        existente = HoleriteColaborador.query.filter_by(
            google_drive_file_id=google_drive_file_id,
        ).first()

        return existente is not None

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


def _novo_estado():
    return {
        "folder_page_token": None,
        "folder_scan_concluido": False,
        "current_folder": None,
        "file_page_token": None,
        "pastas_processadas": 0,
    }


def _listar_proxima_pasta(service, folder_id, folder_page_token):
    pastas, proximo_folder_page_token = listar_itens_da_pasta_pagina(
        service,
        folder_id,
        mime_type=GOOGLE_DRIVE_FOLDER_MIME_TYPE,
        page_token=folder_page_token,
        page_size=TAMANHO_PAGINA_PASTAS,
    )

    if not pastas:
        return None, proximo_folder_page_token

    return pastas[0], proximo_folder_page_token


def sincronizar_holerites_google_drive(
    usuario_id=None,
    drive_service=None,
    folder_id=None,
    estado=None,
    limite_arquivos=TAMANHO_LOTE_PADRAO,
    data_criacao_filtro=None,
):
    resumo = ResumoSincronizacaoHolerites()
    resumo.tamanho_lote = limite_arquivos
    folder_id = folder_id or current_app.config.get("GOOGLE_DRIVE_HOLERITES_FOLDER_ID")
    estado_atual = estado.copy() if estado else _novo_estado()
    data_criacao_processada = normalizar_data_criacao_informada(data_criacao_filtro)

    if not data_criacao_processada and estado_atual.get("data_criacao_filtro"):
        data_criacao_processada = normalizar_data_criacao_informada(
            estado_atual["data_criacao_filtro"]
        )

    if data_criacao_processada:
        estado_atual["data_criacao_filtro"] = data_criacao_processada.isoformat()
        resumo.data_criacao_processada = formatar_data_criacao(data_criacao_processada)

    caches_holerites = {}

    if not folder_id:
        resumo.erros += 1
        resumo.adicionar_mensagem("Pasta principal de Holerites não configurada.")
        return resumo.como_dict()

    try:
        service = drive_service or criar_google_drive_client()
    except GoogleDriveConfiguracaoErro as exc:
        resumo.erros += 1
        resumo.adicionar_mensagem(str(exc))
        return resumo.como_dict()
    except Exception:
        resumo.erros += 1
        resumo.adicionar_mensagem("Não foi possível acessar a pasta principal de Holerites.")
        return resumo.como_dict()

    while resumo.arquivos_processados_lote < limite_arquivos:
        pasta = estado_atual.get("current_folder")

        if not pasta:
            if estado_atual.get("folder_scan_concluido"):
                resumo.concluido = True
                estado_atual = None
                break

            try:
                pasta, proximo_folder_page_token = _listar_proxima_pasta(
                    service,
                    folder_id,
                    estado_atual.get("folder_page_token"),
                )
            except Exception:
                resumo.erros += 1
                resumo.adicionar_mensagem("Não foi possível acessar a próxima pasta de Holerites.")
                break

            estado_atual["folder_page_token"] = proximo_folder_page_token
            estado_atual["folder_scan_concluido"] = proximo_folder_page_token is None
            estado_atual["current_folder"] = pasta
            estado_atual["file_page_token"] = None

            if not pasta:
                resumo.concluido = True
                estado_atual = None
                break

        nome_pasta = pasta.get("name") or ""
        matricula = extrair_matricula_pasta(nome_pasta)

        if not matricula:
            resumo.pastas_ignoradas += 1
            resumo.adicionar_mensagem(f"Pasta ignorada fora do padrão: {nome_pasta}")
            resumo.pastas_processadas += 1
            estado_atual["pastas_processadas"] = estado_atual.get("pastas_processadas", 0) + 1
            estado_atual["current_folder"] = None
            estado_atual["file_page_token"] = None
            continue

        colaborador = buscar_colaborador_por_matricula(matricula)

        if not colaborador:
            resumo.colaboradores_nao_encontrados += 1
            resumo.adicionar_mensagem(f"Colaborador não encontrado para matrícula {matricula}.")
            resumo.pastas_processadas += 1
            estado_atual["pastas_processadas"] = estado_atual.get("pastas_processadas", 0) + 1
            estado_atual["current_folder"] = None
            estado_atual["file_page_token"] = None
            continue

        if hasattr(colaborador, "ativo") and not colaborador.ativo:
            resumo.colaboradores_inativos += 1
            resumo.adicionar_mensagem(f"Colaborador inativo ignorado. Matrícula: {matricula}.")
            resumo.pastas_processadas += 1
            estado_atual["pastas_processadas"] = estado_atual.get("pastas_processadas", 0) + 1
            estado_atual["current_folder"] = None
            estado_atual["file_page_token"] = None
            continue

        try:
            tamanho_pagina = min(
                TAMANHO_PAGINA_ARQUIVOS,
                max(1, limite_arquivos - resumo.arquivos_processados_lote),
            )
            arquivos, proximo_file_page_token = listar_itens_da_pasta_pagina(
                service,
                pasta.get("id"),
                page_token=estado_atual.get("file_page_token"),
                page_size=tamanho_pagina,
            )
        except Exception:
            resumo.erros += 1
            resumo.adicionar_mensagem(f"Não foi possível ler a pasta da matrícula {matricula}.")
            resumo.pastas_processadas += 1
            estado_atual["pastas_processadas"] = estado_atual.get("pastas_processadas", 0) + 1
            estado_atual["current_folder"] = None
            estado_atual["file_page_token"] = None
            continue

        cache_holerites = caches_holerites.get(colaborador.id)

        if cache_holerites is None:
            cache_holerites = carregar_cache_holerites_colaborador(colaborador.id)
            caches_holerites[colaborador.id] = cache_holerites

        for arquivo in arquivos:
            nome_arquivo = arquivo.get("name") or ""
            resumo.arquivos_encontrados += 1
            resumo.arquivos_processados_lote += 1

            if data_criacao_processada:
                data_criacao_arquivo = data_criacao_arquivo_drive(arquivo)

                if data_criacao_arquivo != data_criacao_processada:
                    resumo.arquivos_fora_data += 1
                    continue

                resumo.arquivos_encontrados_data += 1

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

            if holerite_ja_importado_com_cache(
                cache_holerites,
                colaborador.id,
                dados_arquivo,
                arquivo,
            ):
                resumo.ja_existentes += 1
                continue

            criar_holerite(
                colaborador,
                dados_arquivo,
                arquivo,
                usuario_id=usuario_id,
            )
            registrar_holerite_no_cache(cache_holerites, dados_arquivo, arquivo)
            resumo.importados += 1

        if proximo_file_page_token:
            estado_atual["current_folder"] = pasta
            estado_atual["file_page_token"] = proximo_file_page_token
        else:
            resumo.pastas_processadas += 1
            estado_atual["pastas_processadas"] = estado_atual.get("pastas_processadas", 0) + 1
            estado_atual["current_folder"] = None
            estado_atual["file_page_token"] = None

    db.session.commit()

    if estado_atual and not resumo.concluido:
        resumo.proximo_estado = estado_atual
    else:
        resumo.concluido = True

    return resumo.como_dict()
