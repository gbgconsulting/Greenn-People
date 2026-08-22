# Tasks: Conformidade visual das telas ao Freeze v2

**Input**: Design documents from `/specs/016-freeze-screen-conformity/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Sem TDD visual obrigatório. Regressão de domínio (stage/scope/reject) + aceite visual guiado em `quickstart.md`. Asserts novos só de presentation se a auditoria exigir — **sem** alterar asserts de domínio.

**Organization**: Tasks por user story. Sequência obrigatória do plan: Fundação → US1 (progresso) → US2 (Category A) → US3 (Category B + B1) → US4 (paginação) → Polish. MVP = US1 (+ gate de progresso estável).

## Escopo inválido (REJEITAR task/PR)

Qualquer task que toque o seguinte é **INVÁLIDA** (FR-002 / FR-014 / [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md)):

| Zona | Exemplos proibidos |
|------|--------------------|
| AuthZ / escopo | `get_visible_users`, `ScopedObjectMixin`, `apps/accounts/services/scope.py`, ampliar QS |
| Máquina de estados | `apps/cycles/services/stage.py` |
| Ciclo open/close | `apps/cycles/services/cycle.py`, views open/close |
| Aprovação / fórmulas | `approval.py`, mutators `evaluation.py`, `adherence.py` fórmula |
| Persistência | models, migrations |
| Shell / auth / Verdee | nav, shell, login, `base_auth`, Figma Verdee |
| Fora do inventário | expectativas, metas, PDI, avaliações colaborador, listas de ciclo, audit, notifications, `escala_*`, `cargo_competencia_form` |
| Freeze reopen | decisão visual nova além de B1; reabrir A/B/C/D; chart fora do catálogo; barra HTML fake |
| Stack | SPA, DRF, lib nova de gráfico, Chart.js ≠ 4.5.1 |

**Permitido** ([contracts/path-allowlist.md](./contracts/path-allowlist.md)): templates/partials allowlisted; componentes canônicos; B1 em `docs/design-system.md` (+ `input.css` se classe documentada); presentation-only em `chart_payloads.py` / `dashboard_charts.js` / `_chart_block` / context de views; `pagination.html` (fonte única US4); testes de superfície + regressão sem mudar regras.

**Teste de ouro**: desligar CSS/charts **não** muda AuthZ, etapa, aprovação, notas nem visible set. **ESCALATE / STOP** se faltar token/componente/chart no Freeze (exceto B1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US4 conforme spec.md
- Paths relativos à raiz do repositório; cada task cita path **allowlist**

## Path Conventions

Monólito Django na raiz. Allowlist completa em `specs/016-freeze-screen-conformity/contracts/path-allowlist.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar escopo allowlist/denylist e baseline Freeze antes de qualquer remediação

- [x] T001 Confirmar allowlist/denylist e inventário A/B fechados em `specs/016-freeze-screen-conformity/contracts/path-allowlist.md` e `specs/016-freeze-screen-conformity/contracts/non-goals-denylist.md` (só apresentação; denylist de domínio/Verdee/fora-inventário intocável)
- [x] T002 [P] Confirmar contrato B1 Table-frame listas em `specs/016-freeze-screen-conformity/contracts/table-frame-listas-b.md` alinhado a spec Clarifications B1 / FR-015–017 (caps `max-w-5xl`/`max-w-6xl`, form `max-w-lg`, `table-fixed`+colgroup, ações à direita sem `\|`)
- [x] T003 [P] Registrar baseline de componentes canônicos + Chart.js 4.5.1 em `templates/components/{button,input,card,badge_status,empty_state,pagination}.html`, `templates/dashboard/_chart_block.html`, `static/js/dashboard_charts.js` e `apps/dashboard/chart_payloads.py` (sem lib nova; sem tocar denylist)
  **DONE 2026-08-21**: Baseline em `contracts/canonical-components-baseline.md` — 6 includes + `_chart_block` + `dashboard_charts.js` + `chart_payloads.py` confirmados; Chart.js `@4.5.1` nas 6 superfícies com chart; denylist intocada.

**Checkpoint**: Escopo allowlist-only congelado; B1 e canônicos como referência de remediação

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Documentar B1 no DS + checklists de auditoria A/B — **bloqueia** US1–US4  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. Zero models/migrations/AuthZ/stage/approval. Sem reabrir Freeze A/B/C/D.

- [x] T004 Documentar seção **Table-frame · listas de cadastro (Category B / decisão B1)** em `docs/design-system.md` conforme checklist de `specs/016-freeze-screen-conformity/contracts/table-frame-listas-b.md` (FR-017 / SC-006; **somente** esta seção; A/B/C/D intactos)
  **DONE 2026-08-21**: Seção B1 no DS (caps, `table-fixed`+colgroup, ações à direita, A full-bleed, exemplo markup); checklist do contrato marcado; Freeze A/B/C/D intocados.
