# Missão 18.15 — Preparação para Publicação em Produção

Status: em preparação; nenhuma alteração em produção foi realizada.

## Objetivo

Organizar uma publicação controlada da modernização visual da Missão 18, preservando o comportamento funcional já homologado no ambiente local.

## Escopo desta etapa

- Consolidar a sequência de PRs da Missão 18.
- Definir critérios objetivos para autorizar o merge em produção.
- Registrar validações antes e depois da publicação.
- Definir um retorno seguro caso seja identificada regressão visual ou funcional.

Esta missão não autoriza, por si só, merges, deploys ou alterações diretas no ambiente de produção.

## Linha de publicação

As PRs da Missão 18 são encadeadas. A integração deve respeitar a ordem abaixo para que cada alteração mantenha sua base correta:

1. PRs #237 a #248, na sequência numérica.
2. PR #249 — Paridade do ambiente local.
3. PR #250 — Homologação visual e organização dos cabeçalhos.

Depois que uma PR-base for integrada, a próxima deve ser atualizada para usar a base resultante antes de seu merge. O objetivo é que o `main` receba uma linha única, sem duplicação de commits nem conflitos escondidos.

## Critérios para autorizar cada merge

- PR sem conflitos e com base atualizada.
- Revisão visual concluída nas áreas afetadas.
- Testes automatizados disponíveis executados com sucesso no ambiente equivalente ao de produção.
- Nenhuma mudança de regra de negócio, permissão, rota ou integração fora do escopo aprovado.
- Aprovação explícita do responsável pela publicação.

## Validação pós-publicação

Após cada etapa integrada, validar no ambiente de produção:

- Acesso e autenticação.
- Navegação lateral e abertura automática do departamento ativo.
- Cabeçalhos, blocos de ações, botões e retornos.
- Fluxos principais dos módulos Financeiro, Suprimentos, Operação, Departamento Pessoal, Segurança do Trabalho e Fiscal.
- Visualização em desktop e em uma largura reduzida.

## Plano de retorno

Se uma regressão for identificada após uma integração:

1. Suspender a sequência de merges.
2. Identificar a PR e o commit responsáveis.
3. Reverter somente a alteração afetada por meio de uma PR de reversão.
4. Validar novamente o fluxo impactado antes de retomar a publicação.

## Próxima ação

Aguardar a autorização explícita para iniciar a sequência de merges descrita neste documento. Até essa autorização, as PRs permanecem abertas e a produção permanece inalterada.
