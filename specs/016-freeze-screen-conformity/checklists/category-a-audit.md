# Checklist operacional: Category A (auditoria US2)

**Feature**: `016-freeze-screen-conformity`  
**Uso**: Marcar Pass/Fail **tela a tela** nas tarefas US2 (T014–T023). Espelho de [quickstart.md](../quickstart.md) § Checklist Category A.  
**Referência visual (consumo only)**: contratos 009 chart/painel + 012 densidade-empty — **não editar**.  
**Gate**: path ∈ [path-allowlist.md](../contracts/path-allowlist.md); ∉ [non-goals-denylist.md](../contracts/non-goals-denylist.md).

---

## Critérios (espelho quickstart)

| # | Critério |
|---|----------|
| A1 | Ordem KPI(s) → visual → drill/tabela → ações |
| A2 | Charts = catálogo Freeze (`_chart_block`); sem markup fake |
| A3 | Aderência: só Status Triad (3 fatias) onde couber |
| A4 | Rankings longos: Top-N + “Outros” se Freeze D exigir; pipeline etapas sem Top-N |
| A5 | Badges = `badge_status`; CTAs = `button` |
| A6 | Cards/KPIs sem sombra; cores na paleta Freeze |
| A7 | Empty = kinds D (não “sem dados” genérico indevido) |
| A8 | ~375px: sem scroll horizontal da página / bleed |
| A9 | Full-bleed (sem cap B1) |

**N/A**: marcar quando o critério não se aplica à superfície (ex.: A3 fora de aderência; A4 se não houver ranking longo).

---

## Como auditar

1. Abrir a tela com dados **e** (quando possível) sem dados.
2. Percorrer A1–A9; registrar violação + path do template.
3. Remediação = presentation-only; se faltar token Freeze (exceto B1) → **ESCALATE / STOP**.
4. SC-001 = 100% das linhas abaixo com Pass (ou N/A justificado).

---

## Matriz por tela

### A · Painel admin

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/admin.html` (+ chrome `_ciclo_selector` / `_visao_toggle` se tocado) | Marina | T014 (+ progresso US1: T007/T009) |

- [ ] A1 Pass
- [ ] A2 Pass
- [ ] A3 N/A (não é aderência) / Pass se Triad aparecer indevido → Fail
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass (~375px)
- [ ] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

**US1 progresso (T007 · 2026-08-21)** — escopo: bloco `#pipeline-heading` + `chart_ciclo_progresso` / `AdminDashboardView._chart_ciclo_progresso` / `categorical_counts_payload`. Contratos consumidos (não editados): 009 chart-catalog / managerial-panel; 012 density-history-empty.

| # | Critério auditoria | Resultado | Evidência |
|---|-------------------|-----------|-----------|
| V1 | Fake markup (barra `style="width"` / HTML ad hoc) | **Pass** | Com `has_ciclo`: só `{% include "dashboard/_chart_block.html" %}`; sem barra fake no template |
| V2 | Tipo catálogo Freeze A | **Pass** | `type=bar_horizontal`; Chart.js `@4.5.1` em `extra_js` |
| V3 | Mono teal + amber só no gargalo | **Pass** | `highlight_max=True` → `mono_finish_colors`; amber só se pico estrito; JS: bar sem `colors` → mono teal (T012), não Triad |
| V4 | Empty Freeze D / kinds | **Pass** | V-E1/V-E3 remediados T011; V-E2 remediado T009 |
| V5 | Highlight fora do gargalo | **Pass** | Sem arco-íris; Triad não entra no payload com `highlight_max`; fallback JS de barra não é Triad (T012) |
| V6 | Série inventada | **Pass** | `series_payload`: `has_data` só se `total > 0`; labels/values vazios no empty |

Violações abertas (remediação):

