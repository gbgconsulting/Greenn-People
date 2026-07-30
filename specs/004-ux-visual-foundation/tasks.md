# Tasks: Fundação Visual e UX Estável

**Input**: Design documents from `/specs/004-ux-visual-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Aceite principal = revisão guiada + checklist teclado ([quickstart.md](./quickstart.md)). Incluir **apenas** teste leve pytest-django do context processor de ciclo (US4) — seguro, sem schema change; sem TDD de templates.

**Organization**: Tasks agrupadas por user story para implementação e validação independentes. Scaffold de evidência **before** fica na Phase 2; US6 (P1 de aceite) fecha after + freeze após o polish das superfícies.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: User story (US1–US6); Setup/Foundational/Polish sem label de story
- Incluir caminhos de arquivo exatos nas descrições

## Path Conventions

Monólito Django: `config/`, `apps/<domain>/`, `templates/`, `static/`, `tests/`, `docs/` na raiz do repositório.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar superfície de trabalho e tooling CSS sem novas apps/models

- [X] T001 Confirmar scaffold de evidência e convenção de nomes em `specs/004-ux-visual-foundation/evidence/before-after/README.md` (IDs 01–07; arquivos `NN-*-before.png` / `NN-*-after.png`)
- [X] T002 [P] Confirmar dualidade tokens: fonte documental `docs/design-system.md` + CSS `static/src/input.css` (sem criar `DESIGN.md` na raiz; R2)
- [X] T003 [P] Confirmar pipeline Tailwind CLI: mudanças em `static/src/input.css` regeneram `static/css/tailwind.css` (script/comando do README do projeto)

**Checkpoint**: Equipe sabe onde capturar evidência, onde documentar tokens e como rebuildar CSS

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Baseline visual congelável — **before** das 7 telas-piloto antes de qualquer polish

**⚠️ CRITICAL**: Nenhum polish de user story deve começar antes das capturas before

- [X] T004 Capturar screenshots **before** (viewport ~1280px) das telas 01–07 em `specs/004-ux-visual-foundation/evidence/before-after/` conforme [quickstart.md](./quickstart.md) e conjunto A ([research.md](./research.md) R6): shell admin, team, pessoal, login, ciclos, PDI detail, avaliações list
- [X] T005 Atualizar tabela de status em `specs/004-ux-visual-foundation/evidence/before-after/README.md` marcando befores capturados (after ainda pendente)
- [X] T006 Confirmar baseline = UI operacional atual (sem rebase/merge do WIP Impeccable OUT) antes de editar templates

**Checkpoint**: Before completo — polish scoped por superfície pode começar

---

## Phase 3: User Story 1 — Marina encontra Governança em segundos no shell (Priority: P1) 🎯 MVP

**Goal**: Administração com progressive disclosure Governança / Cadastros / Sistema; Ciclos e Aderência com destaque perceptível; URLs e permissões intactas

**Independent Test**: Admin autenticado → sidebar Administração mostra três grupos; Ciclos/Aderência mais destacados que Cadastros; cliques levam às mesmas superfícies ([contracts/admin-nav-grouping.md](./contracts/admin-nav-grouping.md); SC-001)

### Implementation for User Story 1

- [X] T007 [US1] Reorganizar o bloco `{% if user.is_admin %}` em `templates/components/nav_menu.html` em subgrupos Governança / Cadastros / Sistema conforme [contracts/admin-nav-grouping.md](./contracts/admin-nav-grouping.md) (URLs `{% url %}` existentes; preservar lógica Estrutura/Matriz já condicionada)
- [X] T008 [US1] Aplicar classes de destaque documentáveis (peso/ordem/ênfase) a Ciclos e Aderência vs. itens de Cadastros em `templates/components/nav_menu.html` (FR-004)
- [X] T009 [US1] Verificar que `templates/components/sidebar.html` (desktop + drawer mobile) continua incluindo o mesmo `nav_menu` sem regressão de seções Colaborador/Líder/Gerente
- [X] T010 [US1] Capturar `01-shell-admin-after.png` e anotar 1–3 bullets objetivos em `specs/004-ux-visual-foundation/evidence/before-after/README.md`

**Checkpoint**: US1 independentemente aceitável (MVP shell)

---

## Phase 4: User Story 2 — Líder faz scan de status do time em menos de 5 segundos (Priority: P1)

**Goal**: Hierarquia tipográfica/espacial/badges nos KPIs **já existentes** no dashboard time + espelho de clareza no painel pessoal; sem novos gráficos/métricas/cálculos

**Independent Test**: Líder com ciclo/dados → `/dashboard/team/` status operacional legível no first viewport (< 5 s revisão guiada); colaborador em `/` com clareza equivalente sem expor 9-box indevida (SC-002; R5)

### Implementation for User Story 2

- [X] T011 [P] [US2] Reordenar/agrupar first viewport e hierarquia (títulos, badges, indicadores existentes) em `templates/dashboard/team.html` e `templates/dashboard/team_list_partial.html` sem novos KPIs/queries agregadas
- [X] T012 [P] [US2] Aplicar espelho de clareza (tipografia/espaçamento/badges existentes) em `templates/dashboard/personal.html`
- [X] T013 [P] [US2] Polish leve de hierarquia (sem novos KPIs) em `templates/dashboard/admin.html` e `templates/dashboard/structure.html` (FR-002; fora do conjunto A de evidência se tempo limitado — clareza scoped)
- [X] T014 [US2] Garantir empty states acionáveis via `templates/components/empty_state.html` onde listas/KPIs vazios já se aplicam nos dashboards-piloto (sem inventar dados)
- [X] T015 [US2] Capturar `02-dashboard-team-after.png` e `03-dashboard-pessoal-after.png` + bullets em `specs/004-ux-visual-foundation/evidence/before-after/README.md`

**Checkpoint**: US2 independentemente aceitável no scan de liderança/colaborador

---

## Phase 5: User Story 3 — Colaborador percorre autoatendimento com padrões consistentes (Priority: P2)

**Goal**: Tipografia, espaçamento, botões, badges, empty states e tabelas alinhados ao visual incumbente em login / ciclos / PDI / avaliações; HTMX preservado

**Independent Test**: Percurso login → pessoal → PDI detail → avaliações list; empty states claros; ações HTMX atualizam as mesmas regiões ([contracts/htmx-pilot-surfaces.md](./contracts/htmx-pilot-surfaces.md); SC-005)

### Implementation for User Story 3

- [X] T016 [P] [US3] Alinhar tipografia/espaçamento/form ao design system em `templates/accounts/login.html` (e `templates/accounts/base_auth.html` se necessário para consistência sem redesign de marca)
- [X] T017 [P] [US3] Polish hierarquia lista/empty em `templates/cycles/ciclo_list.html` e `templates/cycles/ciclo_list_partial.html` preservando `hx-target` / `#list-container` / paginação
- [X] T018 [P] [US3] Polish badges/ações/empty em `templates/pdi/pdi_detail.html` e partials (`templates/pdi/partials/`, `templates/pdi/acao_list_partial.html`) preservando `hx-target="#modal-container"` e indicadores
- [X] T019 [P] [US3] Polish scan/empty em `templates/reviews/avaliacao_list.html` e `templates/reviews/avaliacao_list_partial.html` preservando contratos HTMX de lista
- [ ] T020 [US3] Unificar uso de `templates/components/button.html`, `input.html`, `badge_status.html`, `empty_state.html`, `card.html` nas superfícies-piloto tocadas (evitar ilhas de estilo)
- [ ] T021 [US3] Claridade de apresentação (sem interação nova) em `templates/talent/matrix.html` se tocado no escopo FR-002 — **não** adicionar drag/drawer/edição (FR-017)
- [ ] T022 [US3] Smoke manual HTMX: abrir modal PDI + paginar/filtrar lista piloto → região esperada atualiza; anotar ok no README de evidência se houver dúvida
- [ ] T023 [US3] Capturar after 04–07 (`04-login-after.png`, `05-lista-ciclos-after.png`, `06-pdi-detail-after.png`, `07-avaliacoes-list-after.png`) + bullets em `specs/004-ux-visual-foundation/evidence/before-after/README.md`

