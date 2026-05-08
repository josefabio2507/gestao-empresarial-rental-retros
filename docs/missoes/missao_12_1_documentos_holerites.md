# Missão 12.1 — Departamento Pessoal > Documentos > Holerites

## 1. Contexto

Projeto **Gestão Empresarial Rental Retros**, em **Python + Flask + SQLAlchemy + Flask-Migrate**, com PostgreSQL no Render, SQLite local, GitHub/GitHub Desktop e deploy no Render.

Fluxo oficial:

```text
ChatGPT/Squad → planeja a missão
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

A **Missão 12.0 — Vínculo entre Usuário e Colaborador** foi concluída. Agora o sistema já tem a base para associar um usuário a um colaborador, sem perder as permissões normais do usuário.

A estrutura de documentos aprovada é:

```text
Departamento Pessoal
└── Documentos
    └── Holerites
```

A estrutura de permissões aprovada é:

```text
Documentos Pessoais
└── Documentos
    └── Holerites
        ├── Visualizar
        └── Exportar
```

---

## 2. Objetivo

Criar a estrutura inicial do módulo:

```text
Departamento Pessoal → Documentos → Holerites
```

com controle de acesso por:

```text
Documentos Pessoais → Documentos → Holerites
```

Esta missão deve preparar a base para consulta segura de holerites por colaborador, mas **não deve implementar ainda integração automática com Google Drive**.

---

## 3. Estrutura atual dos arquivos

A estrutura atual no Google Drive está organizada assim:

```text
Holerites
├── 000123 - João da Silva
│   ├── 000123 - Holerite Mensal - 01.2026 - João da Silva.pdf
│   ├── 000123 - Adiantamento Salarial - 01.2026 - João da Silva.pdf
│   └── 000123 - Holerite Mensal - 02.2026 - João da Silva.pdf
```

Padrão oficial do nome do arquivo:

```text
MATRICULA - TIPO - COMPETENCIA - NOME.pdf
```

Exemplo:

```text
000123 - Holerite Mensal - 01.2026 - João da Silva.pdf
000123 - Adiantamento Salarial - 01.2026 - João da Silva.pdf
```

---

## 4. Decisão da Squad

A Squad aprova a abertura da:

```text
Missão 12.1 — Departamento Pessoal > Documentos > Holerites
```

Decisão técnica:

```text
Holerite deve ser vinculado ao Colaborador, não diretamente ao Usuário.
Usuário vinculado a Colaborador acessa apenas seus próprios holerites.
Visualizar permite ver a tela/lista.
Exportar permite abrir/baixar/exportar o PDF.
```

---

## 5. Escopo aprovado

Entram nesta missão:

- criar hub `Documentos` dentro do Departamento Pessoal, se ainda não existir funcionalmente;
- criar submódulo `Holerites` dentro de Documentos;
- criar model/tabela para holerites vinculados ao colaborador;
- criar tela base de Documentos;
- criar tela base de Holerites;
- criar controle inicial de permissão com as ações Visualizar e Exportar;
- preparar campos para futura integração com Google Drive;
- criar migration;
- criar seed idempotente de módulos/permissões, se necessário.

Não entram nesta missão:

- integração real com Google Drive;
- leitura automática das pastas;
- upload em massa de PDFs;
- OCR/leitura de PDF;
- envio de holerites por e-mail;
- assinatura/recibo de ciência;
- processamento automático dos nomes dos arquivos;
- importação automática dos holerites atuais;
- alteração no módulo Pedido de Refeições.

---

## 6. Regras de permissão

### Estrutura de permissão

Criar/garantir:

```text
Documentos Pessoais
└── Documentos
    └── Holerites
```

Ações principais:

```text
Visualizar
Exportar
```

### Visualizar

Permite acessar a tela/lista de holerites.

Para usuário vinculado a colaborador:

```text
Visualizar → vê apenas holerites do próprio colaborador_id.
```

Para DP/Admin:

```text
Visualizar → acessa a tela de holerites conforme regra administrativa do módulo.
```

### Exportar

Permite abrir/baixar/exportar o PDF.

```text
Exportar → permite download/visualização do arquivo.
```

Usuário sem Exportar pode visualizar a lista, mas não deve baixar/abrir o PDF.

### Sem Visualizar

Usuário sem Visualizar não deve ver o card de Holerites.

Acesso direto por URL deve ser bloqueado.

---

## 7. Regra de vínculo

A estrutura correta é:

```text
Usuário → Colaborador → Holerites
```

O sistema nunca deve vincular holerite diretamente ao usuário.

Quando o usuário logado estiver vinculado a um colaborador, o sistema deve usar:

```text
current_user.colaborador_id
```

para restringir o acesso aos holerites daquele colaborador.

---

## 8. Model sugerido

Criar model conforme o padrão real do projeto, por exemplo:

```python
class HoleriteColaborador(db.Model):
    __tablename__ = "holerites_colaboradores"

    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey("colaboradores.id"), nullable=False)
    competencia = db.Column(db.String(7), nullable=False)
    tipo = db.Column(db.String(80), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    origem_arquivo = db.Column(db.String(50), nullable=True)
    google_drive_file_id = db.Column(db.String(255), nullable=True)
    google_drive_url = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, nullable=False)
    criado_por_usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
