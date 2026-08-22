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

- [x] A1 Pass
- [x] A2 Pass
- [x] A3 Pass (doughnut Triad só no slot de aderência; progresso mono)
- [x] A4 N/A (pipeline etapas sem Top-N; drill Top-10 destaque, não ranking chart longo)
- [x] A5 Pass
- [x] A6 Pass
- [x] A7 Pass
- [x] A8 Pass (~375px; `min-w-0` + `.table-frame` overflow)
- [x] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

**T014 (2026-08-21) — resto além do progresso US1**: KPIs → charts (progresso + aderência via `_chart_block`) → drill `.table-frame` → CTAs `button`. Remediado: (V-A1) empty de aderência em `<p>` ad hoc (operacional / histórico / sem ciclo) → sempre `_chart_block` + kinds D; (V-A2) link “Ver todos” emerald ad hoc → `components/button.html` secondary. Cards/`badge_status`/Chart.js 4.5.1 intactos. Chrome `_visao_toggle` (classes ad hoc) → **T021**. Sem ESCALATE; denylist intocada.

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

- [x] A1 Pass
- [x] A2 Pass (`_chart_block` **fora** do partial HTMX)
- [x] A3 N/A (pipeline `bar_horizontal` mono; sem Triad indevido)
- [x] A4 N/A (pipeline etapas sem Top-N; destaque acionável limitado, não ranking chart longo)
- [x] A5 Pass (badges canônicos; links de ação em tabela = tipografia DS, não `button` Medium h-12)
- [x] A6 Pass
- [x] A7 Pass
- [x] A8 Pass (~375px; `min-w-0` + `.table-frame` overflow)
- [x] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

**T015 (2026-08-21)**: KPIs → `_chart_block` (`bar_horizontal` / kinds D) → destaque (se ciclo) → drill `team_list_partial` (sempre no operacional). Remediado: (V-T1) empty sem ciclo em `empty_state` solto (“Sem ciclo aberto”) → sempre `_chart_block` + kinds D; (V-T2) drill ausente no ramo sem ciclo → lista completa após o visual; (V-T3) polish mini-KPI `Total` + insight do gargalo com dados; (V-T4) link “Ver” secundário no partial alinhado a slate (emerald só em “Avaliar”). Partial **sem** `_chart_block`. Chart.js 4.5.1. Chrome `_visao_toggle` → **T021**. Pytest team/dashboard surface: 48 passed. Denylist AuthZ / views intocadas.

---

### A · Aderência

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/adherence.html`, `adherence_list_partial.html` | Bruno | T016 |

- [x] A1 Pass
- [x] A2 Pass (`_chart_block` **fora** do partial HTMX; doughnut via catálogo)
- [x] A3 Pass (Status Triad — 3 fatias only; sem recalcular `adherence.py`)
- [x] A4 N/A (doughnut Triad fora de Top-N; drill é lista paginada, não ranking chart longo)
- [x] A5 Pass (badges canônicos; sem CTA Medium h-12 na tabela)
- [x] A6 Pass (cards sem sombra; tint `rose` só em linha `baixa` — paleta Triad)
- [x] A7 Pass
- [x] A8 Pass (~375px; `min-w-0` + `.table-frame` overflow)
- [x] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

**T016 (2026-08-21)**: KPIs → `_chart_block` (`doughnut` Status Triad / kinds D) → drill `adherence_list_partial` (sempre). Remediado: (V-Ad1) empty sem ciclo em `empty_state` solto (“Sem ciclo aberto”) → sempre `_chart_block` + kinds D; (V-Ad2) drill ausente no ramo sem ciclo → lista completa após o visual; (V-Ad3) polish insight alinhado ao admin + mini-KPI `Líderes` com dados; (V-Ad4) empty do partial com ciclo → copy `sem_dado` 012. Partial **sem** `_chart_block`. Chart.js 4.5.1. Payload/views/`adherence.py` intocados (Triad já via `aderencia_distribution_payload`). Sem ESCALATE; denylist intocada.

---

### A · Estrutura

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/structure.html` | Bruno | T017 |

- [x] A1 Pass
- [x] A2 Pass (charts cobertura sempre via `_chart_block`; `bar_horizontal` mono)
- [x] A3 N/A (cobertura ≠ aderência; sem Triad indevido no visual principal)
- [x] A4 Pass (Top-N + Outros no payload de cobertura; lacunas são drill, não ranking chart longo)
- [x] A5 Pass (`badge_status` + CTA `button` “Ver aderência”)
- [x] A6 Pass (cards sem sombra; lacuna crítica `text-rose-600`; chrome `.table-frame`)
- [x] A7 Pass
- [x] A8 Pass (~375px; `min-w-0` + `.table-frame` overflow)
- [x] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

