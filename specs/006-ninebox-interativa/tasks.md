# Tasks: 9-box Interativa (Matriz de Talentos)

**Input**: Design documents from `/specs/006-ninebox-interativa/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Aceite principal = revisão guiada + [quickstart.md](./quickstart.md) (SC-001–007). Sem TDD obrigatório. Incluir testes pytest focados em AuthZ/escopo/IDOR (SC-003) e regressão `scripts/validate_t070.py` — sem suite ampla de contract tests HTMX.

**Organization**: Tasks agrupadas por user story (US1 drawer MVP → US2 drag → US3 read-only/a11y) para entrega fatiável (FR-014).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: User story (US1–US3); Setup/Foundational/Polish sem label de story
- Incluir caminhos de arquivo exatos nas descrições

## Path Conventions

Monólito Django: `apps/talent/`, `templates/talent/`, `static/js/`, `docs/`, `tests/` na raiz do repositório. Zero models/migrations.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar superfície de trabalho e criar esqueleto de arquivos (zero apps/models novos)

- [X] T001 Confirmar escopo de código: zero models/migrations; trabalho em `apps/talent/views.py`, `apps/talent/urls.py`, `apps/talent/services/classification.py`, `templates/talent/matrix.html`, `templates/talent/partials/`, `static/js/ninebox_matrix.js` e nota mínima em `docs/design-system.md` — conforme [plan.md](./plan.md) e [data-model.md](./data-model.md)
- [X] T002 [P] Criar diretório `templates/talent/partials/` e stubs vazios `_drawer.html`, `_cell.html`, `_person_card.html`
- [X] T003 [P] Criar esqueleto vazio `static/js/ninebox_matrix.js` (HTML5 DnD + init do drawer; ainda sem lógica completa)

**Checkpoint**: Superfície e stubs definidos

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Partials, builder de grade, serviço de toggle e rotas HTMX esqueleto — **bloqueia** todas as user stories

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase

- [X] T004 Extrair helper de layout da matriz (`_DESEMPENHO_ROWS`, `_POTENCIAL_COLS`, `_QUADRANTE_MEMBER`, builder de `matriz_rows`) de `apps/talent/views.py` para módulo reutilizável (ex.: `apps/talent/services/matrix_layout.py` ou funções no topo de `views.py`) consumível por full page e partials HTMX
- [X] T005 [P] Implementar `toggle_classification_visibility(classificacao, admin) -> ClassificacaoTalento` em `apps/talent/services/classification.py` (admin only / `PermissionDenied`); refatorar `ToggleVisibilityView` em `apps/talent/views.py` para chamar o serviço sem mudar semântica do redirect legado ([research.md](./research.md) R7)
- [X] T006 [P] Implementar partial `templates/talent/partials/_person_card.html` (nome/email, badge Visível/Oculto via `templates/components/badge_status.html`, data attrs para DnD futuro: `data-user-pk`, `data-potencial`, `data-desempenho`)
- [X] T007 [P] Implementar partial `templates/talent/partials/_cell.html` com id estável `#cell-{desempenho}-{potencial}`, rótulo textual de eixos/quadrante (além da cor) e slot de cards via `_person_card.html` — [contracts/a11y-matrix-drawer.md](./contracts/a11y-matrix-drawer.md)
- [X] T008 Refatorar `templates/talent/matrix.html` para compor a grade 3×3 com `_cell.html` / `_person_card.html`, incluir shell `#matrix-drawer` (vazio/placeholder), preservar filtros ciclo/área/cargo e consumir Freeze (`button`, `empty_state`, tokens) sem redesenhar shell/nav/topbar (FR-012)
- [X] T009 Registrar rotas HTMX esqueleto em `apps/talent/urls.py` (nomes internos, não API pública): `GET matrix/drawer/<user_pk>/`, `POST matrix/potencial/<user_pk>/`, `POST matrix/move/<user_pk>/` (+ reuso de `toggle_visibility` existente) conforme [contracts/htmx-drawer-partials.md](./contracts/htmx-drawer-partials.md) e [contracts/drag-persist.md](./contracts/drag-persist.md); views stub em `apps/talent/views.py` que ainda retornam placeholder/405 até US1/US2
- [X] T010 Incluir `{% static 'js/ninebox_matrix.js' %}` no `{% block extra_js %}` de `templates/talent/matrix.html` (não alterar `templates/base.html` além do já existente CSRF/HTMX)

