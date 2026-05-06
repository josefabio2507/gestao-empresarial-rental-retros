# Missão 12.0 — Vínculo entre Usuário e Colaborador

## 1. Contexto

Estamos no projeto **Gestão Empresarial Rental Retros**, desenvolvido em **Python + Flask + SQLAlchemy + Flask-Migrate**, com banco **PostgreSQL no Render**, SQLite local, versionamento via **GitHub/GitHub Desktop**, deploy no **Render** e fluxo oficial de desenvolvimento com:

```text
ChatGPT/Squad → planeja a missão
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

O sistema já possui:

- login funcional;
- cadastro e gestão de usuários;
- permissões por módulo e ação;
- troca obrigatória de senha;
- recuperação de senha por e-mail;
- cadastro de colaboradores;
- importação em massa de colaboradores;
- logs/auditoria;
- Departamento Pessoal com módulos base;
- estrutura futura prevista para documentos e holerites.

Foi definido no planejamento que cada colaborador poderá passar a ser usuário do sistema, mas sem perder a regra atual de permissões.

Hoje existem usuários que também são colaboradores e que possuem permissões para acessar módulos operacionais/administrativos. Esse comportamento deve ser preservado.

A regra oficial aprovada é:

```text
Usuário continua tendo permissões normalmente.
Se estiver vinculado a um colaborador, também poderá acessar áreas pessoais.
```

Esta missão cria a base técnica para isso.

---

## 2. Objetivo da missão

Criar um vínculo opcional entre **Usuário** e **Colaborador**, permitindo que:

1. Um usuário do sistema possa estar vinculado a um colaborador cadastrado.
2. O vínculo seja opcional.
3. Usuários sem colaborador vinculado continuem funcionando normalmente.
4. Usuários com colaborador vinculado continuem mantendo suas permissões atuais normalmente.
5. O sistema fique preparado para o futuro módulo:

```text
Departamento Pessoal
└── Documentos
    └── Holerites
```

Esta missão **não** deve implementar holerites ainda.  
Ela deve apenas criar a base de vínculo entre `Usuario` e `Colaborador`.

---

## 3. Análise e aprovação da Squad

### 3.1 Agente de Desenvolvimento / Arquitetura

A missão é necessária antes de criar o módulo de Holerites, porque o sistema precisa saber qual colaborador está associado ao usuário logado.

Hoje temos duas entidades diferentes:

```text
Usuario
Colaborador
```

A estrutura recomendada é criar uma relação opcional:

```text
Usuario
└── colaborador_id
```

Esse campo deve permitir `NULL`, porque nem todo usuário será necessariamente um colaborador.

Regra arquitetural:

```text
Usuário sem colaborador vinculado:
continua usando permissões normalmente.