- [x] T005 [P] Se B1 exigir utilitário documentado, adicionar classe em `static/src/input.css` e rebuild `static/css/tailwind.css` na mesma entrega; caso contrário, confirmar que tokens Tailwind existentes (`max-w-5xl`/`max-w-6xl`/`table-fixed`) bastam — **ESCALATE** se precisar token ausente
  **DONE 2026-08-21**: Sem classe nova em `input.css` / sem rebuild. B1 (DS + contrato) consome só Tailwind padrão (`max-w-5xl`/`max-w-6xl`/`max-w-lg`/`table-fixed`/`mx-auto`/`w-full`/`text-right`/`w-[…]`) + `.table-frame` já existente. Confirmação em `contracts/table-frame-listas-b.md` § T005. Sem ESCALATE.
- [x] T006 Criar/atualizar checklist operacional de auditoria Category A (A1–A9) e Category B (B1–B9) espelhando `specs/016-freeze-screen-conformity/quickstart.md` para uso tela a tela nas fases US2/US3 (referência; sem editar contratos 009/012)
  **DONE 2026-08-21**: `checklists/category-a-audit.md` (A1–A9 × 7 telas) + `checklists/category-b-audit.md` (B1–B9 × entidades lista/form); quickstart aponta para ambos; contratos 009/012 intocados.

**Checkpoint**: DS + B1 prontos; checklists A/B utilizáveis; US1 pode auditar progresso Freeze A/D

---

## Phase 3: User Story 1 — Progresso do ciclo como visualização real (Priority: P1) 🎯 MVP

**Goal**: Painel admin e detalhe de ciclo mostram progresso por etapa como `bar_horizontal` Freeze (mono teal/cyan; amber só no gargalo); empty Freeze D honesto; zero barra fake  
**Independent Test**: Abrir admin + `cycles/<pk>/` com ciclo em andamento e sem dados; confirmar visual Freeze + ausência de markup ad hoc; counts/etapas com mesmo significado (quickstart § Admin 1.1–1.3; SC-003)

### Implementation for User Story 1

- [x] T007 [P] [US1] Auditar progresso em `templates/dashboard/admin.html` + payload `chart_ciclo_progresso` (view/`chart_payloads`) contra Freeze A/D e contratos 009/012 — registrar violações (fake markup, cor ad hoc, empty genérico, highlight fora do gargalo)
  **DONE 2026-08-21**: Auditoria admin progresso — ver notas em `checklists/category-a-audit.md` § A · Painel admin (US1). **Pass**: sem barra fake; `_chart_block` + `bar_horizontal` com ciclo; `highlight_max` → mono teal + amber só no pico (`chart_payloads` + testes); Chart.js 4.5.1; sem ciclo → `EMPTY_KIND_OPERACIONAL` via `_chart_ciclo_progresso(None)`. **Violações → T009/T011/(T012)**: (1) empty ad hoc zero avaliações (`'Ainda não há avaliações…'` ≠ `sem_dado`); (2) sem ciclo = `empty_state` solto fora de `_chart_block`; (3) `visao=historico` injeta `SEM_NOTA` em `chart_ciclo_progresso` (kind errado p/ pipeline); (4) polish: insight genérico / sem mini-KPI Total; (5) latente JS fallback Triad se `colors` ausente.
- [x] T008 [P] [US1] Auditar progresso em `templates/cycles/ciclo_detail.html` + context `CicloDetailView` espelho presentation — mesmas regras Freeze A/D; **sem** mutar `cycle.py` / `stage.py`
  **DONE 2026-08-21**: Auditoria ciclo_detail progresso — ver notas em `checklists/category-a-audit.md` § A · Ciclo (detalhe) (US1). **Pass**: sem barra fake; `_chart_block` + `bar_horizontal` sempre; `highlight_max` → mono teal + amber só no pico; Chart.js 4.5.1; empty sem série inventada; `visao=historico` mantém pipeline do `pk` (sem V-E3 do admin); sem empty solto “sem ciclo” (DetailView). **Violações → T010/T011/(T012)**: (1) empty ad hoc zero avaliações (`'Não há avaliações…'` ≠ `sem_dado`); (2) polish: insight genérico / sem mini-KPI Total; (3) latente JS fallback Triad (compartilhado). `cycle.py` / `stage.py` intocados.
