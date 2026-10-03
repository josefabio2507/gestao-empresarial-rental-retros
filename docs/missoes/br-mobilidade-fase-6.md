# BR Mobilidade — Fase 6A (fluxo 0200 anterior)

Esta etapa ligava o pedido criado no Rental Retros ao fluxo de geração,
upload e consulta de status. Ela não continuava nem finalizava o pedido no Portal.
O envio automático a partir da tela foi suspenso após o teste do pedido 2969715,
porque o formato 0200 não transmite a data escolhida pelo usuário.

A data de liberação escolhida no sistema é apenas planejada: o layout 0200
não contém essa data, e a rotina atual de upload não a informa ao Portal.
Depois da importação, a data efetiva deve ser conferida no detalhe do pedido
da BR Mobilidade antes de qualquer pagamento ou liberação. No pedido de teste
2969715, a data planejada foi 05/10/2026 e o Portal exibiu 01/10/2026;
esse caso permanece pendente de correção no Portal ou orientação da operadora.

## Correção para o próximo teste

As instruções do Portal confirmam que o layout 0200 não possui campo de data,
e o formulário Importar > Processar só recebe o arquivo. No fluxo manual
Pedidos > Incluir, o Passo 3 possui o campo `txtMemoDate`, intitulado
"Data de liberação da recarga". Portanto, o envio automático 0200 foi
bloqueado na rota web para novos pedidos com data escolhida. A tela local agora
prepara uma execução manual, grava a data planejada e exibe os valores por
colaborador; essa execução não entra na fila de upload. O operador deve informar
a mesma data no Passo 3 e revisar antes de criar o pedido. A automação integral
do fluxo manual ainda precisa ser validada até a confirmação final.

## Configuração histórica do modo local

Configuração sugerida no `.env`:

```env
BR_MOBILIDADE_AMBIENTE=local
BR_MOBILIDADE_INTEGRACAO_ATIVA=true
BR_MOBILIDADE_EXECUCAO_SINCRONA=true
BR_MOBILIDADE_BROWSER_EXECUTABLE_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
```

O processamento síncrono descrito aqui só se aplica às integrações 0200 já
preparadas antes da suspensão do botão de envio.

## Configuração histórica do modo produção no Render

Usar o `Dockerfile` do projeto e configurar no serviço web:

```env
BR_MOBILIDADE_AMBIENTE=producao
BR_MOBILIDADE_INTEGRACAO_ATIVA=true
BR_MOBILIDADE_EXECUCAO_SINCRONA=false
BR_MOBILIDADE_HEADLESS=true
BR_MOBILIDADE_LOGIN=...
BR_MOBILIDADE_SENHA=...
```

Não configurar `BR_MOBILIDADE_BROWSER_EXECUTABLE_PATH` no container; o Playwright
usará o Chromium instalado durante o build.

Criar um Background Worker usando a mesma imagem e o comando:

```text
flask --app run.py br-mobilidade-worker
```

O servidor web não coloca novas criações manuais nessa fila. O worker continua
reservado para integrações 0200 previamente enfileiradas.

## Segurança e idempotência

- Cada arquivo recebe nome único com pedido e hash.
- O conteúdo e seu SHA-256 ficam vinculados à execução.
- Uma chave única bloqueia reenvio do mesmo conteúdo.
- Bloqueio transacional protege o pedido contra concorrência no PostgreSQL.
- Arquivos temporários são removidos após o uso.
- Credenciais, cookies e sessões não são persistidos.
- Resultado com erro interrompe o fluxo.