**Checkpoint**: Foundation pronta — slices US1→US3 podem começar

---

## Phase 3: User Story 1 — Admin calibra potencial e visibilidade via drawer in-matrix (Priority: P1) 🎯 MVP

**Goal**: Drawer lateral in-matrix (HTMX) para inspecionar/salvar potencial e toggle `visivel_ao_colaborador`; grade atualiza sem full reload obrigatório; `classify` vira fallback (FR-013)

**Independent Test**: Admin autenticado + ciclo com classificações → abrir matriz, selecionar pessoa, alterar potencial e toggle no drawer; persistência + UI sem full reload; potencial inválido → erro PT-BR; não-admin POST → 403 ([contracts/htmx-drawer-partials.md](./contracts/htmx-drawer-partials.md), [contracts/authz-scope.md](./contracts/authz-scope.md); SC-001/004)

### Tests for User Story 1 (AuthZ / SC-003)

- [X] T011 [P] [US1] Adicionar testes pytest de escrita admin-only + IDOR (gerente POST potencial/toggle → 403; admin OK) em `tests/test_talent_matrix_authz.py` (ou equivalente) cobrindo novos endpoints e `upsert_classification` / `toggle_classification_visibility`

### Implementation for User Story 1

- [X] T012 [US1] Implementar partial `templates/talent/partials/_drawer.html` (write): identidade, área/cargo, desempenho (rótulo), select potencial 1–3, quadrante, badge Visível/Oculto, botões Salvar/Toggle via `templates/components/button.html` + `input`/`form-control`; link secundário “Abrir classificação clássica” → `talent:classify` (FR-013)
- [X] T013 [US1] Implementar view GET drawer em `apps/talent/views.py`: `RequiresManagerOrAdminMixin` + pessoa ∈ `get_visible_users`; retorna `_drawer.html` (modo write se `is_admin`); request não-HTMX → redirect `talent:matrix` ou 405 — [contracts/htmx-drawer-partials.md](./contracts/htmx-drawer-partials.md)
- [X] T014 [US1] Ligar abertura do drawer: cards em `_person_card.html` / `matrix.html` com `hx-get` → `#matrix-drawer` (`innerHTML`), propagando `ciclo` (e filtros relevantes) na query string
- [X] T015 [US1] Implementar POST salvar potencial HTMX em `apps/talent/views.py`: `RequiresAdminMixin` + `upsert_classification`; sucesso → partial drawer atualizado + refresh de células origem/destino (ou fragmento da grade) + `HX-Trigger` toast sucesso; erro validação/permissão → mensagem PT-BR sem sucesso silencioso (FR-005)
- [X] T016 [US1] Estender `ToggleVisibilityView` (ou action HTMX dedicada) em `apps/talent/views.py` para resposta HTMX usando `toggle_classification_visibility`: atualizar badge no drawer + card; manter redirect legado para request não-HTMX
- [X] T017 [US1] Garantir feedback honesto (loading via `#htmx-indicator` ou indicador local; erros PT-BR; estado anterior preservado em falha) na superfície drawer/grade em `templates/talent/` — SC-004
- [X] T018 [US1] Confirmar que `templates/talent/classify.html` + `ClassifyTalentView` permanecem intactos como fallback; caminho principal do admin = drawer (FR-013)

**Checkpoint**: MVP demonstrável só com US1 (FR-014 slice 1)

---

## Phase 4: User Story 2 — Admin reposiciona potencial por drag-and-drop na grade (Priority: P2)

**Goal**: HTML5 DnD potencial-only com snap (research R4), persistência via `upsert_classification`, revert on error; mobile degrada para drawer (FR-010)

**Independent Test**: Admin arrasta para coluna de potencial diferente → potencial/quadrante atualizam; drop em linha de desempenho incompatível → snap sem alterar desempenho; falha → revert + toast; não-admin sem handles e POST 403; mobile sem drag ([contracts/drag-persist.md](./contracts/drag-persist.md); SC-002/005)