- [x] T009 [US1] Remediar conformidade do bloco progresso em `templates/dashboard/admin.html` reusando `templates/dashboard/_chart_block.html` (`bar_horizontal`, `highlight_max`); remover qualquer residual ad hoc; empty via `empty_state` / kinds D
  **DONE 2026-08-21**: Progresso admin sempre via `_chart_block` (com/sem ciclo; empty kinds D). Removido `empty_state` solto “Sem ciclo aberto”. Com dados: mini-KPI `Total` + insight do gargalo (`ciclo_kpis.gargalo_label`); sem insight genérico. V-E1/V-E3 (payload) → T011; V-L1 (JS) → T012.
- [x] T010 [US1] Remediar conformidade do bloco progresso em `templates/cycles/ciclo_detail.html` (espelho presentation de admin); **sem** mudar semântica de counts/etapas
  **DONE 2026-08-21**: Progresso ciclo_detail espelho T009 — mini-KPI `Total` + insight do gargalo (`progresso_gargalo_label` presentation-only em `CicloDetailView`, mesmo critério `highlight_max`); sem insight genérico; empty via `_chart_block`. Counts/etapas intactos. V-E1 (empty kind) → T011; V-L1 → T012.
- [x] T011 [US1] Se auditoria exigir, ajustar só shape presentation em `apps/dashboard/chart_payloads.py` e/ou context em `apps/dashboard/views.py` / `apps/cycles/views.py` (`highlight_max`, `has_data`, `empty_kind`) — **proibido** alterar significado de negócio ou QS AuthZ
  **DONE 2026-08-21**: V-E1 admin + ciclo_detail — zero avaliações → `empty_kind_payload(EMPTY_KIND_SEM_DADO)` (copy canônica 012). V-E3 admin histórico — `chart_ciclo_progresso` → `SEM_DADO` (não polui pipeline com `sem_nota`); aderência permanece `SEM_NOTA`. Counts/QS AuthZ intactos; `chart_payloads` sem mudança de shape necessária.
- [x] T012 [US1] Se auditoria exigir, ajustar presentation-only em `static/js/dashboard_charts.js` e/ou `templates/dashboard/_chart_block.html` para mono + amber só no gargalo (Chart.js **4.5.1**; sem plugin npm)
  **DONE 2026-08-21**: V-L1 — `buildSingleSeriesConfig`: fallback sem `colors` = mono `COLOR_FINISH_TEAL` em bar/`bar_horizontal` (não `STATUS_TRIAD`); Triad só no doughnut. Amber no gargalo permanece via payload `highlight_max`. `_chart_block` intacto. Regressão fonte: `test_t012_dashboard_charts_bar_fallback_mono_not_triad`.
- [x] T013 [US1] Validar US1 via `specs/016-freeze-screen-conformity/quickstart.md` (Admin 1.1–1.3 + SC-003 ≤ 5 min/inspeção); confirmar denylist diff vazio em paths de domínio
  **DONE 2026-08-21**: Quickstart 1.1–1.3 + SC-003 **PASS**. (1.1) `?ciclo=11` → `bar_horizontal` via `_chart_block`, Chart.js 4.5.1, mono teal `#0d9488` + amber `#d97706` só no gargalo (Metas), mini-KPI Total + insight; sem barra fake. (1.2) sem ciclo aberto → empty operacional via `_chart_block` (sem série inventada); zero avaliações → copy `sem_dado` 012. (1.3) `/cycles/11/` espelho presentation. Pytest US1: 43 passed (`test_chart_payloads` highlight_max + `test_t012_…` + ciclo_detail + operational_default). **Denylist WT diff vazio** (`scope`/`stage`/`cycle`/`approval`/`evaluation`/`adherence`/`accounts`/`nav_menu`); mudanças US1 só allowlist (views presentation, templates progresso, `dashboard_charts.js`, testes, specs).

**Checkpoint**: US1 independentemente testável; gate de progresso estável antes de espalhar remediação A

---

## Phase 4: User Story 2 — Telas gerenciais Category A em conformidade plena (Priority: P1)

**Goal**: Inventário A (admin, time, aderência, estrutura, matriz, ciclo detalhe, meu painel) passa checklist excelente: KPI→visual→drill→ações; charts reais; badges/CTAs canônicos; sem sombra; ~375px sem bleed; full-bleed (sem cap B1)  
**Independent Test**: Percorrer inventário A com/sem dados; checklist A1–A9; viewport ~375px (quickstart Category A + personas)  
**Dependência**: Após US1 estável. Telas A (exceto progresso já fechado) podem paralelizar entre si.

### Implementation for User Story 2

