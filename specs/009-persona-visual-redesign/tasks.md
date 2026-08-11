# Tasks: Redesign Visual por Persona (Painéis Gerenciais)

**Input**: Design documents from `/specs/009-persona-visual-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Payloads/cobertura/AuthZ de detalhe pedidos nos contracts + **regressão obrigatória** stage/scope (diff denylist vazio). Sem TDD visual.

**Organization**: Tasks por user story. **MVP indispensável até 03/09 = US1 + US2 + US3** (+ gate MVP). Depois **US4 (P2)**; **US5 (P3) só se sobrar tempo**; Polish + gate final.

**Prazo**: 03/09/2026 — se o tempo apertar, **parar após gate MVP** (ou após US4 se caber); US5 **não** bloqueia aceite.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que toque o seguinte é **INVÁLIDA** nesta feature (FR-012 / FR-014 / denylist):

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de estados | `advance_stage`, `can_advance` (mutar / “aperfeiçoar”), `apps/cycles/services/stage.py` |
| Aprovação / reprovação | `approve_*`, `reject_*`, `apps/goals/services/approval.py` |
| Fórmulas | `calcular_*`, `%` aderência, mutators em `evaluation.py` / `adherence.py` |
| AuthZ | alterar `get_visible_users`, `ScopedObjectMixin`, `apps/accounts/services/scope.py` |
| Persistência | `apps/*/models.py`, `**/migrations/**` |
| Domínio ciclo | mutar `apps/cycles/services/cycle.py`, open/close, semântica de CRUD de ciclo |
| Stack | SPA, DRF, nova lib de gráficos, Chart.js ≠ 4.5.1 |
| Shell / auth | reabrir nav IA, `base_auth`, login |

**Permitido apenas** (allowlist completa em `contracts/path-allowlist.md`): templates/partials/JS de apresentação; `chart_payloads.py` (shape/types); composição leve de cobertura recebendo `visible`; `CicloDetailView` GET + rota `ciclo_detail`; tokens `input.css` + `docs/design-system.md`; testes de payload/escopo/regressão.

**Teste de ouro**: desligar CSS/charts/painel **não** deve mudar avanço de etapa, aprovação/reprovação, notas, usuários visíveis nem abrir/fechar ciclo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US5 conforme spec.md
- Paths relativos à raiz do repositório; cada task cita path **allowlist** e reforça **denylist**

## Path Conventions

Monólito Django na raiz: allowlist em `contracts/path-allowlist.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar allowlist/denylist e baseline antes de qualquer UI  
**Prazo**: imediato — pré-requisito do MVP

- [X] T001 Confirmar allowlist/denylist de paths em `specs/009-persona-visual-redesign/contracts/path-allowlist.md` e `contracts/non-goals-denylist.md` (só apresentação + composição leve; denylist de domínio intocável — stage/approval/fórmulas/AuthZ/models/migrations)
- [X] T002 [P] Registrar baseline Chart.js **4.5.1** + shape atual em `static/js/dashboard_charts.js`, `templates/dashboard/_chart_block.html` e `apps/dashboard/chart_payloads.py` (sem lib nova; sem tocar denylist) — evidência: `contracts/chart-baseline.md`
- [X] T003 [P] Confirmar contratos de catálogo/painel/ciclo em `specs/009-persona-visual-redesign/contracts/chart-catalog.md`, `managerial-panel.md`, `cycle-managerial-detail.md` alinhados a plan/spec (referência para implementação allowlist-only)

**Checkpoint**: Escopo allowlist-only congelado; denylist de domínio rejeitada em PRs

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Contrato visual compartilhado (Freeze A/B/C + tokens + catálogo JS/payload) — **bloqueia** US1–US3  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. **Zero** models/migrations/AuthZ/stage/approval.

- [X] T004 Documentar reabertura Freeze A/B/C + padrão “painel gerencial” (KPI + visual + tabela) em `docs/design-system.md` (FR-011 / SC-006; **sem** alterar nav/login; denylist intacta)
- [X] T005 [P] Adicionar tokens/classes de painel/chart (ex. `.managerial-panel`, altura/canvas) em `static/src/input.css` e rebuild `static/css/tailwind.css` na **mesma** entrega (allowlist; sem shell/auth)
- [X] T006 Ampliar catálogo de init Chart.js (`bar_horizontal`, `area`, doughnut com valor central inline) em `static/js/dashboard_charts.js` conforme `contracts/chart-catalog.md` — Chart.js **4.5.1** apenas; **sem** plugin npm / lib nova
- [X] T007 [P] Estender types/`legend_items`/`total` compatíveis em `apps/dashboard/chart_payloads.py` mantendo Status Triad e shape `has_data`/`labels`/`values`/`series` (FR-001/002; **sem** inventar métrica; **sem** mutar `adherence.py` / fórmulas)
- [X] T008 [P] Ajustar markup de bloco (mini-KPI/legenda/empty) em `templates/dashboard/_chart_block.html` reusando `templates/components/empty_state.html` e `templates/components/card.html` só apresentação

**Checkpoint**: Fundação visual reutilizável — US1 pode consumir catálogo; US2/US3 não inventam init paralelo

---

## Phase 3: User Story 1 — Charts modernos e gerenciais (Priority: P1) 🎯 MVP (parte 1)

**Goal**: Painéis pessoal / time / admin com charts expressivos, paleta de acabamento e empty honesto — fundação para US2/US3  
**Independent Test**: Abrir Meu painel, Time e Admin com/sem dados; hierarquia visual + Status Triad intacta; ~375px legível (quickstart §1)  
**Prazo**: obrigatório antes de US2/US3; parte do mínimo até 03/09

### Implementation for User Story 1

- [X] T009 [P] [US1] Wire chart expressivo + mini-KPI em `templates/dashboard/personal.html` (`extra_js` Chart.js 4.5.1 + `dashboard_charts.js`; allowlist US1; **sem** AuthZ/fórmulas)
- [X] T010 [P] [US1] Wire chart expressivo (ex. `bar_horizontal` / ranking) acima da tabela em `templates/dashboard/team.html` (allowlist; tabela ainda drill-down; denylist intacta)
- [X] T011 [P] [US1] Polish doughnut/progresso + valor central em `templates/dashboard/admin.html` (allowlist; Status Triad inalterada)
- [X] T012 [US1] Ajustar só context/`type`/payload em Personal/Team/Admin em `apps/dashboard/views.py` (composição de payload; **sem** alterar `get_visible_users` / `scope.py` / models)
- [X] T013 [P] [US1] Cobrir types novos + empty `has_data` falso em `tests/test_chart_payloads.py` ou `tests/test_persona_panels_charts.py` (asserts só de presentation payload; **sem** mudar asserts de stage/scope)
- [X] T014 [US1] Validar US1 via `specs/009-persona-visual-redesign/quickstart.md` §1 (+ SC-003 parcial); confirmar CDN Chart.js **4.5.1** e denylist diff vazio nos paths de domínio — evidência 2026-08-11: CDN pinado em personal/team/admin; denylist clean desde `373134d`; pytest `test_chart_payloads` 16 PASS + stage/scope smoke 23 PASS

**Checkpoint**: US1 independentemente testável; catálogo pronto para US2 ∥ US3

---

## Phase 4: User Story 2 — Painéis gerenciais do Líder/Gestor (Priority: P1) 🎯 MVP (parte 2)

**Goal**: Time / estrutura / aderência no padrão KPI + visual + tabela; cobertura área/cargo na estrutura; ranking acionável  
**Independent Test**: Como líder, abrir time/estrutura/aderência; “onde estamos?” sem depender da tabela; escopo = mesmo conjunto visível (quickstart §2)  
**Prazo**: obrigatório no MVP; **pode rodar em paralelo com US3** após US1  
**Allowlist**: `templates/dashboard/team*.html`, `structure.html`, `adherence*.html`, `apps/dashboard/views.py`, `apps/dashboard/services/structure.py`, builders `chart_payloads.py` — **proibido** mutar `scope.py` / `adherence.py` fórmula / stage

### Implementation for User Story 2

- [X] T015 [US2] Compor painel gerencial (KPI + `_chart_block` + drill-down) em `templates/dashboard/team.html` + `templates/dashboard/team_list_partial.html` (tabela secundária; **sem** predicados AuthZ novos)
- [X] T016 [P] [US2] Implementar builder de cobertura área/cargo **read-only** recebendo `visible` já resolvido em `apps/dashboard/services/structure.py` e/ou `apps/dashboard/chart_payloads.py` (FR-006/013; **nunca** chamar `get_visible_users` com outro user; **sem** alterar `apps/accounts/services/scope.py`)
- [X] T017 [US2] Incluir estrutura no slice charts: KPI + chart cobertura + lacunas secundárias + CDN/init em `templates/dashboard/structure.html` (reabertura B; allowlist; denylist intacta) — evidência 2026-08-11: painel gerencial cobertura + Chart.js 4.5.1; view expõe `cobertura_resumo` / `chart_cobertura_*` via `build_structure_coverage`
- [X] T018 [P] [US2] Painel aderência (KPI + doughnut + lista) em `templates/dashboard/adherence.html` + `templates/dashboard/adherence_list_partial.html` lendo `AderenciaSnapshot` já filtrado (**sem** recalcular em `adherence.py` / `tasks.py`) — evidência 2026-08-11: managerial-panel KPI + doughnut Chart.js 4.5.1 + lista HTMX; context via mesmo QS filtrado (`aderencia_resumo` / `chart_aderencia_distribuicao`); denylist adherence.py/tasks.py intacta
- [X] T019 [US2] Expor context KPIs/payloads em Structure/Adherence/Team em `apps/dashboard/views.py` passando `visible` aos builders (só `get_context_data`; **sem** mudar AuthZ/mixins) — evidência 2026-08-11: Team→`team_resumo`/`chart_escopo_status`/`destaque_atencao` no QS de escopo; Structure→`build_structure_coverage(visible)`; Adherence→KPI/doughnut no QS já filtrado; mixins AuthZ intactos
- [X] T020 [P] [US2] Cobrir cobertura ⊂ escopo e empty em `tests/test_structure_coverage.py` ou `tests/test_persona_panels_structure.py` (assert subset de `get_visible_users`; **sem** alterar `tests` de stage/approval além de PASS) — evidência 2026-08-11: `tests/test_structure_coverage.py` 7 PASS (total⊂visible, outsider excluído, empty sem ciclo/escopo)
- [X] T021 [US2] Validar US2 via quickstart §2 (SC-001 parcial); links de ação só URL names existentes — evidência 2026-08-11: §2.1 team = KPI→chart→destaque→tabela + Chart.js 4.5.1; §2.2 structure = cobertura KPI + charts área/cargo + lacunas secundárias; §2.3 adherence = KPI + doughnut + lista drill-down; §2.4 reverse OK (`reviews:leader_assessment`/`detail`/`feedback_list`, `dashboard:adherence`); pytest `test_structure_coverage`+`test_chart_payloads` 23 PASS

**Checkpoint**: US2 testável sozinha com charts US1; estrutura no slice

---

## Phase 5: User Story 3 — Visão gerencial de Ciclos (Admin RH) (Priority: P1) 🎯 MVP (parte 3)

**Goal**: Página `cycles/<pk>/` consolidando progresso, cobertura, aderência e checklist 008  
**Independent Test**: Lista → detalhe; seções + empty local; não-admin negado; Abrir ciclo intacto (quickstart §3)  
**Prazo**: obrigatório no MVP; **pode rodar em paralelo com US2** após US1  
**Allowlist**: `CicloDetailView`, `apps/cycles/urls.py` **somente** `ciclo_detail`, `ciclo_detail.html`, links em `ciclo_list*.html`, reuso builders dashboard + **leitura** `guidance.py` — **proibido** mutar `cycle.py` / `stage.py` / open/close / models

### Implementation for User Story 3

- [ ] T022 [US3] Adicionar **apenas** `path('<pk>/', …, name='ciclo_detail')` em `apps/cycles/urls.py` (**não** alterar rotas open/close/edit/delete — zona cinza documentada)
- [ ] T023 [US3] Implementar `CicloDetailView` GET read-only com `AdminCyclesMixin`/`RequiresAdminMixin` em `apps/cycles/views.py` (context: progresso/cobertura/aderência/checklist; **sem** `ScopedObjectMixin` inventado; **sem** tocar `CicloOpenView` / `cycle.py`)
- [ ] T024 [P] [US3] Criar painel gerencial em `templates/cycles/ciclo_detail.html` (KPI + `_chart_block` × seções + checklist avisório + `extra_js` Chart.js 4.5.1; empty por seção)
- [ ] T025 [P] [US3] Linkar detalhe a partir de `templates/cycles/ciclo_list.html` e `templates/cycles/ciclo_list_partial.html` (página dedicada — **não** accordion; allowlist)
- [ ] T026 [US3] Reusar `build_rh_pre_open_checklist` só leitura em `apps/reviews/services/guidance.py` no context do detalhe (**sem** mudar advisory → hard-block; **sem** condicionar `open_cycle`)
- [ ] T027 [P] [US3] Testar AuthZ admin 200 / não-admin negado / anônimo login em `tests/test_ciclo_detail.py` (só view GET; **sem** alterar open/close assertions de negócio)
- [ ] T028 [US3] Validar US3 via quickstart §3 (SC-002 parcial); Abrir ciclo = comportamento pré-feature

**Checkpoint**: US3 independentemente testável; AuthZ vigente preservada

---

## Phase 6: Gate MVP (US1 + US2 + US3) — verificação obrigatória 🎯

**Purpose**: Fechar o **mínimo indispensável** antes de P2/P3; equivalente ao padrão T023 da spec 008  
**Prazo**: **obrigatório** antes de demos MVP / seguir para US4; se prazo 03/09 apertar, **este é o último gate exigido** (US4/US5 opcionalmente cortados após US4 ou aqui)

- [ ] T029 Gate MVP / regressão SC-004 / FR-012: `git diff` em serviços de domínio = **vazio** (`apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/goals/services/approval.py`, `apps/accounts/services/scope.py`, mutators/cálculo em `apps/reviews/services/evaluation.py`, `apps/dashboard/services/adherence.py`, `apps/*/models.py`, `**/migrations/**`) **e** suíte stage/scope verde: `python manage.py test tests.test_stage_machine tests.test_scope tests.test_reject_stage_invariant tests.test_can_advance_post_correction tests.test_post_rejection tests.test_production_ux` (+ novos `tests.test_chart_payloads` / `tests.test_structure_coverage` / `tests.test_ciclo_detail` quando existirem). Exceção urls: só adição allowlist `ciclo_detail` — demidas open/close = falha.

**Checkpoint MVP**: US1+US2+US3 entregáveis; denylist de domínio intacta; stage/scope PASS — **release mínimo viável até 03/09**

---

## Phase 7: User Story 4 — Consistência visual do Colaborador (Priority: P2)

**Goal**: Expectativas/metas/avaliações/PDI/classificação no Freeze v2 + CTA sem duplicar guidance 008  
**Independent Test**: Percorrer 5 superfícies P2; tipografia/table-frame/empty; sem segundo “Próximo passo” conflitante (quickstart §4 / SC-005)  
**Prazo**: após gate MVP; desejável até 03/09; **não** faz parte do mínimo US1–3, mas fecha P1+P2 do aceite preferencial  
**Allowlist**: templates goals/reviews/pdi/talent listados no contract — **proibido** reimplementar mapa 008 / mutar evaluation/approval

### Implementation for User Story 4

- [ ] T030 [P] [US4] Polish Freeze + CTA em `templates/goals/expectations.html`, `templates/goals/meta_list.html`, `templates/goals/meta_list_partial.html`, `templates/goals/partials/meta_row.html` (só apresentação; **sem** `approval.py`)
- [ ] T031 [P] [US4] Polish chrome em `templates/reviews/avaliacao_list.html`, `templates/reviews/avaliacao_list_partial.html`, `templates/reviews/avaliacao_detail.html` (**consumir** `next_step`/`stage_stepper` 008; **não** duplicar/contradizer)
- [ ] T032 [P] [US4] Polish PDI em `templates/pdi/pdi_list.html`, `templates/pdi/pdi_list_partial.html`, `templates/pdi/pdi_detail.html`, `templates/pdi/pdi_form.html` (allowlist; denylist intacta)
- [ ] T033 [P] [US4] Polish `templates/talent/my_classification.html` (tokens Freeze; **sem** mudar 9-box/fórmulas)
- [ ] T034 [US4] Context CTA mínimo só se necessário em views goals/reviews/pdi/talent allowlist (**sem** predicados AuthZ novos; **sem** models)
- [ ] T035 [US4] Validar US4 via quickstart §4 (SC-005)

**Checkpoint**: P2 fechado; guidance 008 consumida, não reescrita

---

## Phase 8: User Story 5 — Cadastros e Sistema (Priority: P3) ⚠️ BEST-EFFORT

**Goal**: Tipografia/table-frame/empty em áreas/cargos/usuários/competências/auditoria/notificações  
**Independent Test**: Se entregue — superfícies P3 alinhadas ao Freeze sem mudança CRUD/AuthZ; se omitida — **não** falha release (FR-010)  
**Prazo**: **somente se sobrar tempo após US4 até 03/09**; cortar integralmente sem culpa se prazo apertar  
**Allowlist**: `templates/organization/area_*`, `cargo_*`, `user_*`, `competencies/*`, `audit/*`, `notifications/*` — visual-only

### Implementation for User Story 5 (opcional)

- [ ] T036 [P] [US5] Polish tipografia/table-frame/empty em `templates/organization/area_*.html` e `templates/organization/cargo_*.html` (**sem** AuthZ/CRUD)
- [ ] T037 [P] [US5] Polish `templates/organization/user_*.html` (incl. pending) — só chrome
- [ ] T038 [P] [US5] Polish `templates/competencies/*.html`, `templates/audit/*.html`, `templates/notifications/*.html` (allowlist P3; denylist intacta)
- [ ] T039 [US5] Validar US5 via quickstart §5 **ou** registrar explicitamente “P3 omitido por prazo 03/09” no PR (ausência **não** falha aceite)

**Checkpoint**: P3 entregue **ou** formalmente skipado; aceite P1+P2 preservado

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Aceite guiado, mobile, evidências DS, **gate final** (equivalente T038 da spec 008)  
**Prazo**: após stories desejadas; gate final **sempre** antes de declarar feature done (mesmo se US5 skip)

- [ ] T040 [P] Percorrer `specs/009-persona-visual-redesign/quickstart.md` completo (US1–US4; US5 se houver) e marcar SC-001…SC-007 aplicáveis
- [ ] T041 [P] Revisar viewport ~375px (empilhamento KPI → visual → tabela) nas superfícies P1 em templates dashboard/cycles (SC-007; allowlist)
- [ ] T042 [P] Anexar/confirmar evidências before/after charts + painéis e que `docs/design-system.md` reflete A/B/C (SC-003/SC-006)
- [ ] T043 Confirmar Chart.js **4.5.1** único e ausência de lib nova (network/`extra_js`); `nav_menu`/shell **sem** redesign IA
- [ ] T044 Gate final SC-004 / FR-012: `git diff` em serviços de domínio = **vazio** (mesmos paths da T029: stage/cycle/approval/scope/evaluation mutators/adherence fórmula/models/migrations) **e** suíte stage/scope verde: `python manage.py test tests.test_stage_machine tests.test_scope tests.test_reject_stage_invariant tests.test_can_advance_post_correction tests.test_post_rejection tests.test_production_ux` (+ testes novos de payload/cobertura/ciclo_detail). Paths allowlist-only no diff restante; US5 omitida OK.

---

## Dependencies & Execution Order

### Phase Dependencies

| Fase | Depende de | Notas de prazo (03/09) |
|------|------------|-------------------------|
| Setup (1) | — | Imediato |
| Foundational (2) | Setup | **Bloqueia** todas as stories |
| US1 (3) | Foundational | Obrigatório MVP |
| US2 (4) | US1 | Obrigatório MVP; ∥ US3 |
| US3 (5) | US1 | Obrigatório MVP; ∥ US2 |
| Gate MVP T029 (6) | US1+US2+US3 | **Mínimo indispensável** — parar aqui se tempo apertar |
| US4 (7) | T029 | P2 desejável; após MVP |
| US5 (8) | US4 | P3 best-effort; cortar livremente |
| Polish + T044 (9) | Stories feitas + sempre T044 | Gate final mesmo com US5 skip |

```text
Setup → Foundational → US1 ──┬──► US2 ──┐
                             │         ├──► T029 (MVP) → US4 → [US5?] → Polish + T044
                             └──► US3 ──┘
```

### User Story Dependencies

- **US1 (P1)**: após Foundational; sem dependência de outras stories
- **US2 (P1)**: após US1 (reusa `_chart_block` / `dashboard_charts.js` / payloads)
- **US3 (P1)**: após US1 (mesmo catálogo); **independente de US2** → paralelo
- **US4 (P2)**: após T029; independente de US5
- **US5 (P3)**: após US4; opcional até 03/09

### Within Each Story

- Catálogo/foundation antes de wire de templates
- Builder/context na view antes do template consumir
- Validação quickstart no fim da story
- Gates **T029** / **T044** bloqueiam merge se diff denylist ≠ vazio ou pytest falhar

### Parallel Opportunities

- T002∥T003; T005∥T007∥T008
- T009∥T010∥T011; T013 paralelo a validação parcial
- **Após US1**: Dev A → US2 (T015–T021) ∥ Dev B → US3 (T022–T028)
- T030∥T031∥T032∥T033 (US4)
- T036∥T037∥T038 (US5, se houver tempo)
- T040∥T041∥T042 no polish

---

## Parallel Example: User Story 1

```bash
# Templates de superfície em paralelo (allowlist US1):
Task: "Wire chart em templates/dashboard/personal.html"
Task: "Wire chart em templates/dashboard/team.html"
Task: "Polish chart em templates/dashboard/admin.html"

# Depois: context em apps/dashboard/views.py + testes de payload
```

## Parallel Example: pós-US1 (US2 ∥ US3) — caminho crítico MVP

```bash
# Dev A — US2 (allowlist leader panels; denylist scope/adherence fórmula):
Task: "Builder cobertura em apps/dashboard/services/structure.py"
Task: "Painel structure.html + adherence.html"

# Dev B — US3 (allowlist ciclo_detail only; denylist cycle.py/stage.py):
Task: "CicloDetailView + path ciclo_detail em apps/cycles"
Task: "templates/cycles/ciclo_detail.html + links na lista"
```

## Parallel Example: User Story 4 (após T029)

```bash
Task: "Polish goals templates"
Task: "Polish reviews list/detail chrome"
Task: "Polish pdi + my_classification"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3) — mínimo até 03/09

1. Phase 1 Setup → Phase 2 Foundational  
2. Phase 3 US1  
3. Phase 4 US2 **em paralelo** com Phase 5 US3  
4. **STOP**: executar **T029** (diff denylist vazio + pytest stage/scope)  
5. Demo/MVP se T029 PASS — **aceitável como release mínimo** se prazo apertar  

### Incremental Delivery (preferencial até 03/09)

1. MVP (US1+US2+US3) + **T029**  
2. US4 (P2) → quickstart colaborador  
3. US5 (P3) **somente se sobrar tempo** — senão skip documentado  
4. Polish + **T044**  

### Se o tempo apertar (corte explícito)

| Prioridade | Entrega | Aceite |
|------------|---------|--------|
| **Obrigatório** | US1 + US2 + US3 + T029 (+ T044 se for merge da branch) | Release mínimo gerencial |
| **Desejável** | + US4 | Fecha P1+P2 da spec |
| **Opcional** | + US5 | Best-effort; ausência OK (FR-010) |

### Parallel Team Strategy

1. Time fecha Setup + Foundational juntos  
2. Dev A: US1 catalog/templates → depois US2  
3. Dev B: após T008/T006, prepara builders; após US1 checkpoint → US3 em paralelo  
4. Juntos: **T029**  
5. Se houver prazo: Dev A US4 ∥ (Dev B US5 só se buffer) → **T044**  

---

## Notes

- **[P]** = arquivos diferentes, sem dependência incompleta  
- Toda task de story DEVE ter path de arquivo **allowlist**  
- Task que proponha `advance_stage` / approve-reject / `calcular_*` / mutar AuthZ / models / migrations / nova lib chart → **REJEITAR**  
- Ouro: desligar CSS/charts/painel ⇒ mesmos POSTs e resultados de negócio  
- `apps/cycles/urls.py`: **somente** acrescentar `ciclo_detail`; qualquer outra rota = falha  
- Commit por task ou grupo lógico; **não pular T029 / T044**  
- Data-limite **03/09/2026**: MVP = US1+US2+US3; US5 nunca bloqueia aceite  
