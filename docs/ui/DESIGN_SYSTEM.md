# Rental Retros Design System

**Missão:** 18.1 — Design System  
**Status:** definido para implementação progressiva a partir da Missão 18.2  
**Escopo deste documento:** regras de interface. Este arquivo não altera a aplicação, suas regras de negócio, rotas, permissões, banco de dados ou integrações.

## 1. Propósito e princípios

O Design System orienta a modernização visual do Sistema Rental Retros com uma linguagem única, limpa e operacional. Ele deve reduzir duplicação e poluição visual sem alterar o comportamento das telas existentes.

Princípios:

1. **Clareza operacional:** o conteúdo, o status e a ação principal devem ser reconhecíveis rapidamente.
2. **Consistência:** um mesmo tipo de elemento deve manter aparência e comportamento visual em qualquer módulo.
3. **Densidade equilibrada:** tabelas podem ser densas, mas devem conservar hierarquia, espaçamento e ações legíveis.
4. **Ação por prioridade:** uma ação primária por contexto; ações secundárias discretas; ações destrutivas sempre explícitas.
5. **Preservação funcional:** nomes de campos, atributos `data-*`, IDs, formulários, rotas, permissões e JavaScript existente não fazem parte da modernização visual e devem ser preservados.
6. **Responsividade planejada:** layouts devem se adaptar sem ocultar dados ou impedir operações críticas.
7. **Reuso antes de exceção:** preferir componente global; estilo local somente quando houver necessidade documentada.

## 2. Referências visuais aprovadas

A direção visual aprovada para a Missão 18 utiliza:

- azul-marinho institucional, azul de ação, amarelo Rental, branco e neutros;
- sidebar fixa/retrátil, topbar compacta e cabeçalho de página;
- cards discretos, com bordas suaves e sombra contida;
- filtros organizados em painel, tabelas com cabeçalho legível e ações compactas;
- badges de status e menus de ações em substituição à repetição de botões textuais;
- composição limpa para as telas de Colaboradores, Ficha do Colaborador, Pedido de Refeições e Títulos a Pagar.

As imagens que originaram a direção visual estão versionadas nesta branch em:

```text
docs/ui/references/
  01-colaboradores.png
  02-ficha-colaborador.png
  03-pedido-refeicoes.png
  04-titulos-pagar.png
```

Elas serão referências de hierarquia, composição, espaçamento e densidade de informação — não especificações para reprodução pixel a pixel.

## 3. Tokens visuais

Os valores abaixo consolidam a paleta já presente em `app/static/css/base.css`. A implementação da Missão 18.2 deve usar propriedades CSS reutilizáveis; não deve espalhar valores hexadecimais novos em templates.

### 3.1 Cores

| Token | Valor | Uso |
|---|---:|---|
| `--rr-navy` | `#071A2F` | sidebar, cabeçalhos fortes, texto institucional. |
| `--rr-blue` | `#0B3F75` | ação principal, aba ativa, foco e links de destaque. |
| `--rr-blue-action` | `#005BBB` | compatibilidade temporária com o botão primário existente; consolidar posteriormente em um único azul de ação. |
| `--rr-gold` | `#D7A322` | destaque institucional, indicadores e ênfase não destrutiva. |
| `--rr-gold-soft` | `#FFF4CF` | fundos sutis de atenção/destaque. |
| `--rr-bg` | `#EEF3F8` | fundo de aplicação. |
| `--rr-surface` | `#FFFFFF` | cards, painéis, tabelas e campos. |
| `--rr-text` | `#122033` | texto principal. |
| `--rr-muted` | `#64748B` | texto secundário, ajuda e metadados. |
| `--rr-border` | `#DBE3EC` | bordas sutis e divisores. |
| `--rr-success` | `#16834A` | sucesso, concluído, ativo. |
| `--rr-warning` | `#92400E` | alerta e pendência. |
| `--rr-danger` | `#B42318` | falha, exclusão, cancelamento e bloqueio. |
| `--rr-info` | `#1E40AF` | informação e estado neutro orientativo. |

### 3.2 Tipografia

Enquanto não houver uma fonte institucional aprovada, manter uma pilha sem dependência externa:

```text
Arial, Helvetica, sans-serif
```

| Elemento | Tamanho/altura | Peso | Regra |
|---|---|---:|---|
| Título de página (`h1`) | 28–32 px / 1,2 | 700 | Um por página; descreve a operação. |
| Título de seção (`h2`) | 20–24 px / 1,3 | 700 | Separa blocos funcionais. |
| Título de card (`h3`) | 16–18 px / 1,35 | 700 | Curto e contextual. |
| Corpo | 14–16 px / 1,5 | 400 | Texto operacional e instruções. |
| Label | 13–14 px / 1,35 | 700 | Sempre associado ao campo. |
| Metadado | 12–13 px / 1,4 | 400/600 | Datas, códigos e textos auxiliares. |
| Tabela | 13–14 px / 1,4 | 400 | Cabeçalho em 700. |

Não introduzir fonte remota ou biblioteca tipográfica sem decisão específica, para evitar impacto de dependência, desempenho e produção.