- [x] T014 [P] [US2] Auditar + remediar painel admin (resto além do progresso US1) em `templates/dashboard/admin.html` — ordem KPI→visual→drill→ações; canônicos; sem sombra/chip ad hoc/cor fora da paleta
  **DONE 2026-08-21**: A1–A9 Pass (checklist admin). Empty aderência sempre via `_chart_block` (kinds D; sem `<p>` ad hoc); “Ver todos” → `button` secondary; slot aderência também no ramo sem ciclo. Progresso US1 intacto. Chrome `_visao_toggle` → T021. Pytest admin/dashboard surface: 48 passed. Denylist intocada.
- [x] T015 [P] [US2] Auditar + remediar painel do time em `templates/dashboard/team.html` + `templates/dashboard/team_list_partial.html` (drill **sem** `_chart_block` no partial HTMX; allowlist; denylist AuthZ intacta)
  **DONE 2026-08-21**: A1–A9 Pass (checklist time). Empty sem ciclo sempre via `_chart_block` (kinds D); drill operacional sempre após o visual; mini-KPI Total + insight com dados; partial sem `_chart_block`; link “Ver” slate no partial. Chrome `_visao_toggle` → T021. Pytest team/dashboard surface: 48 passed. Denylist AuthZ intocada.
- [x] T016 [P] [US2] Auditar + remediar aderência em `templates/dashboard/adherence.html` + `templates/dashboard/adherence_list_partial.html` — Status Triad (3 fatias) only; **sem** recalcular `adherence.py`
  **DONE 2026-08-21**: A1–A9 Pass (checklist aderência). Empty sem ciclo sempre via `_chart_block` (kinds D); drill operacional sempre após o visual; mini-KPI Líderes + insight Triad com dados; partial sem `_chart_block`; empty drill `sem_dado` 012. Doughnut 3 fatias via payload existente. Pytest dashboard surface: 91 passed. Denylist / `adherence.py` intocados.
- [x] T017 [P] [US2] Auditar + remediar estrutura em `templates/dashboard/structure.html` (cobertura ≠ aderência; composição painel gerencial Freeze)
  **DONE 2026-08-21**: A1–A9 Pass (checklist estrutura). Empty sem ciclo sempre via `_chart_block` (kinds D); charts cobertura área/cargo sempre após KPIs; drills (líderes + lacunas) sempre após o visual; tabelas `.table-frame`; cobertura ≠ Triad. Pytest structure surface: 15 passed (+ operational_default structure). Denylist / `structure.py` AuthZ intocados.
- [x] T018 [P] [US2] Auditar + remediar meu painel em `templates/dashboard/personal.html` (checklist A; sem tendência/chart novo fora do catálogo)
  **DONE 2026-08-21**: A1–A9 Pass (checklist meu painel). CTAs → `button` secondary; chart sempre `_chart_block` (`bar_grouped`); empty kinds D (`sem_dado`/`sem_nota`); classificação via `card.html`. Sem tendência nova. Pytest personal surface: 4 passed (+ gap unitários). Denylist intocada.
- [x] T019 [P] [US2] Auditar + remediar detalhe de ciclo (resto além do progresso US1) em `templates/cycles/ciclo_detail.html` contra managerial-panel / cycle-managerial-detail 009 (consumo only; **sem** editar contratos 009)
  **DONE 2026-08-21**: A1–A9 Pass (checklist ciclo detalhe). Empty aderência/cobertura sempre via `_chart_block` (kinds D); gaps sem heading duplicado; CTAs checklist → `button` secondary; Triad só no doughnut de aderência. Progresso US1 intacto. Chrome `_visao_toggle` → T021. Pytest ciclo_detail: 16 passed. Denylist / `cycle.py` / `stage.py` / contratos 009 intocados.
- [x] T020 [P] [US2] Auditar + remediar matriz em `templates/talent/matrix.html` + `templates/talent/partials/{_cell,_drawer,_person_card}.html` — polish Freeze only; **sem** AuthZ em `apps/talent/views.py` além de context presentation mínimo se necessário
  **DONE 2026-08-22**: A1–A9 Pass (checklist matriz). Remediado: (V-M1) link emerald “Abrir classificação clássica” → `button` secondary (`data-drawer-classify-fallback` intacto); (V-M2) “Fechar” ad hoc → `button` secondary compacto (`data-drawer-close` intacto); (V-M3) `min-w-0` em filtros/grade/drawer (A8). Pass: ninebox consome DS v2 (`table-frame`, `empty_state`, `badge_status`, `.form-control`, tints emerald/rose documentados); sem chart fake; sem cap B1. `_cell`/`_person_card` já conformes (007). Views/AuthZ intocados. Pytest matrix: `test_talent_matrix_authz.py` (+ surface T020). Denylist intocada.
