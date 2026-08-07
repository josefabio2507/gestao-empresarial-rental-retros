# Missao 14.1 - MVP 14 Suprimentos: Cadastros Base

## 1. Contexto

Projeto **Gestao Empresarial Rental Retros**, em **Python + Flask + SQLAlchemy + Flask-Migrate**, com PostgreSQL no Render, SQLite local, GitHub/GitHub Desktop e deploy no Render.

Fluxo oficial:

```text
ChatGPT/Squad -> planeja a missao
Codex -> implementa em branch separada
Pull Request -> revisao antes de entrar na main
Fabio -> testa, aprova e faz merge/deploy
```

O **MVP 14 - Modulo Suprimentos** foi aprovado. A Rental Retros **nao trabalha com contratos formais de fornecedores**. O modulo deve controlar o processo de compras por cadastros, requisicao, cotacao, mapa comparativo, aprovacao, ordem de compra, recebimento, estoque e preparacao para integracao futura com Financeiro.

Diretriz importante: apos a conclusao 100% do Modulo Suprimentos, sera iniciado o Modulo Financeiro completo no app. Portanto, nesta missao o Suprimentos deve nascer com dados bem estruturados para futura integracao financeira, mas **nao deve implementar Contas a Pagar, Fluxo de Caixa, parcelas financeiras efetivas, baixas, conciliacao, bancos ou relatorios financeiros completos**.

Observacao sobre o projeto atual: existe uma area `financeiro` no app, mas ela deve ser tratada como estrutura/hub inicial. Esta missao nao deve expandir o Modulo Financeiro.

---

## 2. Objetivo da Missao

Criar a base inicial do modulo:

```text
Suprimentos
```

com hub inicial e cadastros estruturais:

```text
Fornecedores
Categorias
Unidades de Medida
Itens / Materiais / Servicos
Centros de Custo, se ainda nao existir
Vinculo Fornecedor x Item
```

A missao deve preparar o sistema para as proximas etapas do MVP 14 sem construir ainda o fluxo operacional de compras.

---

## 3. Escopo aprovado

Entram nesta missao:

- criar o departamento/modulo `Suprimentos` na navegacao principal;
- criar hub inicial de Suprimentos;
- criar cadastro de Fornecedores;
- criar cadastro de Categorias de Itens;
- criar cadastro de Unidades de Medida;
- criar cadastro de Itens / Materiais / Servicos;
- criar cadastro de Centro de Custo, se ainda nao existir no projeto;
- criar vinculo Fornecedor x Item;
- criar models SQLAlchemy e relacionamentos;
- criar migrations;
- criar rotas, services e templates seguindo o padrao atual do app;
- aplicar permissoes por modulo e acao;
- criar seed idempotente para departamento, modulos e permissoes base;
- criar dados ficticios controlados apenas para ambiente local/desenvolvimento;
- criar testes automatizados para regras principais, permissoes e rotas.
- aplicar mascara e validacao de CNPJ/CPF no cadastro de fornecedores;
- impedir duplicidade de fornecedor por CNPJ/CPF;
- cadastrar textos em letras maiusculas, exceto e-mail;
- preparar consulta de dados cadastrais por CNPJ em fonte publica/configuravel.

Nao entram nesta missao:

- requisicao de compra;
- cotacao com fornecedores;
- mapa comparativo;
- aprovacao por alcada;
- ordem de compra;
- recebimento fisico;
- leitura/importacao de XML de NF-e;
- entrada em estoque;
- contas a pagar;
- fluxo de caixa;
- geracao de parcelas financeiras reais;
- integracao bancaria;
- integracao com fornecedor externo;
- contratos de fornecedores;
- alteracoes no modulo Financeiro completo;
- alteracoes nos modulos Pedido de Refeicoes, Vale Transporte, Holerites, Login, Recuperacao de Senha ou Permissoes fora do necessario para registrar Suprimentos.

---

## 4. Estrutura de navegacao esperada

Criar/garantir:

```text
Inicio
└── Suprimentos
    ├── Fornecedores
    ├── Categorias
    ├── Unidades de Medida
    ├── Itens / Materiais / Servicos
    ├── Centros de Custo
    └── Fornecedor x Item
```

O card **Suprimentos** deve aparecer para administrador e para usuarios com permissao de visualizacao em pelo menos um modulo de Suprimentos.

O hub `/suprimentos/` deve exibir cards apenas para os submodulos liberados ao usuario.

---

## 5. Permissoes

Criar/garantir o departamento:

```text
Suprimentos
```

Criar/garantir os modulos:

```text
Fornecedores
Categorias
Unidades de Medida
Itens
Centros de Custo
Fornecedor x Item
```

Acoes por modulo:

