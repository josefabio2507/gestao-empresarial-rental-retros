# Missão 11.9.1 — Sincronização dos Módulos Base em Produção

## 1. Contexto

Estamos no projeto **Gestão Empresarial Rental Retros**, desenvolvido em **Python + Flask + SQLAlchemy + Flask-Migrate**, com banco **PostgreSQL no Render**, SQLite local, versionamento via **GitHub/GitHub Desktop**, deploy no **Render** e fluxo oficial de desenvolvimento com:

```text
ChatGPT/Squad → planeja a missão
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

Após a Missão 11.9, foi identificado comportamento diferente entre o ambiente local e o ambiente de produção no Render.

No ambiente local, ao acessar departamentos como **Financeiro**, o administrador consegue visualizar os cards internos dos módulos em construção.

No Render/produção, com usuário administrador, ao acessar alguns departamentos aparece a mensagem:

```text
Você não possui módulos liberados neste departamento.
```

O diagnóstico técnico apontou que o problema mais provável é **diferença de dados entre o banco local e o banco do Render**: alguns departamentos existem e estão ativos em produção, mas não possuem módulos ativos cadastrados na tabela `modulos`.

---

## 2. Diagnóstico consolidado

O fluxo atual funciona assim:

1. A home `/` busca departamentos liberados em `buscar_departamentos_liberados_usuario`.
2. Para administrador, essa função retorna todos os departamentos ativos.
3. Ao clicar em `/departamentos/<slug>`, a rota chama `buscar_modulos_liberados`.
4. Para administrador, essa função ignora permissões, mas retorna apenas módulos ativos existentes no departamento.
5. Se o departamento não tiver módulos ativos cadastrados, a rota bloqueia com a mensagem:

```text
Você não possui módulos liberados neste departamento.
```

Conclusão:

```text
Administrador ignora permissões, mas não ignora ausência de dados no banco.
```

Portanto, o problema não é a regra de permissão do administrador. O problema provável é que o banco do Render não recebeu os módulos base que existem no banco local.

---

## 3. Análise da Squad

### 3.1 Agente de Desenvolvimento / Arquitetura

O problema é de **sincronização de dados estruturais base**, não de autenticação ou permissão.

A correção recomendada é criar um seed temporário, idempotente e seguro para garantir que os departamentos e módulos base existam em produção.

Diretrizes arquiteturais:

- Não alterar regra de permissão.
- Não alterar lógica de administrador.
- Não alterar models.py.
- Não criar migration.
- Não recriar usuários.
- Não alterar senhas.
- Não apagar registros existentes.
- Não alterar permissões existentes.
- Não forçar IDs manuais.
- Criar apenas o que estiver ausente.
- Atualizar com segurança apenas campos básicos se o registro já existir, como nome, descrição, slug, departamento e status ativo, se fizer sentido e se não causar risco.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 3.2 Agente de Design / Experiência do Usuário

A experiência desejada para administrador é:

- O administrador deve conseguir acessar todos os departamentos principais.
- Quando um módulo ainda não estiver construído, ele pode aparecer como card com indicação clara:
  - “Funcionalidade em construção”
  - “Acessar módulo”, quando aplicável
  - ou mensagem equivalente já existente no sistema.
- O administrador não deve cair em “Acesso negado” apenas porque os módulos base não foram cadastrados no banco.

Esta missão não deve alterar layout, cards ou estilo visual.  
Apenas deve garantir que o conteúdo correto apareça em produção, igual ao ambiente local.

Aprovado pelo Agente de Design / Experiência do Usuário.

---

### 3.3 Agente de Código / Programação

A implementação deve ser feita por seed temporário e idempotente.

Nome sugerido do arquivo:

```text
app/seed_modulos_base_producao.py
```

O seed deve:

1. Usar `create_app()` e `app.app_context()`.
2. Trabalhar com os models reais do projeto.
3. Localizar departamentos pelo slug.
4. Criar departamentos ausentes, se necessário.
5. Garantir módulos base por departamento.
6. Não criar usuário admin.
7. Não alterar permissões existentes.
8. Não apagar nada.
9. Não criar migration.
10. Exibir resumo final no terminal.

O seed deve ser seguro para rodar mais de uma vez.

Aprovado pelo Agente de Código / Programação.

---

### 3.4 Agente de Revisão / Qualidade

A missão envolve produção e banco de dados, então precisa de checklist rigoroso.

Critérios de teste:

- Rodar o seed localmente.
- Confirmar que não duplica departamentos.
- Confirmar que não duplica módulos.
- Confirmar que `/status` continua 200.
- Confirmar que administrador consegue acessar os departamentos localmente.
- Fazer PR antes de chegar na main.
- Após merge/deploy, rodar seed no Render Shell.
- Validar os departamentos em produção.
- Confirmar que permissões existentes não foram removidas ou alteradas.
- Após validação, remover o seed temporário em um commit/PR posterior, se desejado.

Aprovado pelo Agente de Revisão / Qualidade.

---

## 4. Decisão da Squad

A Squad aprova a abertura da:

```text
Missão 11.9.1 — Sincronização dos Módulos Base em Produção
```

Com a seguinte decisão técnica:

```text
Criar seed temporário idempotente para garantir os departamentos e módulos base no banco de produção, sem alterar permissões, sem criar usuário, sem apagar dados, sem alterar models.py e sem migration.
```

---

## 5. Objetivo da missão

Criar um seed temporário para garantir que os departamentos e módulos base existam no banco de produção, corrigindo a diferença entre SQLite local e PostgreSQL do Render.

O objetivo é que o comportamento de produção fique compatível com o ambiente local para o administrador.

---

## 6. Escopo do seed

O seed deve garantir os departamentos base e seus módulos.

### 6.1 Departamentos base

Garantir, se ainda não existirem:

```text
Administração
Departamento Pessoal
Financeiro
Operação
Segurança do Trabalho
```

Usar os slugs reais do projeto. Exemplos prováveis:

```text
administracao
departamento_pessoal
financeiro
operacao
seguranca_trabalho
```

Adaptar conforme o padrão real existente no banco/model.

---

### 6.2 Módulos base — Departamento Pessoal

Garantir os módulos principais esperados:

```text
Colaboradores
Admissão
Folha de Pagamento
Ponto
Férias
Documentos
Pedidos de Refeição
```

Observação importante:

Não reintroduzir como cards diretos do Departamento Pessoal:

```text
Restaurantes
Cardápio
Relatórios de Refeições
Pedido de Refeições - Restaurantes
Pedido de Refeições - Cardápio
Pedido de Refeições - Pedidos
Pedido de Refeições - Relatórios
```

Esses pertencem ao hub interno de Pedidos de Refeição e/ou à tela de permissões, conforme regra já estabilizada.

---

### 6.3 Módulos base — Financeiro

Garantir os módulos:

```text
Contas a Pagar
Contas a Receber
Fluxo de Caixa
Orçamentos
Faturamento
Relatórios
```

Todos podem permanecer como funcionalidade em construção, conforme padrão atual do sistema.

---

### 6.4 Módulos base — Operação

Garantir os módulos base conforme seed local existente no projeto.

Se já houver `seed.py` com essa lista, usar a mesma lista.  
Não inventar nomes novos sem verificar o seed existente.

---

### 6.5 Módulos base — Segurança do Trabalho

Garantir os módulos base conforme seed local existente no projeto.

Se já houver `seed.py` com essa lista, usar a mesma lista.  
Não inventar nomes novos sem verificar o seed existente.

---

### 6.6 Administração

A Administração já possui navegação própria para:

```text
Usuários
Permissões
Auditoria / Logs
```

Não criar cards desnecessários se isso não fizer parte do padrão real do projeto.

Verificar o comportamento atual antes de criar módulos administrativos extras.

---

## 7. Regras de segurança do seed

O seed deve ser idempotente:

```text
Pode rodar uma vez ou várias vezes sem duplicar registros.
```

Deve buscar registros por slug ou chave lógica estável.

Não deve:

- apagar departamentos;
- apagar módulos;
- apagar permissões;
- alterar permissões existentes;
- criar usuário admin;
- alterar senha de usuário;
- alterar dados de colaboradores;
- alterar pedidos de refeição;
- alterar restaurantes;
- alterar cardápio;
- alterar logs;
- alterar tokens de recuperação de senha;
- alterar IDs manualmente;
- criar migration.

---

## 8. Arquivo a criar

Criar:

```text
app/seed_modulos_base_producao.py
```

O script deve executar com:

```bash
python -m app.seed_modulos_base_producao
```

Deve exibir resumo no terminal, por exemplo:

```text
Seed de módulos base iniciado...
Departamentos criados: X
Departamentos atualizados/preservados: X
Módulos criados: X
Módulos atualizados/preservados: X
Permissões alteradas: 0
Seed de módulos base concluído com sucesso.
```

---

## 9. Branch e PR

Criar ou utilizar a branch:

```text
hotfix-11-9-1-seed-modulos-base
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 10. Não alterar