### Implementation for User Story 2

- [X] T019 [US2] Implementar POST move em `apps/talent/views.py`: aceita `ciclo_id` + `potencial` (1–3); **ignora** desempenho da célula-alvo; chama `upsert_classification`; resposta posiciona card em `(desempenho_derivado, potencial_novo)`; noop se potencial inalterado; admin only — [contracts/drag-persist.md](./contracts/drag-persist.md)
- [X] T020 [US2] Implementar HTML5 DnD em `static/js/ninebox_matrix.js`: dragstart/drop entre células; POST move (HTMX ou fetch + CSRF); cancel Esc/fora da grade → zero POST + restore visual
- [X] T021 [US2] Aplicar política de snap: após drop, card termina em `(desempenho_derivado, P′)`; se célula sob cursor tinha desempenho diferente, feedback PT-BR explícito (“Só o potencial é alterado…”) via toast/`HX-Trigger` — research R4
- [X] T022 [US2] Em erro (403/400/rede/5xx): restaurar posição visual anterior + toast erro; **nunca** sucesso silencioso — SC-004
- [X] T023 [US2] Gates de UI: `draggable`/handles somente quando template renderiza `is_admin_viewer`; em `pointer: coarse` / viewport estreito desabilitar DnD e manter drawer como caminho completo (FR-010) em `static/js/ninebox_matrix.js` + `_person_card.html`
- [X] T024 [US2] Estender `tests/test_talent_matrix_authz.py` com casos move: não-admin 403; payload potencial-only não muta desempenho; snap coerente após POST admin

**Checkpoint**: US1 + US2 independentes; calibração por drag e por drawer

---

## Phase 5: User Story 3 — Gerente lê drawer read-only; a11y e estados honestos (Priority: P3)

**Goal**: Drawer somente leitura para não-admin; empty/loading honestos; teclado/foco no drawer; rótulos além da cor (FR-011)

**Independent Test**: Gerente abre matriz/drawer sem save/toggle; escopo respeitado; filtro vazio → empty; teclado Escape/foco; células com texto além da cor ([contracts/a11y-matrix-drawer.md](./contracts/a11y-matrix-drawer.md), [contracts/authz-scope.md](./contracts/authz-scope.md); SC-006)

### Implementation for User Story 3

- [ ] T025 [US3] Completar modo read-only em `templates/talent/partials/_drawer.html` + GET drawer: gerente vê identidade/desempenho/potencial/quadrante **sem** controles de salvar/toggle; POST direto continua 403 no backend (FR-006/008)
- [ ] T026 [US3] Empty/loading honestos em `templates/talent/matrix.html`: `templates/components/empty_state.html` quando zero classificados no filtro/escopo; indicador HTMX/`aria-busy` não confundido com empty definitivo (FR-005)
- [ ] T027 [US3] Implementar a11y do drawer em `static/js/ninebox_matrix.js` (espelhar padrões de `static/js/modal.js`): foco ao abrir, focus trap, Escape fecha, restore foco no card trigger — [contracts/a11y-matrix-drawer.md](./contracts/a11y-matrix-drawer.md)
- [ ] T028 [US3] Garantir rótulos textuais de eixos/quadrante em `_cell.html` / grade (já stubados na fundação) e nomes acessíveis em handles de drag quando presentes — SC-006
- [ ] T029 [US3] Verificar queryset da matriz e GET drawer: apenas `usuario__in=get_visible_users`; gerente não vê fora do escopo; líder puro continua 403 na matriz (research R8) — [contracts/authz-scope.md](./contracts/authz-scope.md)

**Checkpoint**: Todas as user stories independentemente funcionais

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentação Freeze mínima, regressões e validação quickstart