```text
Visualizar
Criar
Editar
Excluir
Exportar
```

Observacoes:

- `Aprovar` deve ficar reservado para missoes futuras de requisicao/cotacao/ordem de compra.
- Administrador deve ter acesso total pelo comportamento atual do sistema.
- Usuario sem `Visualizar` nao deve ver card nem acessar URL direta.
- Usuario com `Criar` ou `Editar` deve automaticamente ter `Visualizar`, respeitando o padrao atual de permissoes.
- `Excluir` deve preferencialmente inativar registros, nao apagar fisicamente, quando houver risco de historico.

---

## 6. Models sugeridos

Adaptar os nomes e tipos conforme o padrao real do projeto.

### Fornecedor

Tabela sugerida: `suprimentos_fornecedores`

Campos:

```text
id
razao_social
nome_fantasia
tipo_pessoa: juridica, fisica
cnpj_cpf
inscricao_estadual
telefone
email
pessoa_contato
endereco
cidade
uf
observacoes
ativo
criado_em
atualizado_em
```

Regras:

- `razao_social` obrigatorio;
- `tipo_pessoa` obrigatorio;
- `cnpj_cpf` opcional no primeiro momento, mas unico quando informado;
- normalizar CNPJ/CPF mantendo apenas numeros;
- nao permitir duplicidade ativa por CNPJ/CPF informado;
- validar CPF e CNPJ pelo digito verificador antes de salvar;
- exibir mascara de CPF ou CNPJ no formulario;
- permitir consulta por CNPJ para preenchimento automatico de razao social, nome fantasia, e-mail, telefone, endereco, cidade e UF;
- deixar a fonte oficial de governo configuravel por variaveis de ambiente, pois a API oficial do Serpro/Receita pode exigir contrato, certificado e token;
- permitir inativacao.

### Categoria de Item

Tabela sugerida: `suprimentos_categorias_itens`

Campos:

```text
id
nome
slug
descricao
ativo
criado_em
atualizado_em
```

Regras:

- `nome` obrigatorio;
- `slug` unico;
- nao duplicar categoria por nome normalizado.

### Unidade de Medida

Tabela sugerida: `suprimentos_unidades_medida`

Campos:

```text
id
nome
sigla
descricao
ativo
criado_em
atualizado_em
```

Regras:

- `nome` obrigatorio;
- `sigla` obrigatoria e unica;
- exemplos: `UN`, `KG`, `L`, `M`, `CX`, `PAR`, `H`.

### Centro de Custo

Criar somente se nao existir entidade equivalente no projeto.

Tabela sugerida: `centros_custo` ou `suprimentos_centros_custo`, conforme melhor aderencia ao padrao do projeto.

Campos:

```text
id
codigo
nome
descricao
ativo
criado_em
atualizado_em
```

Regras:

- `nome` obrigatorio;
- `codigo` opcional, mas unico quando informado;
- deve ser reutilizavel futuramente pelo Modulo Financeiro.

### Item / Material / Servico

Tabela sugerida: `suprimentos_itens`

Campos:

```text
id
codigo_interno
descricao
categoria_id
unidade_medida_id
centro_custo_padrao_id
tipo: material, servico, epi, ferramenta, peca, equipamento, consumo
item_estocavel
ncm
estoque_minimo
observacoes
ativo
criado_em
atualizado_em
```

Regras:

- `descricao` obrigatoria;
- `categoria_id` obrigatoria;
- `unidade_medida_id` obrigatoria;
- `codigo_interno` opcional, mas unico quando informado;
- `tipo` obrigatorio;
- `item_estocavel` booleano;
- `estoque_minimo` deve aceitar nulo e nao pode ser negativo quando informado;
- `ncm` opcional;
- servicos normalmente devem ter `item_estocavel = False`.

### Vinculo Fornecedor x Item

Tabela sugerida: `suprimentos_fornecedor_itens`

Campos:

```text
id
fornecedor_id
item_id
codigo_item_fornecedor
descricao_item_fornecedor
preco_referencia
prazo_entrega_dias
condicao_pagamento
observacoes
fornecedor_preferencial
ativo
criado_em
atualizado_em
```

Regras:

- `fornecedor_id` obrigatorio;
- `item_id` obrigatorio;
- nao permitir duplicidade ativa do mesmo fornecedor para o mesmo item;
- `preco_referencia` opcional e apenas informativo nesta missao;
- `condicao_pagamento` deve ser texto informativo para preparacao futura do Financeiro, sem gerar contas a pagar;
- permitir marcar fornecedor preferencial;
- se houver apenas um fornecedor ativo para o item, pode ser preferencial, mas nao e obrigatorio;
- inativar vinculo em vez de apagar quando ja houver historico futuro.

---

## 7. Telas esperadas

