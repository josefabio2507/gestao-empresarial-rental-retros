# Missão 12.2 — Sincronização de Holerites com Google Drive

## 1. Contexto

Projeto **Gestão Empresarial Rental Retros**, em produção parcial no Render, com fluxo oficial:

```text
ChatGPT/Squad → planeja a missão
Codex → implementa em branch separada
Pull Request → revisão antes de entrar na main
Fábio → testa, aprova e faz merge/deploy
```

A **Missão 12.1 — Departamento Pessoal > Documentos > Holerites** foi concluída e validada em produção.

Ela criou:

```text
Departamento Pessoal
└── Documentos
    └── Holerites
```

Também criou:

```text
HoleriteColaborador / holerites_colaboradores
```

e permissões relacionadas a Holerites.

A decisão para a Missão 12.2 foi ajustada: em vez de iniciar com cadastro manual individual, a prioridade será a **sincronização automática com Google Drive**, porque a empresa possui mais de 120 colaboradores e os holerites já estão organizados em pastas individuais no Drive.

---

## 2. Objetivo da missão

Criar uma rotina de sincronização de holerites com o Google Drive, lendo a pasta principal de holerites, identificando as pastas individuais dos colaboradores, interpretando os nomes dos arquivos PDF e criando automaticamente registros na tabela:

```text
holerites_colaboradores
```

A rotina deve respeitar a estrutura atual:

```text
Holerites
├── 000123 - João da Silva
│   ├── 000123 - Holerite Mensal - 01.2026 - João da Silva.pdf
│   ├── 000123 - Adiantamento Salarial - 01.2026 - João da Silva.pdf
│   └── 000123 - Holerite Mensal - 02.2026 - João da Silva.pdf
│
├── 000124 - Maria Souza
│   ├── 000124 - Holerite Mensal - 01.2026 - Maria Souza.pdf
│   └── 000124 - Holerite Mensal - 02.2026 - Maria Souza.pdf
```

Padrão oficial do arquivo:

```text
MATRICULA - TIPO - COMPETENCIA - NOME.pdf
```

Exemplo:

```text
000123 - Holerite Mensal - 01.2026 - João da Silva.pdf
000123 - Adiantamento Salarial - 01.2026 - João da Silva.pdf
```

---

## 3. Fluxo aprovado

A sincronização deve seguir este fluxo:

```text
1. Acessar a pasta principal Holerites no Google Drive.
2. Ler cada pasta individual.
3. Identificar a matrícula pelo nome da pasta.
4. Procurar o colaborador no banco pela matrícula.
5. Ler os arquivos PDF dentro da pasta.
6. Interpretar o nome do arquivo:
   MATRÍCULA - TIPO - COMPETÊNCIA - NOME.pdf
7. Criar automaticamente o registro na tabela holerites_colaboradores.
8. Salvar:
   - colaborador_id
   - competência
   - tipo
   - nome do arquivo
   - google_drive_file_id
   - google_drive_url
   - ativo
9. Ignorar arquivos já importados.
10. Gerar relatório/resumo de importação.
```

---

## 4. Análise da Squad

### 4.1 Agente de Desenvolvimento / Arquitetura

A missão passa a ser uma integração controlada com Google Drive.

A estrutura correta permanece:

```text
Usuário → Colaborador → Holerites
```

Os holerites devem continuar vinculados ao `colaborador_id`, não ao usuário.

A sincronização deve localizar o colaborador pela matrícula, pois a estrutura das pastas e dos arquivos já utiliza matrícula como chave principal.

A rotina deve ser idempotente:

```text
Executar uma vez → importa arquivos novos.
Executar novamente → não duplica arquivos já importados.
```

A recomendação é considerar um holerite já importado quando houver correspondência por:

```text
colaborador_id
competencia
tipo
google_drive_file_id
```

ou, se o `google_drive_file_id` não estiver disponível em algum cenário, usar uma combinação segura com:

```text
colaborador_id
competencia
tipo
nome_arquivo
```

O ideal é usar `google_drive_file_id` como chave mais confiável.

