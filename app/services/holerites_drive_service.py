import re
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


PADRAO_PASTA_COLABORADOR = re.compile(r"^\s*(?P<matricula>[^-\s][^-]*)\s+-\s+.+$")
PADRAO_ARQUIVO_HOLERITE = re.compile(
    r"^\s*(?P<matricula>[^-\s][^-]*)\s+-\s+"
    r"(?P<tipo>.+?)\s+-\s+"
    r"(?P<competencia>\d{2}\.\d{4})\s+-\s+"
    r"(?P<nome>.+)\.pdf\s*$",
    re.IGNORECASE,
)


@dataclass
class ResumoSincronizacaoHolerites:
    arquivos_encontrados: int = 0
    importados: int = 0
    ja_existentes: int = 0
    pastas_ignoradas: int = 0
    colaboradores_nao_encontrados: int = 0
    arquivos_fora_padrao: int = 0
    arquivos_nao_pdf: int = 0
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
            "erros": self.erros,
            "mensagens": self.mensagens,
        }


def extrair_matricula_pasta(nome_pasta):
    correspondencia = PADRAO_PASTA_COLABORADOR.match(nome_pasta or "")

    if not correspondencia:
        return None

    return correspondencia.group("matricula").strip()


def interpretar_nome_arquivo_holerite(nome_arquivo):
    correspondencia = PADRAO_ARQUIVO_HOLERITE.match(nome_arquivo or "")

    if not correspondencia:
        return None

    return {
        "matricula": correspondencia.group("matricula").strip(),
        "tipo": correspondencia.group("tipo").strip(),
        "competencia": correspondencia.group("competencia").strip(),
        "nome": correspondencia.group("nome").strip(),
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

        colaborador = Colaborador.query.filter_by(matricula=matricula).first()

        if not colaborador:
            resumo.colaboradores_nao_encontrados += 1
            resumo.adicionar_mensagem(f"Colaborador não encontrado para matrícula {matricula}.")
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

            dados_arquivo = interpretar_nome_arquivo_holerite(nome_arquivo)

            if not dados_arquivo:
                resumo.arquivos_fora_padrao += 1
                resumo.adicionar_mensagem(f"Arquivo fora do padrão: {nome_arquivo}")
                continue

            if dados_arquivo["matricula"] != matricula:
                resumo.arquivos_fora_padrao += 1
                resumo.adicionar_mensagem(
                    f"Arquivo com matrícula diferente da pasta: {nome_arquivo}"
                )
                continue

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
