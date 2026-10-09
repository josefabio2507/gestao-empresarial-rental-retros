# Missão 18.0 — Inventário da Interface Atual

**Data do levantamento:** 08/10/2026  
**Escopo:** inventário técnico da camada de apresentação local. Nenhum template, estilo, script, rota, regra de negócio, banco de dados ou permissão foi alterado nesta missão.

## 1. Resumo da arquitetura visual atual

O sistema é uma aplicação Flask com Jinja, estruturada em blueprints por domínio. Foram encontrados **174 arquivos HTML** em `app/templates`, quatro folhas de estilo próprias e um script JavaScript global.

- `app/templates/base.html` é a base visual de quase todas as páginas autenticadas. Ele carrega `css/base.css`, `css/app.css`, mensagens flash, faixa de ambiente de teste, conteúdo da página e rodapé.
- A base não contém navegação global (sidebar, topbar ou menu principal). A navegação atual é distribuída entre cartões/links das páginas-hub e menus locais de alguns submódulos.
- `login.html`, `recuperar_senha.html` e `redefinir_senha.html` são documentos independentes, com `css/login.css`.
- Há parciais Jinja para Contas a Pagar, Contas a Receber e Fluxo de Caixa. Elas são as únicas dependências de layout reutilizáveis identificadas além de `base.html`.
- Os estilos próprios estão em `app/static/css/base.css`, `app/static/css/app.css`, `app/static/css/login.css` e `app/static/css/contas_receber.css`. Não há framework de UI ou biblioteca JavaScript de componentes declarada em `requirements.txt` nem importada nos templates.
- `app/static/js/app.js` fornece comportamentos transversais: máscaras/validações de CPF/CNPJ e telefone, uppercase, datalist, campos condicionais, leitura de abastecimento, consulta de CNPJ, confirmações e autoenvio de holerites. Há também scripts específicos embutidos em templates.

### Dependências de layout

```text
base.html
├── base.css + app.css + app.js
├── mensagens flash / faixa de ambiente / rodapé
└── páginas autenticadas que usam {% extends "base.html" %}
    ├── financeiro/contas_pagar/* → inclui _nav.html
    ├── financeiro/contas_receber/* → inclui _menu.html
    ├── financeiro/fluxo_caixa/* → inclui _menu.html, _filtros.html e _movimentos_table.html
    └── demais módulos → usam diretamente os componentes/classes globais

Páginas independentes
├── login.html, recuperar_senha.html, redefinir_senha.html → login.css
└── alguns arquivos vazios/legados em pedido_refeicoes e departamento_pessoal
```

## 2. Arquivos de estilo, comportamento e bibliotecas

| Recurso | Situação atual | Alcance / observações |
|---|---|---|
| `app/static/css/base.css` | Tokens CSS iniciais e elementos-base | Cores `--rr-*`, página, flashes, rodapé e faixa de ambiente. |
| `app/static/css/app.css` | Folha global principal (~30 KB) | Cards, tabelas, formulários, filtros, badges, abas, listas roláveis, páginas de módulos e regras responsivas. Contém várias regras específicas de domínio. |
| `app/static/css/contas_receber.css` | Folha específica | Carregada por Clientes e pelo menu de Contas a Receber; concentra larguras e grids financeiros. |
| `app/static/css/login.css` | Folha exclusiva de autenticação | Login, recuperação e redefinição de senha; possui identidade visual própria. |
| `app/static/js/app.js` | JavaScript global | 12 contratos `data-*`; não deve ser removido ou renomeado sem preservar os templates que o acionam. |
| JavaScript inline | 25 templates identificados | Aplicado sobretudo a seleção em massa, cálculos, filtros, e-mails e formulários operacionais. |
| CSS inline / `<style>` | 3 templates identificados | Vale Transporte/Pedidos, Fiscal/Documentos e Operação/Central de Custos por Veículo. |
| Framework/UI kit externo | Não identificado | Não há Bootstrap, Font Awesome, DataTables, Select2, SweetAlert ou Chart.js importados. A UI é CSS/JS própria. |