Aprovado pelo Agente de Desenvolvimento / Arquitetura.

---

### 4.2 Agente de Design / Experiência do Usuário

A tela de Holerites deve ganhar uma ação administrativa:

```text
Sincronizar Google Drive
```

Ao executar, o sistema deve apresentar um resumo claro:

```text
Arquivos encontrados
Arquivos importados
Arquivos já existentes
Pastas ignoradas
Colaboradores não encontrados
Arquivos fora do padrão
Erros
```

A tela deve evitar linguagem técnica excessiva.

Exemplo de mensagem:

```text
Sincronização concluída.
120 arquivos encontrados.
118 importados.
2 arquivos já estavam cadastrados.
0 erros.
```

Se houver pendências:

```text
Foram encontrados arquivos que precisam de conferência.
```

Aprovado pelo Agente de Design / Experiência do Usuário.

---

### 4.3 Agente de Código / Programação

A implementação deve ser feita em branch separada:

```text
missao-12-2-sincronizacao-holerites-drive
```

Arquivos prováveis:

```text
app/departamento_pessoal/documentos/routes.py
app/templates/departamento_pessoal/documentos/holerites.html
app/services/google_drive_service.py
app/services/holerites_drive_service.py
app/services/logs_service.py
config.py
requirements.txt
docs/missoes/missao_12_2_sincronizacao_holerites_drive.md
```

Se forem necessárias bibliotecas Google, o Codex deve adicioná-las ao `requirements.txt` somente se ainda não existirem.

A implementação deve verificar a estrutura real do projeto antes de criar novos services.

Variáveis de ambiente prováveis:

```text
GOOGLE_DRIVE_HOLERITES_FOLDER_ID
GOOGLE_SERVICE_ACCOUNT_JSON
```

ou alternativa segura conforme padrão técnico definido pelo Codex.

Não colocar credenciais reais no código.

Aprovado pelo Agente de Código / Programação.

---

### 4.4 Agente de Revisão / Qualidade

Essa missão envolve documentos pessoais/trabalhistas e integração externa.

Cuidados obrigatórios:

```text
Não expor CPF.
Não expor salário.
Não registrar conteúdo do PDF em logs.
Não criar link público inseguro.
Não duplicar holerites.
Não importar arquivo fora do padrão como se fosse válido.
Não permitir que colaborador acesse holerite de outro colaborador.
```

Testes obrigatórios:

```text
1. Sincronizar pasta com colaborador existente.
2. Sincronizar pasta de colaborador inexistente.
3. Sincronizar arquivo com nome correto.
4. Sincronizar arquivo fora do padrão.
5. Rodar sincronização duas vezes e confirmar que não duplica.
6. Confirmar que os registros aparecem na tela de Holerites.
7. Confirmar que usuário vinculado ao colaborador vê apenas seus próprios holerites.
8. Confirmar que Exportar exige permissão.
9. Confirmar que /status continua 200.
10. Confirmar que Pedido de Refeições não foi impactado.
```

Aprovado pelo Agente de Revisão / Qualidade.

---

## 5. Decisão consolidada da Squad

A Squad aprova a abertura da:

```text
Missão 12.2 — Sincronização de Holerites com Google Drive
```

Regra consolidada:

```text
O sistema deve ler a estrutura atual de pastas no Google Drive, identificar colaboradores por matrícula, importar automaticamente os holerites em PDF e registrar os documentos na tabela holerites_colaboradores sem duplicidade.
```

---

## 6. Escopo aprovado

Entram nesta missão:

- criar rotina de acesso ao Google Drive;
- configurar leitura da pasta principal de Holerites;
- ler pastas individuais dos colaboradores;
- identificar matrícula pelo nome da pasta;
- buscar colaborador no banco pela matrícula;
- ler PDFs dentro da pasta;
- interpretar nome do arquivo no padrão:
  `MATRICULA - TIPO - COMPETENCIA - NOME.pdf`;