- [ ] T030 [P] Documentar padrão mínimo de drawer lateral (se canônico) e superfície `talent/matrix.html` + `ninebox_matrix.js` em `docs/design-system.md` — sem redesenhar marca/shell (FR-012 / research R10)
- [ ] T031 Confirmar gate colaborador intacto: default `visivel_ao_colaborador=False`; `/talent/mine/` via `get_visible_classification_for_collaborator` sem vazamento; fórmulas `derive_desempenho` / `calculate_quadrante` em `apps/talent/services/classification.py` **inalteradas** (SC-007)
- [ ] T032 [P] Rodar regressão `scripts/validate_t070.py` (líder puro 403 na matriz) e `pytest tests/test_talent_matrix_authz.py` (+ correlatos de escopo se existirem) — SC-003
- [ ] T033 Executar validação guiada [quickstart.md](./quickstart.md) slices 1–3 + checklist SC-001–007

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — começar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — **bloqueia** todas as user stories
- **User Stories (Phase 3+)**: Dependem da Foundational
  - Sequência recomendada: P1 → P2 → P3 (FR-014)
  - US2 depende semanticamente do mesmo upsert do US1, mas é testável sozinha após foundation + endpoint move
  - US3 refina drawer/a11y sobre a superfície do US1
- **Polish (Phase 6)**: Após as stories desejadas (mínimo US1 para MVP)

### User Story Dependencies

- **User Story 1 (P1)**: Após Foundational — sem dependência de outras stories — **MVP**
- **User Story 2 (P2)**: Após Foundational; reutiliza `upsert_classification` e partials de célula/card do foundation/US1
- **User Story 3 (P3)**: Após Foundational; idealmente após US1 (drawer já existe) para modo read-only/a11y

### Within Each User Story

- AuthZ tests (US1) podem ser escritos cedo e falhar até endpoints existirem
- Partials/views antes de wiring HTMX fino
- Feedback/erros antes de considerar a story completa
- Story completa antes de avançar prioridade (salvo paralelismo com staff)

### Parallel Opportunities

- T002/T003 em paralelo no Setup
- T005/T006/T007 em paralelo na Foundational (após T004 se o builder for compartilhado; T006/T007 podem seguir o contrato de ids mesmo antes)
- T011 em paralelo ao início da implementação US1
- T030/T032 em paralelo no Polish
- Com 2 devs após Foundational: Dev A = US1, Dev B prepara T019 stub + testes move (integra após US1 estável)

---

## Parallel Example: User Story 1

```bash
# Em paralelo (arquivos diferentes):
Task: "T011 — testes AuthZ em tests/test_talent_matrix_authz.py"
Task: "T012 — partial _drawer.html write"

# Sequencial depois:
Task: "T013 — GET drawer view"
Task: "T014 — hx-get nos cards"
Task: "T015 — POST potencial HTMX"
Task: "T016 — toggle HTMX"
```

---

## Parallel Example: User Story 2

```bash
# Sequencial servidor → cliente:
Task: "T019 — POST move em apps/talent/views.py"
Task: "T020 — DnD em static/js/ninebox_matrix.js"
Task: "T021 — snap + feedback"
Task: "T022 — revert on error"
# Em paralelo com polish de UI gates:
Task: "T023 — mobile/admin gates"
Task: "T024 — testes move AuthZ"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRITICAL)
3. Completar Phase 3: User Story 1
4. **STOP and VALIDATE**: quickstart Slice 1 / SC-001
5. Demo/calibração via drawer sem `classify` obrigatório

### Incremental Delivery

1. Setup + Foundational → foundation pronta
2. US1 drawer → MVP operacional (FR-014 slice 1)
3. US2 drag → calibração visual em lote (slice 2)
4. US3 read-only/a11y/empty → leitura gerente + SC-006 (slice 3)
5. Polish → design-system + quickstart SC-001–007

### Parallel Team Strategy

1. Time fecha Setup + Foundational junto
2. Após Foundational:
   - Dev A: US1 (drawer HTMX)
   - Dev B: stubs move + testes AuthZ (integra após T015 estável)
3. US3 após drawer base existir

---

## Notes

- **[P]** = arquivos diferentes, sem dependência de tarefa incompleta
- Label **[USx]** só nas phases de user story
- Zero migrations; não alterar `derive_desempenho` / `calculate_quadrante`
- Não expandir matriz a líderes puros (research R8)
- Não introduzir DRF/SPA/Chart.js/SortableJS
- Commit após cada task ou grupo lógico
- Parar em qualquer checkpoint para validar a story independentemente