### Hub Suprimentos

Rota sugerida:

```text
/suprimentos/
```

Conteudo:

- titulo `Suprimentos`;
- cards para os cadastros base;
- cards respeitando permissao de visualizacao;
- mensagem amigavel se nenhum modulo estiver liberado.

### Fornecedores

Rotas sugeridas:

```text
/suprimentos/fornecedores/
/suprimentos/fornecedores/novo
/suprimentos/fornecedores/<id>
/suprimentos/fornecedores/<id>/editar
/suprimentos/fornecedores/<id>/status
```

Listagem com filtros por nome, CNPJ/CPF e status.

### Categorias

CRUD simples com nome, descricao e status.

### Unidades de Medida

CRUD simples com nome, sigla, descricao e status.

### Centros de Custo

CRUD simples com codigo, nome, descricao e status.

### Itens

Listagem com filtros por descricao, categoria, tipo, estocavel e status.

Formulario com categoria, unidade de medida, centro de custo padrao, tipo, item estocavel, NCM e estoque minimo.

### Fornecedor x Item

Tela para vincular fornecedores a itens.

Filtros por fornecedor, item, categoria e status.

Nao deve virar cotacao nesta missao.

---

## 8. Dados ficticios locais/desenvolvimento

Criar dados ficticios apenas para ambiente local/desenvolvimento.

Regra obrigatoria:

```text
Nunca rodar seed de dados ficticios automaticamente em producao.
```

Implementacao sugerida:

- criar seed separado, por exemplo `app/seed_suprimentos_dev.py`;
- exigir `FLASK_ENV=development` ou config equivalente;
- opcionalmente exigir variavel explicita `ALLOW_DEV_SEED=1`;
- o seed deve ser idempotente;
- o seed nao deve criar usuarios, alterar senhas ou permissao de usuarios reais.
- os dados ficticios de texto devem seguir a regra de letras maiusculas, exceto e-mail.

Dados ficticios sugeridos:

Fornecedores:

```text
Fornecedor Demo Pecas Ltda
EPI Seguro Demo Ltda
Servicos Hidraulicos Demo ME
```

Categorias:

```text
Pecas
EPI
Ferramentas
Servicos
Consumo
```

Unidades:

```text
UN
KG
L
M
CX
PAR
H
```

Centros de custo:

```text
Administrativo
Operacao
Manutencao
Seguranca do Trabalho
```

Itens:

```text
Filtro de oleo demo
Luva de seguranca demo
Disco de corte demo
Servico de manutencao hidraulica demo
Detergente desengraxante demo
```

Vinculos:

```text
Fornecedor Demo Pecas Ltda -> Filtro de oleo demo
EPI Seguro Demo Ltda -> Luva de seguranca demo
Servicos Hidraulicos Demo ME -> Servico de manutencao hidraulica demo
```

---

## 9. Migrations

Criar migration para as tabelas da base de Suprimentos.

Comandos esperados localmente:

```bash
flask db migrate -m "cria cadastros base suprimentos"
flask db upgrade
```

Ou usar migration manual se o autogenerate nao capturar corretamente constraints, indices e check constraints.

A migration deve:

- criar somente estruturas da Missao 14.1;
- nao alterar tabelas financeiras existentes;
- nao apagar ou recriar tabelas existentes;
- incluir indices e constraints necessarios para unicidade e performance basica.

---

## 10. Arquivos provaveis

Verificar a estrutura real antes de alterar.

Arquivos provaveis:

```text
app/models.py
app/__init__.py
app/suprimentos/__init__.py
app/suprimentos/routes.py
app/suprimentos/fornecedores/__init__.py
app/suprimentos/fornecedores/routes.py
app/suprimentos/categorias/__init__.py
app/suprimentos/categorias/routes.py
app/suprimentos/unidades_medida/__init__.py
app/suprimentos/unidades_medida/routes.py
app/suprimentos/itens/__init__.py
app/suprimentos/itens/routes.py
app/suprimentos/centros_custo/__init__.py
app/suprimentos/centros_custo/routes.py
app/suprimentos/fornecedor_itens/__init__.py
app/suprimentos/fornecedor_itens/routes.py
app/services/suprimentos_service.py
app/services/permissoes_service.py
app/templates/suprimentos/index.html
app/templates/suprimentos/fornecedores/*.html
app/templates/suprimentos/categorias/*.html
app/templates/suprimentos/unidades_medida/*.html
app/templates/suprimentos/itens/*.html
app/templates/suprimentos/centros_custo/*.html
app/templates/suprimentos/fornecedor_itens/*.html
app/templates/departamentos/detalhe.html
app/seed_modulos_base_producao.py
app/seed_suprimentos_permissoes.py
app/seed_suprimentos_dev.py
migrations/versions/
tests/test_suprimentos_*.py
docs/missoes/missao_14_1_cadastros_base_suprimentos.md
```

