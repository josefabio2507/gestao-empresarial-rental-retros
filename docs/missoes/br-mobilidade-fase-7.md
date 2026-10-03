# BR Mobilidade — Fase 7: conferência e finalização

A Fase 7 automatiza o fluxo manual **Pedidos > Incluir > Valor por usuário**.
Ela não usa o arquivo 0200, porque esse formato não transmite a data de
liberação da recarga.

## Fluxo seguro

1. O sistema preenche os usuários, valores e a data planejada no Portal.
2. No Passo 4, compara data, quantidade de usuários, créditos, taxa, cartões e
   total com o pedido local.
3. O navegador é encerrado sem clicar em **Finalizar Pedido**.
4. A tela local exibe o resumo conferido e aguarda autorização explícita de um
   usuário autenticado.
5. Após a autorização, a automação refaz o fluxo e exige que o novo resumo seja
   idêntico ao resumo autorizado antes de clicar no botão final.
6. O número do pedido é identificado no Histórico de Pedidos e gravado no
   sistema.

Nenhum pedido é finalizado durante uma simples conferência.

## Estados

- `AGUARDANDO_CRIACAO_MANUAL`: pronto para preencher e conferir.
- `AGUARDANDO_AUTORIZACAO_FINALIZACAO`: Passo 4 conferido, sem finalização.
- `AUTORIZADO_FINALIZACAO`: autorização humana registrada.
- `FINALIZANDO_PORTAL`: execução reservada, protegida contra clique duplicado.
- `FINALIZADO_PORTAL`: pedido confirmado e número registrado.
- `ERRO_FINALIZACAO`: falha anterior ao clique final.
- `FINALIZACAO_INCERTA`: o clique pode ter ocorrido, mas o histórico não
  confirmou o resultado. Nesse estado não há nova tentativa automática.

## Configuração

O ambiente precisa de `BR_MOBILIDADE_LOGIN`, `BR_MOBILIDADE_SENHA`,
`BR_MOBILIDADE_INTEGRACAO_ATIVA=true` e um navegador Playwright disponível.
Em produção, o navegador deve operar em modo headless. As credenciais não são
gravadas no banco, nos logs ou na tela.

## Regra operacional

Em `FINALIZACAO_INCERTA`, o operador deve consultar manualmente o Histórico de
Pedidos do Portal BR Mobilidade antes de qualquer correção. Repetir a execução
sem essa conferência pode criar um pedido duplicado.

## Validação real concluída

Em 02/10/2026, o fluxo foi validado com autorização explícita até a criação do
pedido `2972189`. O Portal confirmou um usuário, R$ 41,10 em créditos, liberação
em 07/10/2026, status `Novo` e total de R$ 41,10. A leitura do histórico passou
a exigir que a célula contenha exclusivamente o número do pedido, evitando que
tabelas externas aninhadas produzam um identificador concatenado.

Antes da Fase 8, a geração do layout 0200 e o preenchimento do Portal foram
ajustados para considerar apenas colaboradores com valor a receber maior que
R$ 0,00. Itens com total exatamente zero são contabilizados como não enviados e
não bloqueiam os demais colaboradores. Totais negativos continuam bloqueados.
