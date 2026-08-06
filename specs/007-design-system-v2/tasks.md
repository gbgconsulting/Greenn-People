# Tasks: Design System v2 — Polish Visual

**Input**: Design documents from `/specs/007-design-system-v2/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Não solicitados na spec (aceite = revisão before/after + checklist OUT + smoke 005/006). Sem tasks TDD.

**Organization**: Tasks agrupadas por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US5 conforme spec.md
- Paths absolutos relativos à raiz do repositório

## Path Conventions

Monólito Django na raiz: `templates/`, `static/`, `docs/`, `apps/` (última allowlist: **não** editar serviços/models/views de negócio).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar baseline de evidência e confirmar allowlist antes de qualquer alteração visual

- [X] T001 Confirmar scaffold de evidência e convenção de nomes em `specs/007-design-system-v2/evidence/before-after/README.md` (pilotos 01–08; login só como prova de isolamento)
- [X] T002 Capturar screenshots **before** dos 5–8 pilotos autenticados em `specs/007-design-system-v2/evidence/before-after/` (`NN-<slug>-before.png` para dashboard-admin-charts, dashboard-team, dashboard-pessoal, talent-matrix, lista-ciclos, pdi-detail; opcionais avaliacoes-list / shell-chrome)
- [X] T003 [P] Capturar prova de isolamento login em `specs/007-design-system-v2/evidence/before-after/login-unchanged-before.png` (não conta para SC-001)
- [X] T004 [P] Registrar allowlist/deny list de paths (plan + research R4) como referência de implementação: permitido `docs/design-system.md`, `static/src/input.css`, `static/fonts/*`, `static/css/tailwind.css`, `templates/base.html`, `templates/components/{button,card,empty_state,badge_status,sidebar,topbar}.html`, pilotos listados no plan; **proibido** `templates/accounts/base_auth.html`, `templates/accounts/login.html`, `apps/*/services`, models, migrations, urls/views de negócio → `contracts/path-allowlist.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fontes self-host + tokens + `.app-shell` + draft Freeze — base bloqueante para todas as stories

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [X] T005 Adicionar WOFF2 self-hosted **Fraunces** (display) e **Source Sans 3** (UI) em `static/fonts/` (InterVariable.woff2 permanece; licenças OFL)
- [X] T006 Declarar `@font-face` + tokens `--font-display` / `--font-ui` e utilitários `font-display` / `font-ui` em `static/src/input.css` **sem** alterar `--font-sans` Inter nem `@apply font-sans` do `body` global (contracts/auth-surface-isolation.md + freeze-v2.md)
- [X] T007 Escopar tipografia UI v2 sob `.app-shell` em `static/src/input.css` (ex.: `.app-shell { font-family: var(--font-ui), … }`)
- [X] T008 Adicionar classe `app-shell` no `<body>` de `templates/base.html` apenas (não tocar auth)
- [X] T009 Rebuild Tailwind: `tailwindcss -i static/src/input.css -o static/css/tailwind.css` gerando `static/css/tailwind.css`
- [X] T010 Rascunhar seção tipografia Freeze v2 (status Draft → caminho para Freeze v2) em `docs/design-system.md`: Fraunces display + Source Sans 3 UI; Inter global/auth; isolamento `.app-shell` (contracts/freeze-v2.md)
- [X] T011 Verificar isolamento auth: `git diff templates/accounts/base_auth.html templates/accounts/login.html` vazio; login sem classe `app-shell` e tipografia efetiva Inter

**Checkpoint**: Foundation pronta — tokens e isolamento comprováveis; stories podem iniciar

---

## Phase 3: User Story 1 — Tipografia e tokens v2 no app autenticado (Priority: P1) 🎯 MVP

**Goal**: Hierarquia tipográfica display vs UI perceptível nas superfícies piloto autenticadas; login intacto; doc tipográfica acionável

**Independent Test**: Comparar before/after em ≥3 pilotos (admin, team, lista); hierarquia display/UI; login/`base_auth` inalterados (quickstart §1)

### Implementation for User Story 1

