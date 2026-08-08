# Missao 14.7 - Recebimento Fisico da Ordem de Compra

## Objetivo

Registrar o recebimento fisico parcial ou total dos itens de uma ordem de compra gerada no Modulo Suprimentos.

## Entregas

- Novos status da ordem de compra:
  - Gerada;
  - Parcialmente Recebida;
  - Recebida;
  - Cancelada.
- Tela para registrar recebimento a partir da ordem de compra.
- Tipo de documento do recebimento: Nota Fiscal, Cupom Fiscal, Romaneio ou Outro.
- Numero do documento obrigatorio.
- Data do documento opcional.
- Controle de quantidade comprada, quantidade recebida e saldo a receber por item.
- Historico de recebimentos dentro da tela de detalhes da ordem de compra.
- Bloqueio de recebimento acima do saldo do item.
- Bloqueio de cancelamento de ordem de compra que ja possui recebimento.
- Migration com tabelas de recebimento e itens recebidos.
- Testes automatizados para recebimento parcial, recebimento total e permissoes.

## Fora do escopo desta missao

- Entrada definitiva em estoque.
- Baixa ou movimento de almoxarifado.
- Leitura automatica de XML da NF-e.
- Criacao de contas a pagar.
- Integracao com o futuro Modulo Financeiro.

Esses pontos permanecem para as proximas missoes do MVP 14.