### 3.3 Espaçamento e geometria

| Token | Valor | Uso típico |
|---|---:|---|
| `--rr-space-1` | 4 px | microespaço entre ícone e texto. |
| `--rr-space-2` | 8 px | itens relacionados. |
| `--rr-space-3` | 12 px | controles e células compactas. |
| `--rr-space-4` | 16 px | grid e conteúdo de card compacto. |
| `--rr-space-5` | 24 px | padding padrão de card e distância entre seções. |
| `--rr-space-6` | 32 px | separação de blocos principais. |
| `--rr-space-7` | 48 px | respiro em páginas e estados vazios. |

| Propriedade | Padrão |
|---|---|
| Raio de card | 12–16 px |
| Raio de botão/input | 8–10 px |
| Raio de badge | 999 px |
| Borda | 1 px sólida em `--rr-border` |
| Sombra de card | `0 8px 24px rgba(7, 26, 47, 0.08)` ou mais suave |
| Altura de controles | 40–44 px; manter compatibilidade com os controles atuais |

## 4. Arquitetura de layout para a Missão 18.2

### 4.1 Shell autenticado

```text
App shell
├── Sidebar
│   ├── marca Rental Retros
│   ├── navegação por módulo e submódulo
│   └── item ativo e estado recolhido
├── Área principal
│   ├── topbar: busca/atalhos futuros, usuário e logout
│   ├── mensagens flash e faixa de ambiente
│   └── conteúdo da rota
└── rodapé discreto
```

- A sidebar deve refletir somente módulos e permissões já existentes; não cria rotas, opções ou permissões novas.
- A topbar não deve simular funcionalidades indisponíveis. Busca e notificações só poderão ser exibidas se houver comportamento definido ou forem marcadas como indisponíveis sem interação.
- A faixa de ambiente de teste continuará visualmente prioritária.
- O conteúdo deve preservar o bloco Jinja usado pela base atual e os pontos em que as mensagens flash são renderizadas.

### 4.2 Cabeçalho de página

Todo módulo deve convergir para:

```text
Breadcrumb/contexto opcional
Título da página                         ação primária
Descrição curta ou metadados             ações secundárias
```

Classes de destino sugeridas: `page-header`, `page-kicker`, `page-header-actions`. A implementação deve manter as classes atuais durante a transição se algum estilo ou script delas depender.

## 5. Componentes

### 5.1 Botões e ações

| Variante | Uso | Regras |
|---|---|---|
| Primário | criar, salvar, confirmar, avançar | No máximo uma ação dominante por bloco. |
| Secundário | voltar, cancelar, limpar, editar não prioritário | Menos contraste que o primário. |
| Sucesso | confirmar operação positiva já compreendida | Não substituir o primário sem necessidade. |
| Aviso | operação que exige atenção, mas é reversível | Usar rótulo explícito. |
| Perigo | excluir, cancelar, inativar, desfazer irreversível | Sempre com confirmação já existente preservada. |
| Ícone/ação de tabela | visualizar, editar, download, mais ações | Deve possuir `title`/rótulo acessível; não remover a ação existente. |

- Não usar cor como único significado.
- Não esconder ações necessárias atrás de menu sem preservar alternativa acessível.
- Em tabelas, priorizar visualização, edição e menu de mais ações para reduzir poluição, mantendo todos os links/formulários funcionais.

### 5.2 Cards

| Componente | Uso |
|---|---|
| `content-card` | agrupamento de conteúdo genérico. |
| `metric-card` | KPI, contador, valor financeiro ou status resumido. |
| `filter-card` | filtros de consulta e ações Aplicar/Limpar. |
| `form-card` | formulário de criação/edição. |
| `details-card` | dados de uma entidade e informações relacionadas. |
| `module-card` | entrada para módulo/submódulo em hubs. |

Todos devem usar superfície branca, borda discreta, sombra contida e padding baseado na escala. Cards não devem ser usados apenas como decoração.

### 5.3 Formulários

- Usar `label` visível, campo, texto de ajuda e validação no mesmo agrupamento.
- Manter `name`, `id`, `required`, `method`, `action`, `enctype`, `data-*` e valores Jinja existentes.
- Aplicar uma grade que passe de várias colunas a uma coluna em telas estreitas.
- Agrupar campos extensos por assunto (dados principais, classificação, observações), sem alterar a ordem funcional salvo aprovação posterior.
- Mensagens de erro e ajuda devem ser próximas do campo e não podem depender somente de cor.

### 5.4 Filtros

- Painel `filter-card` com rótulo, campo e ações claras.
- Ordem recomendada: filtros mais usados, filtros de status, filtros avançados e ações.
- Manter parâmetros GET, nomes de campos e links de limpar existentes.
- Para telas densas, permitir recolhimento apenas se não ocultar filtros essenciais e após validação da tela piloto.

### 5.5 Tabelas e listas