| ID | Severidade | Onde | Violação | Task |
|----|------------|------|----------|------|
| V-E1 | Alta (A7 / 012) | `apps/dashboard/views.py` `_chart_ciclo_progresso` | Ciclo com **zero** avaliações: `empty_message` ad hoc `'Ainda não há avaliações neste ciclo.'` em vez de `empty_kind_payload(kind=EMPTY_KIND_SEM_DADO)` (012: sem avaliações → `sem_dado`) | **Remediado T011** — zero avaliações → `empty_kind_payload(SEM_DADO)` |
| V-E2 | Média (A2/A7) | `templates/dashboard/admin.html` | Sem ciclo: `empty_state` **solto** (title “Sem ciclo aberto”) — não passa por `_chart_block` do progresso | **Remediado T009** — ramo sem ciclo usa `_chart_block` + `chart_ciclo_progresso` (`operacional`) |
| V-E3 | Baixa (contexto) | `AdminDashboardView` branch `visao=historico` | `chart_ciclo_progresso` recebe `EMPTY_KIND_SEM_NOTA` (cópia de desempenho); 012 reserva `sem_nota` p/ desempenho/gap/aderência. Não renderiza no histórico, mas kind errado no context | **Remediado T011** — histórico: progresso → `SEM_DADO`; aderência permanece `SEM_NOTA` |
| V-P1 | Baixa (polish A) | `admin.html` progresso | Insight genérico (“Quantas avaliações…”) — DS pede callout do gargalo; sem mini-KPI `Total` (exemplo DS `_chart_block`) | **Remediado T009** — insight do gargalo via `ciclo_kpis.gargalo_label`; mini-KPI `Total` + `kpi_body` |
| V-L1 | Latente | `static/js/dashboard_charts.js` `buildSingleSeriesConfig` | Fallback `STATUS_TRIAD` se `colors` ausente em `bar_horizontal` — hoje mitigado porque `highlight_max` emite `colors` | **Remediado T012** — bar/`bar_horizontal` sem `colors` → mono teal; Triad só doughnut |

**T009 (2026-08-21)**: V-E2 + V-P1 fechados no template. **T011 (2026-08-21)**: V-E1 / V-E3 fechados (presentation). **T012 (2026-08-21)**: V-L1 fechado (JS presentation).

**T013 (2026-08-21) — gate US1**: quickstart Admin 1.1–1.2 + SC-003 **PASS** (HTML/payload live + browser `?ciclo=11`: `_chart_block` + `bar_horizontal`, amber só em Metas, Chart.js 4.5.1; empty operacional sem série inventada; denylist WT vazio).

Não ESCALATE: tokens/componentes/chart existem no Freeze; remediação = presentation-only allowlist.

---

### A · Painel do time

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/team.html`, `team_list_partial.html` | Bruno | T015 |

- [ ] A1 Pass
- [ ] A2 Pass (`_chart_block` **fora** do partial HTMX)
- [ ] A3 N/A / Fail se Triad indevido
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Aderência

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/adherence.html`, `adherence_list_partial.html` | Bruno | T016 |

- [ ] A1 Pass
- [ ] A2 Pass
- [ ] A3 Pass (Status Triad — 3 fatias only; sem recalcular `adherence.py`)
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Estrutura

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/structure.html` | Bruno | T017 |

- [ ] A1 Pass
- [ ] A2 Pass
- [ ] A3 N/A (cobertura ≠ aderência; sem Triad indevido)
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Matriz de talentos

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/talent/matrix.html`, `partials/_cell.html`, `_drawer.html`, `_person_card.html` | Marina / Bruno | T020 |

- [ ] A1 Pass (composição gerencial / polish Freeze; ninebox consome Freeze)
- [ ] A2 Pass / N/A se sem chart de catálogo
- [ ] A3 N/A
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Ciclo (detalhe)

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/cycles/ciclo_detail.html` | Marina | T019 (+ progresso US1: T008/T010) |

- [ ] A1 Pass
- [ ] A2 Pass (`bar_horizontal` / `_chart_block`; sem barra fake)
- [ ] A3 N/A
- [ ] A4 Pass / N/A (pipeline etapas **sem** Top-N indevido)
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

**US1 progresso (T008 · 2026-08-21)** — escopo: bloco `#progresso-heading` + `chart_ciclo_progresso` / `CicloDetailView._chart_ciclo_progresso` / `categorical_counts_payload`. Espelho presentation de admin (T007). Contratos consumidos (não editados): 009 chart-catalog / managerial-panel / cycle-managerial-detail; 012 density-history-empty. **Denylist**: `cycle.py` / `stage.py` intocados (auditoria only).