**Checkpoint**: US3 independentemente aceitável (consistência + HTMX intacto)

---

## Phase 6: User Story 4 — Topbar com contexto operacional mínimo (Priority: P2)

**Goal**: Topbar mostra ciclo aberto (nome) ou fallback “Sem ciclo aberto” via context processor + `get_open_ciclo()`; sem filtros/CTAs novos

**Independent Test**: Sessão auth com ciclo aberto → linha na topbar; sem ciclo aberto → fallback; densidade em uma linha ([contracts/topbar-cycle-context.md](./contracts/topbar-cycle-context.md))

### Tests for User Story 4

- [ ] T024 [P] [US4] Criar teste leve em `tests/test_topbar_ciclo_context.py`: context processor retorna ciclo quando `status=ABERTO` e ausente/None quando não há ciclo (reutilizar fixtures de `tests/conftest.py`)

### Implementation for User Story 4

- [ ] T025 [US4] Criar `apps/core/context_processors.py` com processor (ex.: `ciclo_aberto`) chamando `apps.goals.forms.get_open_ciclo` — só leitura; anônimo sem bloco de ciclo
- [ ] T026 [US4] Registrar o processor em `TEMPLATES['OPTIONS']['context_processors']` em `config/settings/base.py`
- [ ] T027 [US4] Renderizar contexto mínimo + fallback em `templates/components/topbar.html` (uma linha; truncar no mobile com `title` se preciso; sem filtros/listas/CTAs)
- [ ] T028 [US4] Garantir que `tests/test_topbar_ciclo_context.py` passa (`pytest tests/test_topbar_ciclo_context.py`)

