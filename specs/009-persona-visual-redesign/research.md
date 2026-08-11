# Research: Redesign Visual por Persona (Painéis Gerenciais)

**Branch**: `009-redesign-ux-persona` | **Date**: 2026-08-11  
**Spec**: [spec.md](./spec.md)

Pesquisa consolidada a partir da spec (clarifications 2026-08-11), Constituição (`.specify/memory/constitution.md`), Freeze em `docs/design-system.md`, código atual de `apps/dashboard`, `apps/cycles`, `static/js/dashboard_charts.js` e o padrão allowlist de `specs/008-cycle-guidance-ux/tasks.md`. Todos os itens do Technical Context foram resolvidos (sem `NEEDS CLARIFICATION` remanescente).

---

## R1 — Stack de charts (manter Chart.js 4.5.1; ampliar tipos no init local)

- **Decision**: Continuar **Chart.js 4.5.1** (CDN jsDelivr UMD) + `static/js/dashboard_charts.js` + `templates/dashboard/_chart_block.html`. Ampliar o init local com catálogo por propósito: `doughnut` (+ plugin/pluginette de **valor central** via `plugins.datalabels` **não** — usar plugin inline Chart.js `afterDraw` ou `Chart.registry` mínimo no próprio arquivo), `bar` com `indexAxis: 'y'` quando `type: 'bar_horizontal'`, `line` com `fill: true` quando `type: 'area'`, e `bar_grouped` / multi-série já existentes. **Sem** nova lib, **sem** npm plugin, **sem** DRF/SPA.
- **Rationale**: Spec FR-001/FR-014 + Constituição I/stack; Freeze v2 reabre apenas polish de tipos/paleta de acabamento; shape canônico permanece.
- **Alternatives considered**:
  - ApexCharts / ECharts — rejeitado (stack + Freeze).
  - Plugin npm `chartjs-plugin-datalabels` — rejeitado (nova dependência); valor central via plugin inline no IIFE.
  - Subir Chart.js em `base.html` — rejeitado (contrato 005/007: só `extra_js` das páginas com gráfico).

---

## R2 — Sequenciamento: US1 fundação → US2/US3 consomem

- **Decision**: Planejar e implementar **US1 (charts modernos)** antes de US2 (painéis líder) e US3 (detalhe de ciclo RH). US2/US3 **reusam** `_chart_block.html`, `dashboard_charts.js` e helpers de `chart_payloads.py` ampliados; não duplicar init/markup.
- **Rationale**: Spec prioriza US1 como fundação (“sem charts ricos, painéis continuam tabelas com decoração”); Clarification Session confirma catálogo único.
- **Alternatives considered**: Paralelizar US1+US2 — rejeitado (risco de divergência de contrato visual); começar por US3 — rejeitado (depende do mesmo bloco de chart + padrão painel).

---

## R3 — Paleta ampliada vs Status Triad

- **Decision**: Status Triad de **negócio** (`#059669` / `#d97706` / `#e11d48`) permanece para categorias de status (aderência alta/média/baixa e equivalentes). Paleta ampliada / gradientes CSS/Canvas **só** no acabamento Chart.js (fills de área, tipografia, grid, séries não-semânticas já em `GROUPED_DEFAULTS` / ciclagem). **Não** criar novas cores semânticas de status no DS.
- **Rationale**: Clarification A + FR-001; Constituição + SC-004.
- **Alternatives considered**: Substituir Triad por paleta marketing — rejeitado (quebra semântica).

---

## R4 — Cobertura por área/cargo (estrutura) sem inventar métrica AuthZ

- **Decision**: Na `StructureDashboardView`, métrica visual **principal** = **cobertura** composta por contagens já autorizadas no escopo: usuários ativos visíveis (`get_visible_users` → filter ativo) agrupados por área/cargo **vs** presença de `Avaliacao` no ciclo selecionado (mesma regra de “tem avaliação” já usada em team chart). Helper de **apresentação** em `apps/dashboard` (ex.: extensão de `structure.py` ou builder em `chart_payloads.py`) que:
  1. Recebe o mesmo `QuerySet` `visible` já resolvido pela view;
  2. Faz `Count`/`annotate` leves síncronos;
  3. Emite payload no shape canônico (`has_data`, `labels`, `values` / `series`, `legend_items`).
  Lacunas (`gaps_by_area` / `gaps_by_cargo`) permanecem **destaque secundário** (lista/ranking acionável), sem misturar com aderência.
- **Rationale**: Clarification B + FR-006; Princípio II — escopo só no backend; FR-013 — composição sem fórmula nova de nota.
- **Alternatives considered**:
  - Inventar “score de saúde estrutural” — rejeitado (OUT).
  - Snapshot Celery de cobertura — prematuro; só se medição mostrar peso (clarification).
  - Alterar `get_visible_users` — **proibido**.

---

## R5 — Views/agregações novas para US2 (structure/adherence) e US3 (ciclo)