**T017 (2026-08-21)**: KPIs → `_chart_block` (cobertura área/cargo / kinds D) → drills (líderes secundário + lacunas). Remediado: (V-S1) empty sem ciclo em `empty_state` solto (“Sem ciclo aberto”) → sempre `_chart_block` + kinds D; (V-S2) charts só com `has_data` → ambos os slots sempre via `_chart_block`; (V-S3) drills ausentes no ramo sem ciclo → líderes/lacunas sempre após o visual; (V-S4) empty de drill com kinds D (`sem_dado` / operacional); (V-S5) tabelas alinhadas ao chrome `.table-frame` (sem classes ad hoc no `<table>`); (V-S6) copy do drill de líderes deixa claro que aderência é secundária (CTA para aderência). Chart.js 4.5.1. Payload/views/`structure.py` / AuthZ intocados. Sem ESCALATE; denylist intocada.

---

### A · Matriz de talentos

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/talent/matrix.html`, `partials/_cell.html`, `_drawer.html`, `_person_card.html` | Marina / Bruno | T020 |

- [x] A1 Pass (header KPI count → filtros → grade 9-box → drawer drill)
- [x] A2 N/A (sem chart de catálogo; ninebox ≠ barra fake)
- [x] A3 N/A
- [x] A4 N/A
- [x] A5 Pass (`badge_status` + CTAs drawer via `button`; person card = controle de drill)
- [x] A6 Pass (cards/drawer sem sombra; tints emerald/rose DS ninebox)
- [x] A7 Pass (`empty_state` honesto — ciclo/filtro/idle drawer; kinds D N/A sem `_chart_block`)
- [x] A8 Pass (~375px; `min-w-0` + `.table-frame` overflow-x)
- [x] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1)

Notas / violações:

**T020 (2026-08-22)**: Header (count + `badge_status`) → filtros (`.form-control`) → grade `#ninebox-matrix` (`table-frame`) → drawer lateral (drill HTMX). Remediado: (V-M1) link emerald classify → `button` secondary + `data-drawer-classify-fallback`; (V-M2) botão “Fechar” ad hoc → `button` secondary compacto + `data-drawer-close`; (V-M3) `min-w-0` em seções flex (A8). `_cell`/`_person_card` já alinhados ao DS v2 ninebox (007). Sem chart; AuthZ/`get_visible_users`/hx-* intactos. Sem ESCALATE; denylist intocada. Pytest: `test_talent_matrix_authz.py` (+ `test_matrix_surface_t020_freeze_markers`).

