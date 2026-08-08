# Missao 14.6 - Ordens de Compra

## Objetivo

Gerar ordens de compra a partir de cotacoes aprovadas no Modulo Suprimentos.

## Entregas

- Novo modulo `Ordens de Compra` no hub de Suprimentos.
- Listagem de ordens de compra com filtros por numero, fornecedor e status.
- Tela de detalhes da ordem de compra com fornecedor, requisicao, cotacao, condicao de pagamento, itens e total.
- Geracao de ordem de compra a partir da cotacao aprovada.
- Criacao de uma ordem por fornecedor vencedor, quando os itens aprovados tiverem fornecedores diferentes.
- Bloqueio de duplicidade de ordem de compra para a mesma cotacao e fornecedor.
- Cancelamento simples da ordem de compra.
- Migration com tabelas de cabecalho e itens da ordem de compra.
- Permissoes no modulo `ordens_compra`.

## Fora do escopo desta missao

- Recebimento fisico.
- Leitura de XML da NF-e.
- Entrada em estoque.
- Criacao de contas a pagar.
- Fluxo financeiro completo.

Esses pontos serao tratados nas proximas missoes do MVP 14.