- [x] T021 [P] [US2] Polish chrome compartilhado A se auditoria exigir em `templates/dashboard/_ciclo_selector.html` e/ou `templates/dashboard/_visao_toggle.html` (canônicos only; ESCALATE se faltar token)
  **DONE 2026-08-22**: `_visao_toggle.html` — links ad hoc (`bg-emerald-50` / `border-line` / `bg-surface-card`) → `components/button.html` (`outlined` ativo, `secondary` inativo, compacto `!h-auto px-3 py-1.5`); URLs via `{% querystring %}` (preserva ciclo/ciclos/q). `_ciclo_selector.html` — Pass (já `form-control` + `button` secondary). Sem ESCALATE; denylist intocada. Pytest history_mode + ciclo_detail: 40 passed.
- [x] T022 [US2] Se auditoria A exigir, ajustar context presentation only em `apps/dashboard/views.py` (e `apps/cycles/views.py` / `apps/talent/views.py` se tocados) — **proibido** mixins AuthZ / `scope.py` / fórmulas
  **DONE 2026-08-22**: Sweep US2 — time/estrutura/aderência/admin já conformes (empty kinds D + insight gargalo em `_chart_escopo_status`; T011 US1). Remediação T022: `PersonalDashboardView._chart_gaps_competencia` → `empty_kind_payload` (`sem_dado` vínculo/lista vazia; `sem_nota` sem notas). `apps/cycles/views.py` / `apps/talent/views.py` intocados (auditoria A sem violação view-level). Pytest T022: 13 passed (`test_dashboard_operational_default` time/structure/adherence/personal empty kinds). Denylist WT diff vazio.
- [x] T023 [US2] Validar inventário A completo via checklist A + `specs/016-freeze-screen-conformity/quickstart.md` (personas Marina/Bruno/Ana nas superfícies A; SC-001 / SC-004 / SC-005 amostral); ~375px sem scroll horizontal de página
  **DONE 2026-08-22**: Gate US2 fechado — 7 superfícies A + chrome T021 com A1–A9 Pass/N/A no [category-a-audit.md](./checklists/category-a-audit.md) § Fechamento; personas Marina/Bruno/Ana amostradas (quickstart § Validação por persona); SC-004/SC-005 via grep + pytest estático (`test_t034_superficies_com_chart_usam_min_w0_e_canvas_css`, partials HTMX sem chart, Chart.js 4.5.1); denylist domínio diff vazio; contratos 009/012 intocados. Checkpoint: Category A 100% — US3 pode iniciar B1.

**Checkpoint**: Category A 100% no checklist excelente; US3 pode começar B1 nas listas

---

## Phase 5: User Story 3 — Cadastros Category B limpos e funcionais (Priority: P2)

**Goal**: Áreas, Cargos, Usuários (+ pendentes), Competências — listas e forms — conformidade decente + B1 (cap, `table-fixed`+colgroup, ações à direita com separador leve); forms `max-w-lg`; zero KPI/chart indevido  
**Independent Test**: Abrir lista + form de cada entidade B; checklist B1–B9; confirmar cap lista ≠ form; ~375px scroll só no frame (quickstart Category B)  
**Dependência**: Fundação B1 (T004) concluída. Entidades B podem paralelizar entre si.

### Implementation for User Story 3

- [x] T024 [P] [US3] Remediar Áreas lista B1 em `templates/organization/area_list.html` + `templates/organization/area_list_partial.html` (`mx-auto w-full max-w-5xl`, `.table-frame`, `table-fixed`+colgroup ~40/25/15/20, ações `text-right` com `·`, sem `\|`)
- [x] T025 [P] [US3] Remediar Áreas form em `templates/organization/area_form.html` — manter `mx-auto max-w-lg`; card/inputs/botões canônicos; sem sombra; erros de validação Freeze-only
  **DONE 2026-08-22**: `area_form.html` — cap `mx-auto min-w-0 max-w-lg` (B8); card chrome (`border-line`/`bg-surface-card`, sem sombra) separado do `<form>`; `nome` via `components/input.html`; `parent` via `.form-control` + erro rose DS; checkbox/`button` canônicos; non-field/field errors Freeze-only (`rose-50`/`rose-600`). Views/forms.py intocados. Pytest DB indisponível no ambiente; lógica `AreaForm` inalterada.
- [x] T026 [P] [US3] Remediar Cargos lista B1 em `templates/organization/cargo_list.html` + `templates/organization/cargo_list_partial.html` (mesmo perfil 4 cols / `max-w-5xl`)
  **DONE 2026-08-22**: `cargo_list.html` — cap `mx-auto w-full max-w-5xl` (B2). `cargo_list_partial.html` — `.table-frame`, `table-fixed w-full` + colgroup ~40/25/15/20 (B3/B4); ações `text-right` com `·` (B5); `badge_status`/`empty_state`/`pagination` canônicos (B6); sem KPI/chart (B7 N/A); scroll no frame (B8). Views intocados.