Usuário com colaborador vinculado:
continua usando permissões normalmente
e também poderá acessar áreas pessoais do colaborador.
```

Essa missão provavelmente exige:

- alteração em `models.py`;
- migration;
- ajuste na criação/edição de usuários;
- validações de vínculo;
- logs de alteração de vínculo.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 3.2 Agente de Design / Experiência do Usuário

A experiência deve ser simples para o administrador.

Na tela de criação/edição de usuário, deve existir um campo opcional:

```text
Colaborador vinculado
```

O campo deve permitir selecionar um colaborador já cadastrado.

Para evitar confusão com nomes iguais, a opção deve exibir informações suficientes, como:

```text
Matrícula - Nome - Equipe
```

Exemplo:

```text
1234 - João da Silva - Operação
```

Na listagem ou detalhe de usuários, deve ser possível identificar o vínculo.

Exemplo:

```text
Colaborador vinculado: 1234 - João da Silva
```

Se não houver vínculo:

```text
Colaborador vinculado: Não vinculado
```

Não criar telas do Portal do Colaborador nesta missão.

Aprovado pelo Agente de Design / Experiência do Usuário.

---

### 3.3 Agente de Código / Programação

A implementação deve ser objetiva e segura.

Arquivos prováveis:

```text
app/models.py
app/usuarios/routes.py
app/templates/usuarios/criar.html
app/templates/usuarios/editar.html
app/templates/usuarios/listar.html
app/templates/usuarios/detalhes.html, se existir
app/services/usuarios_service.py, se existir
app/services/logs_service.py, se necessário
migrations/versions/
docs/missoes/missao_12_0_vinculo_usuario_colaborador.md
```

Implementação esperada:

1. Adicionar campo opcional `colaborador_id` em `Usuario`.
2. Criar relacionamento com `Colaborador`.
3. Criar migration.
4. Incluir seleção de colaborador na criação e edição de usuário.
5. Exibir colaborador vinculado na gestão de usuários.
6. Impedir vínculo duplicado de um mesmo colaborador em mais de um usuário ativo, se aplicável.
7. Preservar todo o funcionamento atual de permissões.

Regras recomendadas:

```text
Um usuário pode ter no máximo um colaborador vinculado.
Um colaborador deve estar vinculado a no máximo um usuário ativo.
O vínculo deve ser opcional.
Usuário sem vínculo continua funcionando normalmente.
Usuário com vínculo continua mantendo permissões normalmente.
```

Aprovado pelo Agente de Código / Programação.

---

### 3.4 Agente de Revisão / Qualidade

A missão envolve identidade de usuário e dados de colaborador. Deve ser testada com cuidado.

Testes obrigatórios:

1. Criar usuário sem colaborador vinculado.
2. Criar usuário com colaborador vinculado.
3. Editar usuário e adicionar vínculo.
4. Editar usuário e trocar vínculo.
5. Editar usuário e remover vínculo.
6. Confirmar que permissões do usuário continuam funcionando.
7. Confirmar que login continua funcionando.
8. Confirmar que troca de senha continua funcionando.
9. Confirmar que recuperação de senha continua funcionando.
10. Confirmar que usuário administrador continua funcionando.
11. Confirmar que usuário comum com permissões continua acessando seus módulos.
12. Confirmar que colaborador já vinculado a usuário ativo não pode ser vinculado novamente a outro usuário ativo.
13. Confirmar que `/status` continua 200.

A missão deve seguir obrigatoriamente:

```text
Branch separada
Pull Request
Migration revisada
Teste local antes do merge
Deploy controlado
flask db upgrade no Render
```

Aprovado pelo Agente de Revisão / Qualidade.

---

## 4. Decisão consolidada da Squad

A Squad aprova a abertura da:

```text
Missão 12.0 — Vínculo entre Usuário e Colaborador
```

Com a seguinte decisão técnica:

```text
Criar vínculo opcional entre Usuario e Colaborador, preservando a lógica atual de permissões e preparando a base para o futuro Portal do Colaborador / Documentos / Holerites.
```

---

## 5. Escopo aprovado

Entram nesta missão:

- criar vínculo opcional entre `Usuario` e `Colaborador`;
- atualizar criação de usuários;
- atualizar edição de usuários;
- exibir colaborador vinculado na gestão de usuários;
- impedir duplicidade de vínculo em usuários ativos;
- registrar logs operacionais do vínculo;
- criar migration;
- preservar permissões atuais;
- preservar login;
- preservar troca obrigatória de senha;
- preservar recuperação de senha por e-mail.

Não entram nesta missão:

- Portal do Colaborador;
- tela de Holerites;
- upload de documentos;
- download de holerites;
- integração com Google Drive;
- leitura automática de pastas do Drive;
- documentos admissionais;
- criação de documentos trabalhistas;
- alteração na regra geral de permissões;
- alteração no módulo Pedido de Refeições.

---

## 6. Estrutura futura validada

A Squad valida a estrutura futura:

```text
Departamento Pessoal
└── Documentos
    └── Holerites
