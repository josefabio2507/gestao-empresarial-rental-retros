# Missão 11.9 — Recuperação de Senha com Token por E-mail

## 1. Contexto

Estamos no projeto **Gestão Empresarial Rental Retros**, desenvolvido em **Python + Flask + SQLAlchemy + Flask-Migrate**, com banco **PostgreSQL no Render**, SQLite local, versionamento via **GitHub/GitHub Desktop** e deploy no **Render**.

O sistema já possui:

- login funcional;
- cadastro e gestão de usuários;
- níveis de acesso;
- permissões por módulo e ação;
- troca obrigatória de senha no primeiro acesso;
- alteração voluntária de senha dentro do sistema;
- link “Esqueci minha senha” informativo;
- auditoria/logs operacionais;
- produção parcial no Render.

Atualmente, o fluxo **“Esqueci minha senha”** ainda é apenas informativo.  
Agora precisamos torná-lo funcional, com **token seguro enviado por e-mail**.

---

## 2. Objetivo da missão

Implementar recuperação de senha segura por e-mail:

1. Usuário clica em **Esqueci minha senha**.
2. Informa o e-mail cadastrado.
3. Sistema gera token seguro com validade.
4. Sistema envia link de redefinição por e-mail.
5. Usuário acessa o link.
6. Usuário define nova senha.
7. Token é invalidado após uso.
8. Usuário consegue fazer login com a nova senha.

---

## 3. Análise e aprovação da Squad

### 3.1 Agente de Design / Experiência do Usuário

A experiência deve ser simples, clara e segura.

Fluxo desejado:

```text
Login
└── Esqueci minha senha
    ├── Solicitar recuperação
    ├── Mensagem neutra de confirmação
    └── Redefinir senha pelo link recebido
```

Diretrizes de UX:

- A tela deve ser objetiva e profissional.
- Não informar se o e-mail existe ou não.
- Mensagens devem ser claras e neutras.
- Evitar linguagem técnica para o usuário final.
- A tela de redefinição deve pedir nova senha e confirmação.
- Em caso de token inválido, expirado ou já usado, mostrar mensagem amigável.
- Manter identidade visual já aplicada no sistema.

Mensagem recomendada após solicitação:

```text
Se o e-mail informado estiver cadastrado, enviaremos as instruções de recuperação.
```

Essa mensagem deve ser exibida tanto para e-mails existentes quanto inexistentes.

Aprovado pelo Agente de Design.

---

### 3.2 Agente de Desenvolvimento / Arquitetura

A recuperação de senha é uma funcionalidade de segurança.  
Deve ser implementada com arquitetura própria, evitando lógica espalhada nas rotas.

Recomendação arquitetural:

- Criar model próprio para tokens de recuperação.
- Não salvar token puro no banco.
- Salvar apenas hash do token.
- Definir validade do token.
- Invalidar token após uso.
- Preservar o login atual.
- Preservar a troca obrigatória de senha.
- Preservar alteração voluntária de senha.
- Registrar logs operacionais sem dados sensíveis.

Recomendação de model:

```text
TokenRecuperacaoSenha
```

Campos sugeridos:

```text
id
usuario_id
token_hash
expira_em
usado_em
criado_em
ip_solicitacao
user_agent
```

Essa missão provavelmente exige alteração em `models.py` e criação de migration.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 3.3 Agente de Código / Programação

A implementação deve ser feita com services específicos.

Arquivos prováveis:

```text
app/models.py
app/auth/routes.py
app/services/recuperacao_senha_service.py
app/services/email_service.py
app/templates/auth/esqueci_senha.html
app/templates/auth/redefinir_senha.html
app/templates/auth/recuperacao_senha_instrucoes.html, se necessário
app/templates/auth/login.html
config.py
requirements.txt, se necessário
migrations/
```

Preferência técnica:

- Criar service para gerar, validar e consumir token.
- Criar service para envio de e-mail.
- Usar variáveis de ambiente para configuração SMTP.
- Usar token com `secrets.token_urlsafe`.
- Salvar hash do token com SHA-256 ou método equivalente seguro.
- Não enviar senha por e-mail.
- Não logar token puro.
- Não exibir token em logs.

