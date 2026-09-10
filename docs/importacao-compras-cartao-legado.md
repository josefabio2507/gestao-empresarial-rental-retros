# Importação de compras de cartão do legado

Implementação local. Não executar publicação ou deploy sem nova solicitação.

## Uso

1. Acesse **Financeiro > Contas a Pagar > Cartões > Importar compras do legado**.
2. Envie o arquivo `.xlsx`, com a aba **Parcelas**.
3. Confira a ligação entre o final de cada cartão e seu cadastro. Se faltar um cartão, cadastre-o com banco, fechamento e vencimento corretos. O importador não inventa esses dados.
4. Se alterar os vínculos, clique em **Validar cartões**.
5. Confira os totais, as pendências e a prévia. A prévia mostra 100 linhas, mas o processamento abrange a planilha inteira.
6. Clique em **Confirmar importação das linhas aptas**. A cada 100 linhas processadas, há uma pausa de 10 segundos.
7. Ao final, confira os contadores e baixe o relatório de pendências. Uma importação interrompida pode ser retomada em **Importações recentes**, sem reenviar o arquivo.

Cartões ainda não vinculados não bloqueiam as demais compras. As linhas correspondentes ficam no relatório de pendências e somente as linhas aptas são importadas.

## Campos e regras

- Uma linha gera somente a parcela informada, sem criar novamente as demais parcelas da compra.
- ID legado da parcela e final do cartão formam a chave para evitar duplicidades. A chave fica protegida por uma restrição única no banco. Não altere esses identificadores ao reenviar o mesmo histórico.
- Nome do cartão e ID da compra são opcionais. A identificação é feita pelo final ou pelo vínculo escolhido na prévia.
- Documento, centro de custo, competência e observações podem ficar vazios. Centro de custo vazio permanece sem preenchimento; quando informado, deve corresponder a um cadastro.
- Sem competência, usa-se o mês do vencimento informado na parcela.
- Datas reais do Excel, números de série de data e textos `DD/MM/AAAA` ou `AAAA-MM-DD` são aceitos. Fórmulas devem ser substituídas pelos valores.
- **Pago** registra o valor pago histórico, sem criar uma baixa com data inventada. O pagamento histórico aparece no detalhe do título e é preservado nos recálculos.
- Situação vazia é tratada como **em aberto**, conforme solicitado. O sistema apresenta **Vencido** ou **A vencer**, de acordo com a data.
- Origem **Legado**, tipo e forma **Cartão de Crédito**. O nome do fornecedor é preservado como histórico, sem criar automaticamente cadastros de fornecedores.
- Vencimentos originais permanecem nas parcelas. Na fatura mensal nova, o cabeçalho usa o dia de vencimento do cadastro do cartão. Faturas já existentes mantêm suas datas. Essa interpretação foi apresentada ao usuário para conferência.
- Valores negativos/zero não são transformados em compras positivas. Ficam separados no relatório de pendências. Os quatro descontos da planilha precisam ser conferidos antes de encerrar a conciliação das faturas.
- Faturas canceladas não recebem parcelas; essas linhas são reportadas como pendências.
- A importação exige permissão de criar em Contas a Pagar. A prévia, os lotes e as pendências só podem ser acessados pelo usuário que enviou o arquivo.

## Validação do arquivo fornecido

Arquivo `Modelo_Legado_Compras_Cartao.xlsx`, analisado em 10/09/2026:

| Resultado | Quantidade | Valor |
|---|---:|---:|
| Parcelas positivas pagas | 2.031 | R$ 2.716.112,91 |
| Parcelas positivas em aberto | 367 | R$ 350.047,43 |
| Total positivo importável | 2.398 | R$ 3.066.160,34 |
| Descontos negativos, separados | 4 | -R$ 1,42 |
| Total de linhas | 2.402 | R$ 3.066.158,92 |

Os quatro descontos têm IDs legados 32779, 32782, 33640 e 33641 e estão marcados como pagos. Por isso, das 2.035 linhas originalmente marcadas como Pago, 2.031 são compras positivas.

Finais encontrados: 0903, 3539, 4729, 6226, 7216, 8356 e 8887.

## Banco e testes

A migração `m3c4d5e6f7a8`, filha de `l2b3c4d5e6f7`, adiciona o identificador único do legado de cartões, o pagamento histórico e a tabela de importações. Não importa dados por seed. O arquivo e o progresso ficam no banco, não no cookie de sessão ou em arquivo temporário do servidor.

Os lotes usam atualização condicional do cursor, transações e proteção contra repetição. Uma falha inesperada desfaz somente o lote em andamento. O banco impõe a pausa entre os lotes; atualizar a página não acelera nem repete a gravação.

Testar em banco isolado, configurando a conexão **antes** de criar a aplicação. Nunca usar `drop_all` em banco local de trabalho ou de produção. A simulação da planilha real é feita em memória, com cartões fictícios, sem gravar os títulos no banco de trabalho.
