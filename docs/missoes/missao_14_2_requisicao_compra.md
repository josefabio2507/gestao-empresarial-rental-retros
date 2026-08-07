# Missao 14.2 - MVP 14 Suprimentos: Requisicao de Compra

## Objetivo

Criar o primeiro fluxo operacional do modulo Suprimentos: abertura de requisicoes internas de compra de materiais e servicos, usando os cadastros base criados na Missao 14.1.

## Escopo

Entram nesta missao:

- modulo `Requisicoes de Compra` dentro de Suprimentos;
- criar requisicao em rascunho;
- informar centro de custo, justificativa e observacoes;
- adicionar itens ativos do cadastro de itens;
- salvar quantidade e snapshot do item/unidade;
- remover itens enquanto a requisicao estiver em rascunho;
- enviar requisicao para analise;
- cancelar requisicao;
- migrations, rotas, telas, permissoes e testes.

Nao entram nesta missao:

- cotacao com fornecedores;
- mapa comparativo;
- aprovacao por alcada;
- ordem de compra;
- recebimento;
- estoque;
- contas a pagar;
- fluxo de caixa;
- integracao financeira.

## Status

```text
Rascunho
Enviada para Analise
Cancelada
```

Somente requisicoes em `Rascunho` podem ser editadas ou receber/remover itens.

## Criterios de aceite

1. Usuario com permissao acessa `Suprimentos > Requisicoes de Compra`.
2. Usuario sem permissao nao acessa URL direta.
3. Administrador cria requisicao em rascunho.
4. Requisicao gera numero sequencial.
5. Justificativa e obrigatoria.
6. Item exige quantidade maior que zero.
7. Item duplicado na mesma requisicao e bloqueado.
8. Ao adicionar item, gravar snapshot de codigo, descricao e unidade.
9. Requisicao sem item nao pode ser enviada.
10. Requisicao com item pode ser enviada para analise.
11. Requisicao enviada nao pode ser editada.
12. Requisicao pode ser cancelada.
13. Nenhum financeiro, cotacao ou ordem de compra e criado nesta missao.
