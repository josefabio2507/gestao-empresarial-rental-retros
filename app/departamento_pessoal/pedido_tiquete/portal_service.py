"""Integração controlada com o Portal Ticket.

O envio permanece desativado por padrão. A simulação nunca abre navegador nem
transmite arquivos. O retorno "upload_iniciado" não significa pedido aprovado.
"""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class PortalTicketError(RuntimeError):
    """Falha segura na integração com o Portal Ticket."""


class PortalTicketInteracaoHumana(PortalTicketError):
    """O portal exige MFA, CAPTCHA ou outra intervenção humana."""


@dataclass(frozen=True)
class ResultadoPortalTicket:
    status: str
    mensagem: str
    protocolo: str | None = None


def _tem_desafio_humano(page):
    seletores = (
        'iframe[src*="captcha"]',
        'iframe[title*="captcha" i]',
        '[id*="captcha" i]',
        '[class*="captcha" i]',
        'input[autocomplete="one-time-code"]',
        'input[name*="otp" i]',
    )
    return any(page.locator(seletor).count() for seletor in seletores)


def _validar_url_portal(url):
    destino = urlparse(url)
    hosts_permitidos = {"beneficios.ticket.com.br", "ticketcustomers.b2clogin.com"}
    if destino.scheme != "https" or destino.hostname not in hosts_permitidos:
        raise PortalTicketError("A URL configurada para o Portal Ticket não é permitida.")


def enviar_planilha_para_portal(
    caminho_arquivo,
    *,
    operador_id,
    confirmado,
    settings,
    playwright_factory=None,
):
    """Envia uma planilha após confirmação expressa do pedido.

    A simulação e as validações locais não iniciam navegador nem transmitem
    dados. No fluxo real, o estado retornado é apenas upload_iniciado.
    """
    arquivo = Path(caminho_arquivo)
    if arquivo.suffix.lower() != ".xlsx" or not arquivo.is_file():
        raise PortalTicketError("O arquivo do pedido não está disponível em formato XLSX.")
    if not settings.get("PEDIDO_TICKET_UPLOAD_ENABLED", False):
        raise PortalTicketError("O envio ao Portal Ticket está desabilitado.")
    if not confirmado or not operador_id:
        raise PortalTicketError("Confirme o pedido como operador autorizado antes do envio.")

    if settings.get("PEDIDO_TICKET_SIMULATION", False):
        return ResultadoPortalTicket(
            status="simulado",
            mensagem="Simulação concluída. Nenhum arquivo foi enviado ao Portal Ticket.",
        )

    login = (settings.get("PEDIDO_TICKET_PORTAL_LOGIN") or "").strip()
    senha = settings.get("PEDIDO_TICKET_PORTAL_PASSWORD") or ""
    portal_url = (settings.get("PEDIDO_TICKET_PORTAL_URL") or "https://beneficios.ticket.com.br/").strip()
    if not login or not senha:
        raise PortalTicketError("As credenciais do Portal Ticket não estão configuradas como segredos.")
    _validar_url_portal(portal_url)

    if playwright_factory is None:
        from playwright.sync_api import sync_playwright
        playwright_factory = sync_playwright

    navegador = None
    try:
        with playwright_factory() as playwright:
            navegador = playwright.chromium.launch(headless=True)
            pagina = navegador.new_page()
            pagina.set_default_timeout(30000)
            pagina.goto(portal_url, wait_until="domcontentloaded")

            if pagina.locator("#localAccountForm").count():
                pagina.get_by_label("E-mail", exact=True).fill(login)
                pagina.get_by_label("Senha", exact=True).fill(senha)
                pagina.locator("#next").click()
                pagina.wait_for_timeout(1500)

            if _tem_desafio_humano(pagina):
                raise PortalTicketInteracaoHumana(
                    "O Portal Ticket exige validação humana (MFA/CAPTCHA). Use o envio manual."
                )
            if pagina.locator("#localAccountForm").count():
                raise PortalTicketInteracaoHumana(
                    "O Portal Ticket não concluiu o login automaticamente. Use o envio manual."
                )
            if not pagina.locator("#send-ticket-file-button").count():
                raise PortalTicketError("A página de envio do Portal Ticket mudou ou não está disponível.")

            pagina.locator("#send-ticket-file-button").click()
            pagina.wait_for_function(
                "() => location.pathname === '/pedidos/novo-pedido' && "
                "new URLSearchParams(location.search).get('fileType') === 'upload-ticket'"
            )
            if _tem_desafio_humano(pagina):
                raise PortalTicketInteracaoHumana(
                    "O Portal Ticket exige validação humana. Use o envio manual."
                )
            seletor_arquivo = pagina.locator("#sheetFileInput")
            if not seletor_arquivo.count():
                raise PortalTicketError("O campo de arquivo do Portal Ticket não foi encontrado.")

            seletor_arquivo.set_input_files(str(arquivo))
            pagina.wait_for_timeout(1000)
            if _tem_desafio_humano(pagina):
                raise PortalTicketInteracaoHumana(
                    "O Portal Ticket exige validação humana. Confira o envio manualmente."
                )

            return ResultadoPortalTicket(
                status="upload_iniciado",
                mensagem="Upload iniciado no Portal Ticket; processamento e aprovação ainda não confirmados.",
            )
    except PortalTicketError:
        raise
    except Exception:
        raise PortalTicketError(
            "Não foi possível concluir o upload no Portal Ticket. Use o download e o envio manual."
        ) from None
    finally:
        if navegador is not None:
            navegador.close()
