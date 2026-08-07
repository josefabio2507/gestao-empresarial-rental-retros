# Missao 14.3 - MVP 14 Suprimentos: Cotacao com Fornecedores

## Objetivo

Criar o registro inicial de cotacoes com fornecedores a partir de requisicoes de compra enviadas para analise.

## Escopo

Entram nesta missao:

- modulo `Cotacoes` dentro de Suprimentos;
- abrir cotacao para requisicao com status `Enviada para Analise`;
- registrar propostas por fornecedor e item da requisicao;
- exigir fornecedor vinculado ao item;
- registrar preco unitario, prazo de entrega, condicao de pagamento e observacoes;
- gravar snapshots de fornecedor, item, unidade e quantidade;
- encerrar ou cancelar cotacao;
- migrations, rotas, telas, permissoes e testes.

Nao entram nesta missao:

- mapa comparativo;
- escolha de fornecedor vencedor;
- aprovacao por alcada;
- ordem de compra;
- recebimento;
- estoque;
- financeiro ou contas a pagar.

## Criterios de aceite

1. Usuario com permissao acessa `Suprimentos > Cotacoes`.
2. Usuario sem permissao nao acessa URL direta.
3. Cotacao so pode ser criada a partir de requisicao `Enviada para Analise`.
4. Requisicao em rascunho ou cancelada nao inicia cotacao.
5. Fornecedor precisa estar vinculado ao item.
6. Proposta exige preco unitario maior ou igual a zero.
7. Item/fornecedor duplicado na mesma cotacao e bloqueado.
8. Cotacao aberta pode receber/remover propostas.
9. Cotacao sem propostas nao pode ser encerrada.
10. Cotacao com proposta pode ser encerrada.
11. Encerramento nao escolhe fornecedor vencedor.
12. Nenhuma ordem de compra ou financeiro e criado.