```

Mas esta Missão 12.0 tratará apenas da base:

```text
Usuario ↔ Colaborador
```

Depois dela, a sequência recomendada será:

```text
Missão 12.1 — Departamento Pessoal > Documentos > Holerites
Missão 12.2 — Consulta segura de holerites pelo colaborador
Missão 12.3 — Integração com Google Drive
```

---

## 7. Regras funcionais

### 7.1 Vínculo opcional

O campo de colaborador vinculado deve ser opcional.

Usuário pode existir sem colaborador vinculado.

### 7.2 Preservação das permissões atuais

A criação do vínculo não deve alterar a lógica atual de permissões.

O sistema deve continuar usando as permissões atuais:

```text
Visualizar
Criar
Editar
Excluir
Aprovar
Exportar
```

O vínculo com colaborador não deve remover, substituir ou limitar permissões existentes.

### 7.3 Usuário vinculado a colaborador

Se o usuário estiver vinculado a um colaborador, futuramente ele poderá acessar áreas pessoais.

Nesta missão, basta salvar e exibir esse vínculo.

### 7.4 Usuário sem vínculo

Se o usuário não estiver vinculado a colaborador, tudo deve continuar funcionando normalmente.

### 7.5 Evitar duplicidade

Um colaborador não deve estar vinculado a mais de um usuário ativo.

Se tentar vincular um colaborador já vinculado a outro usuário ativo, o sistema deve impedir e exibir mensagem amigável.

Exemplo:

```text
Este colaborador já está vinculado a outro usuário ativo.
```

Se houver usuários inativos, avaliar conforme regra real do projeto. Preferência:

```text
A restrição deve considerar usuários ativos.
```

### 7.6 Remoção do vínculo

Na edição do usuário, deve ser possível remover o vínculo.

---

## 8. Alterações no model

Verificar a estrutura real de `app/models.py`.

Adicionar ao model `Usuario` um campo opcional semelhante a:

```python
colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=True)
```

E relacionamento semelhante a:

```python
colaborador = db.relationship("Colaborador", backref="usuarios")
```

Adaptar os nomes conforme tabelas e models reais do projeto.

Atenção:

- Não alterar campos existentes sem necessidade.
- Não alterar hashing de senha.
- Não alterar método de login.
- Não alterar permissões.
- Não alterar models de Pedido de Refeições.
- Não alterar models de recuperação de senha, salvo se estritamente necessário.

---

## 9. Migration

Como haverá alteração estrutural, criar migration.

Comandos esperados localmente:

```bash
flask db migrate -m "adiciona vinculo usuario colaborador"
flask db upgrade
```

Ou conforme padrão real do projeto.

A migration deve:

- adicionar `colaborador_id` em `usuarios`;
- criar foreign key para `colaboradores`;
- se tecnicamente adequado, criar índice para `colaborador_id`.

Evitar alteração em outras tabelas.

---

## 10. Tela de criação de usuário

Na tela de criação de usuário, adicionar campo opcional:

```text
Colaborador vinculado
```

Esse campo deve listar colaboradores ativos, preferencialmente com:

```text
Matrícula - Nome - Equipe
```

Deve haver uma opção:

```text
Nenhum colaborador vinculado
```

Ao salvar:

- se nenhum colaborador for selecionado, salvar `NULL`;
- se colaborador for selecionado, validar duplicidade;
- salvar o vínculo.

---

## 11. Tela de edição de usuário

Na tela de edição de usuário:

- exibir o colaborador atualmente vinculado;
- permitir trocar o colaborador;
- permitir remover o vínculo;
- validar duplicidade.

A troca de vínculo deve gerar log operacional.

---

## 12. Listagem/detalhe de usuários

Na listagem ou tela de detalhe de usuários, exibir o vínculo de forma simples.

Exemplo:

```text
Colaborador: 1234 - João da Silva
```

Se não houver vínculo:

```text
Colaborador: Não vinculado
```

Não exibir CPF, telefone ou dados sensíveis desnecessários.

---

## 13. Logs operacionais

Registrar logs sem dados sensíveis.

Eventos sugeridos:

```text
Usuário ID X vinculado ao colaborador ID Y.
Vínculo de colaborador removido do usuário ID X.
Vínculo de colaborador alterado no usuário ID X.
```

Não registrar:

- CPF;
- telefone;
- e-mail pessoal;
- documentos;
- senha.

Se existir `logs_service.py`, usar o padrão atual.

---

## 14. Não alterar

Não alterar:

- regra de login;
- regra de senha;
- recuperação de senha;
- tokens de recuperação;
- permissões atuais;
- módulos;
- departamentos;
- colaboradores, exceto consulta para seleção;
- Pedido de Refeições;
- relatórios;
- LGPD;
- cards/responsividade;
- seeds;
- Google Drive;
- holerites.

---

## 15. Arquivos prováveis

Verificar a estrutura real antes de alterar.

Arquivos prováveis:

```text
app/models.py
app/usuarios/routes.py
app/templates/usuarios/criar.html
app/templates/usuarios/editar.html
app/templates/usuarios/listar.html
app/templates/usuarios/detalhes.html
app/services/usuarios_service.py
app/services/logs_service.py
migrations/versions/
docs/missoes/missao_12_0_vinculo_usuario_colaborador.md
```

---

## 16. Branch e PR

Criar ou utilizar a branch:

```text
missao-12-0-vinculo-usuario-colaborador
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 17. Critérios de aceite

