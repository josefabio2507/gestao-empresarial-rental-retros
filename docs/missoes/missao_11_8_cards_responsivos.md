# Missão 11.8 — Responsividade e Padronização dos Cards

## 1. Contexto

Estamos no projeto **Gestão Empresarial Rental Retros**, desenvolvido em **Python + Flask + SQLAlchemy + Flask-Migrate**, com banco **PostgreSQL no Render**, SQLite local, versionamento via **GitHub/GitHub Desktop** e deploy no **Render**.

O sistema já possui uma base visual aplicada nas missões anteriores:

- Missão 11.6.1 — Base Visual Global e Identidade Rental Retros
- Missão 11.6.2 — Refinamento Visual por Módulo
- Ajustes posteriores de logo nos cards de cabeçalho

A questão do logo nos cards de cabeçalho já foi resolvida.

Agora o foco é exclusivamente corrigir e padronizar o comportamento dos **cards** do sistema.

---

## 2. Objetivo da missão

Padronizar os cards do sistema para que:

1. Cards de cabeçalho fiquem estáticos, sem movimento vertical.
2. Cards de módulos e submódulos sejam responsivos.
3. No mobile, os cards fiquem em lista vertical.
4. No desktop/tela horizontal, os cards fiquem organizados em grade horizontal.
5. Somente cards clicáveis tenham hover visual.
6. Não haja alteração em regras de negócio.

---

## 3. Regra visual principal

Separar claramente os cards em categorias:

### 3.1 Card de cabeçalho / institucional

São os cards superiores das páginas, normalmente contendo:

- título da página;
- subtítulo;
- logo;
- botão voltar, quando existir;
- informações institucionais.

Exemplos:

- Tela Inicial
- Administração
- Departamento Pessoal
- Pedidos de Refeição
- Colaboradores
- Permissões
- Auditoria / Logs

Esses cards devem ser totalmente estáticos.

Não devem ter:

- `transform: translateY(...)`;
- movimento vertical;
- efeito de “subir/descer”;
- comportamento de botão;
- cursor de link, salvo se houver botão interno.

### 3.2 Card de módulo / submódulo

São cards usados para navegação entre áreas do sistema.

Exemplos:

- Departamentos na tela inicial;
- módulos dentro de um departamento;
- submódulos dentro do hub de Pedidos de Refeição;
- atalhos internos.

Esses cards devem ser responsivos:

- mobile: lista vertical, 1 card por linha;
- tablet: 2 cards por linha;
- desktop: 3 ou 4 cards por linha, conforme espaço disponível.

Podem ter hover discreto quando forem clicáveis.

### 3.3 Card de funcionalidade em construção

São cards que representam módulos ainda não implementados.

Devem seguir o mesmo padrão visual dos cards de módulo, mas deixando claro o status:

- “Funcionalidade em construção”
- “Em breve”
- ou badge equivalente já usado no sistema.

Não devem parecer uma funcionalidade plenamente ativa se estiverem em construção.

---

## 4. Comportamento responsivo esperado

Aplicar padrão responsivo nos grids/listas de cards.

### Mobile / telas estreitas

Até aproximadamente 767px:

- 1 card por linha;
- lista vertical;
- espaçamento confortável;
- área clicável adequada para toque;
- texto sem quebrar de forma inadequada.

### Tablet

A partir de aproximadamente 768px:

- 2 cards por linha;
- espaçamento equilibrado;
- cards com altura visual consistente.

### Desktop / telas largas

A partir de aproximadamente 1200px:

- 3 ou 4 cards por linha;
- aproveitar melhor a largura da tela;
- manter boa leitura.

Exemplo conceitual:

```css
.modules-grid,
.module-grid,
.cards-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 18px;
}

@media (min-width: 768px) {
    .modules-grid,
    .module-grid,
    .cards-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (min-width: 1200px) {
    .modules-grid,
    .module-grid,
    .cards-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }
}
```

Adaptar aos nomes reais das classes existentes no projeto.

---

## 5. Cards de cabeçalho não devem se mover

Garantir que classes de cabeçalho fiquem estáticas.

Verificar classes existentes, como:

- `.page-header`
- `.page-header-card`
- `.hero-card`
- `.header-card`
- `.department-header`
- equivalentes reais do projeto

Adicionar regra de proteção, se necessário:

```css
.page-header:hover,
.page-header-card:hover,
.hero-card:hover,
.header-card:hover,
.department-header:hover {
    transform: none;
}
```

Preferência técnica:

- remover `transform` de classes genéricas como `.card:hover`;
- aplicar hover com movimento apenas em cards clicáveis de navegação.

Evitar regras genéricas como:

```css
.card:hover {
    transform: translateY(...);
}
```

Se houver essa regra, trocar por algo mais específico, por exemplo:

```css
.module-card:hover,
.department-card:hover,
.clickable-card:hover {
    transform: translateY(-3px);
}
```

---

## 6. Cards de navegação

Padronizar cards clicáveis com:

- título claro;
- descrição curta;
- badge/status quando existir;
- ação visual clara, como “Acessar módulo”;
- hover discreto apenas no desktop;
- responsividade adequada.

Sugestão de comportamento:

