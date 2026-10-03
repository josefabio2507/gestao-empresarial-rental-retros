# BR Mobilidade — Fase 5

Esta fase implementa a consulta automática de `Pedidos > Importar > Status`.

O serviço:

- autentica com as credenciais do ambiente;
- abre a grade de status das importações de pedidos;
- localiza a ocorrência mais recente pelo nome completo do arquivo;
- captura data/hora, nome, status e comentário;
- abre e captura os erros detalhados por linha, quando disponíveis;
- classifica o resultado como sucesso ou erro sem continuar o pedido.

O ponto de entrada é
`consultar_status_arquivo_br_mobilidade_com_config(nome_arquivo, app.config)`,
definido em
`app/departamento_pessoal/vale_transporte/br_mobilidade_portal.py`.

## Validação controlada

Em 01/10/2026, a consulta localizou o arquivo sintético enviado na Fase 4 e
retornou `Erro no arquivo`. O detalhe informou que o funcionário não pertence à
empresa ou está inativo e que todas as linhas do arquivo continham erro. Esse é
o resultado esperado para o CPF sintético e confirma que a automação consegue
capturar tanto o resumo quanto os detalhes fornecidos pelo Portal.

Esta fase não cria, confere ou finaliza pedidos.