A missão será considerada concluída quando:

1. `Usuario` puder ter vínculo opcional com `Colaborador`.
2. Migration for criada.
3. Migration aplicar corretamente localmente.
4. Usuário puder ser criado sem colaborador vinculado.
5. Usuário puder ser criado com colaborador vinculado.
6. Usuário puder ser editado para adicionar vínculo.
7. Usuário puder ser editado para trocar vínculo.
8. Usuário puder ser editado para remover vínculo.
9. Colaborador já vinculado a outro usuário ativo não puder ser vinculado novamente.
10. Listagem/detalhe de usuários mostrar colaborador vinculado ou “Não vinculado”.
11. Permissões atuais continuarem funcionando.
12. Login continuar funcionando.
13. Troca obrigatória de senha continuar funcionando.
14. Recuperação de senha por e-mail continuar funcionando.
15. Logs não exibirem dados sensíveis.
16. `/status` continuar 200.
17. Nenhuma funcionalidade de holerite for criada nesta missão.
18. Nenhuma integração com Google Drive for criada nesta missão.
19. PR for aberto antes do merge.

---

## 18. Testes locais

Testar localmente:

1. Rodar migration.
2. Testar `/status`.
3. Criar usuário sem colaborador vinculado.
4. Criar usuário com colaborador vinculado.
5. Editar usuário e adicionar vínculo.
6. Editar usuário e trocar vínculo.
7. Editar usuário e remover vínculo.
8. Tentar vincular o mesmo colaborador em dois usuários ativos.
9. Confirmar bloqueio com mensagem amigável.
10. Confirmar que login funciona.
11. Confirmar que permissões do usuário continuam funcionando.
12. Confirmar que troca de senha continua funcionando.
13. Confirmar que recuperação de senha continua funcionando.
14. Confirmar que administrador continua funcionando.
15. Confirmar que logs não mostram dados sensíveis.

---

## 19. Deploy e produção

Após PR aprovado, merge e deploy no Render:

1. Aguardar deploy.
2. Abrir Render Shell.
3. Executar:

```bash
flask db upgrade
```

Se necessário:

```bash
python -m flask db upgrade
```

Se necessário:

```bash
export FLASK_APP=run.py
python -m flask db upgrade
```

Depois validar produção:

1. `/status`;
2. login administrador;
3. criação/edição de usuário;
4. vínculo com colaborador;
5. login de usuário comum;
6. recuperação de senha;
7. permissões.

---

## 20. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Se `models.py` foi alterado.
4. Migration criada.
5. Nome da migration.
6. Como foi criado o vínculo.
7. Como foi feita a validação de duplicidade.
8. Como testar localmente.
9. Como aplicar em produção.
10. Pontos de atenção antes do merge/deploy.
