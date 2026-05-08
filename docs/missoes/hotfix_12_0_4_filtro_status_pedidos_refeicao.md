# Hotfix 12.0.4 — Filtro de Status no Histórico de Pedidos de Refeição

## 1. Contexto

Projeto **Gestão Empresarial Rental Retros**, em produção parcial no Render, com fluxo oficial:

```text
ChatGPT/Squad → planeja a missão/hotfix
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

Após os ajustes recentes no módulo **Pedido de Refeições**, foi identificada uma melhoria necessária na tela de histórico/listagem de pedidos.

Tela atual:

```text
Departamento Pessoal
└── Pedido de Refeições
    └── Pedidos de Refeição
        └── Histórico/Listagem de pedidos
```

Atualmente, ao abrir a tela, todos os pedidos são exibidos diretamente na listagem.

Regra desejada:

```text
Incluir um filtro de status dos pedidos.
O valor padrão do filtro deve ser "Novo Pedido".
Quando a tela abrir com esse valor padrão, nenhum pedido deve ser exibido.
```

O objetivo é evitar que a tela carregue diretamente todo o histórico e permitir que o usuário selecione conscientemente o status que deseja consultar.

---

## 2. Objetivo do hotfix

Criar filtro de status na tela de histórico/listagem de pedidos de refeição.

O filtro deve permitir consultar pedidos por status, como:

```text
Novo Pedido
Aberto
Fechado
Enviado
Cancelado
Todos
```

A opção padrão deve ser:

```text
Novo Pedido
```

Quando o filtro estiver em **Novo Pedido**, a tela não deve listar nenhum pedido.

---

## 3. Análise da Squad

### 3.1 Agente de Desenvolvimento / Arquitetura

O ajuste é pontual e deve ser tratado como hotfix, pois altera uma tela já existente em produção.

A implementação deve ficar restrita à rota e ao template da listagem/histórico de pedidos de refeição.

A lógica recomendada é:

```text
1. Ao abrir a tela sem parâmetro de filtro, assumir status_filtro = "novo_pedido".
2. Se status_filtro = "novo_pedido", não buscar/listar pedidos.
3. Se status_filtro for um status real, filtrar pedidos pelo status selecionado.
4. Se status_filtro = "todos", listar todos os pedidos.
```

A alteração não deve mexer em:

- banco de dados;
- models.py;
- migrations;
- cálculo do pedido;
- WhatsApp;
- PDF;
- relatórios;
- fechamento/reenvio;
- inclusão de consumo;
- permissões.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 3.2 Agente de Design / Experiência do Usuário

A tela deve ter um filtro claro antes da tabela.

Layout sugerido:

```text
Status do pedido: [Novo Pedido ▼] [Filtrar]
```

Opções sugeridas:

```text
Novo Pedido
Aberto
Fechado
Enviado
Cancelado
Todos
```

Comportamento esperado:

```text
Novo Pedido:
não mostra pedidos e exibe mensagem amigável.

Aberto:
mostra apenas pedidos abertos.

Fechado:
mostra apenas pedidos fechados.

Enviado:
mostra apenas pedidos enviados.

Cancelado:
mostra apenas pedidos cancelados.