### Responsividade atual

Há regras responsivas em `app.css` (breakpoints de 640 px, 760 px, 768 px e 1200 px), `contas_receber.css` (640 px) e `login.css` (520 px). O padrão predominante para tabelas largas é rolagem horizontal por `.table-responsive` ou classes `*-listbox`, com larguras mínimas específicas. A responsividade existe, mas é descentralizada: há muitas tabelas com largura mínima de 760 a 2.200 px e não há uma arquitetura de navegação móvel global a validar.

## 3. Inventário de módulos e telas

**Convenções da tabela:** páginas autenticadas usam `base.html` e, portanto, `base.css + app.css + app.js`, salvo indicação. `A` = alta, `M` = média, `B` = baixa. Os caminhos separados por vírgula descrevem todas as telas daquele agrupamento; parciais são identificadas como tal.

| Módulo | Tela | Template principal | Template base / herança | CSS utilizado | JS utilizado | Componentes relevantes | Responsividade atual | Complexidade | Risco de regressão | Observações |
|---|---|---|---|---|---|---|---|---|---|---|
| Global | Estrutura autenticada | `base.html` | raiz | `base.css`, `app.css` | `app.js` | flash, faixa de teste, rodapé, bloco de conteúdo | básica; sem navegação global | A | A | Ponto de entrada visual de quase todas as telas. |
| Global | Início e acesso negado | `inicio.html`, `acesso_negado.html` | `base.html` | global | global | cards, ações, estado de erro | grid de cards | M | M | Hub inicial e estado de autorização. |
| Global | Departamentos | `departamentos/detalhe.html` | `base.html` | global | global | cabeçalho, cards de módulos | grid | M | M | Navegação atual por páginas-hub. |
| Autenticação | Login | `login.html` | documento próprio | `login.css` | nenhum local | logo, formulário, flash, link de recuperação | breakpoint 520 px | M | A | Página pública; não usa `base.html`. |
| Autenticação | Recuperar/redefinir senha | `recuperar_senha.html`, `redefinir_senha.html` | documentos próprios | `login.css` | nenhum local | formulários, flash, estados do token | breakpoint 520 px | M | A | Mesmo padrão visual do login, mas duplicado em três documentos. |
| Autenticação | Troca/minha senha | `trocar_senha.html`, `minha_senha.html` | `base.html` | global | global | formulário de senha, flash | formulário fluido | M | A | Fluxo sensível de segurança; apenas apresentação poderá mudar futuramente. |
| Departamento Pessoal | Hub do módulo | `departamento_pessoal/index.html` | arquivo vazio | — | — | — | — | B | B | Arquivo sem conteúdo; confirmar se é rota ativa/legado antes de qualquer migração. |
| Departamento Pessoal | Colaboradores | `colaboradores/listar.html`, `form.html`, `detalhes.html`, `importar.html` | `base.html` | global | global e atributos de validação | tabela, filtros, formulários, importação, detalhes | tabelas roláveis / grids | A | A | Referência visual planejada; contém CRUD e importação. |
| Departamento Pessoal | Documentos/Holerites | `documentos/index.html`, `documentos/holerites.html` | `base.html` | global | `app.js` (autoenvio) | cards, filtros, tabela, sincronização | tabelas roláveis | A | A | Autoenvio controlado por `data-auto-submit-delay`; preservar o contrato. |
| Departamento Pessoal | Vale Transporte — hub e cadastros | `vale_transporte/index.html`, `linhas_listar.html`, `linha_form.html`, `vinculos.html` | `base.html` | global | global | cards, tabelas, formulários e vínculos | tabelas roláveis | A | A | Fluxo com regras e dados sensíveis de colaboradores. |
| Departamento Pessoal | Vale Transporte — pedidos/histórico | `vale_transporte/pedidos.html`, `pedidos_listar.html`, `pedido_detalhes.html`, `historico_colaborador.html` | `base.html` | global + estilo inline em `pedidos.html` | scripts inline | filtros, tabelas, detalhes, ações e confirmação | rolagem horizontal | A | A | Estilo inline e scripts locais exigem cuidado adicional. |
| Pedido de Refeições | Hub, pedidos e detalhe | `pedido_refeicoes/index.html`, `pedidos.html`, `pedido_detalhes.html`, `pedido_form.html` | `base.html` | global | scripts inline em listagem/detalhe | cards, filtros, tabela, formulário, ações | tabelas roláveis | A | A | Tela prevista como referência conceitual; envolve pedidos e WhatsApp. |
| Pedido de Refeições | Cardápio, restaurantes e fretes | `cardapios.html`, `restaurantes.html`, `fretes.html` | `base.html` | global | global | CRUDs, cards, tabelas e formulários | grid/formulários fluidos | M | M | `fretes.html` é compacto/minificado. |
| Pedido de Refeições | Consumo e histórico | `consumo_form.html`, `historico_colaborador.html` | `base.html` | global | global | formulário e consulta histórica | tabelas/grades | A | A | Afeta apuração operacional; não alterar comportamento. |
| Pedido de Refeições | Templates sem conteúdo | `consumo.html`, `historico.html`, `novo_pedido.html`, `resumo.html`, `selecionar_colaboradores.html` | sem herança | — | — | — | — | B | B | Arquivos vazios/legados; não devem receber design antes de confirmar uso. |
| Financeiro | Hub e relatórios gerais | `financeiro/index.html`, `financeiro/relatorios.html` | `base.html` | global | global | cards, filtros, tabelas, exportação | tabelas roláveis | M | A | Relatórios são dependentes de filtros e exportações. |
| Financeiro / Contas a Pagar | Navegação local | `contas_pagar/_nav.html` | parcial incluída | global | global | abas/submenu | overflow horizontal | M | A | Incluída por 11 telas; centralizará a migração futura do submódulo. |
| Financeiro / Contas a Pagar | Dashboard e títulos | `dashboard.html`, `titulos.html`, `form.html`, `detalhes.html` | `base.html` + `_nav.html` | global | scripts inline em títulos/formulário | KPIs, filtros, tabela, badges, CRUD | tabelas roláveis | A | A | `titulos.html` é a tela piloto planejada; seleção e filtros não podem ser alterados funcionalmente. |
| Financeiro / Contas a Pagar | Baixas e pagamentos | `baixa_em_massa.html`, `lote_baixa_detalhes.html`, `pagamento_form.html` | `base.html` + `_nav.html` | global | script inline na baixa em massa | seleção múltipla, formulários, histórico | tabelas largas | A | A | Alto risco: pagamentos e baixa em massa. |
| Financeiro / Contas a Pagar | XML e O.C. | `agendamentos_xml.html`, `conferir_xml.html`, `agendamentos_oc.html` | `base.html` + `_nav.html` | global | global | filtros, tabelas, ações de integração | tabelas roláveis | A | A | Integrações fiscal/O.C.; mudar somente a apresentação. |
| Financeiro / Contas a Pagar | Cartões e faturas | `cartoes.html`, `cartao_form.html`, `faturas.html`, `fatura_detalhes.html` | `base.html` + `_nav.html` | global | global | CRUD, detalhes, tabelas e badges | tabelas roláveis | A | A | Dados financeiros e vínculos com títulos. |
| Financeiro / Contas a Receber | Navegação local | `contas_receber/_menu.html` | parcial incluída | `contas_receber.css` | global | abas/submenu | overflow horizontal | M | A | Incluída pelas telas do submódulo e injeta CSS próprio. |
| Financeiro / Contas a Receber | Dashboard e títulos | `dashboard.html`, `titulos.html`, `form.html`, `detalhe.html`, `baixa_massa.html`, `lotes.html`, `lote_detalhe.html`, `recebimento_form.html` | `base.html` + `_menu.html` | global + `contas_receber.css` | scripts inline em títulos/form/baixa | KPIs, filtros, tabelas, baixa, lote, paginação por dados quando aplicável | muitas tabelas mín. 1.500–1.980 px | A | A | Alto acoplamento entre títulos, recebimentos e baixa em massa. |
| Financeiro / Contas a Receber | Clientes | `clientes/listar.html`, `form.html`, `detalhes.html` | `base.html` | global + `contas_receber.css` | script inline no formulário | tabela, filtro, consulta de CNPJ, detalhes | tabela mín. 1.600 px | A | A | CSS é carregado diretamente pelos templates, não por uma base de bloco. |
| Financeiro / Contas a Receber | Contratos e medições | `contratos.html`, `contrato_form.html`, `contrato_detalhe.html`, `medicoes.html`, `medicao_form.html`, `medicao_detalhe.html`, `medicao_gerar_titulos.html`, `medicao_vincular_titulo.html`, `medicao_vincular_nota.html` | `base.html` + `_menu.html` | global + `contas_receber.css` | scripts inline nos formulários | detalhes compostos, filtros, formulários extensos, tabelas | tabelas de até 1.820 px | A | A | Parte dos arquivos é minificada em uma linha; grande densidade de ações e vínculos. |
| Financeiro / Contas a Receber | Notas e cobrança | `notas_emitidas.html`, `nota_form.html`, `nota_detalhe.html`, `nota_gerar_titulos.html`, `nota_vincular_titulo.html`, `inadimplencia.html`, `cobranca_form.html` | `base.html` + `_menu.html` | global + `contas_receber.css` | scripts inline em notas | filtros, ações financeiras, tabelas e formulários | tabelas até 2.200 px | A | A | Integra nota, título, inadimplência e cobrança; atenção especial. |
| Financeiro / Fluxo de Caixa | Dashboard, movimentos e visão | `fluxo_caixa/dashboard.html`, `movimentos.html`, `visao.html` | `base.html` + parciais | global + `contas_receber.css` | global | KPIs, filtros, tabelas e exportação | tabela mín. 2.200 px | A | A | Depende de `_menu.html`, `_filtros.html` e `_movimentos_table.html`; candidato forte a componentes globais. |
| Fiscal | Documentos fiscais | `fiscal/documentos.html` | `base.html` | global + `<style>` local | script inline | filtros, tabela, ações de documento/SEFAZ | tabela rolável | A | A | Possui estilo e script próprios; integrações fiscais tornam a tela sensível. |
| Fiscal | Certificado | `fiscal/certificado.html` | `base.html` | global | global | formulário, lista e mensagens | formulário fluido | A | A | Tela sensível por manipular certificado. |
| Suprimentos | Hub e indicadores | `suprimentos/index.html`, `indicadores/painel.html` | `base.html` | global | global | cards, KPIs, ações e tabelas | grid responsivo | M | M | Hubs adequados para a migração após componentes globais. |
| Suprimentos | Cadastros-base | `categorias/*`, `unidades_medida/*`, `itens/*`, `centros_custo/*`, `fornecedores/*`, `fornecedor_itens/*`, `compradores/*`, `alcadas_aprovacao/*` | `base.html` | global | `app.js` para máscara/consulta quando aplicável | listagens, filtros, CRUDs e detalhes | tabelas roláveis / formulários em grid | A | A | 17 templates; padrões repetidos são oportunidade clara de centralização. |
| Suprimentos | Requisições | `requisicoes/listar.html`, `form.html`, `detalhes.html`, `abrir_email.html` | `base.html` | global | script inline em e-mail | filtros, tabelas, fluxo de requisição e e-mail | tabelas roláveis | A | A | Fluxo operacional e comunicação externa. |
| Suprimentos | Cotações | `cotacoes/listar.html`, `form.html`, `detalhes.html`, `mapa_comparativo.html`, `aprovacao_publica.html`, `abrir_email.html` | `base.html` | global | scripts inline em detalhe/e-mail | filtros, comparativo, aprovação, e-mail | `cotacoes-listbox` próprio | A | A | A aprovação pública e os e-mails exigem preservação integral de formulários/links. |
| Suprimentos | Ordens de Compra | `ordens_compra/listar.html`, `detalhes.html`, `receber.html`, `editar_recebimento.html`, `aguardando_financeiro.html`, `documentos_fiscais.html`, `evidencias.html`, `evidencias_ordem.html`, `evidencia_item.html`, `abrir_email.html` | `base.html` | global | script inline em e-mail | tabelas, recebimento, evidências, NF-e, ações | tabelas roláveis | A | A | Maior conjunto de telas do módulo; conecta Suprimentos, Fiscal e Financeiro. |
| Suprimentos | Estoque | `estoque/listar.html`, `movimentacoes.html`, `form_movimentacao.html` | `base.html` | global | global | tabela, filtros, movimentação e exportação/PDF | tabelas roláveis | A | A | Transações de estoque e histórico; atenção à legibilidade de tabelas. |
| Operação | Hub, pool e vínculo | `operacao/index.html`, `pool.html`, `vinculo_form.html`, `correcao_vinculo.html` | `base.html` | global | global | KPIs, cards, filtros e formulários | grids e tabelas | A | A | Operação de disponibilidade/vínculo. |
| Operação | Veículos e EPGs | `gestao_veiculos_epgs/index.html`, `veiculos_equipamentos/listar.html`, `form.html`, `detalhes.html` | `base.html` | global | global | dashboard, CRUD, detalhes e tabelas | tabelas roláveis | A | A | Navegação de submódulo hoje é local. |
| Operação | Abastecimento | `abastecimentos.html`, `abastecimento_form.html`, `abastecimento_detalhes.html` | `base.html` | global | `app.js` + script inline no formulário | filtros, tabela, campos condicionais, detalhes | tabelas largas | A | A | Depende de `data-abastecimento-reading`; preservar ids e atributos. |
| Operação | Custos, impostos e multas | `central_custos.html`, `central_custos_veiculo.html`, `impostos_taxas.html`, `imposto_taxa_form.html`, `imposto_taxa_detalhes.html`, `multas_transito.html`, `multa_transito_form.html`, `multa_transito_boleto_form.html`, `multa_transito_detalhes.html`, `historico.html`, `veiculo_form.html` | `base.html` | global + `<style>` em custo por veículo | scripts inline em formulários | tabelas, anexos, formulários, detalhes e histórico | tabelas roláveis | A | A | Central de custos por veículo possui CSS inline; multas e impostos possuem formulários com lógica local. |
| Segurança do Trabalho | Hub e EPI | `seguranca_trabalho/index.html`, `epis/listar.html`, `epis/form.html` | `base.html` | global | script inline na listagem | cards, filtros, tabela, formulário | tabelas roláveis | A | A | Registro de entregas de EPI/uniforme. |
| Administração | Hub e logs | `admin/index.html`, `admin/logs.html` | `base.html` | global | global | cards, filtros, tabela de auditoria | tabelas roláveis | A | A | Logs devem manter legibilidade e filtros. |
| Administração | Usuários | `usuarios/listar.html`, `form.html`, `detalhes.html` | `base.html` | global | global | CRUD, tabelas, formulários e detalhes | tabelas roláveis | A | A | Controle de contas e acesso. |
| Administração | Permissões | `permissoes/listar.html`, `editar.html`, `visualizar.html` | `base.html` | global | global | cartões de módulos, checkboxes, resumo de permissões | grids/fluidos | A | A | Mudança visual não pode alterar nomes/valores dos inputs. |
| Administração | Cargos e equipes | `admin/cargos/*`, `admin/equipes/*` | `base.html` | global | script inline nas listagens | CRUD, tabelas, detalhes, formulários | tabelas roláveis | M | A | Padrões quase idênticos aos demais cadastros. |

