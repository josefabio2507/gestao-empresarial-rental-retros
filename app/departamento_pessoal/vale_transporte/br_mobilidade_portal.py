from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Callable, Iterable
from urllib.parse import urljoin

from app.departamento_pessoal.vale_transporte.br_mobilidade_conferencia import (
    ResumoPedidoPortal,
    conferir_resumo_pedido,
)


PORTAL_URL_PADRAO = "https://portalvt.brmobilidadebs.com.br/wfm_default.aspx"
MENSAGEM_ENVIO_ACEITO = "Seu arquivo foi enviado para execução"


class BRMobilidadePortalErro(RuntimeError):
    """Falha controlada durante login ou envio ao Portal BR Mobilidade."""


class BRMobilidadeFinalizacaoIncerta(BRMobilidadePortalErro):
    """O clique final ocorreu, mas não foi possível confirmar o resultado."""


@dataclass(frozen=True)
class ResultadoEnvioBRMobilidade:
    nome_arquivo: str
    enviado_em: datetime
    mensagem_portal: str


@dataclass(frozen=True)
class ErroImportacaoBRMobilidade:
    linha: int | None
    mensagem: str


@dataclass(frozen=True)
class StatusImportacaoBRMobilidade:
    nome_arquivo: str
    processado_em: datetime
    status: str
    comentario: str
    erros: tuple[ErroImportacaoBRMobilidade, ...] = ()

    @property
    def processado_com_sucesso(self):
        return "sucesso" in self.status.casefold()

    @property
    def possui_erro(self):
        return "erro" in self.status.casefold()


@dataclass(frozen=True)
class ResultadoFinalizacaoBRMobilidade:
    numero_pedido: str
    status: str
    finalizado_em: datetime
    resumo: ResumoPedidoPortal


@dataclass(frozen=True)
class ResultadoDocumentosBRMobilidade:
    numero_pedido: str
    status: str
    valor_historico: Decimal
    boleto_pdf: bytes
    relatorio_pdf: bytes
    relatorio_texto: str
    capturado_em: datetime


def _contextos_da_pagina(page) -> Iterable:
    """Devolve a página e seus frames, pois o portal ASP.NET usa frames."""
    yield page
    for frame in page.frames:
        if frame != page.main_frame:
            yield frame


def _localizador_visivel(page, seletores):
    for contexto in _contextos_da_pagina(page):
        for seletor in seletores:
            localizador = contexto.locator(seletor)
            try:
                for indice in range(localizador.count()):
                    candidato = localizador.nth(indice)
                    if candidato.is_visible():
                        return candidato
            except Exception:
                continue
    return None


def _preencher(page, seletores, valor, descricao):
    localizador = _localizador_visivel(page, seletores)
    if localizador is None:
        raise BRMobilidadePortalErro(
            f"Não foi possível localizar o campo de {descricao} no Portal BR Mobilidade."
        )
    localizador.fill(valor)


def _clicar(page, seletores, descricao, *, force=False):
    localizador = _localizador_visivel(page, seletores)
    if localizador is None:
        raise BRMobilidadePortalErro(
            f"Não foi possível localizar {descricao} no Portal BR Mobilidade."
        )
    localizador.click(force=force)


def _texto_visivel(page, texto):
    for contexto in _contextos_da_pagina(page):
        try:
            if contexto.get_by_text(texto, exact=False).first.is_visible():
                return True
        except Exception:
            continue
    return False


