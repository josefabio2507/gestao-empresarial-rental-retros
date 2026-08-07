# Missao 14.4 - MVP 14 Suprimentos: Mapa Comparativo de Cotacoes

## Objetivo

Criar uma tela de mapa comparativo para analisar as propostas registradas em uma cotacao, agrupadas por item da requisicao.

## Escopo

Entram nesta missao:

- tela `Mapa comparativo` dentro de uma cotacao;
- agrupamento das propostas por item da requisicao;
- exibicao de fornecedor, preco unitario, valor total, prazo e condicao de pagamento;
- destaque de menor preco unitario por item;
- destaque de menor valor total por item;
- destaque de menor prazo informado por item;
- indicadores de itens, itens cotados, itens sem proposta e quantidade de propostas;
- testes automatizados da regra e da tela.

Nao entram nesta missao:

- escolha ou gravacao de fornecedor vencedor;
- aprovacao por alcada;
- ordem de compra;
- recebimento;
- estoque;
- financeiro ou contas a pagar.

## Criterios de aceite

1. Usuario com permissao de visualizar Cotacoes acessa o mapa comparativo.
2. Usuario sem permissao nao acessa URL direta.
3. O mapa agrupa propostas por item da requisicao.
4. O sistema destaca menor preco unitario.
5. O sistema destaca menor valor total.
6. O sistema destaca menor prazo quando houver prazo informado.
7. Itens sem proposta aparecem claramente no mapa.
8. Nenhum vencedor e gravado nesta missao.
9. Nenhuma ordem de compra ou financeiro e criado.