## 4. Componentes e padrões identificados

| Categoria | Implementação atual | Reutilização observada | Destino recomendado na Missão 18.3 |
|---|---|---|---|
| Página/cabeçalho | `.page`, `.page-wide`, `.top-bar`, `.page-kicker` | recorrente nos módulos | `page-header` com título, contexto e área de ações. |
| Ações | `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-warning`, `.btn-danger`, `.actions`, `.form-actions` | 164 templates usam `btn-*` | família única de botões e ações compactas de tabela. |
| Cards | `.card`, `.table-card`, `.form-card`, `.details-card`, `.filter-card`, `.module-card` | transversal | content card, metric card, filter card e detail card. |
| Tabelas | `.table`, `.table-responsive`, `.listbox-*` e muitas classes específicas | 93 templates com tabelas | tabela padrão, cabeçalho sticky opcional, wrapper responsivo e célula de ações. |
| Formulários | `.form-group`, `.form-grid`, `textarea`, selects e checkboxes | 131 templates com formulários | campo, grupo, grid de formulário, ajuda e validação visual. |
| Filtros | `.filter-card`, `.filter-grid`, `.filter-actions` | 54 templates com filtros | painel de filtros único com ações Aplicar/Limpar. |
| Status | `.badge`, variações sucesso/alerta/perigo | 75 templates | taxonomia única de badge/status. |
| Subnavegação | `.submodule-tabs`, `_nav.html`, `_menu.html` | sobretudo Financeiro | componente de abas/submenu responsivo. |
| Feedback | flashes e `.alert-info` | base e vários módulos | alertas, confirmação e estados vazios padronizados. |
| Listas vazias | `.empty-state` em tabelas | distribuído | estado vazio reutilizável. |