```css
.module-card,
.department-card,
.clickable-card {
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

@media (hover: hover) and (pointer: fine) {
    .module-card:hover,
    .department-card:hover,
    .clickable-card:hover {
        transform: translateY(-3px);
    }
}
```

No mobile, evitar hover exagerado.

---

## 7. Telas onde aplicar

Aplicar a padronização especialmente em:

- Tela Inicial
- Administração
- Departamento Pessoal
- Hub de Pedidos de Refeição
- Colaboradores, se houver cards
- Permissões, se houver cards
- Auditoria / Logs, se houver cards
- demais telas internas que usem cards de navegação

---

## 8. Preservar estrutura atual do Departamento Pessoal

O Departamento Pessoal foi restaurado corretamente.

Preservar os módulos principais atuais, como:

- Colaboradores
- Admissão
- Folha de Pagamento
- Ponto
- Férias
- Documentos
- Pedidos de Refeição

Não reintroduzir como cards diretos do Departamento Pessoal:

- Restaurantes
- Cardápio
- Relatórios de Refeições
- Pedido de Refeições - Restaurantes
- Pedido de Refeições - Cardápio
- Pedido de Refeições - Pedidos
- Pedido de Refeições - Relatórios

Esses acessos pertencem ao hub interno de Pedidos de Refeição.

---

## 9. Preservar hub interno de Pedidos de Refeição

Dentro do hub:

```text
/departamento-pessoal/pedido-refeicoes/
```

Preservar os submódulos internos:

- Restaurantes
- Cardápio
- Pedidos de Refeição
- Relatórios de Refeições

Esses cards também devem seguir a nova responsividade:

- mobile: lista vertical;
- desktop: grade horizontal.

Preservar as permissões individuais por submódulo:

- Restaurantes → `pedido-refeicoes-restaurantes`
- Cardápio → `pedido-refeicoes-cardapio`
- Pedidos de Refeição → `pedido-refeicoes-pedidos`
- Relatórios de Refeições → `pedido-refeicoes-relatorios`

---

## 10. Não alterar

Não alterar:

- `models.py`
- migrations
- rotas Python
- services
- permissões
- regras de negócio
- LGPD
- logs
- relatórios
- pedidos de refeição
- filtros
- banco de dados

Não criar migration.

Esta missão deve ser visual/responsiva, preferencialmente via CSS e pequenos ajustes de template.

---

## 11. Arquivos prováveis

Verificar a estrutura real antes de alterar.

Arquivos prováveis:

- `app/static/css/app.css`
- `app/static/css/base.css`
- `app/templates/inicio.html`
- `app/templates/admin/index.html`
- `app/templates/departamentos/detalhe.html`
- `app/templates/departamento_pessoal/pedido_refeicoes/index.html`

Evitar alteração em Python. Só alterar template/CSS se possível.

---

## 12. Critérios de aceite

A missão será considerada concluída quando:

1. Cards de cabeçalho não se moverem no hover.
2. Cards de cabeçalho permanecerem estáticos em todas as telas principais.
3. Cards de módulos ficarem em lista vertical no mobile.
4. Cards de submódulos ficarem em lista vertical no mobile.
5. Cards de módulos ficarem em grade horizontal no desktop.
6. Cards de submódulos ficarem em grade horizontal no desktop.
7. Tela Inicial respeitar o padrão responsivo.
8. Tela Administração respeitar o padrão responsivo.
9. Departamento Pessoal respeitar o padrão responsivo.
10. Hub Pedidos de Refeição respeitar o padrão responsivo.
11. Cards clicáveis continuarem visualmente identificáveis.
12. Cards em construção ficarem padronizados.
13. Departamento Pessoal não voltar a exibir Restaurantes/Cardápio/Relatórios como cards diretos.
14. Hub de Pedidos de Refeição continuar exibindo seus submódulos conforme permissão.
15. Mobile continuar funcionando bem.
16. `/status` continuar respondendo 200.
17. `models.py` não ser alterado.
18. Nenhuma migration ser criada.
19. Nenhuma regra de negócio ser alterada.

---

## 13. Testes manuais

Testar localmente:

1. Acessar a Tela Inicial.
2. Confirmar que o card de cabeçalho não se move.
3. Reduzir largura da tela e confirmar cards em lista vertical.
4. Ampliar para desktop e confirmar cards em grade horizontal.
5. Acessar Administração.
6. Validar o mesmo comportamento.
7. Acessar Departamento Pessoal.
8. Confirmar que os módulos principais aparecem corretamente.
9. Confirmar que Restaurantes/Cardápio/Relatórios não aparecem diretamente no Departamento Pessoal.
10. Acessar Pedidos de Refeição.
11. Confirmar que o hub interno mostra Restaurantes, Cardápio, Pedidos e Relatórios conforme permissão.
12. Confirmar que os cards do hub também são responsivos.
13. Validar em modo mobile pelo navegador.
14. Testar `/status`.

---

## 14. Entrega esperada

Ao finalizar, informar:

1. Arquivos alterados.
2. Classes CSS criadas ou ajustadas.
3. Quais cards de cabeçalho foram protegidos contra movimento.
4. Quais telas passaram a usar grid responsivo.
5. Como ficou o comportamento mobile.
6. Como ficou o comportamento desktop.
7. Se houve alteração em `models.py`.
8. Se houve migration.
9. Como testar localmente.
