# Biblioteca de Componentes — Missão 18.3

## Objetivo

Esta biblioteca disponibiliza componentes visuais reutilizáveis para as próximas migrações da Missão 18. Ela não altera as telas existentes automaticamente.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `app/static/css/components.css` | Estilos de cabeçalho, botões, cards, campos, filtros, tabelas, badges e estados vazios. |
| `app/templates/components/ui.html` | Macros Jinja para botões, badges e estados vazios. |
| `app/templates/base.html` | Carrega a folha de componentes para as páginas autenticadas. |

## Uso nas próximas telas

```jinja
{% from "components/ui.html" import link_button, submit_button, badge, empty_state %}

{{ link_button("Novo lançamento", url_for("financeiro_contas_pagar.novo")) }}
{{ submit_button("Salvar") }}
{{ badge("Pendente", "warning") }}
{{ empty_state("Nenhum registro", "Ajuste os filtros ou cadastre um novo item.") }}
```

As macros não devem substituir campos, formulários ou ações existentes sem preservar seus atributos e comportamento. Para controles que exigirem ícone, confirmação, `data-*`, `id`, `name`, `method` ou `action` específico, o template deve manter esses contratos e aplicar as classes `ui-*` diretamente.

## Componentes definidos

- `ui-page-header`, `ui-page-kicker`, `ui-page-title`, `ui-page-description`, `ui-page-actions`
- `ui-button` e variantes `primary`, `secondary`, `success`, `warning`, `danger`, `icon`
- `ui-card`, `ui-card--compact`, `ui-card__header`, `ui-card__title`
- `ui-filter-grid`, `ui-form-grid`, `ui-field`, `ui-input`, `ui-select`, `ui-textarea`
- `ui-table-wrap`, `ui-table`, `ui-table-actions`
- `ui-badge` e tons `success`, `warning`, `danger`, `info`, `neutral`
- `ui-empty-state`

## Regras de transição

1. As classes antigas (`btn`, `card`, `table`, `form-group`, `filter-card` e equivalentes) continuam válidas até cada tela ser migrada e aprovada.
2. Não criar CSS inline novo; usar a biblioteca ou justificar a exceção.
3. A primeira aplicação integral será a tela piloto Financeiro → Contas a Pagar → Títulos, na Missão 18.4.
