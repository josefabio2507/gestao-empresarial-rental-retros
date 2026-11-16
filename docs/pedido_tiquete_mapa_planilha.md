# Mapa do modelo Excel � Pedido T�cket

**Arquivo de refer�ncia:** `Planilha Pedido T�cket.xlsx`

O arquivo de refer�ncia tem quatro abas. O modelo interno preserva a ordem, as valida��es, os nomes definidos, as f�rmulas auxiliares e o estado oculto da aba `FonteDados`, removendo as linhas de exemplo com dados pessoais.

## Mapeamento de campos

| Aba | Primeira linha de dados | Colunas usadas |
|---|---:|---|
| `Empresa` | 5 | A: CNPJ/CPF; B: nome da empresa; C: contrato; D: produto; E: data de cr�dito; F: status do registro. O n�mero do pedido fica em E2. |
| `Unidade(s) de Entrega` | 4 | A: CNPJ/CPF da empresa; B: c�digo; C: nome; D: tipo de logradouro; E: logradouro; F: n�mero; G: complemento; H: bairro; I: UF; J: cidade; K: CEP; L: interlocutor; M: CPF; N: RG; O: DDD; P: telefone; Q: ramal; R: status. |
| `Beneficiarios` | 4 | A: matr�cula; B: CPF; C: nome; D: nascimento; E: departamento; F: unidade; G: valor mensal; H: contrato/produto; I: parcelas; J: status do registro. |
| `FonteDados` | 2 | Aba auxiliar oculta. A cont�m f�rmulas para contrato/produto e C para c�digo/nome da unidade; alimenta as listas da aba de benefici�rios. |

## Valida��es e limites do modelo

- A aba `Empresa` valida o n�mero do pedido em E2, produtos em D e campos dos registros a partir da linha 5.
- `FonteDados` tem 248 f�rmulas para contrato/produto e 245 para unidade. O gerador limita cada pedido a essas quantidades para que as listas suspensas do modelo continuem cobrindo os registros.
- Os campos de matr�cula, CPF, CNPJ/CPF, contrato, c�digo de unidade e CEP devem ser escritos como texto para preservar zeros � esquerda.
- As colunas de status existem, mas n�o cont�m f�rmulas no modelo. O gerador as mant�m vazias.
- As f�rmulas e listas s�o preservadas; `openpyxl` n�o recalcula f�rmulas. A aceita��o final do arquivo depende da abertura e importa��o no Portal da T�cket, que ainda n�o foi executada.

## Sanitiza��o

Os registros de exemplo foram exclu�dos da c�pia-base usada na implementa��o local. O arquivo de refer�ncia permanece no diret�rio do projeto para consulta local e est� exclu�do do Git pelo `.gitignore`, para evitar versionar dados pessoais contidos nele.