- criar registros na tabela `holerites_colaboradores`;
- salvar `colaborador_id`, competência, tipo, nome do arquivo, `google_drive_file_id`, `google_drive_url` e ativo;
- ignorar arquivos já importados;
- gerar resumo da sincronização;
- adicionar botão/ação administrativa para sincronizar;
- registrar logs operacionais sem dados sensíveis;
- preservar permissões Visualizar e Exportar.

Não entram nesta missão:

- upload manual de arquivos;
- OCR/leitura do conteúdo do PDF;
- envio por e-mail;
- assinatura/recibo de ciência;
- edição avançada de holerites;
- exclusão física de arquivos no Drive;
- alteração no módulo Pedido de Refeições;
- alteração na estrutura de colaboradores;
- armazenamento de credenciais reais no repositório.

---

## 7. Regras de identificação

### 7.1 Pasta do colaborador

Formato esperado:

```text
MATRICULA - Nome do Colaborador
```

Exemplo:

```text
000123 - João da Silva
```

A matrícula deve ser extraída do início do nome da pasta.

### 7.2 Arquivo de holerite

Formato esperado:

```text
MATRICULA - TIPO - COMPETENCIA - NOME.pdf
```

Exemplo:

```text
000123 - Holerite Mensal - 01.2026 - João da Silva.pdf
```

### 7.3 Competência

Formato esperado:

```text
MM.AAAA
```

Exemplo:

```text
01.2026
```

### 7.4 Tipo

Deve ser extraído do segundo bloco do nome do arquivo.

Exemplo:

```text
Holerite Mensal
Adiantamento Salarial
13º Salário
Férias
Rescisão
Outro
```

A rotina deve aceitar os tipos encontrados no nome do arquivo, desde que o padrão geral seja válido.

---

## 8. Regras de importação

### 8.1 Colaborador encontrado

Se a matrícula da pasta existir na base de colaboradores:

```text
Criar registros para os PDFs válidos ainda não importados.
```

### 8.2 Colaborador não encontrado

Se a matrícula da pasta não existir:

```text
Não importar os arquivos.
Adicionar ao resumo como colaborador não encontrado.
```

### 8.3 Arquivo fora do padrão

Se o arquivo não seguir o padrão:

```text
Não importar.
Adicionar ao resumo como arquivo fora do padrão.
```

### 8.4 Arquivo já importado

Se o arquivo já estiver cadastrado:

```text
Ignorar.
Adicionar ao resumo como já existente.
```

### 8.5 Arquivo não PDF

Ignorar arquivos que não sejam PDF.

---

## 9. Regras de segurança

Não registrar em logs:

```text
CPF
salário
conteúdo do PDF
link público sensível
credenciais
token
```

Pode registrar:

```text
Usuário ID X executou sincronização de holerites.
Arquivo ID Y importado para colaborador ID Z.
Quantidade de arquivos importados.
Quantidade de arquivos ignorados.
```

---

## 10. Permissões

A ação de sincronizar deve ser restrita a usuário autorizado.

Regra recomendada:

```text
Apenas administrador ou usuário com permissão adequada em Holerites pode executar a sincronização.
```

Se o sistema só tiver Visualizar/Exportar nesta etapa, o Codex deve usar a regra mais segura disponível, preferencialmente administrador.

Se entender necessário, pode preparar uma ação futura `Criar` ou `Importar`, mas não deve alterar amplamente a estrutura de permissões sem justificar.

---

## 11. Configuração do Google Drive

O Codex deve implementar de forma segura, usando variáveis de ambiente.

Variáveis prováveis:

```text
GOOGLE_DRIVE_HOLERITES_FOLDER_ID
GOOGLE_SERVICE_ACCOUNT_JSON
```

ou nomes equivalentes claros.

Não commitar credenciais reais.

A documentação de configuração deve orientar onde preencher essas variáveis no Render.

---

## 12. Tela de Holerites

Na tela:

```text
Departamento Pessoal → Documentos → Holerites
```

deve haver uma ação administrativa:

```text
Sincronizar Google Drive
```

Após executar, exibir resumo:

