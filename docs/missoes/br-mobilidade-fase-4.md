# BR Mobilidade — Fase 4

Esta fase implementa somente o login e o upload determinístico do arquivo 0200.
Ela não consulta o status da importação, não continua o pedido e não clica em
`Finalizar Pedido`.

## Variáveis de ambiente

- `BR_MOBILIDADE_LOGIN`: login/CNPJ do Portal.
- `BR_MOBILIDADE_SENHA`: senha do Portal.
- `BR_MOBILIDADE_PORTAL_URL`: opcional; usa o endereço oficial por padrão.
- `BR_MOBILIDADE_HEADLESS`: opcional; `true` por padrão.
- `BR_MOBILIDADE_TIMEOUT_MS`: opcional; `30000` por padrão.
- `BR_MOBILIDADE_BROWSER_EXECUTABLE_PATH`: opcional; caminho de um Chromium já
  instalado.

As credenciais não são incluídas nas mensagens de erro nem nos resultados do
serviço.

## Dependência de implantação

O pacote Python `playwright` foi incluído em `requirements.txt`. O ambiente que
executar a automação também precisa disponibilizar o navegador Chromium. Como o
repositório não possui `Dockerfile` nem `render.yaml`, a infraestrutura do Render
não foi alterada nesta fase. Antes de ativar o envio em produção, o processo de
build deverá instalar o Chromium compatível com a versão do Playwright.

## Uso interno

O ponto de entrada é
`enviar_arquivo_br_mobilidade_com_config(caminho_arquivo, app.config)`, definido
em `app/departamento_pessoal/vale_transporte/br_mobilidade_portal.py`.

O serviço valida localmente a existência, a extensão `.txt` e o cabeçalho `0200`,
faz login, abre `Pedidos > Importar > Processar`, envia o arquivo e somente retorna
sucesso quando o Portal exibe `Seu arquivo foi enviado para execução`.
