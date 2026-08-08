# Missao 14.5 - MVP 14 Suprimentos: Selecao e Aprovacao do Fornecedor

## Objetivo

Permitir selecionar a proposta vencedora por item da cotacao e enviar a cotacao para aprovacao por alcada inicial, sem gerar Ordem de Compra.

## Escopo

Entram nesta missao:

- selecionar uma proposta vencedora por item;
- registrar usuario, data e justificativa da selecao;
- exigir justificativa quando a proposta escolhida nao for a de menor preco;
- enviar cotacao para aprovacao somente quando todos os itens tiverem vencedor;
- aprovar cotacao com usuario que possua permissao de aprovacao no modulo Cotacoes;
- reprovar cotacao com justificativa obrigatoria, liberando para ajustes;
- novos status: `Em Aprovacao`, `Aprovada` e `Reprovada`;
- migration, rotas, telas e testes.

Nao entram nesta missao:

- ordem de compra;
- recebimento;
- estoque;
- financeiro ou contas a pagar;
- parametrizacao avancada de valores de alcada.

## Regra de alcada inicial

Nesta missao, a alcada inicial usa a permissao `aprovar` do modulo `Cotacoes`.
A parametrizacao por valor, cargo, centro de custo ou categoria fica preparada para evolucao futura.

## Criterios de aceite

1. Usuario com permissao de editar pode selecionar vencedores enquanto a cotacao estiver aberta ou reprovada.
2. Cada item pode ter apenas uma proposta selecionada.
3. Escolha acima do menor preco exige justificativa.
4. Cotacao so pode ir para aprovacao com todos os itens selecionados.
5. Usuario sem permissao de aprovar nao aprova nem reprova.
6. Aprovacao muda o status para `Aprovada`.
7. Reprovacao exige justificativa e muda o status para `Reprovada`.
8. Cotacao reprovada pode ser ajustada e reenviada.
9. Nenhuma Ordem de Compra e criada nesta missao.