- [X] T012 [P] [US1] Aplicar `font-display` em títulos de página / headlines de KPI em `templates/dashboard/admin.html`
- [X] T013 [P] [US1] Aplicar tipografia v2 (display títulos / UI corpo) em `templates/dashboard/team.html`
- [X] T014 [P] [US1] Aplicar tipografia v2 em `templates/dashboard/personal.html`
- [X] T015 [P] [US1] Aplicar tipografia v2 em títulos/labels de `templates/cycles/ciclo_list.html` e `templates/cycles/ciclo_list_partial.html`
- [X] T016 [P] [US1] Aplicar tipografia v2 em `templates/pdi/pdi_detail.html` e/ou `templates/pdi/pdi_form.html`
- [X] T017 [US1] Completar documentação da escala tipográfica (pesos, usos display vs UI, tokens) em `docs/design-system.md` alinhada a `static/src/input.css`
- [X] T018 [US1] Validar US1 via quickstart §1 (admin + team + lista + login inalterado + diff auth vazio)

**Checkpoint**: US1 testável de forma independente — tipografia v2 no autenticado, auth isolado

---

## Phase 4: User Story 2 — Botões, cards, KPI, table-frame e empty states (Priority: P2)

**Goal**: Componentes compartilhados com ritmo/densidade Freeze v2 nas superfícies piloto, mesmas variantes semânticas, sem novas ações de negócio

**Independent Test**: Percorrer dashboards + lista + form/detalhe; validar primary/secondary/outlined/loading, KPI/table-frame/empty; CTAs existentes funcionam (quickstart §2)

### Implementation for User Story 2

- [X] T019 [P] [US2] Refinar ritmo, pesos, hover/focus das variantes existentes em `templates/components/button.html` (primary/secondary/outlined/loading — sem novas variantes de negócio)
- [X] T020 [P] [US2] Refinar densidade/hierarquia KPI em `templates/components/card.html` (evitar cardificar excessivamente)
- [X] T021 [P] [US2] Refinar acabamento visual honest/acionável em `templates/components/empty_state.html`
- [X] T022 [P] [US2] Ajustar tipografia/densidade visual em `templates/components/badge_status.html` se necessário ao DS v2 (Status Triad hex intacto)
- [X] T023 [US2] Adicionar/refinar padrões **table-frame** (densidade, bordas, sombra mínima se preciso) em `static/src/input.css` e aplicá-los nas listas piloto `templates/cycles/ciclo_list.html` / `templates/cycles/ciclo_list_partial.html` (e `templates/reviews/avaliacao_list.html` se no conjunto de evidência)
- [X] T024 [US2] Garantir composição KPI/listas nos dashboards piloto (`templates/dashboard/admin.html`, `team.html`, `personal.html`) alinhada ao v2 sem markup de negócio novo
- [X] T025 [US2] Documentar botões, cards/KPI, table-frame e empty no Freeze em `docs/design-system.md`
- [X] T026 [US2] Rebuild `static/css/tailwind.css` após classes novas e validar US2 via quickstart §2

**Checkpoint**: US1 + US2 independentes — componentes refinados e documentados

---

## Phase 5: User Story 3 — Charts 005 com acabamento visual (Priority: P3)

**Goal**: Polish visual Chart.js options + bloco CSS; payloads/Status Triad/empty honesto intactos

**Independent Test**: Admin (e time) com/sem dados; polish perceptível; diff de negócio `apps/dashboard/` sem mudança de shape/endpoints (quickstart §3; contracts/chart-visual-polish.md)

### Implementation for User Story 3

- [X] T027 [US3] Refinar options visuais apenas em `static/js/dashboard_charts.js` (font family/size/weight eixos/legendas/tooltips apontando stack UI; grid sutil; `borderRadius`/`maxBarThickness`/cutout; tooltip chrome) — **sem** alterar shape JSON nem CDN Chart.js 4.5.1
- [X] T028 [P] [US3] Refinar markup visual do bloco (padding, radius, tipografia título/figcaption) em `templates/dashboard/_chart_block.html`
- [X] T029 [P] [US3] Ajustar altura/ritmo `.dashboard-chart-canvas` (e classes do bloco se preciso) em `static/src/input.css`
- [X] T030 [US3] Documentar seção **charts polish** em `docs/design-system.md` (options/CSS; sem novas métricas/libs)
- [X] T031 [US3] Rebuild `static/css/tailwind.css` se CSS mudou; smoke quickstart §3 + confirmar diff vazio de negócio em `apps/dashboard/chart_payloads.py`, views e `apps/dashboard/urls.py`

