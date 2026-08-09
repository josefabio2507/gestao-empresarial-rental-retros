# Missao 14.8 - Entrada em Estoque via Recebimento da OC

## Objetivo

Registrar automaticamente entradas de estoque a partir dos itens recebidos fisicamente em Ordens de Compra.

## Regras implementadas

- A entrada de estoque e criada no momento do recebimento da OC.
- Apenas itens marcados como estocaveis geram movimentacao de estoque.
- Itens nao estocaveis e servicos seguem apenas como recebidos, sem saldo de estoque.
- Cada item de recebimento pode gerar no maximo uma movimentacao de estoque.
- A movimentacao guarda item, OC, fornecedor, documento, quantidade, valor unitario e valor total.
- O saldo de estoque do item passa a ser calculado pelas movimentacoes registradas.
- A tela de detalhes da OC exibe as entradas de estoque geradas.

## Fora do escopo desta missao

- Saidas de estoque.
- Ajustes manuais de estoque.
- Inventario.
- Integracao com o Modulo Financeiro.