def _aguardar_condicao(page, condicao: Callable[[], bool], timeout_ms, erro):
    intervalo_ms = 250
    tentativas = max(1, timeout_ms // intervalo_ms)
    for _ in range(tentativas):
        if condicao():
            return
        page.wait_for_timeout(intervalo_ms)
    raise BRMobilidadePortalErro(erro)


def _validar_arquivo_para_upload(caminho_arquivo):
    caminho = Path(caminho_arquivo).resolve()
    if not caminho.is_file():
        raise BRMobilidadePortalErro("Arquivo BR Mobilidade não encontrado para envio.")
    if caminho.suffix.lower() != ".txt":
        raise BRMobilidadePortalErro("O arquivo BR Mobilidade deve possuir extensão .txt.")
    if caminho.read_bytes().splitlines()[:1] != [b"0200"]:
        raise BRMobilidadePortalErro("O arquivo informado não possui o cabeçalho 0200.")
    return caminho


def _autenticar(page, login, senha, portal_url, timeout_ms):
    page.set_default_timeout(timeout_ms)
    page.goto(portal_url, wait_until="domcontentloaded")
    _aguardar_condicao(
        page,
        lambda: _localizador_visivel(
            page,
            ("#txtDocNumber", "input[type='password']"),
        )
        is not None,
        timeout_ms,
        "A tela de login do Portal BR Mobilidade não foi carregada.",
    )
    _preencher(
        page,
        (
            "#txtDocNumber",
            "input[type='text'][name*='login' i]",
            "input[type='text'][id*='login' i]",
            "input[type='text'][name*='usuario' i]",
            "input[type='text'][id*='usuario' i]",
            "input[type='text']",
        ),
        str(login).strip(),
        "login",
    )
    _preencher(
        page,
        ("input[type='password']", "input[name*='senha' i]", "input[id*='senha' i]"),
        senha,
        "senha",
    )
    _clicar(
        page,
        (
            "#loginbutton",
            "input[type='button'][value='OK' i]",
            "input[type='submit'][value*='Entrar' i]",
            "button:has-text('Entrar')",
            "input[type='image']",
            "input[type='submit']",
        ),
        "o botão de entrada",
    )
    _aguardar_condicao(
        page,
        lambda: _texto_visivel(page, "Pedidos"),
        timeout_ms,
        "O login no Portal BR Mobilidade não foi confirmado.",
    )


def _abrir_menu_importar(page):
    _clicar(page, ("a:has-text('Pedidos')",), "o menu Pedidos")
    _clicar(page, ("a:has-text('Importar')",), "Pedidos > Importar")


def _abrir_menu_incluir(page):
    _clicar(page, ("a:has-text('Pedidos')",), "o menu Pedidos")
    _clicar(
        page,
        (
            "a[href*='wfm_Orders_Ins_SelType.aspx']",
            "a:has-text('Incluir')",
        ),
        "Pedidos > Incluir",
    )


def _moeda_portal(texto):
    valor = str(texto or "").strip().replace("R$", "").replace(" ", "")
    valor = valor.replace(".", "").replace(",", ".")
    try:
        return Decimal(valor).quantize(Decimal("0.01"))
    except InvalidOperation as erro:
        raise BRMobilidadePortalErro(
            f"O Portal retornou um valor monetário inválido: {texto}."
        ) from erro


def _campo_resumo(texto, rotulo):
    padrao = rf"{re.escape(rotulo)}\s*:?\s*(?:\r?\n\s*)?([^\r\n]+)"
    encontrado = re.search(padrao, texto, flags=re.IGNORECASE)
    if not encontrado:
        raise BRMobilidadePortalErro(
            f"O Portal não exibiu o campo {rotulo} na conferência."
        )
    return encontrado.group(1).strip()


def _resumo_revisao_por_texto(texto, quantidade_usuarios):
    """Interpreta o texto do Passo 4 sem depender da posição visual dos campos."""
    try:
        return ResumoPedidoPortal(
            numero="",
            data_pedido=datetime.strptime(
                _campo_resumo(texto, "Data do Pedido"), "%d/%m/%Y"
            ).date(),
            data_liberacao=datetime.strptime(
                _campo_resumo(texto, "Data de Liberação"), "%d/%m/%Y"
            ).date(),
            status=_campo_resumo(texto, "Status do Pedido"),
            valor_creditos=_moeda_portal(_campo_resumo(texto, "Valor do Pedido")),
            taxa_administrativa=_moeda_portal(
                _campo_resumo(texto, "Taxa Administrativa")
            ),
            valor_cartoes=_moeda_portal(
                _campo_resumo(texto, "Valor de Impressão de Cartões")
            ),
            valor_total=_moeda_portal(_campo_resumo(texto, "Valor Total")),
            quantidade_usuarios=quantidade_usuarios,
        )
    except ValueError as erro:
        raise BRMobilidadePortalErro(
            "O Portal retornou uma data inválida na conferência do pedido."
        ) from erro


def _contexto_revisao(page):
    for contexto in _contextos_da_pagina(page):
        try:
            texto = contexto.locator("body").inner_text()
            if "Data do Pedido" in texto and "Valor Total" in texto:
                return contexto, texto
        except Exception:
            continue
    raise BRMobilidadePortalErro("A tela de conferência do pedido não foi carregada.")


def _quantidade_usuarios_revisao(contexto):
    tabelas = contexto.locator("table")
    candidatas = []
    for indice in range(tabelas.count()):
        tabela = tabelas.nth(indice)
        try:
            texto = tabela.inner_text()
            if "Usuário" not in texto or "Cartão" not in texto or "Remover" not in texto:
                continue
            candidatas.append((len(texto), tabela))
        except Exception:
            continue
    for _, tabela in sorted(candidatas, key=lambda item: item[0]):
        quantidade = 0
        linhas = tabela.locator(":scope > tbody > tr")
        for linha_indice in range(linhas.count()):
            celulas = linhas.nth(linha_indice).locator(":scope > td")
            if celulas.count() < 3:
                continue
            primeiro = celulas.nth(0).inner_text().strip()
            if primeiro and primeiro.casefold() != "usuário":
                quantidade += 1
        if quantidade:
            return quantidade
    raise BRMobilidadePortalErro(
        "Não foi possível contar os usuários na conferência do pedido."
    )


def _cpf_normalizado(valor):
    return re.sub(r"\D", "", str(valor or ""))


def _numero_pedido_da_celula(valor):
    """Aceita somente uma célula cujo conteúdo inteiro seja o número do pedido."""
    texto = str(valor or "").strip()
    return texto if re.fullmatch(r"\d{5,15}", texto) else None


def _linha_historico_por_numero(page, numero_pedido):
    candidatas = []
    for contexto in _contextos_da_pagina(page):
        linhas = contexto.locator("tr")
        for indice in range(linhas.count()):
            linha = linhas.nth(indice)
            try:
                celulas = linha.locator(":scope > td")
                if celulas.count() < 5:
                    continue
                numero = _numero_pedido_da_celula(celulas.nth(0).inner_text())
                if numero == numero_pedido:
                    candidatas.append((len(linha.inner_text()), linha))
            except Exception:
                continue
    return min(candidatas, key=lambda item: item[0])[1] if candidatas else None


def _abrir_historico_e_localizar(page, numero_pedido, timeout_ms):
    _clicar(page, ("a:has-text('Pedidos')",), "o menu Pedidos")
    _clicar(
        page,
        ("a:has-text('Histórico de Pedidos')",),
        "Pedidos > Histórico de Pedidos",
    )
    _aguardar_condicao(
        page,
        lambda: _texto_visivel(page, "Histórico de Pedidos"),
        timeout_ms,
        "O Histórico de Pedidos não foi carregado.",
    )

    if _linha_historico_por_numero(page, numero_pedido) is None:
        campo = _localizador_visivel(page, ("#txtUsuario",))
        pesquisar = _localizador_visivel(page, ("#query",))
        if campo is not None and pesquisar is not None:
            campo.fill(numero_pedido)
            pesquisar.click()
    _aguardar_condicao(
        page,
        lambda: _linha_historico_por_numero(page, numero_pedido) is not None,
        timeout_ms,
        f"O pedido {numero_pedido} não foi localizado no Histórico do Portal.",
    )
    return _linha_historico_por_numero(page, numero_pedido)


def _linha_usuario_por_cpf(contexto, cpf):
    candidatos = []
    linhas = contexto.locator("tr")
    for indice in range(linhas.count()):
        linha = linhas.nth(indice)
        try:
            texto = " ".join(linha.inner_text().split())
            if cpf not in _cpf_normalizado(texto):
                continue
            if linha.locator("input[type='checkbox']").count() != 1:
                continue
            if not linha.locator("input[type='text']").count():
                continue
            candidatos.append((len(texto), linha))
        except Exception:
            continue
    return min(candidatos, key=lambda item: item[0])[1] if candidatos else None


def _linha_usuario(page, cpf, nome, timeout_ms=30000):
    """Filtra o Passo 2 pelo CPF e devolve exatamente a linha encontrada."""
    cpf = _cpf_normalizado(cpf)
    if len(cpf) != 11:
        raise BRMobilidadePortalErro(
            f"O CPF do colaborador {nome} é inválido para pesquisa no Portal."
        )

    for contexto in _contextos_da_pagina(page):
        campo_documento = contexto.locator("#txtCode")
        botao_filtrar = contexto.locator("#query")
        if not campo_documento.count() or not botao_filtrar.count():
            continue
        try:
            if not campo_documento.is_visible():
                expandir = contexto.locator(
                    "a[onclick*='content'][onclick*='inline']"
                )
                for indice in range(expandir.count()):
                    controle = expandir.nth(indice)
                    if controle.is_visible():
                        controle.click()
                        break
            campo_documento.fill(cpf)
            botao_filtrar.click()

            intervalo_ms = 250
            for _ in range(max(1, timeout_ms // intervalo_ms)):
                linha = _linha_usuario_por_cpf(contexto, cpf)
                if linha is not None:
                    return linha
                page.wait_for_timeout(intervalo_ms)
        except Exception:
            continue
    raise BRMobilidadePortalErro(
        f"O CPF {cpf} do colaborador {nome} não foi localizado no Portal BR Mobilidade."
    )


def _quantidade_itens_passo_2(page):
    for contexto in _contextos_da_pagina(page):
        try:
            texto = contexto.locator("body").inner_text()
            encontrado = re.search(
                r"Quantidade\s+de\s+Itens\s+no\s+Pedido\s*:\s*(\d+)",
                texto,
                flags=re.IGNORECASE,
            )
            if encontrado:
                return int(encontrado.group(1))
        except Exception:
            continue
    return None


def _preencher_valor_pedido(page, valor):
    """Digita centavos para acionar a máscara JavaScript do campo global Valor."""
    campo = _localizador_visivel(page, ("#txtValue",))
    if campo is None:
        raise BRMobilidadePortalErro(
            "O campo de valor do pedido não foi localizado no Portal."
        )
    centavos = int((Decimal(valor) * 100).quantize(Decimal("1")))
    if centavos <= 0:
        raise BRMobilidadePortalErro("O valor do colaborador deve ser maior que zero.")
    campo.click()
    campo.press("Control+A")
    campo.press("Backspace")
    campo.press_sequentially(str(centavos), delay=30)
    campo.press("Tab")


def _avancar_ate(page, seletor_destino, timeout_ms, descricao, *, force=False):
    for _ in range(2):
        _clicar(
            page,
            ("#btnNext", "input[value='Próximo Passo']", "button:has-text('Próximo Passo')"),
            "Próximo Passo",
            force=force,
        )
        try:
            _aguardar_condicao(
                page,
                lambda: _localizador_visivel(page, (seletor_destino,)) is not None,
                timeout_ms,
                descricao,
            )
            return
        except BRMobilidadePortalErro:
            continue
    raise BRMobilidadePortalErro(descricao)


def _executar_fluxo_manual(
    page,
    registros,
    data_liberacao,
    timeout_ms,
    *,
    finalizar,
    resumo_autorizado=None,
):
    _abrir_menu_incluir(page)
    _aguardar_condicao(
        page,
        lambda: _localizador_visivel(page, ("select",)) is not None,
        timeout_ms,
        "O Passo 1 da inclusão de pedidos não foi carregado.",
    )
    seletor_tipo = _localizador_visivel(page, ("select",))
    seletor_tipo.select_option(label="Valor por usuário")
    _avancar_ate(
        page,
        "#txtValue",
        timeout_ms,
        "O Passo 2 da inclusão de pedidos não foi carregado.",
    )

    for quantidade_adicionada, registro in enumerate(registros, start=1):
        linha = _linha_usuario(page, registro.cpf, registro.nome, timeout_ms)
        checkbox = linha.locator("input[type='checkbox']").first
        _preencher_valor_pedido(page, registro.valor_total)
        checkbox.check()
        _clicar(page, ("#btnAdd",), "o botão Adicionar")
        _aguardar_condicao(
            page,
            lambda: _quantidade_itens_passo_2(page) == quantidade_adicionada,
            timeout_ms,
            f"O Portal não confirmou a inclusão de {registro.nome} no pedido.",
        )

    _avancar_ate(
        page,
        "#txtMemoDate",
        timeout_ms,
        "O Passo 3 da data de liberação não foi carregado.",
        force=True,
    )
    _preencher(
        page,
        ("#txtMemoDate",),
        data_liberacao.strftime("%d/%m/%Y"),
        "data de liberação",
    )
    _clicar(
        page,
        ("#btnConfirm", "input[value='Próximo Passo']", "button:has-text('Próximo Passo')"),
        "Próximo Passo",
    )
    _aguardar_condicao(
        page,
        lambda: _texto_visivel(page, "Finalizar Pedido"),
        timeout_ms,
        "O Passo 4 de conferência não foi carregado.",
    )

    contexto, texto = _contexto_revisao(page)
    resumo = _resumo_revisao_por_texto(
        texto,
        _quantidade_usuarios_revisao(contexto),
    )
    esperado = type(
        "Esperado",
        (),
        {
            "numero_pedido_portal": None,
            "quantidade_colaboradores": len(registros),
            "valor_creditos": sum(
                (registro.valor_total for registro in registros), Decimal("0.00")
            ),
            "data_liberacao": data_liberacao,
        },
    )()
    conferencia = conferir_resumo_pedido(esperado, resumo)
    if not conferencia.aprovado:
        raise BRMobilidadePortalErro(
            "Pedido não finalizado. " + " ".join(conferencia.divergencias)
        )
    if resumo_autorizado is not None:
        campos_autorizados = (
            ("data do pedido", resumo.data_pedido, resumo_autorizado.data_pedido),
            ("data de liberação", resumo.data_liberacao, resumo_autorizado.data_liberacao),
            ("status", resumo.status, resumo_autorizado.status),
            ("valor dos créditos", resumo.valor_creditos, resumo_autorizado.valor_creditos),
            ("taxa administrativa", resumo.taxa_administrativa, resumo_autorizado.taxa_administrativa),
            ("valor de cartões", resumo.valor_cartoes, resumo_autorizado.valor_cartoes),
            ("valor total", resumo.valor_total, resumo_autorizado.valor_total),
            ("quantidade de usuários", resumo.quantidade_usuarios, resumo_autorizado.quantidade_usuarios),
        )
        divergentes = [
            rotulo
            for rotulo, atual, autorizado in campos_autorizados
            if atual != autorizado
        ]
        if divergentes:
            raise BRMobilidadePortalErro(
                "Pedido não finalizado. A revisão atual diverge da autorizada em: "
                + ", ".join(divergentes)
                + "."
            )
    if not finalizar:
        return resumo, None

    try:
        page.once("dialog", lambda dialog: dialog.accept())
    except Exception:
        pass
    _clicar(
        page,
        (
            "input[value*='Finalizar Pedido' i]",
            "button:has-text('Finalizar Pedido')",
        ),
        "Finalizar Pedido",
    )
    try:
        _aguardar_condicao(
            page,
            lambda: _texto_visivel(page, "Histórico de Pedidos"),
            timeout_ms,
            "O Portal não confirmou a finalização nem abriu o histórico.",
        )

        data_pedido = resumo.data_pedido.strftime("%d/%m/%Y")
        data_liberacao_texto = resumo.data_liberacao.strftime("%d/%m/%Y")
        total_texto = f"{resumo.valor_total:.2f}".replace(".", ",")
        for contexto_atual in _contextos_da_pagina(page):
            linhas = contexto_atual.locator("tr")
            for indice in range(linhas.count()):
                linha = linhas.nth(indice)
                try:
                    celulas = linha.locator(":scope > td")
                    if celulas.count() < 5:
                        continue
                    numero = _numero_pedido_da_celula(celulas.nth(0).inner_text())
                    if not numero:
                        continue
                    texto_linha = " ".join(linha.inner_text().split())
                    if (
                        data_pedido in texto_linha
                        and data_liberacao_texto in texto_linha
                        and total_texto in texto_linha
                    ):
                        status = celulas.nth(4).inner_text().strip() or "Novo"
                        return resumo, (numero, status)
                except Exception:
                    continue
    except Exception as erro:
        raise BRMobilidadeFinalizacaoIncerta(
            "O clique de finalização ocorreu, mas o Portal não confirmou o resultado. "
            "Não repita automaticamente; confira o histórico manualmente."
        ) from erro
    raise BRMobilidadeFinalizacaoIncerta(
        "O clique de finalização ocorreu, mas o pedido não foi identificado no histórico. "
        "Não repita automaticamente; confira o histórico manualmente."
    )


def executar_pedido_manual_br_mobilidade(
    registros,
    data_liberacao,
    *,
    login,
    senha,
    autorizar_finalizacao=False,
    resumo_autorizado=None,
    portal_url=PORTAL_URL_PADRAO,
    headless=True,
    timeout_ms=30000,
    executable_path=None,
    playwright_factory=None,
    agora=None,
):
    """Reproduz os Passos 1–4 e só finaliza com autorização explícita."""
    registros = tuple(registros or ())
    if not registros:
        raise BRMobilidadePortalErro("Nenhum colaborador foi informado para o pedido.")
    if not isinstance(data_liberacao, date):
        raise BRMobilidadePortalErro("A data de liberação do pedido é inválida.")
    if not str(login or "").strip() or not senha:
        raise BRMobilidadePortalErro(
            "Credenciais da BR Mobilidade não foram configuradas no ambiente."
        )

    playwright_factory = _obter_playwright_factory(playwright_factory)
    navegador = None
    try:
        with playwright_factory() as playwright:
            navegador = playwright.chromium.launch(
                **_opcoes_navegador(headless, executable_path)
            )
            page = navegador.new_context().new_page()
            _autenticar(page, login, senha, portal_url, timeout_ms)
            resumo, resultado = _executar_fluxo_manual(
                page,
                registros,
                data_liberacao,
                timeout_ms,
                finalizar=bool(autorizar_finalizacao),
                resumo_autorizado=resumo_autorizado,
            )
            if not autorizar_finalizacao:
                return resumo
            numero, status = resultado
            return ResultadoFinalizacaoBRMobilidade(
                numero_pedido=numero,
                status=status,
                finalizado_em=(agora or datetime.now)(),
                resumo=resumo,
            )
    except BRMobilidadePortalErro:
        raise
    except Exception as erro:
        raise BRMobilidadePortalErro(
            "Falha inesperada no fluxo manual do Portal BR Mobilidade. "
            "Não repita automaticamente antes de consultar o histórico."
        ) from erro
    finally:
        if navegador is not None:
            try:
                navegador.close()
            except Exception:
                pass


def executar_pedido_manual_br_mobilidade_com_config(
    registros,
    data_liberacao,
    config,
    **opcoes,
):
    return executar_pedido_manual_br_mobilidade(
        registros,
        data_liberacao,
        login=config.get("BR_MOBILIDADE_LOGIN"),
        senha=config.get("BR_MOBILIDADE_SENHA"),
        portal_url=config.get("BR_MOBILIDADE_PORTAL_URL", PORTAL_URL_PADRAO),
        headless=config.get("BR_MOBILIDADE_HEADLESS", True),
        timeout_ms=config.get("BR_MOBILIDADE_TIMEOUT_MS", 30000),
        executable_path=config.get("BR_MOBILIDADE_BROWSER_EXECUTABLE_PATH") or None,
        **opcoes,
    )


def capturar_documentos_br_mobilidade(
    numero_pedido,
    *,
    login,
    senha,
    portal_url=PORTAL_URL_PADRAO,
    headless=True,
    timeout_ms=30000,
    executable_path=None,
    playwright_factory=None,
    agora=None,
):
    """Baixa o boleto original e gera o PDF do relatório de um pedido."""
    numero_pedido = str(numero_pedido or "").strip()
    if not _numero_pedido_da_celula(numero_pedido):
        raise BRMobilidadePortalErro("Número do pedido inválido para captura.")
    if not str(login or "").strip() or not senha:
        raise BRMobilidadePortalErro(
            "Credenciais da BR Mobilidade não foram configuradas no ambiente."
        )

    playwright_factory = _obter_playwright_factory(playwright_factory)
    navegador = None
    try:
        with playwright_factory() as playwright:
            navegador = playwright.chromium.launch(
                **_opcoes_navegador(headless, executable_path)
            )
            contexto_navegador = navegador.new_context(
                accept_downloads=True,
                # O Chromium aceita a cadeia do Portal pelo repositório do
                # Windows; o cliente HTTP interno precisa desta equivalência.
                ignore_https_errors=True,
            )
            page = contexto_navegador.new_page()
            _autenticar(page, login, senha, portal_url, timeout_ms)
            linha = _abrir_historico_e_localizar(page, numero_pedido, timeout_ms)
            celulas = linha.locator(":scope > td")
            valor_historico = _moeda_portal(celulas.nth(2).inner_text())
            status = celulas.nth(4).inner_text().strip() or "Novo"

            detalhe = linha.locator("a[onclick*='DetailOrder']").first
            onclick = detalhe.get_attribute("onclick") or ""
            parametros = re.search(
                r"DetailOrder\((\d+),\s*(\d+),\s*(\d+)\)", onclick
            )
            if not parametros:
                raise BRMobilidadePortalErro(
                    "O Portal não informou os parâmetros dos documentos do pedido."
                )
            provedor, transacao, sequencia = parametros.groups()
            base_pages = urljoin(portal_url, "/Pages/")

            resposta_boleto = contexto_navegador.request.get(
                urljoin(
                    base_pages,
                    "wfm_Billet.aspx?"
                    f"ProviderID={provedor}&TransactionID={transacao}"
                    f"&SequenceID={sequencia}",
                ),
                timeout=timeout_ms,
            )
            boleto_pdf = resposta_boleto.body()
            content_type = (
                resposta_boleto.headers.get("content-type", "")
            )
            if (
                not resposta_boleto.ok
                or "application/pdf" not in content_type
                or not boleto_pdf.startswith(b"%PDF")
            ):
                raise BRMobilidadePortalErro(
                    "O Portal não retornou um boleto PDF válido para este pedido."
                )

            pagina_relatorio = contexto_navegador.new_page()
            resposta_relatorio = pagina_relatorio.goto(
                urljoin(
                    base_pages,
                    "wfm_Order_Itens_Print.aspx?"
                    f"PRV_ID={provedor}&ROM_TRANID={transacao}"
                    f"&ROM_SEQNBR={sequencia}",
                ),
                wait_until="networkidle",
                timeout=timeout_ms,
            )
            if not resposta_relatorio or not resposta_relatorio.ok:
                raise BRMobilidadePortalErro(
                    "O relatório do pedido não foi carregado pelo Portal."
                )
            relatorio_texto = " ".join(
                pagina_relatorio.locator("body").inner_text().split()
            )
            if numero_pedido not in relatorio_texto:
                raise BRMobilidadePortalErro(
                    "O relatório retornado pertence a outro pedido."
                )
            pagina_relatorio.emulate_media(media="print")
            relatorio_pdf = pagina_relatorio.pdf(
                format="A4",
                print_background=True,
                margin={"top": "10mm", "right": "10mm", "bottom": "10mm", "left": "10mm"},
            )
            if not relatorio_pdf.startswith(b"%PDF"):
                raise BRMobilidadePortalErro(
                    "Não foi possível gerar o PDF do relatório do pedido."
                )

            return ResultadoDocumentosBRMobilidade(
                numero_pedido=numero_pedido,
                status=status,
                valor_historico=valor_historico,
                boleto_pdf=boleto_pdf,
                relatorio_pdf=relatorio_pdf,
                relatorio_texto=relatorio_texto,
                capturado_em=(agora or datetime.now)(),
            )
    except BRMobilidadePortalErro:
        raise
    except Exception as erro:
        raise BRMobilidadePortalErro(
            "Não foi possível capturar o boleto e o relatório no Portal BR Mobilidade."
        ) from erro
    finally:
        if navegador is not None:
            try:
                navegador.close()
            except Exception:
                pass


def capturar_documentos_br_mobilidade_com_config(numero_pedido, config, **opcoes):
    return capturar_documentos_br_mobilidade(
        numero_pedido,
        login=config.get("BR_MOBILIDADE_LOGIN"),
        senha=config.get("BR_MOBILIDADE_SENHA"),
        portal_url=config.get("BR_MOBILIDADE_PORTAL_URL", PORTAL_URL_PADRAO),
        headless=config.get("BR_MOBILIDADE_HEADLESS", True),
        timeout_ms=config.get("BR_MOBILIDADE_TIMEOUT_MS", 30000),
        executable_path=config.get("BR_MOBILIDADE_BROWSER_EXECUTABLE_PATH") or None,
        **opcoes,
    )


def _opcoes_navegador(headless, executable_path):
    opcoes = {"headless": bool(headless)}
    if executable_path:
        opcoes["executable_path"] = executable_path
    return opcoes


def _obter_playwright_factory(playwright_factory):
    if playwright_factory is not None:
        return playwright_factory
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as erro:
        raise BRMobilidadePortalErro(
            "Playwright não está instalado no ambiente da aplicação."
        ) from erro
    return sync_playwright


def enviar_arquivo_br_mobilidade(
    caminho_arquivo,
    *,
    login,
    senha,
    portal_url=PORTAL_URL_PADRAO,
    headless=True,
    timeout_ms=30000,
    executable_path=None,
    playwright_factory=None,
    agora=None,
):
    """Efetua somente login e upload; não consulta status nem finaliza pedido."""
    caminho = _validar_arquivo_para_upload(caminho_arquivo)
    if not str(login or "").strip() or not senha:
        raise BRMobilidadePortalErro(
            "Credenciais da BR Mobilidade não foram configuradas no ambiente."
        )

    playwright_factory = _obter_playwright_factory(playwright_factory)

    navegador = None
    try:
        with playwright_factory() as playwright:
            navegador = playwright.chromium.launch(
                **_opcoes_navegador(headless, executable_path)
            )
            contexto = navegador.new_context()
            page = contexto.new_page()
            _autenticar(page, login, senha, portal_url, timeout_ms)
            _abrir_menu_importar(page)
            _clicar(
                page,
                (
                    "a[href*='wfm_Orders_Archive_Ins.aspx']",
                    "a:has-text('Processar')",
                ),
                "Pedidos > Importar > Processar",
            )
            _aguardar_condicao(
                page,
                lambda: _localizador_visivel(page, ("input[type='file']",)) is not None,
                timeout_ms,
                "A tela de importação não foi carregada.",
            )

            campo_arquivo = _localizador_visivel(page, ("input[type='file']",))
            campo_arquivo.set_input_files(str(caminho))
            _clicar(
                page,
                (
                    "input[type='submit'][value*='Processar' i]",
                    "button:has-text('Processar')",
                    "input[type='submit']",
                ),
                "o botão Processar",
            )

            _aguardar_condicao(
                page,
                lambda: _texto_visivel(page, MENSAGEM_ENVIO_ACEITO),
                timeout_ms,
                "O Portal BR Mobilidade não confirmou o recebimento do arquivo.",
            )
            return ResultadoEnvioBRMobilidade(
                nome_arquivo=caminho.name,
                enviado_em=(agora or datetime.now)(),
                mensagem_portal=MENSAGEM_ENVIO_ACEITO,
            )
    except BRMobilidadePortalErro:
        raise
    except Exception as erro:
        raise BRMobilidadePortalErro(
            "Não foi possível concluir o login e o upload no Portal BR Mobilidade."
        ) from erro
    finally:
        if navegador is not None:
            try:
                navegador.close()
            except Exception:
                # O encerramento do Playwright pode já ter fechado o navegador.
                pass


def enviar_arquivo_br_mobilidade_com_config(caminho_arquivo, config, **opcoes):
    """Adapta a configuração Flask sem expor credenciais em parâmetros de rota."""
    return enviar_arquivo_br_mobilidade(
        caminho_arquivo,
        login=config.get("BR_MOBILIDADE_LOGIN"),
        senha=config.get("BR_MOBILIDADE_SENHA"),
        portal_url=config.get("BR_MOBILIDADE_PORTAL_URL", PORTAL_URL_PADRAO),
        headless=config.get("BR_MOBILIDADE_HEADLESS", True),
        timeout_ms=config.get("BR_MOBILIDADE_TIMEOUT_MS", 30000),
        executable_path=config.get("BR_MOBILIDADE_BROWSER_EXECUTABLE_PATH") or None,
        **opcoes,
    )


def consultar_status_arquivo_br_mobilidade(
    nome_arquivo,
    *,
    login,
    senha,
    portal_url=PORTAL_URL_PADRAO,
    headless=True,
    timeout_ms=30000,
    executable_path=None,
    playwright_factory=None,
):
    """Consulta a ocorrência mais recente do arquivo e seus erros detalhados."""
    nome_procurado = Path(nome_arquivo).name.upper()
    if not nome_procurado:
        raise BRMobilidadePortalErro("Nome do arquivo não informado para consulta.")
    if not str(login or "").strip() or not senha:
        raise BRMobilidadePortalErro(
            "Credenciais da BR Mobilidade não foram configuradas no ambiente."
        )

    playwright_factory = _obter_playwright_factory(playwright_factory)
    navegador = None
    try:
        with playwright_factory() as playwright:
            navegador = playwright.chromium.launch(
                **_opcoes_navegador(headless, executable_path)
            )
            page = navegador.new_context().new_page()
            _autenticar(page, login, senha, portal_url, timeout_ms)
            _abrir_menu_importar(page)
            _clicar(
                page,
                ("a[href*='ARCHIVETYPE=O']",),
                "Pedidos > Importar > Status",
            )

            def frame_status():
                for frame in page.frames:
                    if "wfm_Providers_Archive_Lst.aspx" in frame.url:
                        return frame
                return None

            _aguardar_condicao(
                page,
                lambda: frame_status() is not None,
                timeout_ms,
                "A tela de status da importação não foi carregada.",
            )
            frame = frame_status()
            linhas = frame.locator("#dgdUsuarios tr")
            registro = None
            for indice in range(1, linhas.count()):
                linha = linhas.nth(indice)
                celulas = linha.locator("td")
                if celulas.count() < 4:
                    continue
                arquivo = (celulas.nth(1).get_attribute("title") or "").strip().upper()
                if arquivo == nome_procurado:
                    registro = linha
                    break

            if registro is None:
                raise BRMobilidadePortalErro(
                    f"O arquivo {nome_procurado} não foi encontrado no status do Portal."
                )

            celulas = registro.locator("td")
            data_texto = celulas.nth(0).inner_text().strip()
            status = celulas.nth(2).inner_text().strip()
            comentario = celulas.nth(3).inner_text().strip()
            erros = []
            link_detalhes = celulas.nth(2).locator("a")
            if link_detalhes.count():
                link_detalhes.first.click()

                def frame_detalhes():
                    for frame_atual in page.frames:
                        if "archive_detail" in frame_atual.url.casefold():
                            return frame_atual
                    return None

                _aguardar_condicao(
                    page,
                    lambda: frame_detalhes() is not None,
                    timeout_ms,
                    "Os detalhes do erro de importação não foram carregados.",
                )
                linhas_erro = frame_detalhes().locator("#dgdUsuarios tr")
                for indice in range(1, linhas_erro.count()):
                    celulas_erro = linhas_erro.nth(indice).locator("td")
                    if celulas_erro.count() < 2:
                        continue
                    numero_texto = celulas_erro.nth(0).inner_text().strip()
                    erros.append(
                        ErroImportacaoBRMobilidade(
                            linha=int(numero_texto) if numero_texto.isdigit() else None,
                            mensagem=celulas_erro.nth(1).inner_text().strip(),
                        )
                    )

            return StatusImportacaoBRMobilidade(
                nome_arquivo=nome_procurado,
                processado_em=datetime.strptime(data_texto, "%d/%m/%Y %H:%M:%S"),
                status=status,
                comentario=comentario,
                erros=tuple(erros),
            )
    except BRMobilidadePortalErro:
        raise
    except Exception as erro:
        raise BRMobilidadePortalErro(
            "Não foi possível consultar o status no Portal BR Mobilidade."
        ) from erro
    finally:
        if navegador is not None:
            try:
                navegador.close()
            except Exception:
                pass


def consultar_status_arquivo_br_mobilidade_com_config(nome_arquivo, config, **opcoes):
    return consultar_status_arquivo_br_mobilidade(
        nome_arquivo,
        login=config.get("BR_MOBILIDADE_LOGIN"),
        senha=config.get("BR_MOBILIDADE_SENHA"),
        portal_url=config.get("BR_MOBILIDADE_PORTAL_URL", PORTAL_URL_PADRAO),
        headless=config.get("BR_MOBILIDADE_HEADLESS", True),
        timeout_ms=config.get("BR_MOBILIDADE_TIMEOUT_MS", 30000),
        executable_path=config.get("BR_MOBILIDADE_BROWSER_EXECUTABLE_PATH") or None,
        **opcoes,
    )