### A · Ciclo (detalhe)

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/cycles/ciclo_detail.html` | Marina | T019 (+ progresso US1: T008/T010) |

- [x] A1 Pass
- [x] A2 Pass (`bar_horizontal` / doughnut / cobertura sempre via `_chart_block`; sem barra fake)
- [x] A3 Pass (doughnut Triad só no slot de aderência; progresso/cobertura mono)
- [x] A4 Pass (pipeline etapas sem Top-N; cobertura Top-N + Outros no payload)
- [x] A5 Pass (`badge_status` + CTAs `button`; checklist fix → `button` secondary)
- [x] A6 Pass (cards sem sombra; checklist avisório amber/emerald da paleta Freeze)
- [x] A7 Pass
- [x] A8 Pass (~375px; `min-w-0` + grid charts)
- [x] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

**T019 (2026-08-21) — resto além do progresso US1**: KPIs → charts (progresso + aderência + cobertura + gaps empty via `_chart_block`) → checklist (drill 008) → CTAs header. Remediado: (V-C1) empty de aderência em `<h3>`/`<p>` ad hoc → sempre `_chart_block` + kinds D; (V-C2) cobertura só com `has_data` + heading externo → ambos os slots sempre via `_chart_block` (espelho structure T017); (V-C3) gaps com heading duplicado → título só via `_chart_block`; (V-C4) links emerald “Corrigir vínculos”/“Revisar cargos” → `button` secondary. Progresso US1 intacto. Chart.js 4.5.1. Chrome `_visao_toggle` → **T021**. Views/`cycle.py`/`stage.py` intocados. Sem ESCALATE; denylist intocada. Pytest ciclo_detail: 16 passed.

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

- [x] A1 Pass
- [x] A2 Pass (sem tendência/chart novo fora do catálogo; só `bar_grouped` via `_chart_block`)
- [x] A3 N/A (sem aderência / Triad)
- [x] A4 Pass (Top-N por \|gap\| no payload; resto omitido sem “Outros”)
- [x] A5 Pass (`badge_status` + CTAs `button` secondary)
- [x] A6 Pass (cards/`card.html` sem sombra; chrome perfil com tokens Freeze)
- [x] A7 Pass (empty do chart via kinds D; drill vínculo com `empty_state`)
- [x] A8 Pass (~375px; `min-w-0` + `.table-frame` overflow)
- [x] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

**T018 (2026-08-21)**: Orientação → KPIs → `_chart_block` (`bar_grouped`) → drill `.table-frame` → CTAs. Remediado: (V-P1) links emerald ad hoc (“Ver expectativas…” / “Ver detalhes…”) → `components/button.html` secondary; (V-P2) heading duplicado no slot do chart → título/insight só via `_chart_block`; (V-P3) bloco classificação ad hoc → `card.html` + CTA `button`; (V-P4) empty do gap com `empty_message` ad hoc → kinds D (`sem_dado` vínculo/lista vazia; `sem_nota` sem notas comparáveis) em `PersonalDashboardView._chart_gaps_competencia` (presentation-only). Chart.js 4.5.1; sem tendência/`visao=historico`. AuthZ / fórmulas / denylist intocados. Sem ESCALATE.

**T022 (2026-08-22) — sweep views presentation US2**: V-P4 fechado em `apps/dashboard/views.py` (`empty_kind_payload` no gap pessoal). Time/estrutura/aderência/admin: empty kinds D + insight gargalo já conformes (sem diff view adicional). `apps/cycles/views.py` / `apps/talent/views.py` intocados. Pytest T022: 13 passed. Denylist diff vazio.

---

## Chrome compartilhado (se auditoria exigir)

| Paths | Tasks |
|-------|-------|
| `templates/dashboard/_ciclo_selector.html`, `_visao_toggle.html` | T021 |

- [x] Canônicos only (`button` / tokens Freeze); sem ilha de estilo
- [x] ESCALATE se faltar token — N/A (tokens existentes suficientes)

Notas / violações:

**T021 (2026-08-22)**: `_visao_toggle.html` — `<a>` ad hoc (emerald-50/slate chip) → `components/button.html` (`outlined`/`secondary`, compacto); query via `{% querystring visao=None|historico %}`. `_ciclo_selector.html` — Pass (sem remediação: `form-control` + `button` secondary). Sem ESCALATE; denylist intocada. Pytest history_mode + ciclo_detail: 40 passed.

---

## Fechamento US2 (T023)

- [x] 7 superfícies A acima com A1–A9 Pass (ou N/A justificado) — SC-001
- [x] Personas Marina / Bruno / Ana amostradas nas superfícies A do mapa
- [x] SC-004 / SC-005 amostral (~375px; sem sombra/chip/cor ad hoc)
- [x] Diff denylist vazio (AuthZ / stage / approval / fórmulas / fora-inventário)
- [x] Contratos 009/012 **não** editados

**T023 (2026-08-22) — gate US2 / Category A 100%**:

| Gate | Evidência |
|------|-----------|
| SC-001 | 7 superfícies (admin, time, aderência, estrutura, matriz, ciclo detalhe, meu painel) + chrome T021 — todas A1–A9 Pass ou N/A documentado neste checklist |
| Personas | Marina: admin (1.1–1.3), ciclo detalhe (1.3), matriz (1.4). Bruno: time (2.1), aderência/estrutura (2.2), matriz (2.3). Ana: meu painel (3.1) |
| SC-004 | `min-w-0` em todas as superfícies A; `.table-frame` / canvas `15.5rem` em `_chart_block` + CSS; sem `max-w-5xl`/`max-w-6xl` no conteúdo A; pytest estático `test_t034_superficies_com_chart_usam_min_w0_e_canvas_css` **Pass** |
| SC-005 | Grep inventário A: 0× `shadow-` em cards/KPI; 0× barra fake `style="width"`; CTAs via `components/button.html`; tints emerald/amber/rose = paleta Freeze (checklist avisório ciclo, ninebox `_cell`) |
| Denylist | `git diff HEAD` vazio em `scope.py`, `stage.py`, `cycle.py`, `approval.py`, `adherence.py`, mixins; único diff view = `apps/dashboard/views.py` presentation-only (`empty_kind_payload` gap pessoal, T022) |
| 009/012 | Specs/contratos 009 e 012 **fora** do diff desta feature |

Pytest estático US2 (sem DB): 9 passed (`test_t034_*`, `test_t012_*`, `test_t037_*`, `test_nenhuma_rota_historico_nos_urlconfs`). Integração com DB pendente de ambiente local (PostgreSQL); cobertura documentada nas tasks T014–T022.