Não foi identificado componente modal reutilizável nem componente de paginação visual padronizado. As confirmações atuais usam `window.confirm` ou comportamentos locais.

## 5. Inconsistências principais

1. A base global não possui navegação unificada; menus, hubs e atalhos variam por módulo.
2. `app.css` é global, mas concentra estilos de domínio (Vale Transporte, cotações, requisições, EPIs e outros), tornando difícil distinguir componente de exceção de tela.
3. As tabelas repetem wrappers, larguras mínimas e regras de rolagem com muitas variantes (`listbox`, `*-table`, `*-listbox`).
4. O CSS de Contas a Receber é carregado por templates e por uma parcial, enquanto a maior parte dos estilos vem da folha global.
5. Há três ocorrências de CSS inline/blocos `<style>` e scripts inline em 25 templates, reduzindo a centralização.
6. Há páginas completas minificadas em uma linha, principalmente em Contas a Receber, o que torna alterações visuais e revisão mais arriscadas.
7. Os fluxos de autenticação duplicam estruturas de documento, flash e formulário fora de uma base pública compartilhada.
8. Existem seis templates vazios no Departamento Pessoal/Pedido de Refeições, a confirmar como legados antes de removê-los, reaproveitá-los ou modernizá-los.
9. Há responsividade por breakpoint, mas muitas tabelas dependem exclusivamente de rolagem horizontal; não há política visual comum para tablet/mobile.