- [x] T027 [P] [US3] Remediar Cargos form em `templates/organization/cargo_form.html` — `max-w-lg` + canônicos
  **DONE 2026-08-22**: `cargo_form.html` — cap `mx-auto min-w-0 max-w-lg` (B8); card chrome (`border-line`/`bg-surface-card`, sem sombra) separado do `<form>`; `nome`/`nivel` via `components/input.html` (`type="number"` + `min="1"`); checkbox/`button` canônicos; non-field/field errors Freeze-only (`rose-50`/`rose-600`). Views/forms.py intocados.
- [x] T028 [P] [US3] Remediar Usuários lista B1 em `templates/organization/user_list.html` + `templates/organization/user_list_partial.html` (`max-w-6xl`, 7 cols, ações ~12–15% à direita)
  **DONE 2026-08-22**: `user_list.html` — cap `mx-auto w-full max-w-6xl` (B2). `user_list_partial.html` — `.table-frame`, `table-fixed w-full` + colgroup 19/19/12/12/11/12/15 (nome+email maiores; ações 15% à direita, B3/B4); ações `text-right` com `·` (B5); `badge_status`/`empty_state`/`pagination` canônicos (B6); sem KPI/chart (B7 N/A); scroll no frame (B8). Views intocados.
- [x] T029 [P] [US3] Remediar Usuários form em `templates/organization/user_form.html` — `max-w-lg` + canônicos
  **DONE 2026-08-22**: `user_form.html` — cap `mx-auto min-w-0 max-w-lg` (B8); card chrome (`border-line`/`bg-surface-card`, sem sombra) separado do `<form>`; `input.html` para `nome`/`data_entrada`; selects via `.form-control` + erros rose DS; aviso amber com CTA `button` secondary; checkbox/`button` canônicos; erros Freeze-only. Views/forms.py intocados.
- [x] T030 [P] [US3] Remediar Usuários pendentes (correlata CTA) em `templates/organization/user_pending_list.html` + `templates/organization/user_pending_list_partial.html` com regra B1 por nº de colunas
  **DONE 2026-08-22**: `user_pending_list.html` — cap `mx-auto w-full max-w-6xl` (B2, 6 cols >4); CTAs avisório/header via `button` secondary (B6); guidance `data-blocker-kind` preservado. `user_pending_list_partial.html` — `.table-frame`, `table-fixed w-full` + colgroup 19/19/12/12/18/15 (B3/B4); ações `text-right` (B5); `badge_status`/`empty_state`/`pagination` canônicos (B6); sem KPI/chart (B7 N/A); scroll no frame (B8). Views intocados.
- [x] T031 [P] [US3] Remediar Competências lista B1 em `templates/competencies/competencia_list.html` + `templates/competencies/competencia_list_partial.html` (`max-w-5xl`, 4 cols) — **não** tocar `escala_*` / `cargo_competencia_form`
  **DONE 2026-08-22**: `competencia_list.html` — cap `mx-auto w-full max-w-5xl` (B2). `competencia_list_partial.html` — `.table-frame`, `table-fixed w-full` + colgroup ~40/25/15/20 (B3/B4); ações `text-right` com `·` (B5); `empty_state`/`pagination`/`button` canônicos (B6); sem KPI/chart (B7 N/A); scroll no frame (B8). `escala_*` / `cargo_competencia_form` intocados. Views intocados.
- [x] T032 [P] [US3] Remediar Competências form em `templates/competencies/competencia_form.html` — `max-w-lg` + canônicos
  **DONE 2026-08-22**: `competencia_form.html` — cap `mx-auto min-w-0 max-w-lg` (B1/B8); card chrome (`border-line`/`bg-surface-card`, sem sombra) separado do `<form>`; `nome` via `components/input.html`; `descricao` textarea + `tipo`/`escala` selects via `.form-control` + erros rose DS; `button` primary/secondary canônicos; erros Freeze-only (`rose-50`/`rose-600`). Sem KPI/chart (B6). Views/forms.py intocados.
- [x] T033 [US3] Confirmar badges/empty/CTAs B via `templates/components/{badge_status,empty_state,button,input,card}.html` nas listas/forms remediadas — sem chip/botão solto; **proibido** mudar QS/AuthZ em `apps/organization/views.py` / `apps/competencies/views.py` (só context presentation se inevitável)
  **DONE 2026-08-22**: Sweep 9 listas + 5 forms remediados (T024–T032). **Pass**: `badge_status`/`empty_state`/`button`/`input`/`pagination` canônicos; forms com card chrome DS (`border-line`/`bg-surface-card`) + `.form-control` em selects/textarea; CTAs header/footer via `button.html`; ações de tabela = tipografia DS (B5, não Medium h-12). **Remediação T033**: chip solto “Admin” em `user_list_partial.html` → `badge_status` neutro. Views `apps/organization/views.py` / `apps/competencies/views.py`: diff vazio (QS/AuthZ intocados).