Não alterar:

- `models.py`
- migrations
- regras de permissão
- regra de administrador
- login
- recuperação de senha
- LGPD
- pedido de refeições
- colaboradores
- relatórios
- templates visuais
- CSS
- routes, salvo se houver necessidade justificada para import/teste, mas a preferência é não alterar

Não criar migration.

---

## 11. Arquivos prováveis

Arquivos prováveis:

```text
app/seed_modulos_base_producao.py
docs/missoes/missao_11_9_1_seed_modulos_base.md
```

Arquivos a consultar:

```text
seed.py
app/models.py
app/services/permissoes_service.py
app/departamentos/routes.py
app/templates/departamentos/detalhe.html
```

Preferência:

```text
Criar apenas o seed temporário e o documento da missão.
```

---

## 12. Critérios de aceite

A missão será considerada concluída quando:

1. Seed temporário for criado.
2. Seed for idempotente.
3. Seed não criar usuário admin.
4. Seed não alterar senhas.
5. Seed não apagar dados.
6. Seed não alterar permissões existentes.
7. Seed garantir departamentos base.
8. Seed garantir módulos base do Departamento Pessoal.
9. Seed garantir módulos base do Financeiro.
10. Seed garantir módulos base da Operação conforme `seed.py`.
11. Seed garantir módulos base da Segurança do Trabalho conforme `seed.py`.
12. Seed não reintroduzir Restaurantes/Cardápio/Relatórios como cards diretos do Departamento Pessoal.
13. Seed exibir resumo no terminal.
14. `/status` continuar 200.
15. `models.py` não ser alterado.
16. Nenhuma migration ser criada.
17. PR ser aberto para revisão antes do merge.
18. Após execução no Render, administrador conseguir acessar departamentos com módulos base.
19. Produção e local ficarem com comportamento compatível.

