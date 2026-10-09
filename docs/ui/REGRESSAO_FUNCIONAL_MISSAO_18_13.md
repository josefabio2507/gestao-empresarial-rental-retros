# Missão 18.13 — Testes Funcionais e Regressão Completa

Data da execução: 08/10/2026

## Ambiente

- Execução local com `pytest` 9.1.1.
- Banco de testes: SQLite em memória.
- Produção não foi acessada nem alterada.

## Resultado consolidado

| Métrica | Resultado |
| --- | --- |
| Testes aprovados | 464 |
| Testes com falha | 17 |
| Subtestes aprovados | 6 |
| Avisos | 621 |
| Tempo total | 2 min 47 s |

## Falhas identificadas

| Área | Quantidade | Diagnóstico inicial |
| --- | ---: | --- |
| Fiscal / DANFE | 5 | A biblioteca `brazilfiscalreport` lança `KeyError` ao processar XML de teste sem o campo de modalidade de frete. Uma falha de consulta NSU decorre da mesma geração de DANFE. |
| Financeiro / Relatórios | 1 | A expectativa do teste usa o texto sem acentuação (`Relatorios`), enquanto o template apresenta `Relatórios`. Não há relação com a camada CSS. |
| Operação | 4 | Falhas de regras e expectativas de conteúdo em multas e cartões de Operação, sem relação com estilos. |
| Suprimentos | 4 | Falhas em validações de cadastro, requisição e mensagens de WhatsApp, sem relação com estilos. |
| Vale-Transporte | 3 | Falhas nas regras de geração do arquivo da BR Mobilidade, sem relação com estilos. |

## Conclusão

As alterações visuais da Missão 18 permanecem limitadas a templates e CSS. A suíte de regressão expôs 17 falhas funcionais que exigem uma missão corretiva separada, pois envolvem regras de negócio, dependência de DANFE e expectativas de testes fora do escopo da modernização visual.

Os 621 avisos são majoritariamente avisos de uso legado do SQLAlchemy (`Query.get`) e não bloquearam a execução.