**Checkpoint**: US4 independentemente aceitável em qualquer página autenticada com shell

---

## Phase 7: User Story 5 — Acessibilidade mínima do shell e modal (Priority: P2)

**Goal**: Skip link, `aria-current`, focus-visible, focus trap no modal, indicador HTMX anunciável — sem libs a11y novas

**Independent Test**: Checklist teclado SC-004 em [quickstart.md](./quickstart.md) + [contracts/a11y-shell.md](./contracts/a11y-shell.md)

### Implementation for User Story 5

- [ ] T029 [US5] Adicionar skip link “Ir para o conteúdo” → `#main-content` no início do `body` e id no `<main>` em `templates/base.html` (visível no foco)
- [ ] T030 [P] [US5] Marcar item ativo com `aria-current="page"` além das classes visuais em `templates/components/nav_menu.html`
- [ ] T031 [P] [US5] Adicionar regras `:focus-visible` (anel coerente com tokens) em `static/src/input.css` e regenerar `static/css/tailwind.css`
- [ ] T032 [US5] Implementar focus trap Tab/Shift+Tab no dialog aberto em `static/js/modal.js` (manter Escape + restore no trigger já existentes)
- [ ] T033 [US5] Ajustar `templates/components/htmx_indicator.html` (e hook mínimo em `templates/base.html` se necessário) para estado “Carregando…” anunciável quando `.htmx-request` — não manter `aria-hidden="true"` permanente anulando `role="status"`

**Checkpoint**: SC-004 checklist teclado passa

---

## Phase 8: User Story 6 — Congelar tokens e padrões após before/after (Priority: P1)

**Goal**: Documentar tokens/padrões alinhados ao incumbente; 5–8 pares before/after aceitos; declaração Freeze; verificar OUT

**Independent Test**: Revisar `docs/design-system.md` (Freeze), evidência 01–07, ausência de itens OUT (SC-003, SC-006, SC-007)

### Implementation for User Story 6

- [ ] T034 [US6] Expandir `docs/design-system.md` com hierarquia do shell Admin, badges, empty states, KPI/cards, focus-visible e padrões de botão/form usados nos componentes
- [ ] T035 [US6] Alinhar comentários/tokens em `static/src/input.css` com a doc na mesma entrega (evitar docs↔CSS divergentes)
- [ ] T036 [US6] Completar/revisar todos os pares after + bullets objetivos em `specs/004-ux-visual-foundation/evidence/before-after/README.md` (7 pares; ≥1 dashboard + ≥1 autoatendimento)
- [ ] T037 [US6] Declarar seção **Freeze** explícita em `docs/design-system.md` (fonte da verdade para features seguintes de gráficos / 9-box interativa)
- [ ] T038 [US6] Checklist OUT em evidência/README ou nota na feature: zero gráficos novos, zero 9-box interativa, zero dependência Impeccable (FR-017 / SC-007)

**Checkpoint**: Fundação documentada e congelada

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validação guiada ponta a ponta e higiene final

