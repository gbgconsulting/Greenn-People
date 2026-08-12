# Data Model: Redesign Visual por Persona

**Branch**: `009-redesign-ux-persona` | **Date**: 2026-08-11

## Declaração

Esta feature **não introduz models Django novos**, **não cria migrations** e **não altera** campos, FKs, `on_delete`, snapshots de negócio nem máquina de estados.

As Key Entities da [spec.md](./spec.md) são **conceitos de apresentação** mapeados para contexto de views, helpers de payload e templates. Persistência de aderência continua `AderenciaSnapshot` (Celery); charts e painéis apenas leem/compõem.

Contratos: [contracts/](./contracts/).

---

## Entidades de apresentação

### Bloco de gráfico

| Campo lógico | Origem |
|---|---|
| `has_data`, `type`, `title`, `labels`, `values` / `series`, `colors?`, `legend_items`, `empty_message`, `total?` | `apps/dashboard/chart_payloads.py` |
| Render | `templates/dashboard/_chart_block.html` + `static/js/dashboard_charts.js` |
| Types novos (US1) | `bar_horizontal`, `area`, `doughnut` com valor central (plugin inline); `bar_grouped` / `doughnut_or_bar` existentes |

**Validação**: Status Triad e significado de categorias intactos; empty quando `has_data` falso.

### Painel gerencial

| Slot | Implementação |
|---|---|
| KPI(s) | `templates/components/card.html` |
| Visualização | `_chart_block.html` |
| Drill-down | `.table-frame` / partials HTMX existentes |
| Ações | links/CTAs já disponíveis no produto |

Documentado em [contracts/managerial-panel.md](./contracts/managerial-panel.md).

### Destaque de atenção

| Aspecto | Valor |
|---|---|
| Fonte | Etapas de ação do líder / lacunas (`gaps_by_*`) / snapshots baixos — já no domínio |
| Apresentação | Ranking `bar_horizontal` ou lista destacada + links |
| Escopo | Subconjunto do `get_visible_users` já aplicado pela view |

### Visão gerencial de ciclo

| Aspecto | Valor |
|---|---|
| Persistência | `cycles.Ciclo` (leitura) + `Avaliacao` / `AderenciaSnapshot` / checklist 008 |
| View | `CicloDetailView` (nova) — `AdminCyclesMixin` |
| URL | `cycles/<pk>/` (`ciclo_detail`) |
| Template | `templates/cycles/ciclo_detail.html` |
| Seções | Progresso etapa; cobertura área/cargo; aderência; checklist avisório |

---

## Mapeamento de dados por superfície

### US1 — Charts (personal / team / admin)

| Painel | Fonte existente | Mudança 009 |
|---|---|---|
| Pessoal gaps | `build_fr005_context` → `competencias_resumo` → `grouped_series_payload` | Tipo/acabamento visual; shape estável |
| Time status | Contagem etapas sobre `get_visible_users` | Preferir barras horizontais / hierarquia visual |
| Admin aderência | `AderenciaSnapshot` + `aderencia_distribution_payload` | Doughnut + valor central |
| Admin progresso | `Avaliacao` por etapa | Tipo área ou barras expressivas sem mudar counts |

### US2 — Estrutura / Aderência / Time

| Visual | Fonte | Agregação |
|---|---|---|
| Cobertura por área/cargo | `visible` + `Avaliacao` no ciclo | Counts composição (helper novo de apresentação) |
| Lacunas (secundário) | `gaps_by_area` / `gaps_by_cargo` | Já existem — ranking/destaque |
| Distribuição aderência (lista) | `AdherenceListView` queryset + snapshots | Reuso `aderencia_distribution_payload` |
| Time painel | Mesmo escopo team | KPIs + chart US1 + tabela drill-down |

**Regra de escopo**: builder **nunca** chama `get_visible_users` com outro usuário; recebe o QS da view.

### US3 — Detalhe do ciclo

| Seção | Fonte | AuthZ |
|---|---|---|
| Progresso | `Avaliacao` filtrada pelo `ciclo` | Admin-only |
| Cobertura | Mesma composição da estrutura, ciclo = object | Admin-only |
| Aderência | `AderenciaSnapshot` do ciclo | Admin-only |
| Checklist | `build_rh_pre_open_checklist()` (008) | Já admin |

---

## State transitions

**Nenhuma.** Esta feature não altera estados de `Ciclo` nem `Avaliacao`.

---

## Validation rules (apresentação)

1. Payload com `has_data !== true` → empty; sem séries fictícias.
2. Cores de status semântico ⊂ Status Triad.
3. Diff em denylist de domínio = falha de aceite.
4. Cobertura e aderência semanticamente distintas na UI (labels/copy).
