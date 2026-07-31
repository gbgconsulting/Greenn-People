# Contract: HTMX nos dashboards (preservação)

**Feature**: `005-dashboard-charts`  
**Objetivo**: Inclusão de gráficos **não** altera contratos HTMX das listas/partials já existentes.

## Superfícies

| Superfície | Partial / target | Regra |
|---|---|---|
| Time | `team_list_partial.html` → `#list-container` (via `HtmxPaginatedListMixin`) | Chart **fora** do partial; swaps de paginação/filtro não destroem o canvas do pai |
| Aderência (lista) | `adherence_list_partial.html` | Sem chart nesta feature; atributos `hx-*` intactos |
| Admin / Pessoal | Sem list HTMX crítica no first viewport | N/A |

## Regras

- Preservar `hx-target`, `hx-swap`, ids de container e `hx-indicator` vigentes.
- Se markup ao redor do chart mudar classes, ids de HTMX permanecem.
- Feedback `aria-live` / toasts em `base.html` inalterados.

## Fora

- Migrar listas para SPA; endpoint HTMX só para série de gráfico no MVP; quebrar paginação do time.