```text
Sincronização concluída.
Arquivos encontrados: X
Importados: Y
Já existentes: Z
Colaboradores não encontrados: W
Arquivos fora do padrão: K
Erros: N
```

A tela de listagem deve exibir os holerites importados.

---

## 13. Exportação / abertura do arquivo

A exportação deve continuar protegida pela permissão Exportar.

A rota de exportação deve validar:

```text
login
permissão Exportar
acesso ao holerite
vínculo colaborador, quando aplicável
```

Se a exportação redirecionar para Google Drive, deve fazê-lo somente após validar permissão no sistema.

---

## 14. Não alterar

Não alterar:

- Pedido de Refeições;
- recuperação de senha;
- login;
- usuários;
- vínculo usuário-colaborador;
- colaboradores, salvo consulta por matrícula;
- permissões fora de Holerites;
- Google Drive real removendo/alterando arquivos;
- upload manual;
- OCR;
- dados salariais;
- conteúdo do PDF.

---

## 15. Branch e PR

Criar ou utilizar a branch:

```text
missao-12-2-sincronizacao-holerites-drive
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 16. Critérios de aceite

A missão será considerada concluída quando:

1. Existir ação/botão de sincronização com Google Drive.
2. A rotina acessar a pasta principal configurada.
3. A rotina ler pastas individuais dos colaboradores.
4. A matrícula for identificada pelo nome da pasta.
5. O colaborador for localizado pela matrícula.
6. Arquivos PDF forem lidos dentro da pasta.
7. O nome do arquivo for interpretado no padrão correto.
8. Registros forem criados em `holerites_colaboradores`.
9. Arquivos já importados não forem duplicados.
10. Arquivos fora do padrão forem ignorados e informados no resumo.
11. Colaboradores não encontrados forem informados no resumo.
12. Registros importados aparecerem na listagem de Holerites.
13. Usuário vinculado a colaborador continuar vendo apenas próprios holerites.
14. Exportar continuar protegido por permissão Exportar.
15. Credenciais não forem gravadas no código.
16. /status continuar 200.
17. Login e permissões continuarem funcionando.
18. Pedido de Refeições não ser impactado.
19. PR ser aberto antes do merge.

---

## 17. Testes locais

Testar localmente com uma pasta de teste no Drive, preferencialmente com poucos arquivos:

```text
Holerites Teste
├── 000123 - João da Silva
│   ├── 000123 - Holerite Mensal - 01.2026 - João da Silva.pdf
│   └── arquivo_fora_padrao.pdf
├── 999999 - Colaborador Inexistente
│   └── 999999 - Holerite Mensal - 01.2026 - Fulano.pdf
```

Testes:

1. Configurar variáveis locais.
2. Executar sincronização.
3. Confirmar importação do arquivo válido.
4. Confirmar rejeição do arquivo fora do padrão.
5. Confirmar colaborador inexistente no resumo.
6. Executar sincronização novamente.
7. Confirmar que não duplica.
8. Confirmar listagem.
9. Confirmar exportação com permissão.
10. Confirmar bloqueio sem permissão.
11. Confirmar /status 200.

---

## 18. Deploy e produção

Após PR aprovado, merge e deploy no Render:

1. Aguardar deploy automático.
2. Configurar variáveis de ambiente no Render.
3. Executar migration apenas se houver migration criada e justificada.
4. Executar seed apenas se houver seed criado.
5. Testar com pasta controlada ou subconjunto de arquivos antes de sincronizar tudo.
6. Validar resumo da sincronização.
7. Validar listagem e exportação.

---

## 19. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Se houve alteração em `models.py`.
4. Se houve migration.
5. Se houve seed.
6. Quais variáveis de ambiente são necessárias.
7. Como configurar localmente.
8. Como configurar no Render.
9. Como a sincronização identifica colaborador.
10. Como evita duplicidade.
11. Como trata arquivos fora do padrão.
12. Como trata colaboradores não encontrados.
13. Como a exportação fica protegida.
14. Testes executados.
15. Link do Pull Request.