- [ ] T039 Percorrer validação por user story e checklist teclado em `specs/004-ux-visual-foundation/quickstart.md` (SC-001–SC-007)
- [ ] T040 [P] Revisar que nenhuma migration/models novos foram introduzidos (`apps/**/migrations/`, models) e que escopo UI não alterou autorização (FR-014)
- [ ] T041 Remover classes/markup morto introduzido só como experimento no polish dos templates-piloto tocados

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências
- **Foundational (Phase 2)**: Depende do Setup — **bloqueia** polish até befores capturados
- **US1 (Phase 3)**: Após Phase 2 — MVP
- **US2 (Phase 4)**: Após Phase 2; independente de US1 (mesmos tokens visuais)
- **US3 (Phase 5)**: Após Phase 2; beneficia-se de tokens descobertos em US1–US2, mas testável sozinha
- **US4 (Phase 6)**: Após Phase 2; independente de US1–US3 (arquivos distintos: core + topbar)
- **US5 (Phase 7)**: Após Phase 2; acoplamento leve com `nav_menu.html` (US1) — preferir após US1 para evitar conflito de merge no mesmo arquivo
- **US6 (Phase 8)**: After shots parciais ocorrem nas fases US1–US3; Freeze e fechamento de evidência **após** polish desejado (idealmente pós-US5)
- **Polish (Phase 9)**: Após stories desejadas

### User Story Dependencies

- **US1 (P1)**: Após Phase 2 — sem dependência de outras stories — 🎯 MVP
- **US2 (P1)**: Após Phase 2 — independente de US1
- **US3 (P2)**: Após Phase 2 — independente; preservar HTMX
- **US4 (P2)**: Após Phase 2 — independente (processor + topbar)
- **US5 (P2)**: Após Phase 2; sequenciar após US1 se mesmo `nav_menu.html`
- **US6 (P1 aceite)**: Scaffold before na Phase 2; fechamento Freeze na Phase 8 após superfícies polishadas

### Within Each User Story

- Evidence after da superfície logo após o polish daquela superfície
- US4: teste leve do processor antes/junto da implementação (T024 → T025–T028)
- Sem migrations; sem endpoints REST novos

### Parallel Opportunities

- T002 ∥ T003 (Setup)
- T011 ∥ T012 ∥ T013 (US2 dashboards distintos)
- T016 ∥ T017 ∥ T018 ∥ T019 (US3 templates distintos)
- T024 ∥ preparação de settings (depois serializar registro + topbar)
- T030 ∥ T031 (aria-current vs CSS)
- US1 ∥ US2 ∥ US4 em paralelo após Phase 2 se equipe > 1 (cuidado: US5 vs US1 no mesmo `nav_menu.html`)

---

## Parallel Example: User Story 2

```bash
# Dashboards em paralelo (arquivos diferentes):
Task: "Hierarquia em templates/dashboard/team.html + team_list_partial.html"
Task: "Clareza em templates/dashboard/personal.html"
Task: "Polish leve em templates/dashboard/admin.html + structure.html"
```

## Parallel Example: User Story 3

```bash
# Telas-piloto de autoatendimento em paralelo:
Task: "Polish templates/accounts/login.html"
Task: "Polish templates/cycles/ciclo_list*.html"
Task: "Polish templates/pdi/pdi_detail.html + partials"
Task: "Polish templates/reviews/avaliacao_list*.html"
```

## Parallel Example: User Story 4 + Setup CSS

```bash
# Após Phase 2, em paralelo com US1/US2:
Task: "tests/test_topbar_ciclo_context.py + apps/core/context_processors.py"
# Depois serial: settings → topbar.html → pytest verde
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational (befores) — CRITICAL
3. Phase 3 US1 (nav Admin)
4. **STOP e VALIDAR**: SC-001 + after 01
5. Demo shell reorganizado

### Incremental Delivery

1. Setup + Foundational → baseline before
2. US1 → MVP shell
3. US2 → scan dashboards
4. US3 → consistência autoatendimento + HTMX check
5. US4 → topbar ciclo
6. US5 → a11y shell/modal
7. US6 → Freeze + evidência completa
8. Polish → quickstart SC-001–007

### Parallel Team Strategy

1. Todos: Phase 1–2 (captura before)
2. Dev A: US1 → depois US5 (nav/a11y no shell)
3. Dev B: US2 → US3 (dashboards + autoatendimento)
4. Dev C: US4 (processor + topbar + pytest)
5. Todos: US6 Freeze + evidência + quickstart

---

## Notes

- [P] = arquivos diferentes, sem dependência de tarefa incompleta
- Zero models/migrations/APIs REST nesta feature
- Uma superfície/padrão por vez (FR-016); não redesenhar dezenas de templates fora do piloto
- OUT: gráficos novos, 9-box interativa, SPA/DRF, Impeccable, landing marketing
- Commit após cada tarefa ou grupo lógico (quando o usuário pedir commits)