## 6. Páginas que exigirão atenção especial

- **Financeiro / Contas a Pagar / Títulos:** tela piloto prevista; filtros, seleção em massa, exportação, navegação e ações por registro.
- **Financeiro / Contas a Receber:** títulos, baixa em massa, contratos, medições, notas e inadimplência combinam tabelas muito largas, CSS específico e regras locais.
- **Pedido de Refeições:** pedidos, detalhes, consumo e histórico têm comportamento operacional e scripts locais.
- **Vale Transporte:** pedidos e histórico combinam estilo/script local com integrações operacionais.
- **Suprimentos / Ordens de Compra e Cotações:** concentram vínculos com Fiscal/Financeiro, e-mails, aprovação e evidências.
- **Fiscal / Documentos e Certificado:** integrações e informações sensíveis; mudanças futuras devem ser estritamente de apresentação.
- **Operação / Abastecimento e custos:** atributos `data-*`, leitura de odômetro/horímetro, uploads e tabelas densas.
- **Administração / Permissões e Usuários:** preservar valores, nomes e estrutura dos controles de autorização.
- **Autenticação:** telas públicas e críticas que não herdam `base.html`.

## 7. Proposta preliminar de ordem de migração

1. **18.1 — Design System:** documentar tokens, tipografia, espaçamento, estados, ícones e padrões a partir dos arquivos globais existentes e das referências aprovadas.
2. **18.2 — Estrutura global:** evoluir `base.html` e estilos globais para uma navegação/layout comum, preservando blocos, flashes, atributos e rotas.
3. **18.3 — Componentes reutilizáveis:** consolidar cabeçalho, botões, cartões, filtros, tabelas, badges, ações, abas, estados vazios e feedbacks antes de migrar páginas.
4. **18.4 — Piloto:** Financeiro / Contas a Pagar / `titulos.html`, incluindo a parcial `_nav.html`, sem alterar a lógica de filtros, seleção, exportação ou baixa.
5. **Financeiro restante:** Contas a Pagar, Contas a Receber, Clientes e Fluxo de Caixa; é o conjunto com mais componentes compartilháveis e risco elevado.
6. **Departamento Pessoal:** Colaboradores, Documentos/Holerites, Vale Transporte e Pedido de Refeições, usando os componentes validados.
7. **Suprimentos + Fiscal:** primeiro cadastros e hubs, depois Requisições, Cotações, Ordens de Compra, Estoque e documentos fiscais.
8. **Operação + Segurança do Trabalho:** hub, veículos/EPGs, abastecimento, custos, multas, impostos e EPIs.
9. **Administração, acesso e exceções:** usuários, permissões, cargos/equipes, logs, login, recuperação, redefinição, troca de senha e acesso negado.
10. **Responsividade, auditoria visual e regressão:** somente após a cobertura visual dos módulos.