| # | Critério auditoria | Resultado | Evidência |
|---|-------------------|-----------|-----------|
| V1 | Fake markup (barra `style="width"` / HTML ad hoc) | **Pass** | Sempre `{% include "dashboard/_chart_block.html" %}` (has_data e empty); sem barra fake no template |
| V2 | Tipo catálogo Freeze A | **Pass** | `CHART_TYPE_BAR_HORIZONTAL`; Chart.js `@4.5.1` em `extra_js` |
| V3 | Mono teal + amber só no gargalo | **Pass** | `highlight_max=True` → mesmo path `categorical_counts_payload` / `mono_finish_colors` que admin; JS T012 mono se sem `colors` |
| V4 | Empty Freeze D / kinds | **Pass** | V-E1 remediado T011 (`sem_dado`) |
| V5 | Highlight fora do gargalo | **Pass** | Sem cores manuais; Triad não entra com `highlight_max`; fallback JS de barra não é Triad (T012) |
| V6 | Série inventada | **Pass** | `has_data` falso zera labels/values; test `test_ciclo_detail_quickstart_s3_empty_local_sem_inventar` |
| V7 | Sem ciclo / empty solto | **N/A → Pass** | `DetailView` sempre tem `ciclo`; empty do progresso passa por `_chart_block` (sem análogo a V-E2 do admin) |
| V8 | `visao=historico` vs pipeline | **Pass** | Pipeline do `pk` montado **antes** do branch histórico e mantido; aderência/gap viram `sem_nota` — kind correto p/ desempenho, não polui `chart_ciclo_progresso` (melhor que admin V-E3) |

Violações abertas (remediação):

| ID | Severidade | Onde | Violação | Task |
|----|------------|------|----------|------|
| V-E1 | Alta (A7 / 012) | `apps/cycles/views.py` `_chart_ciclo_progresso` | Zero avaliações: `empty_message` ad hoc `'Não há avaliações neste ciclo para exibir progresso.'` em vez de `empty_kind_payload(kind=EMPTY_KIND_SEM_DADO)` / `EMPTY_KIND_COPY[SEM_DADO]` (012: sem avaliações → `sem_dado`) | **Remediado T011** — zero avaliações → `empty_kind_payload(SEM_DADO)` |
| V-P1 | Baixa (polish A) | `ciclo_detail.html` `#progresso-heading` | Insight genérico (“Quantas avaliações estão em cada etapa.”) — DS pede callout do gargalo; sem mini-KPI `Total` | **Remediado T010** — insight do gargalo via `progresso_gargalo_label` (presentation-only); mini-KPI `Total` + `kpi_body` |
| V-L1 | Latente | `static/js/dashboard_charts.js` `buildSingleSeriesConfig` | Mesmo fallback Triad se `colors` ausente — mitigado por `highlight_max`; compartilhado com admin | **Remediado T012** — bar/`bar_horizontal` sem `colors` → mono teal; Triad só doughnut |

**T010 (2026-08-21)**: V-P1 fechado (template + context presentation `progresso_gargalo_label`). **T011 (2026-08-21)**: V-E1 fechado (presentation). **T012 (2026-08-21)**: V-L1 fechado (JS presentation, compartilhado).

**T013 (2026-08-21) — gate US1**: quickstart 1.3 + SC-003 **PASS** (`/cycles/11/` espelho admin: `bar_horizontal`, amber no gargalo, Chart.js 4.5.1, mini-KPI + insight; denylist WT vazio).

Não ESCALATE: tokens/componentes/chart existem no Freeze; remediação = presentation-only allowlist. Diff denylist domínio (`cycle.py` / `stage.py`) = vazio nesta task.

---

### A · Meu painel

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/personal.html` | Ana | T018 |

- [ ] A1 Pass
- [ ] A2 Pass (sem tendência/chart novo fora do catálogo)
- [ ] A3 N/A
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

## Chrome compartilhado (se auditoria exigir)

| Paths | Tasks |
|-------|-------|
| `templates/dashboard/_ciclo_selector.html`, `_visao_toggle.html` | T021 |

- [ ] Canônicos only (`button` / tokens Freeze); sem ilha de estilo
- [ ] ESCALATE se faltar token

Notas / violações:

---

## Fechamento US2 (T023)

- [ ] 7 superfícies A acima com A1–A9 Pass (ou N/A justificado) — SC-001
- [ ] Personas Marina / Bruno / Ana amostradas nas superfícies A do mapa
- [ ] SC-004 / SC-005 amostral (~375px; sem sombra/chip/cor ad hoc)
- [ ] Diff denylist vazio (AuthZ / stage / approval / fórmulas / fora-inventário)
- [ ] Contratos 009/012 **não** editados
