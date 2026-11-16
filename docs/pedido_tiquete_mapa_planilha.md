# Mapa do modelo Excel — Pedido Tícket

**Arquivo de referência:** `Planilha Pedido Tícket.xlsx`

O arquivo de referência tem quatro abas. O modelo interno preserva a ordem, as validações, os nomes definidos, as fórmulas auxiliares e o estado oculto da aba `FonteDados`, removendo as linhas de exemplo com dados pessoais.

## Mapeamento de campos

| Aba | Primeira linha de dados | Colunas usadas |
|---|---:|---|
| `Empresa` | 5 | A: CNPJ/CPF; B: nome da empresa; C: contrato; D: produto; E: data de crédito; F: status do registro. O número do pedido fica em E2. |
| `Unidade(s) de Entrega` | 4 | A: CNPJ/CPF da empresa; B: código; C: nome; D: tipo de logradouro; E: logradouro; F: número; G: complemento; H: bairro; I: UF; J: cidade; K: CEP; L: interlocutor; M: CPF; N: RG; O: DDD; P: telefone; Q: ramal; R: status. |
| `Beneficiarios` | 4 | A: matrícula; B: CPF; C: nome; D: nascimento; E: departamento; F: unidade; G: valor mensal; H: contrato/produto; I: parcelas; J: status do registro. |
| `FonteDados` | 2 | Aba auxiliar oculta. A contém fórmulas para contrato/produto e C para código/nome da unidade; alimenta as listas da aba de beneficiários. |

## Validações e limites do modelo

- A aba `Empresa` valida o número do pedido em E2, produtos em D e campos dos registros a partir da linha 5.
- `FonteDados` tem 248 fórmulas para contrato/produto e 245 para unidade. O gerador limita cada pedido a essas quantidades para que as listas suspensas do modelo continuem cobrindo os registros.
- Os campos de matrícula, CPF, CNPJ/CPF, contrato, código de unidade e CEP devem ser escritos como texto para preservar zeros à esquerda.
- As colunas de status existem, mas não contêm fórmulas no modelo. O gerador as mantém vazias.
- As fórmulas e listas são preservadas; `openpyxl` não recalcula fórmulas. A aceitação final do arquivo depende da abertura e importação no Portal da Tícket, que ainda não foi executada.

## Sanitização

Os registros de exemplo foram excluídos da cópia-base usada na implementação local. O arquivo de referência permanece no diretório do projeto para consulta local e está excluído do Git pelo `.gitignore`, para evitar versionar dados pessoais contidos nele.