```

Adaptar nomes, imports, defaults e relacionamentos conforme padrão real do projeto.

Campos de Google Drive devem ficar apenas preparados, sem integração via API nesta missão.

---

## 9. Migration

Criar migration para a nova tabela.

Comandos esperados localmente:

```bash
flask db migrate -m "cria holerites colaboradores"
flask db upgrade
```

Ou conforme padrão real do projeto.

A migration deve criar somente a estrutura necessária para holerites/documentos desta missão.

---

## 10. Navegação esperada

### Departamento Pessoal

O card **Documentos** deve permanecer dentro de Departamento Pessoal.

```text
Departamento Pessoal
└── Documentos
```

### Hub Documentos

Ao clicar em Documentos, abrir tela/hub:

```text
Departamento Pessoal > Documentos
```

Dentro dela, exibir o card:

```text
Holerites
```

conforme permissão Visualizar.

### Holerites

Ao clicar em Holerites, abrir:

```text
Departamento Pessoal > Documentos > Holerites
```

---

## 11. Tela de Holerites

Criar tela base com listagem preparada.

Colunas sugeridas:

```text
Colaborador
Matrícula
Competência
Tipo
Arquivo
Status
Ações
```

Se não houver registros:

```text
Nenhum holerite cadastrado até o momento.
```

Para colaborador vinculado sem holerites:

```text
Nenhum holerite disponível para o seu usuário.
```

---

## 12. Segurança e LGPD

Não exibir dados sensíveis desnecessários.

Evitar exibir:

```text
CPF
telefone
e-mail pessoal
dados bancários
valores salariais na listagem
```

A listagem deve ser documental, não financeira.

Logs não devem registrar conteúdo do holerite.

---

## 13. Logs

Registrar eventos sem dados sensíveis, se aplicável:

```text
Usuário ID X acessou módulo Holerites.
Usuário ID X exportou holerite ID Y.
```

Não registrar:

```text
CPF
salário
token
conteúdo do PDF
link público sensível
```

---

## 14. Seed de permissões/módulos

Se necessário, criar seed idempotente para garantir:

```text
Documentos Pessoais
Documentos
Holerites
```

e as ações:

```text
Visualizar
Exportar
```

O seed deve:

- não apagar permissões;
- não duplicar módulos;
- não criar usuários;
- não alterar senhas;
- não alterar colaboradores;
- exibir resumo no terminal.

---

## 15. Não alterar

Não alterar:

- login;
- recuperação de senha;
- troca de senha;
- Pedido de Refeições;
- importação CSV de colaboradores;
- LGPD já aplicada aos colaboradores;
- cards/responsividade;
- integração Google Drive;
- upload/download real de arquivos, salvo estrutura mínima protegida;
- regras de permissões existentes fora de Holerites.

---

## 16. Arquivos prováveis

Verificar a estrutura real antes de alterar.

Arquivos prováveis:

```text
app/models.py
app/departamento_pessoal/documentos/__init__.py
app/departamento_pessoal/documentos/routes.py
app/templates/departamento_pessoal/documentos/index.html
app/templates/departamento_pessoal/documentos/holerites.html
app/templates/departamentos/detalhe.html
app/services/permissoes_service.py
app/seed_documentos_holerites_permissoes.py
migrations/versions/
docs/missoes/missao_12_1_documentos_holerites.md
```

---

## 17. Branch e PR

Criar ou utilizar a branch:

```text
missao-12-1-documentos-holerites
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 18. Critérios de aceite

A missão será considerada concluída quando:

1. Estrutura Departamento Pessoal → Documentos → Holerites existir.
2. Controle de permissão Documentos Pessoais → Documentos → Holerites existir ou estiver preparado.
3. Ações Visualizar e Exportar forem consideradas no acesso.
4. Model/tabela de holerites vinculados ao colaborador for criado.
5. Migration for criada.
6. Migration aplicar corretamente localmente.
7. Holerite for vinculado ao colaborador, não ao usuário.
8. Usuário sem Visualizar não ver Holerites.
9. Acesso direto sem Visualizar for bloqueado.
10. Usuário sem Exportar não conseguir baixar/exportar.
11. Usuário vinculado a colaborador só visualizar seus próprios holerites.
12. Administrador conseguir acessar a tela base.
13. Tela sem registros exibir mensagem amigável.
14. Nenhuma integração real com Google Drive for implementada.
15. Nenhum download público inseguro for criado.
16. `/status` continuar 200.
17. Login, permissões e recuperação de senha continuarem funcionando.
18. PR ser aberto antes do merge.

---

## 19. Testes locais

Testar localmente:

1. Rodar migration.
2. Testar `/status`.
3. Login como administrador.
4. Acessar Departamento Pessoal.
5. Acessar Documentos.
6. Acessar Holerites.
7. Confirmar tela base.
8. Testar usuário com Visualizar.
9. Testar usuário sem Visualizar.
10. Testar usuário com Visualizar sem Exportar.
11. Confirmar que Exportar é bloqueado sem permissão.
12. Confirmar que usuário vinculado só vê próprios registros, se houver registros de teste.
13. Confirmar que login continua funcionando.
14. Confirmar que recuperação de senha continua funcionando.
15. Confirmar que Pedido de Refeições não foi impactado.

---

## 20. Deploy e produção

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

Se houver seed de permissões/módulos:

```bash
python -m app.seed_documentos_holerites_permissoes
```

Adaptar ao nome real criado.

---

## 21. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Se `models.py` foi alterado.
4. Migration criada.
5. Nome da migration.
6. Se seed foi criado.
7. Nome do seed e comando de execução.
8. Como foi estruturada a navegação Documentos > Holerites.
9. Como foram aplicadas as permissões Visualizar e Exportar.
10. Como testar localmente.
11. Como aplicar em produção.
12. Pontos de atenção antes do merge/deploy.