- [x] T034 [US3] Validar inventário B completo via checklist B + quickstart Admin 1.5 (SC-002 / SC-004 / SC-005); confirmar DS já documenta B1 (T004); confirmar **não** remediou listas de ciclo / audit / notifications
  **DONE 2026-08-22**: Gate US3 fechado — inventário B (Áreas/Cargos/Usuários+pendentes/Competências) B1–B9 Pass/N/A no [category-b-audit.md](./checklists/category-b-audit.md) § Fechamento; quickstart Admin 1.5 amostrado (caps B1, table-frame, canônicos); SC-002 **PASS**; SC-004/SC-005 amostral (forms `min-w-0`, scroll no frame, 0× `shadow-`/`\|` ad hoc); B9/DS B1 (T004) confirmado; ciclo/audit/notifications/`escala_*` **não** remediados; contratos 009/012 intocados; denylist WT diff vazio. Checkpoint: Category B 100% — US4 pode iniciar.

**Checkpoint**: Category B 100% decente + B1; US4 corrige paginação na fonte se ainda houver violação

---

## Phase 6: User Story 4 — Filtros e paginação na fonte única (Priority: P3)

**Goal**: Controles de busca/filtros/paginação nas telas B reutilizam padrão existente; correção de token **uma vez** em `pagination.html`  
**Independent Test**: Inspecionar `templates/components/pagination.html`; listas B pagináveis consomem o include; sem HTML paralelo (quickstart US4)

### Implementation for User Story 4

- [x] T035 [US4] Auditar `templates/components/pagination.html` contra Freeze (links Anterior/Próxima com classes ad hoc vs `button`/tokens) e remediar **somente** nesta fonte única
- [x] T036 [P] [US4] Confirmar reuso do include (sem segunda implementação) nas listas B allowlisted: `templates/organization/{area,cargo,user,user_pending}_list*.html` e `templates/competencies/competencia_list*.html`
- [x] T037 [P] [US4] Onde filtros/busca existirem nas listas B, garantir `input`/`.form-control` + `button` canônicos — **sem** criar componente novo de paginação/filtro
  **DONE 2026-08-22**: Auditoria das 10 superfícies allowlisted (5 entidades × lista+partial): `area_*`, `cargo_*`, `user_*`, `user_pending_*`, `competencia_*`. **N/A remediação** — 0× `<form role="search">`, 0× `type="search"`, 0× `<input>`/`<select>` de filtro nas listas B; views `AreaListView`/`CargoListView`/`UserListView`/`UserPendingListView`/`CompetenciaListView` sem query params de busca/filtro. Paginação consome `pagination.html` (T035/T036); `querystring` preserva filtros futuros sem componente novo. Referência canônica documentada: `auditlog_list.html` / `structure.html` (`.form-control` + `button.html`). Sem ESCALATE; denylist intocada.
- [x] T038 [US4] Validar US4 via quickstart § US4 (4.1–4.3); HTMX `#list-container` e canvas A intactos; SC-005 amostral na paginação
  **DONE 2026-08-22**: Gate US4 fechado — quickstart § US4 **PASS**.
  - **4.1**: Única fonte `templates/components/pagination.html`; Anterior/Próxima via `button.html` `secondary`; chrome `border-slate-200` / `text-slate-500` (tokens DS); 0× links ad hoc.
  - **4.2**: 5 partials B allowlisted (`area`/`cargo`/`user`/`user_pending`/`competencia_list_partial`) incluem o componente; shells `*_list.html` só embutem o partial; 0× HTML paralelo de paginação nas listas B (`Anterior`/`has_previous`/`page_obj` fora do include = vazio).
  - **4.3**: `hx_target="#list-container"` + `hx_swap="outerHTML"` na fonte; cada partial B abre com `<div id="list-container">`. Canvas A intacto: `_chart_block` + Chart.js 4.5.1 ficam **fora** dos partials HTMX (`adherence.html`/`team.html`/etc.); swap não toca charts.
  - **SC-005 amostral (paginação)**: 0× `shadow-` / chip / cor fora da paleta em `pagination.html`; CTAs só canônico `secondary` (sem sombra de card/KPI na fonte). Sem ESCALATE.
  Checkpoint: Uma fonte Freeze-compliant; B consome sem forks — Phase 7 (T039+) pode iniciar.

**Checkpoint**: Uma fonte de paginação Freeze-compliant; B consome sem forks

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Gates de aceite mensuráveis, regressão de domínio, confirmação de escopo