Todos:
mostra todos os pedidos.
```

Mensagem sugerida para o filtro padrão:

```text
Selecione um status para consultar os pedidos.
```

Aprovado pelo Agente de Design / Experiência do Usuário.

---

### 3.3 Agente de Código / Programação

O Codex deve localizar a rota da listagem de pedidos e o template correspondente.

Arquivos prováveis:

```text
app/departamento_pessoal/pedido_refeicoes/routes.py
app/templates/departamento_pessoal/pedido_refeicoes/pedidos.html
app/templates/departamento_pessoal/pedido_refeicoes/listar_pedidos.html
app/templates/departamento_pessoal/pedido_refeicoes/*.html
```

O Codex deve verificar os nomes reais do projeto.

Implementação esperada:

- ler parâmetro GET, por exemplo `status`;
- definir padrão como `novo_pedido`;
- montar query conforme status;
- enviar `status_filtro` ao template;
- renderizar select com o valor selecionado;
- exibir mensagem quando não houver pedidos;
- manter botões existentes, como `+ Novo Pedido` e `Voltar`.

Exemplo conceitual:

```text
/departamento-pessoal/pedido-refeicoes/pedidos?status=aberto
/departamento-pessoal/pedido-refeicoes/pedidos?status=fechado
/departamento-pessoal/pedido-refeicoes/pedidos?status=todos
```

Aprovado pelo Agente de Código / Programação.

---

### 3.4 Agente de Revisão / Qualidade

O hotfix deve ser testado nos seguintes cenários:

```text
1. Abrir a tela sem filtro.
2. Confirmar que o filtro aparece como "Novo Pedido".
3. Confirmar que nenhum pedido aparece ao abrir a tela.
4. Selecionar Aberto e confirmar que aparecem apenas pedidos abertos.
5. Selecionar Fechado e confirmar que aparecem apenas pedidos fechados.
6. Selecionar Enviado e confirmar que aparecem apenas pedidos enviados.
7. Selecionar Cancelado e confirmar que aparecem apenas pedidos cancelados.
8. Selecionar Todos e confirmar que aparecem todos os pedidos.
9. Confirmar que o botão + Novo Pedido continua funcionando.
10. Confirmar que a abertura/detalhe do pedido continua funcionando.
11. Confirmar que WhatsApp, fechamento, reenvio, relatório/PDF e inclusão de consumo não foram impactados.
12. Confirmar /status 200.
13. Confirmar que nenhuma migration foi criada.
```

Aprovado pelo Agente de Revisão / Qualidade.

---

## 4. Decisão consolidada da Squad

A Squad aprova a abertura do:

```text
Hotfix 12.0.4 — Filtro de Status no Histórico de Pedidos de Refeição
```

Regra consolidada:

```text
A tela de histórico/listagem de pedidos de refeição deve abrir com filtro padrão "Novo Pedido" e, nesse estado inicial, não deve exibir nenhum pedido.
```

---

## 5. Escopo aprovado

Entram neste hotfix:

- incluir filtro de status na tela de histórico/listagem de pedidos;
- definir valor padrão como "Novo Pedido";
- não exibir pedidos quando o filtro estiver em "Novo Pedido";
- permitir filtrar por status reais dos pedidos;
- permitir opção "Todos";
- manter botões e navegação atuais.

Não entram neste hotfix:

- alteração de banco de dados;
- migration;
- alteração em models.py;
- alteração em permissões;
- alteração em WhatsApp;
- alteração em relatório/PDF;
- alteração em fechamento/reenvio;
- alteração em inclusão de consumo;
- alteração em Documentos/Holerites;
- Missão 12.1.

---

## 6. Regra funcional detalhada

### 6.1 Estado inicial da tela

Ao abrir a tela de pedidos sem filtro informado:

```text
Filtro selecionado: Novo Pedido
Pedidos exibidos: nenhum
Mensagem: Selecione um status para consultar os pedidos.
```

### 6.2 Opções do filtro

O filtro deve conter, no mínimo:

```text
Novo Pedido
Aberto
Fechado
Enviado
Cancelado
Todos
```

Se o projeto possuir outros status reais, o Codex deve preservar ou incluir conforme a estrutura real.

### 6.3 Filtro por status

Quando o usuário selecionar um status real, listar apenas pedidos daquele status.

Exemplo:

```text
Aberto → lista pedidos abertos.
Fechado → lista pedidos fechados.
Enviado → lista pedidos enviados.
Cancelado → lista pedidos cancelados.
```

### 6.4 Filtro Todos

Quando selecionar:

```text
Todos
```

A tela deve listar todos os pedidos, conforme comportamento atual.

---

## 7. Branch e PR

Criar ou utilizar a branch:

```text
hotfix-12-0-4-filtro-status-pedidos-refeicao
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 8. Arquivos prováveis

Verificar a estrutura real antes de alterar.

Arquivos prováveis:

```text
app/departamento_pessoal/pedido_refeicoes/routes.py
app/templates/departamento_pessoal/pedido_refeicoes/pedidos.html
app/templates/departamento_pessoal/pedido_refeicoes/listar_pedidos.html
app/templates/departamento_pessoal/pedido_refeicoes/*.html
```

---

## 9. Não alterar

Não alterar:

- models.py;
- migrations;
- permissões;
- WhatsApp;
- relatório/PDF;
- fechamento/reenvio;
- inclusão de consumo;
- cardápio;
- restaurantes;
- colaboradores;
- Documentos/Holerites;
- Missão 12.1.

---

## 10. Critérios de aceite

O hotfix será considerado concluído quando:

1. Tela de histórico/listagem de pedidos exibir filtro de status.
2. Filtro abrir com valor padrão "Novo Pedido".
3. Com "Novo Pedido", nenhum pedido for exibido.
4. Com "Novo Pedido", aparecer mensagem amigável orientando a selecionar um status.
5. Filtro "Aberto" listar apenas pedidos abertos.
6. Filtro "Fechado" listar apenas pedidos fechados.
7. Filtro "Enviado" listar apenas pedidos enviados.
8. Filtro "Cancelado" listar apenas pedidos cancelados.
9. Filtro "Todos" listar todos os pedidos.
10. Botão "+ Novo Pedido" continuar funcionando.
11. Acesso/detalhe dos pedidos continuar funcionando.
12. WhatsApp não ser impactado.
13. Fechamento/reenvio não serem impactados.
14. Relatório/PDF não serem impactados.
15. Inclusão de consumo não ser impactada.
16. Nenhuma migration ser criada.
17. /status continuar 200.
18. PR ser aberto antes do merge.

---

## 11. Testes locais

Testar localmente:

1. Abrir tela de Pedidos de Refeição.
2. Confirmar filtro padrão "Novo Pedido".
3. Confirmar que nenhum pedido aparece.
4. Confirmar mensagem amigável.
5. Filtrar por Aberto.
6. Filtrar por Fechado.
7. Filtrar por Enviado.
8. Filtrar por Cancelado.
9. Filtrar por Todos.
10. Abrir detalhe de um pedido.
11. Criar novo pedido.
12. Testar WhatsApp rapidamente.
13. Testar /status.

---

## 12. Deploy e produção

Após PR aprovado, merge e deploy no Render:

1. Aguardar deploy automático.
2. Não executar migration.
3. Testar em produção:
   - tela abre sem listar pedidos;
   - filtro "Novo Pedido" selecionado;
   - filtros por status funcionando;
   - "Todos" funcionando;
   - botão Novo Pedido funcionando.

---

## 13. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos alterados.
2. Confirmação de que não houve migration.
3. Como o filtro foi implementado.
4. Quais status foram incluídos.
5. Como a tela se comporta no status padrão "Novo Pedido".
6. Testes executados.
7. Confirmação de que WhatsApp, relatório/PDF e inclusão de consumo não foram impactados.
8. Link do Pull Request.