- Cabeçalho destacado e legível; primeira leitura deve identificar entidade, status, valores/datas e ações.
- Colunas numéricas e monetárias alinhadas à direita; datas e status consistentes; ações agrupadas no fim.
- Manter rolagem horizontal onde necessária durante a migração. A redução de colunas ou transformação para cartões exige validação funcional por tela.
- Usar cabeçalho sticky apenas quando houver contêiner rolável e ele não prejudicar acessibilidade.
- Padronizar estados vazios, carregamento quando existir e mensagens de filtro sem resultado.
- Não remover checkbox de seleção em massa, links de exportação, paginação existente ou ações por linha.

### 5.6 Badges e status

| Estado semântico | Cor principal | Exemplos |
|---|---|---|
| Sucesso | verde | ativo, pago, concluído, aprovado. |
| Atenção | amarelo/âmbar | pendente, aguardando, vencendo. |
| Perigo | vermelho | cancelado, recusado, vencido, erro. |
| Informação | azul | em análise, aberto, processando. |
| Neutro | cinza | inativo, rascunho, não informado. |

O mapeamento de cada texto de status deve ser decidido por módulo, sem alterar a regra que produz o status.

### 5.7 Abas e subnavegação

- Usar abas para telas do mesmo fluxo, como Contas a Pagar, Contas a Receber e Fluxo de Caixa.
- A aba ativa deve ter indicação visual e semântica; as demais devem permanecer legíveis.
- Em telas menores, permitir rolagem horizontal sem quebrar o item ativo.
- As parciais atuais (`_nav.html`, `_menu.html` e as parciais de Fluxo de Caixa) são a base para a primeira padronização.

### 5.8 Feedback, confirmação e estados vazios

- Preservar mensagens flash e suas categorias atuais.
- Continuar utilizando as confirmações existentes até que haja componente comum aprovado.
- Exibir estado vazio com contexto e próximo passo permitido, sem criar nova ação sem permissão/rota existente.
- Reservar aparência visual específica para sucesso, alerta, erro e informação, além de texto explícito.

## 6. Ícones

Não há biblioteca de ícones instalada. Na implementação, a escolha deverá seguir uma destas opções, sem misturar estilos:

1. usar caracteres/ícones já existentes, quando suficientes; ou
2. aprovar uma única biblioteca de ícones leve antes de adicioná-la como dependência/asset.

Ícones devem complementar, nunca substituir sem rótulo, ações de alto risco ou ambíguas.

## 7. Responsividade

| Faixa | Objetivo | Regras |
|---|---|---|
| Desktop amplo (≥ 1200 px) | produtividade e tabelas densas | sidebar expandida, múltiplas colunas quando apropriado. |
| Desktop/tablet (768–1199 px) | preservar leitura | sidebar recolhida ou ajustada, grids reduzidos, abas roláveis. |
| Mobile (< 768 px) | operação essencial | uma coluna para formulários, ações em fluxo, tabelas com rolagem explícita ou adaptação aprovada. |

Prioridades de validação futura: sidebar, cabeçalho, filtros, ações de tabela, formulários longos, modais/diálogos se existirem e páginas de autenticação.

## 8. Acessibilidade e qualidade visual

- Manter contraste suficiente entre texto, fundo e estado; não usar amarelo claro para texto crítico.
- Todo controle interativo deve ter foco visível.
- Todo ícone de ação deve possuir nome acessível (`aria-label`, texto oculto ou `title`, conforme o componente aprovado).
- Não utilizar placeholders como substitutos de labels.
- Preservar ordem de tabulação e semântica de tabelas, formulários e botões.
- Não criar layout dependente exclusivamente de hover; há uso em dispositivos de toque.

## 9. Convenções de implementação

1. Implementar tokens e componentes em arquivos globais antes de aplicá-los em massa.
2. Não inserir novos estilos inline; migrar os atuais apenas quando a tela correspondente for modernizada e validada.
3. Não remover classes existentes enquanto houver dependência conhecida de CSS ou JavaScript.
4. Não modificar rotas, controllers, queries, banco, permissões, nomes de campos, atributos `data-*` ou contratos de formulário durante uma mudança visual.
5. Cada módulo deve reutilizar componentes já aprovados; exceções precisam ser justificadas no respectivo commit/PR.
6. Validar visualmente em desktop, tablet e mobile após cada módulo modernizado; validar funcionalmente apenas o fluxo impactado.
7. Evitar bibliotecas novas até haver necessidade concreta e aprovação explícita.

## 10. Critérios de aceite da Missão 18.1

- [x] Paleta, tipografia, espaçamento, superfícies, bordas e sombras documentados.
- [x] Diretrizes de sidebar, topbar e cabeçalho de página definidas para a Missão 18.2.
- [x] Padrões de botões, cards, formulários, filtros, tabelas, badges, abas e feedbacks definidos para a Missão 18.3.
- [x] Regras de responsividade, acessibilidade e preservação funcional registradas.
- [x] Referências de imagem e sua localização futura registradas.
- [x] Nenhuma tela nem código de produção modificados.

## 11. Próximo passo autorizado apenas mediante aprovação

A Missão 18.2 deverá implementar a estrutura global (layout base, sidebar e topbar) com base neste documento. Ela não deve iniciar sem aprovação explícita.