Bibliotecas possíveis:

- Preferir implementação simples com `smtplib` e `email.message`, para evitar dependência nova.
- Se já houver biblioteca de e-mail no projeto, reaproveitar.
- Se optar por `Flask-Mail` ou similar, atualizar `requirements.txt`.

Aprovado pelo Agente de Código / Programação.

---

### 3.4 Agente de Revisão / Qualidade

A missão deve ser testada com cuidado porque envolve segurança.

Cenários obrigatórios:

1. Solicitação com e-mail cadastrado.
2. Solicitação com e-mail inexistente.
3. Mensagem neutra em ambos os casos.
4. Link enviado por e-mail para usuário existente.
5. Token válido permite redefinir senha.
6. Token expirado não permite redefinir senha.
7. Token já usado não permite reutilização.
8. Senha e confirmação diferentes não devem salvar.
9. Nova senha deve ser salva com hash.
10. Login com nova senha deve funcionar.
11. Login com senha antiga deve falhar.
12. Logs não devem conter senha nem token.
13. `/status` deve continuar 200.
14. Troca obrigatória de senha deve continuar funcionando.
15. Alteração voluntária de senha deve continuar funcionando.

Aprovado pelo Agente de Revisão / Qualidade.

---

## 4. Decisão da Squad

A Squad aprova a abertura da:

```text
Missão 11.9 — Recuperação de Senha com Token por E-mail
```

Com a seguinte decisão técnica:

```text
Criar model próprio para tokens de recuperação de senha.
Gerar migration.
Enviar link seguro por e-mail.
Salvar apenas hash do token.
Invalidar token após uso.
Não informar se o e-mail existe.
Registrar logs sem dados sensíveis.
```

---

## 5. Fluxo funcional esperado

### 5.1 Solicitação de recuperação

Rota sugerida:

```text
/auth/esqueci-senha
```

Métodos:

```text
GET
POST
```

Fluxo:

1. Usuário acessa a tela.
2. Informa e-mail.
3. Sistema procura usuário ativo com aquele e-mail.
4. Se encontrar, gera token e envia e-mail.
5. Se não encontrar, não gera token.
6. Em ambos os casos, exibe a mesma mensagem neutra.

Mensagem:

```text
Se o e-mail informado estiver cadastrado, enviaremos as instruções de recuperação.
```

---

### 5.2 Link de redefinição

Rota sugerida:

```text
/auth/redefinir-senha/<token>
```

Métodos:

```text
GET
POST
```

Fluxo:

1. Sistema recebe token pela URL.
2. Calcula hash do token.
3. Procura token válido, não expirado e não usado.
4. Se inválido, expirado ou usado, exibe mensagem amigável.
5. Se válido, mostra formulário para nova senha.
6. Usuário informa nova senha e confirmação.
7. Sistema valida.
8. Sistema salva nova senha com hash usando método existente do model `Usuario`, preferencialmente `definir_senha()`.
9. Sistema marca token como usado.
10. Sistema invalida outros tokens ativos do mesmo usuário, se houver.
11. Sistema redireciona para login com mensagem de sucesso.

---

## 6. Regras de segurança

### 6.1 Não revelar existência de e-mail

A tela de solicitação nunca deve revelar se o e-mail existe.

Correto:

```text
Se o e-mail informado estiver cadastrado, enviaremos as instruções de recuperação.
```

Incorreto:

```text
E-mail não encontrado.
Usuário inexistente.
E-mail enviado com sucesso para usuário cadastrado.
```

---

### 6.2 Não enviar senha por e-mail

O sistema nunca deve enviar senha atual ou nova senha por e-mail.

O e-mail deve conter apenas link de redefinição.

---

### 6.3 Não salvar token puro no banco

O banco deve salvar apenas hash do token.

Exemplo conceitual:

```python
token = secrets.token_urlsafe(48)
token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
```

A URL usa o token puro, mas o banco guarda apenas o hash.

---

### 6.4 Validade do token

Definir validade padrão:

```text
60 minutos
```

Idealmente configurável por variável ou constante.

---

### 6.5 Token de uso único