- [ ] T039 [P] Rodar regressão de domínio **sem** alterar asserts: `pytest tests/test_stage_machine.py tests/test_scope.py tests/test_reject_stage_invariant.py`
- [ ] T040 [P] Revisar diff final contra `specs/016-freeze-screen-conformity/contracts/path-allowlist.md` e `non-goals-denylist.md` — `scope.py` / stage / approval / fórmulas / models / migrations / nav / login = diff vazio
- [ ] T041 Executar aceite completo `specs/016-freeze-screen-conformity/quickstart.md` (gates SC-001…SC-006; personas; ~375px; ESCALATE documentado se houver gap Freeze)
- [ ] T042 Confirmar `docs/design-system.md` ganhou **somente** B1 (SC-006) e Chart.js permanece 4.5.1 nos templates A que carregam charts

**Checkpoint**: Feature pronta para `/speckit-implement` / PR — conformidade A+B+B1 sem reabrir domínio

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — começar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — **bloqueia** todas as user stories
- **US1 (Phase 3)**: Após Foundational — MVP / gate de progresso
- **US2 (Phase 4)**: Após US1 estável — telas A em paralelo entre si
- **US3 (Phase 5)**: Após Foundational (T004 B1); preferível após US2 se compartilhando revisão visual, mas independentemente testável
- **US4 (Phase 6)**: Após US3 ter listas B consumindo paginação (ou em paralelo fino se só tocar `pagination.html`)
- **Polish (Phase 7)**: Após stories desejadas

### User Story Dependencies

- **US1 (P1)**: Após Phase 2 — sem dependência de outras stories — 🎯 MVP
- **US2 (P1)**: Após US1 (gate progresso); telas A paralelizáveis
- **US3 (P2)**: Após T004 (doc B1); entidades B paralelizáveis; não inventa chart/KPI
- **US4 (P3)**: Correção na fonte `pagination.html`; B já deve referenciar o include

### Within Each User Story

- Auditoria antes de remediação na mesma superfície
- Presentation context/payload só se markup sozinho não fechar a violação
- ESCALATE / STOP se faltar token fora de B1
- Story completa e validável via quickstart antes da próxima prioridade (exceto paralelismo A/B documentado)

### Parallel Opportunities

- T002 ∥ T003 (Setup)
- T005 ∥ T006 após T004 iniciado (Foundational; T004 bloqueia consumo B1 em US3)
- T007 ∥ T008 (auditoria progresso admin ∥ ciclo_detail)
- T014…T021 (telas A) em paralelo após US1
- T024…T032 (entidades B lista/form) em paralelo após T004
- T036 ∥ T037 (US4)
- T039 ∥ T040 (Polish)

---

## Parallel Example: User Story 2

```bash
# Após US1 estável, lançar remediações A em arquivos distintos:
Task: "Auditar + remediar team.html + team_list_partial.html"
Task: "Auditar + remediar adherence.html + adherence_list_partial.html"
Task: "Auditar + remediar structure.html"
Task: "Auditar + remediar personal.html"
Task: "Auditar + remediar matrix.html + partials"
```

## Parallel Example: User Story 3

```bash
# Após T004 (B1 no DS), lançar entidades B em paralelo:
Task: "Remediar Áreas lista+form B1"
Task: "Remediar Cargos lista+form B1"
Task: "Remediar Usuários lista+form+pendentes B1"
Task: "Remediar Competências lista+form B1"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (B1 no DS + checklists) — CRITICAL
3. Complete Phase 3: US1 (progresso admin + ciclo_detail)
4. **STOP and VALIDATE**: quickstart 1.1–1.3 + SC-003
5. Prosseguir US2 só com gate de progresso estável

### Incremental Delivery

1. Setup + Foundational → base Freeze/B1 pronta
2. US1 → progresso real (MVP)
3. US2 → Category A excelente (SC-001)
4. US3 → Category B + B1 (SC-002)
5. US4 → paginação fonte única
6. Polish → regressão domínio + SC-001…SC-006

### Parallel Team Strategy

1. Time fecha Setup + Foundational juntos
2. Dev A: US1 → depois coordena gate
3. Após US1: Dev B/C paralelizam telas A (US2)
4. Após T004: Dev D paraleliza entidades B (US3)
5. US4: um dono de `pagination.html` + smoke nas listas B

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- Labels [US1]–[US4] mapeiam stories da spec
- Cada story é independentemente testável via quickstart
- Commit após cada task ou grupo lógico allowlist-safe
- Parar em qualquer checkpoint para validar
- Evitar: gold-plating fora do inventário; segunda paginação; unificar cap lista↔form; cap B1 em A; editar contratos 009/012