| Superfície | View nova? | Agregação | Escopo |
|---|---|---|---|
| Time | Não (`TeamDashboardView`) | Preferir payloads existentes; KPIs/ranking a partir do mesmo queryset de escopo | Já usa `get_visible_users` |
| Estrutura | Não (mesma `StructureDashboardView`) | **Sim** — composição leve cobertura → chart payload; reuso lacunas | `visible = get_visible_users(...).filter(is_active=True)` **inalterado** |
| Aderência | Não (`AdherenceListView`) | **Sim (leve)** — distribuição doughnut a partir de `AderenciaSnapshot` já filtrado por escopo (mesmo padrão admin) | Já filtra `lider__in=get_visible_users` se não admin |
| Ciclo RH detalhe | **Sim** — `CicloDetailView` (DetailView read-only) em `apps/cycles` | Composição: progresso por etapa + cobertura + aderência do `pk` + checklist 008 | AuthZ = `AdminCyclesMixin` / `RequiresAdminMixin` (precedente de ciclos); **não** relaxar nem alterar `ScopedObjectMixin` / `get_visible_users` |

- **Decision**: Agregações novas ficam em helpers de **leitura/apresentação** (`chart_payloads.py` e/ou `dashboard/services/structure.py` + context da DetailView de ciclo). Preferir reutilizar `aderencia_distribution_payload`, `categorical_counts_payload`, builders de cobertura. Celery **somente** o pipeline já existente de `AderenciaSnapshot`; sem task nova até evidência de peso.
- **Rationale**: Clarifications + FR-007/FR-013 + Princípios II/VI.
- **Alternatives considered**:
  - Accordion na lista de ciclos — rejeitado (spec: página `cycles/<pk>/`).
  - Colocar detalhe em `apps/dashboard` — rejeitado (ciclo é domínio `cycles`; dashboard só fornece builders de payload se compartilhado).
  - Aplicar `ScopedObjectMixin` com `scope_user_field` em `Ciclo` — inadequado (Ciclo não tem FK de “dono” usuário); o precedente real é **admin-only**. Spec exige respeitar AuthZ vigente — isso é `RequiresAdminMixin`, não inventar Scoped para Ciclo.

---

## R6 — Allowlist/denylist no formato 008

- **Decision**: Contratos `contracts/path-allowlist.md` + `contracts/non-goals-denylist.md` no mesmo formato de 008: allowlist por story com templates/partials/JS; denylist de máquina de estados, approval, fórmulas, AuthZ (`scope.py` mutação), models/migrations de domínio. **Exceção documentada**: `apps/cycles/urls.py` e nova `CicloDetailView` **somente** para rota GET de detalhe gerencial (US3) — sem mudar `open`/`close`/CRUD.
- **Rationale**: Pedido explícito do plano + FR-012.
- **Alternatives considered**: Diff livre “só UI” sem contrato — rejeitado (falhou em 008 como padrão de aceite).

---

## R7 — Padrão canônico “painel gerencial” + docs Freeze

- **Decision**: Documentar em `docs/design-system.md` (Freeze v2) a composição **KPI(s) via `components/card.html` + `_chart_block` + tabela `.table-frame` como drill-down**. Qualquer token/classe nova (ex.: wrapper `.managerial-panel`, altura chart se necessário) entra em `static/src/input.css` **na mesma entrega**, com rebuild Tailwind.
- **Rationale**: Clarification C + FR-011 + pedido do usuário.
- **Alternatives considered**: Só mudar templates sem DS — rejeitado (SC-006 / Freeze).

---

## R8 — Celery vs sync (gate de performance)

- **Decision**: Default = agregação **síncrona leve** no request (Counts sobre querysets já escopados). Continuar lendo `AderenciaSnapshot` (Celery Beat diário existente). Introduzir nova task/snapshot **somente** se profiling local mostrar degradação vs padrão aceito do produto; registrar em Complexity Tracking se isso ocorrer.
- **Rationale**: Clarification sobre Celery + Princípio VI (não async prematuro; não cálculo pesado de aderência no request).
- **Alternatives considered**: Snapshot genérico de “painel do ciclo” na entrega — rejeitado como prematuro.

---

## R9 — P2/P3 e prazo

- **Decision**: P2 (colaborador) = polish visual + orientação sem duplicar guidance 008. P3 = best-effort até **03/09**; ausência não bloqueia aceite. Paths na allowlist por story; P3 marcada como opcional no plano.
- **Rationale**: Clarification esforço P3 + FR-010.
- **Alternatives considered**: Bloquear release sem P3 — rejeitado pela spec.

---

## R10 — Agent context script

- **Decision**: Script `update-agent-context` **não existe** neste repositório (`.specify/scripts` só PowerShell de feature setup). Atualização de contexto: **skip** documentado; artefatos em `specs/009-persona-visual-redesign/` são a fonte de verdade (mesmo precedente 008).
- **Rationale**: Inventário de scripts do repo.
- **Alternatives considered**: Inventar script ad hoc — fora do workflow Speckit neste monólito.