Após redefinir senha:

```text
usado_em = data/hora atual
```

Token usado não pode ser reutilizado.

---

### 6.6 Invalidação de tokens antigos

Ao gerar novo token ou após redefinir senha, invalidar tokens anteriores ainda ativos do mesmo usuário, se fizer sentido com a estrutura do model.

---

## 7. Model sugerido

Criar model em `app/models.py` conforme padrão real do projeto.

Nome sugerido:

```python
class TokenRecuperacaoSenha(db.Model):
    __tablename__ = "tokens_recuperacao_senha"
```

Campos sugeridos:

```text
id
usuario_id
token_hash
expira_em
usado_em
criado_em
ip_solicitacao
user_agent
```

Relacionamento:

```text
usuario_id → usuarios.id
```

Ajustar nomes conforme padrão real do projeto.

Índices recomendados:

```text
token_hash
usuario_id
expira_em
```

---

## 8. Migration

Como haverá novo model/tabela, criar migration com Flask-Migrate.

Comandos esperados localmente:

```bash
flask db migrate -m "cria tokens de recuperacao de senha"
flask db upgrade
```

Ou conforme padrão de execução do projeto.

A migration deve criar a tabela de tokens.

Não alterar tabelas existentes sem necessidade.

---

## 9. Service de recuperação de senha

Criar service dedicado, por exemplo:

```text
app/services/recuperacao_senha_service.py
```

Funções sugeridas:

```python
gerar_token_recuperacao(usuario, ip=None, user_agent=None)
validar_token_recuperacao(token)
redefinir_senha_por_token(token, nova_senha)
invalidar_tokens_usuario(usuario)
```

Responsabilidades:

- gerar token;
- salvar hash;
- definir expiração;
- validar token;
- marcar token como usado;
- chamar `usuario.definir_senha(nova_senha)`;
- retornar estados claros para as rotas.

---

## 10. Service de e-mail

Criar ou ajustar service:

```text
app/services/email_service.py
```

Responsabilidades:

- montar mensagem;
- enviar e-mail via SMTP;
- usar variáveis de ambiente;
- não expor senha/token em logs;
- falhar de forma controlada.

Variáveis de ambiente sugeridas:

```text
MAIL_SERVER
MAIL_PORT
MAIL_USE_TLS
MAIL_USE_SSL
MAIL_USERNAME
MAIL_PASSWORD
MAIL_DEFAULT_SENDER
BASE_URL
```

Exemplo produção:

```text
BASE_URL=https://apprentalretros.onrender.com
```

Exemplo local:

```text
BASE_URL=http://127.0.0.1:5000
```

Se não houver configuração de SMTP, em ambiente local pode registrar no terminal apenas uma mensagem controlada com o link, mas sem vazar em produção.

---

## 11. Configuração

Atualizar `config.py` para ler variáveis de ambiente, se necessário.

Exemplo conceitual:

```python
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
```

Adaptar conforme padrão real do projeto.

---

## 12. Templates

### 12.1 Tela de solicitação

Template sugerido:

```text
app/templates/auth/esqueci_senha.html
```

Campos:

```text
email
```

Botões:

```text
Enviar instruções
Voltar ao login
```

Mensagem neutra após envio.

---

### 12.2 Tela de redefinição

Template sugerido:

```text
app/templates/auth/redefinir_senha.html
```

Campos:

```text
nova_senha
confirmar_senha
```

Botões:

```text
Redefinir senha
Voltar ao login
```

Validar:

- senha obrigatória;
- confirmação obrigatória;
- senha e confirmação iguais;
- aplicar regra mínima de senha, se já existir no projeto.

---

## 13. Atualizar tela de login

O link atual:

```text
Esqueci minha senha
```

deve deixar de apontar para tela apenas informativa e passar a abrir:

```text
/auth/esqueci-senha
```

Preservar o visual já aplicado no login.

---

## 14. Logs operacionais

Registrar logs sem dados sensíveis:

Eventos sugeridos:

```text
Solicitação de recuperação de senha recebida.
Token de recuperação gerado para usuário ID X.
Senha redefinida via recuperação para usuário ID X.
Tentativa de uso de token inválido/expirado.
```