## 8. Arquivos com provável impacto nas Missões 18.1–18.4

Os arquivos abaixo **não foram alterados** nesta missão; são a lista preliminar do provável escopo futuro.

| Missão | Arquivos candidatos | Motivo |
|---|---|---|
| 18.1 — Design System | `docs/ui/DESIGN_SYSTEM.md` (novo), `docs/ui/references/*` (quando as imagens forem disponibilizadas) | Registrar a direção visual e suas referências sem implementar telas. |
| 18.2 — Layout global | `app/templates/base.html`, `app/static/css/base.css`, `app/static/css/app.css`, possivelmente `app/static/js/app.js` | O layout base carrega toda a experiência autenticada; qualquer mudança exigirá preservar blocos e contratos JS. |
| 18.2 — Autenticação | `app/templates/login.html`, `recuperar_senha.html`, `redefinir_senha.html`, `app/static/css/login.css` | Base pública independente a ser alinhada somente depois da arquitetura autenticada. |
| 18.3 — Componentes | `app/static/css/app.css`, `base.css`, `contas_receber.css`, `base.html`; parciais futuras sob `app/templates/...` | Centralizar componentes sem reescrever telas antes da validação. |
| 18.3 — Subnavegação existente | `app/templates/financeiro/contas_pagar/_nav.html`, `financeiro/contas_receber/_menu.html`, `financeiro/fluxo_caixa/_menu.html`, `_filtros.html`, `_movimentos_table.html` | Parciais atuais são os primeiros candidatos para padronização controlada. |
| 18.4 — Tela piloto | `app/templates/financeiro/contas_pagar/titulos.html`, `app/templates/financeiro/contas_pagar/_nav.html`, `app/static/css/app.css` | Aplicar os componentes aprovados preservando ações, nomes de campos, scripts e rotas. |

## 9. Limites e decisão de continuidade

Esta Missão 18.0 está limitada a este inventário. A modernização visual, a criação do Design System, a alteração de `base.html`, CSS, HTML, JavaScript, rotas, banco, permissões ou comportamento **não deve começar sem aprovação explícita para a Missão 18.1**.

