# BR Mobilidade — Fase 8: boleto e relatório

A Fase 8 localiza o pedido finalizado no Histórico de Pedidos e captura dois
documentos sem realizar pagamento:

- o boleto original retornado pelo endpoint PDF do Portal;
- o relatório oficial de itens, convertido para PDF pela impressão do Chromium.

Antes do download, o sistema exige que a linha do histórico tenha exatamente o
número do pedido confirmado e que o relatório contenha esse mesmo número. Os
dois PDFs são reunidos em um arquivo ZIP e enviados diretamente ao navegador.
Nenhum boleto ou relatório é gravado no banco ou no disco do servidor.

O total financeiro e a taxa administrativa são atualizados conforme o valor do
Histórico de Pedidos. Créditos e taxa permanecem em campos separados.

## Validação real

O pedido `2972189` foi localizado com status `Novo`, créditos de R$ 41,10, taxa
de R$ 1,23 e total financeiro de R$ 42,33. O download contém:

- `BOLETO_BR_MOBILIDADE_2972189.pdf`;
- `RELATORIO_BR_MOBILIDADE_2972189.pdf`.

O pedido permanece em `FINALIZADO_PORTAL`, permitindo baixar o pacote novamente
sem recriar ou finalizar o pedido. O navegador salva o ZIP na pasta de downloads
configurada no computador do usuário.
