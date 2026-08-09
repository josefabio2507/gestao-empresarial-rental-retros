# Missao 14.9 - Consulta de Estoque e Historico de Movimentacoes

## Objetivo

Criar uma tela geral de consulta de estoque dentro do Modulo Suprimentos, permitindo acompanhar saldos atuais e historico de movimentacoes geradas pelos recebimentos de Ordens de Compra.

## Regras implementadas

- Criado o submodulo Estoque em Suprimentos.
- A tela Estoque lista apenas itens ativos e estocaveis.
- O saldo atual e calculado pelas movimentacoes registradas.
- Itens abaixo do estoque minimo sao destacados.
- A tela Historico de Estoque lista movimentacoes com data, tipo, origem, item, documento, OC, fornecedor, quantidade, valor e status.
- O historico pode ser filtrado por item, fornecedor, documento e periodo.
- O acesso respeita permissao do modulo `suprimentos / estoque`.

## Fora do escopo desta missao

- Saidas de estoque.
- Ajustes manuais.
- Inventario.
- Alteracoes diretas de saldo.