Não registrar:

- senha;
- token puro;
- hash do token;
- conteúdo do e-mail.

Se existir `logs_service.py`, usar o padrão atual.

---

## 15. Não alterar

Não alterar:

- regras de permissões;
- regras de LGPD;
- importação CSV;
- pedido de refeições;
- relatórios;
- módulos de departamento;
- cards;
- layouts fora do fluxo de senha, salvo ajuste mínimo necessário;
- lógica de login além do redirecionamento do link “Esqueci minha senha”.

---

## 16. Arquivos prováveis

Analisar estrutura real antes de alterar.

Arquivos prováveis:

```text
app/models.py
app/auth/routes.py
app/templates/auth/login.html
app/templates/auth/esqueci_senha.html
app/templates/auth/redefinir_senha.html
app/services/recuperacao_senha_service.py
app/services/email_service.py
app/services/logs_service.py, se necessário
config.py
requirements.txt, se adicionar biblioteca
migrations/
```

---

## 17. Critérios de aceite

A missão será considerada concluída quando:

1. Tela “Esqueci minha senha” funcionar.
2. Usuário puder informar e-mail.
3. Mensagem após solicitação for neutra.
4. Sistema não revelar se o e-mail existe.
5. Token seguro for gerado para e-mail cadastrado.
6. Token puro não for salvo no banco.
7. Token tiver validade.
8. Link de redefinição for enviado por e-mail.
9. Link válido abrir tela de redefinição.
10. Token expirado for recusado.
11. Token já usado for recusado.
12. Nova senha for salva com hash.
13. Senha antiga deixar de funcionar.
14. Nova senha permitir login.
15. Token for invalidado após uso.
16. Logs não registrarem senha ou token.
17. Troca obrigatória de senha continuar funcionando.
18. Alteração voluntária de senha continuar funcionando.
19. `/status` continuar 200.
20. Migration ser criada e aplicada localmente.
21. Produção exigir configuração das variáveis SMTP no Render.
22. Nenhuma regra de negócio fora do fluxo de senha ser alterada.

---

## 18. Testes manuais locais

Testar localmente:

1. Acessar login.
2. Clicar em “Esqueci minha senha”.
3. Informar e-mail existente.
4. Confirmar mensagem neutra.
5. Confirmar geração do token.
6. Obter link de teste local conforme estratégia definida.
7. Acessar link.
8. Definir nova senha.
9. Fazer login com nova senha.
10. Confirmar que senha antiga não funciona.
11. Tentar reutilizar o mesmo link.
12. Confirmar bloqueio.
13. Testar e-mail inexistente.
14. Confirmar que a mensagem é igual.
15. Testar token inválido.
16. Testar token expirado, se possível.
17. Testar alteração voluntária de senha.
18. Testar troca obrigatória de senha.
19. Testar `/status`.

---

## 19. Variáveis no Render

Antes do teste em produção, configurar no Render:

```text
MAIL_SERVER
MAIL_PORT
MAIL_USE_TLS
MAIL_USE_SSL
MAIL_USERNAME
MAIL_PASSWORD
MAIL_DEFAULT_SENDER
BASE_URL
```

Valor recomendado:

```text
BASE_URL=https://apprentalretros.onrender.com
```

Não commitar senhas SMTP.

Não colocar credenciais reais no código.

---

## 20. Deploy e produção

Sequência sugerida:

1. Implementar localmente.
2. Criar migration.
3. Rodar upgrade local.
4. Testar local.
5. Commit.
6. Push.
7. Deploy Render.
8. Configurar variáveis SMTP no Render.
9. Executar migration no Render, se o fluxo do projeto exigir.
10. Testar recuperação com e-mail real controlado.
11. Validar logs.
12. Validar login com nova senha.

---

## 21. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Model criado.
4. Migration criada.
5. Rotas criadas.
6. Services criados.
7. Templates criados/alterados.
8. Variáveis de ambiente necessárias.
9. Como testar localmente.
10. Como testar em produção.
11. Se `models.py` foi alterado.
12. Se migration foi necessária.
13. Pontos de atenção antes do deploy.