---

## 11. Nao alterar

Nao alterar:

- login;
- recuperacao de senha;
- troca de senha;
- Pedido de Refeicoes;
- Vale Transporte;
- Holerites;
- importacao CSV de colaboradores;
- regras LGPD existentes;
- Google Drive;
- Financeiro, exceto se for apenas para garantir que nada foi acoplado;
- seeds de usuarios reais;
- senhas;
- dados de producao;
- migrations antigas ja aplicadas.

---

## 12. Testes automatizados

Criar testes para:

1. Administrador acessa hub Suprimentos.
2. Usuario sem permissao nao acessa hub nem rotas diretas.
3. Usuario com `Visualizar` ve apenas os cards liberados.
4. Usuario sem `Criar` nao acessa rotas de criacao.
5. Criacao, edicao e inativacao de fornecedor.
6. Bloqueio de CNPJ/CPF duplicado quando informado.
7. Criacao, edicao e inativacao de categoria.
8. Bloqueio de categoria duplicada.
9. Criacao, edicao e inativacao de unidade de medida.
10. Bloqueio de sigla duplicada.
11. Criacao, edicao e inativacao de centro de custo.
12. Criacao, edicao e inativacao de item.
13. Validacao de estoque minimo nao negativo.
14. Servico nao exige estoque.
15. Criacao, edicao e inativacao de vinculo fornecedor x item.
16. Bloqueio de vinculo ativo duplicado para o mesmo fornecedor e item.
17. Seed de modulos/permissoes e idempotente.
18. Seed dev nao roda em modo de producao.
19. `/status` continua respondendo 200 se existir teste padrao para isso no projeto.

Comando local sugerido:

```bash
python -m unittest
```

Ou o comando de teste ja adotado pelo projeto.

---

## 13. Criterios de aceite

A missao sera considerada concluida quando:

1. Departamento/modulo Suprimentos existir na base.
2. Hub `/suprimentos/` existir e respeitar permissoes.
3. Cadastro de fornecedores funcionar com criar, listar, editar, detalhes e inativar/reativar.
4. Cadastro de categorias funcionar.
5. Cadastro de unidades de medida funcionar.
6. Cadastro de itens funcionar.
7. Cadastro de centros de custo existir ou reutilizar entidade equivalente existente.
8. Vinculo fornecedor x item funcionar.
9. Nenhuma regra de contrato de fornecedor for criada.
10. Nenhuma rotina do Financeiro completo for criada.
11. Campos preparatorios para informacoes comerciais/financeiras ficarem apenas no Suprimentos.
12. Dados ficticios existirem somente em seed local/desenvolvimento.
13. Seed de dados ficticios nao rodar automaticamente em producao.
14. Migrations aplicarem corretamente localmente.
15. Testes automatizados cobrirem as regras principais.
16. Login e permissoes existentes continuarem funcionando.
17. Modulos existentes nao sofrerem regressao visual ou de acesso.
18. PR ser aberto antes do merge.

---

## 14. Branch e PR

Criar ou utilizar a branch:

```text
missao-14-1-cadastros-base-suprimentos
```

Ao finalizar, abrir Pull Request para:

```text
main
```

---

## 15. Deploy e producao

Apos PR aprovado, merge e deploy no Render:

1. Aguardar deploy.
2. Abrir Render Shell.
3. Executar migration:

```bash
flask db upgrade
```

Se necessario:

```bash
python -m flask db upgrade
```

Se necessario:

```bash
export FLASK_APP=run.py
python -m flask db upgrade
```

Se houver seed de modulos/permissoes:

```bash
python -m app.seed_suprimentos_permissoes
```

Nao executar seed de dados ficticios em producao.

---

## 16. Entrega esperada do Codex

Ao finalizar, informar:

1. Arquivos criados.
2. Arquivos alterados.
3. Models criados/alterados.
4. Migration criada e nome do arquivo.
5. Seeds criados e comandos de execucao.
6. Como foi estruturada a navegacao de Suprimentos.
7. Como foram aplicadas as permissoes.
8. Como os dados ficticios ficaram restritos ao ambiente local/desenvolvimento.
9. Como testar localmente.
10. Como aplicar em producao.
11. Testes executados e resultado.
12. Pontos de atencao antes do merge/deploy.

---

## 17. Proxima missao depois desta

Somente depois da Missao 14.1 estar concluida e aprovada, iniciar:

```text
Missao 14.2 - Requisicao de Compra
```

A Missao 14.2 deve usar os cadastros base criados aqui, sem recriar fornecedores, itens, categorias, unidades ou centros de custo.