**Checkpoint**: Charts visualmente alinhados ao v2; contrato 005 preservado

---

## Phase 6: User Story 4 — Matriz 9-box alinhada ao DS v2 (Priority: P4)

**Goal**: Polish visual-only da grade, cards, drawer de domínio e feedback drag/empty; contratos 006 intactos

**Independent Test**: Happy path 006 (abrir, drawer, move potencial autorizado, empty); aparência v2; AuthZ/fórmulas/HTMX inalterados (quickstart §4; contracts/ninebox-visual-only.md)

### Implementation for User Story 4

- [ ] T032 [P] [US4] Refinar tipografia/densidade/bordas/empty da grade em `templates/talent/matrix.html` e `templates/talent/partials/_cell.html`
- [ ] T033 [P] [US4] Refinar person cards (classes/estados visuais) em `templates/talent/partials/_person_card.html`
- [ ] T034 [P] [US4] Refinar shell visual do drawer de domínio em `templates/talent/partials/_drawer.html` **sem** alterar atributos `hx-*` / targets `/ URLs de negócio
- [ ] T035 [US4] Refinar feedback visual de drag (opacity/ring/cursor) e ARIA de suporte em `static/js/ninebox_matrix.js` **sem** mudar handlers de POST, política potencial-only nem contratos 006
- [ ] T036 [US4] Documentar seção **ninebox polish** (visual-only; contratos 006 intactos) em `docs/design-system.md`
- [ ] T037 [US4] Validar US4 via quickstart §4; confirmar ausência de `templates/components/drawer.html` canônico novo e zero mudança em AuthZ/fórmulas

**Checkpoint**: Matriz polida; denylist 006 respeitada

---

## Phase 7: User Story 5 — Freeze v2 + evidência before/after + checklist OUT (Priority: P5)

**Goal**: Fechar Freeze v2 (doc↔CSS↔components), evidência 5–8 pilotos e checklist OUT completo

**Independent Test**: Doc declara Freeze v2; scan ≤10s/tela distingue ≥5 melhorias (nenhuma login); OUT 100% críticos (quickstart §5–6; contracts/out-checklist.md)

### Implementation for User Story 5

- [ ] T038 [US5] Fechar status **Freeze v2** em `docs/design-system.md` cobrindo tipografia, botões, cards/KPI, charts polish e ninebox polish (SC-004; contracts/freeze-v2.md) — dualidade alinhada a `static/src/input.css` e components tocados
- [ ] T039 [US5] Capturar `NN-<slug>-after.png` dos mesmos 5–8 pilotos em `specs/007-design-system-v2/evidence/before-after/`
- [ ] T040 [P] [US5] Capturar `login-unchanged-after.png` em `specs/007-design-system-v2/evidence/before-after/` e confirmar indistinguível do before
- [ ] T041 [US5] Preencher checklist OUT em `specs/007-design-system-v2/contracts/out-checklist.md` (OUT-LOGIN-*, OUT-005-*, OUT-006-*, OUT-NO-*, OUT-FREEZE-V2, OUT-EVIDENCE) com métodos e evidências
- [ ] T042 [US5] Revisar scan guiado (SC-001/SC-005): ≥5 superfícies com melhoria perceptível; tipografia citada em ≥3; atualizar notas no README de `specs/007-design-system-v2/evidence/before-after/` se útil
- [ ] T043 [US5] Scan final de escopo: sem libs front novas; sem rotas/models/migrations; `templates/accounts/*` intocados; grupos nav Governança/Cadastros/Sistema intactos

**Checkpoint**: Feature aceitável formalmente — Freeze v2 + evidência + OUT

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Shell leve opcional + validação ponta a ponta (não bloqueia MVP US1)

- [ ] T044 [P] Opcional após US1–US4: densidade/tipografia apenas em `templates/components/sidebar.html` e `templates/components/topbar.html` sob `.app-shell` — **sem** redesign de IA nav (FR-008); se feito, incluir piloto 08 shell-chrome na evidência
- [ ] T045 Rebuild final `static/css/tailwind.css` e executar validação completa de `specs/007-design-system-v2/quickstart.md` (seções 1–6)
- [ ] T046 Confirmar ausência de diffs em paths denylist (`templates/accounts/base_auth.html`, `templates/accounts/login.html`, `apps/*/services`, models, migrations) e fechar notas de aceite no checklist OUT

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — capturar before o mais cedo possível
- **Foundational (Phase 2)**: Depende do Setup (T001–T004); **bloqueia** todas as user stories
- **US1 (Phase 3)**: Após Phase 2 — MVP
- **US2 (Phase 4)**: Após Phase 2; idealmente após US1 (consome tipografia nos components)
- **US3 (Phase 5)**: Após Phase 2; beneficia-se de US1/US2 (font-ui + empty)
- **US4 (Phase 6)**: Após Phase 2; beneficia-se de US1 tipografia
- **US5 (Phase 7)**: Após US1–US4 ( Freeze final + after shots + OUT)
- **Polish (Phase 8)**: Após stories desejadas; T044 opcional

### User Story Dependencies

- **US1 (P1)**: Só Foundational — sem dependência de outras stories
- **US2 (P2)**: Pode iniciar após Foundational; visualmente coerente se US1 tokens já aplicados
- **US3 (P3)**: Independente no código (`dashboard_charts.js` / `_chart_block`); melhor após tokens UI
- **US4 (P4)**: Independente no código (templates talent + `ninebox_matrix.js`); melhor após tipografia
- **US5 (P5)**: Depende das implementações anteriores para after + Freeze completo

### Within Each User Story

- Sem tasks de teste TDD
- Implementação → documentação Freeze da área → validação quickstart da story
- Rebuild Tailwind sempre que `input.css` ou classes novas entrarem

### Parallel Opportunities

- Phase 1: T003 ‖ T004
- Phase 2: T005 sequencial antes de T006–T009; T010 pode rascunhar em paralelo a T007/T008 após tokens definidos
- US1: T012–T016 em paralelo (templates distintos)
- US2: T019–T022 em paralelo (components distintos)
- US3: T028 ‖ T029 após/enquanto T027
- US4: T032–T034 em paralelo
- US5: T040 ‖ partes de T041 após after shots

---

## Parallel Example: User Story 1

```bash
# Templates piloto em paralelo (após Phase 2):
Task: "Aplicar font-display em templates/dashboard/admin.html"
Task: "Aplicar tipografia v2 em templates/dashboard/team.html"
Task: "Aplicar tipografia v2 em templates/dashboard/personal.html"
Task: "Aplicar tipografia v2 em templates/cycles/ciclo_list.html (+ partial)"
Task: "Aplicar tipografia v2 em templates/pdi/pdi_detail.html e/ou pdi_form.html"
```

## Parallel Example: User Story 2

```bash
Task: "Refinar templates/components/button.html"
Task: "Refinar templates/components/card.html"
Task: "Refinar templates/components/empty_state.html"
Task: "Ajustar templates/components/badge_status.html"
```

## Parallel Example: User Story 4

```bash
Task: "Refinar templates/talent/matrix.html + partials/_cell.html"
Task: "Refinar templates/talent/partials/_person_card.html"
Task: "Refinar templates/talent/partials/_drawer.html (visual-only)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup + before shots
2. Phase 2: Fontes + tokens + `.app-shell` + isolamento auth
3. Phase 3: Tipografia nos pilotos + doc
4. **STOP e VALIDAR** quickstart §1
5. Demo tipografia autenticada vs login intacto

### Incremental Delivery

1. Setup + Foundational → isolamento comprovável
2. US1 → MVP tipografia
3. US2 → components diários
4. US3 → charts polish
5. US4 → ninebox polish
6. US5 → Freeze v2 + evidência + OUT
7. Phase 8 → shell leve opcional + quickstart completo

### Parallel Team Strategy

1. Time fecha Phase 1–2 junto
2. Depois:
   - Dev A: US1 → US2
   - Dev B: US3 (charts)
   - Dev C: US4 (ninebox)
3. Todos convergem em US5 (Freeze + evidence + OUT)

---

## Notes

- [P] = arquivos distintos, sem dependência incompleta
- Labels [US1]–[US5] obrigatórios só nas fases de story
- Zero models/migrations/rotas/libs novas
- Login/`base_auth` = falha de aceite se tocados
- Aceite visual (não suite TDD)
- Commit por task ou grupo lógico; validar checkpoint antes da próxima prioridade