---

## 13. Testes locais

Testar localmente:

1. Garantir que está na branch correta.
2. Rodar:

```bash
python -m app.seed_modulos_base_producao
```

3. Rodar novamente para confirmar que não duplica.
4. Iniciar aplicação local.
5. Testar `/status`.
6. Login como administrador.
7. Acessar Departamento Pessoal.
8. Confirmar que os módulos principais aparecem corretamente.
9. Confirmar que Restaurantes/Cardápio/Relatórios não aparecem diretamente no Departamento Pessoal.
10. Acessar Financeiro.
11. Confirmar que os módulos base aparecem.
12. Acessar Operação.
13. Confirmar comportamento esperado.
14. Acessar Segurança do Trabalho.
15. Confirmar comportamento esperado.

---

## 14. Execução em produção

Após PR aprovado, merge e deploy no Render, executar no Render Shell:

```bash
python -m app.seed_modulos_base_producao
```

Depois validar em produção:

1. Login como administrador.
2. Acessar Departamento Pessoal.
3. Acessar Financeiro.
4. Acessar Operação.
5. Acessar Segurança do Trabalho.
6. Confirmar que não aparece “Você não possui módulos liberados neste departamento” para administrador quando o departamento deveria ter módulos base.
7. Testar `/status`.

---

## 15. Pós-validação

Após validar produção, decidir se o seed temporário deve permanecer ou ser removido.

Recomendação:

- Manter temporariamente até estabilização.
- Depois remover em PR separado, se a equipe decidir que não deve ficar no repositório.

Nome sugerido para futura remoção:

```text
Remoção do seed temporário de módulos base
```

---

## 16. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Se `models.py` foi alterado.
4. Se migration foi criada.
5. Lista de departamentos garantidos.
6. Lista de módulos garantidos por departamento.
7. Como o seed evita duplicidade.
8. Se permissões foram alteradas.
9. Como testar localmente.
10. Como executar no Render.
11. Pontos de atenção antes do merge/deploy.
