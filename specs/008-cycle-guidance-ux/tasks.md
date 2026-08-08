# Tasks: Orientação de Próximo Passo no Ciclo (Guidance UX)

**Input**: Design documents from `/specs/008-cycle-guidance-ux/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Unitários de **derivação read-only** pedidos no plan/research (`test_guidance_mapping`, `test_leader_pending_count`) + **regressão obrigatória** stage/scope sem mudar asserts de negócio. Sem TDD visual.

**Organization**: Tasks por user story. **MVP = US1 + US2**; depois **US3 + US4**.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que toque o seguinte é **INVÁLIDA** nesta feature (FR-013 / denylist):

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de estados | `advance_stage`, `can_advance` (mutar / “aperfeiçoar”) |
| Aprovação / reprovação | `approve_*`, `reject_*`, `apps/goals/services/approval.py` |
| Fórmulas | `calcular_*`, mutators em `evaluation.py` |
| AuthZ | alterar `get_visible_users`, `ScopedObjectMixin`, `apps/accounts/services/scope.py` |
| Persistência | `apps/*/models.py`, `**/migrations/**` |
| Domínio | `apps/cycles/services/stage.py`, abertura `open_cycle` / comportamento de `CicloOpenView`, `apps/*/urls.py` de negócio |

**Permitido apenas**: `guidance.py` / `pending_counts.py` (leitura), context em views existentes, templates/components, CSS mínimo do stepper, testes de mapeamento/contagem + garantir PASS das suites de regressão.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US4 conforme spec.md
- Paths relativos à raiz do repositório

## Path Conventions

Monólito Django na raiz: allowlist em `contracts/path-allowlist.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar allowlist/denylist e scaffold só de apresentação antes de qualquer UI

- [X] T001 Confirmar allowlist/denylist de paths em `specs/008-cycle-guidance-ux/contracts/path-allowlist.md` e `contracts/non-goals-denylist.md` (UI + context read-only apenas; denylist de domínio intocável)
- [X] T002 [P] Criar stub vazio `apps/reviews/services/guidance.py` (módulo puro leitura; docstring FR-013; **sem** imports de `advance_stage` / `approve_*` / `calcular_*`)
- [X] T003 [P] Criar stubs de partials `templates/components/next_step.html` e `templates/components/stage_stepper.html` (markup mínimo; sem lógica de negócio)

**Checkpoint**: Scaffold allowlist-only pronto

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DTO + derivação read-only + stepper DTO — bloqueia todas as user stories

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. **Zero** models/migrations/AuthZ.

- [X] T004 Implementar dataclass/`TypedDict` `NextStepGuidance` e helper `resolve_next_step(...)` com mapa etapa×papel da tabela em `contracts/guidance-derivation.md` em `apps/reviews/services/guidance.py` (somente leitura de `Avaliacao.etapa` / ciclo / papel; destinos só na allowlist de URL names)
- [X] T005 [P] Implementar builder `StageStepperState` / etapas `concluida|atual|futura|bloqueada` em `apps/reviews/services/guidance.py` (marcação visual; **não** chama mutators de stage)
- [X] T006 [P] Cobrir mapa etapa×papel + estados especiais (sem ciclo / vínculo pendente / concluída) em `tests/test_guidance_mapping.py` (asserts só de DTO de apresentação)
- [X] T007 Documentar na docstring de `apps/reviews/services/guidance.py` o checklist zero-write de `contracts/guidance-derivation.md` (sem `.save()`, sem `advance_stage` / `approve_*` / `calcular_nota_*`)

**Checkpoint**: Foundation de leitura testável — stories de UI podem iniciar

---

## Phase 3: User Story 1 — Próximo passo + stepper (Priority: P1) 🎯 MVP (parte 1)

**Goal**: Meu painel e detalhe da avaliação mostram bloco “Próximo passo” + stepper shared das 6 etapas, honestos em estados especiais

**Independent Test**: Colaborador e líder em etapa conhecida → Meu painel + detalhe com bloco + stepper coerentes; sem ciclo / vínculo pendente / concluído → copy sem CTA de avanço inventado (quickstart C1–C2 / L1 parcial)

### Implementation for User Story 1

- [ ] T008 [P] [US1] Completar markup de `templates/components/next_step.html` (título, body, CTA único ou ausência de CTA + `blocked_reason`; reutilizar button Freeze existente)
- [ ] T009 [P] [US1] Completar markup de `templates/components/stage_stepper.html` (6 etapas; estados visuais; variante compacta mobile legível — SC-006)
- [ ] T010 [US1] Injetar context `next_step` + `stage_stepper` em `apps/dashboard/views.py` (`PersonalDashboardView.get_context_data`) chamando apenas `guidance.py` (sem AuthZ nova)
- [ ] T011 [US1] Incluir `{% include %}` de `next_step` + `stage_stepper` em `templates/dashboard/personal.html`
- [ ] T012 [US1] Injetar context guidance/stepper em detalhe da avaliação em `apps/reviews/views.py` (Detail) — só `get_context_data` / flags de apresentação
- [ ] T013 [US1] Incluir stepper (e bloco se couber no hub) em `templates/reviews/avaliacao_detail.html` via partials shared (FR-002)
- [ ] T014 [P] [US1] Adicionar classes mínimas do stepper em `static/src/input.css` **somente se** utilitários insuficientes; rebuild `static/css/tailwind.css`
- [ ] T015 [US1] Validar US1 via quickstart (cenários C1–C2 + stepper no detalhe); confirmar CTA usa só URL names existentes

**Checkpoint**: US1 independentemente testável no Meu painel + detalhe

---

## Phase 4: User Story 2 — Hub CTA + badge líder + coerência metas (Priority: P1) 🎯 MVP (parte 2)

**Goal**: Hub com um CTA primário + ações secundárias; badge único de pendências na nav do líder; hints de metas coerentes (FR-007)

**Independent Test**: Detalhe com hierarquia CTA; líder vê um total = aprovações+avaliações+feedbacks elegíveis; grupos nav intactos; hint de metas não contradiz orientação (quickstart L1–L2)

### Implementation for User Story 2

- [ ] T016 [US2] Ajustar hierarquia visual de CTAs em `templates/reviews/avaliacao_detail.html` (exatamente um primário alinhado a `NextStepGuidance`; demais secundários; copy humana FR-005) — **sem** alterar predicados `can_advance` / POST existentes
- [ ] T017 [P] [US2] Implementar contagem read-only `LeaderPendingBadge` (soma 3 fontes com predicados **já existentes**) em `apps/reviews/services/guidance.py` ou `apps/reviews/services/pending_counts.py` — reusa `get_visible_users` **sem alterar** `apps/accounts/services/scope.py`
- [ ] T018 [P] [US2] Cobrir soma N+M+K e exclusão fora do escopo em `tests/test_leader_pending_count.py`
- [ ] T019 [US2] Expor total do badge via `apps/core/context_processors.py` (leitura por request autenticado; sem AuthZ nova)
- [ ] T020 [US2] Aceitar slot opcional `badge_count` em `templates/components/nav_link.html` e passar total em `templates/components/nav_menu.html` **sem** reordenar/renomear grupos Governança/Cadastros/Sistema
- [ ] T021 [US2] Alinhar copy/contexto do hint pós-reprovação em `apps/goals/views.py` / templates `templates/goals/meta_list.html` (+ partials) com `_proximo_passo_pos_reprovacao` — **sem** mudar `meta_approval_actionable` / approval service
- [ ] T022 [US2] Validar US2 via quickstart L1–L2 (badge ≤5s; nav grupos intactos; hub 1 CTA)

### MVP Gate (US1+US2) — verificação obrigatória

- [ ] T023 Verificar regressão SC-002 / FR-013 após MVP: `git diff` em serviços de regra de negócio = **vazio** (`apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/goals/services/approval.py`, `apps/accounts/services/scope.py`, mutators/cálculo em `apps/reviews/services/evaluation.py`, `apps/*/models.py`, `**/migrations/**`, `apps/*/urls.py`) **e** pytest stage+scope verdes: `python manage.py test tests.test_stage_machine tests.test_scope tests.test_reject_stage_invariant tests.test_can_advance_post_correction tests.test_post_rejection tests.test_production_ux` (+ `tests.test_guidance_mapping` / `tests.test_leader_pending_count`)

**Checkpoint MVP**: US1+US2 entregáveis; denylist de domínio intacta; stage/scope PASS

---

## Phase 5: User Story 3 — Menos atrito em ações longas (Priority: P2)

**Goal**: Progresso “faltam N” + sticky + save claro no leader assessment; pós-reprovação acionável; ciente de feedback óbvio — só UI/context

**Independent Test**: Leader assessment com notas incompletas; colaborador pós-reprovação; fluxo ciente com hops reduzidos **sem** mudar `can_acknowledge_feedback` (quickstart C3–C4 / L3)

### Implementation for User Story 3

- [ ] T024 [P] [US3] Expor flags de progresso (ex. notas restantes) só via leitura de formset/queryset em `apps/reviews/views.py` (leader assessment) — **sem** `calcular_nota_*`
- [ ] T025 [P] [US3] UI “faltam N”, contexto sticky do colaborador e confirmação de salvamento em `templates/reviews/leader_assessment.html`
- [ ] T026 [P] [US3] Clarificar progresso/orientação em `templates/reviews/self_assessment.html` se necessário à copy (sem mutar etapa)
- [ ] T027 [US3] Tornar ação de ciente óbvia e reduzir hops via copy/links existentes em `templates/reviews/feedback_list.html`, `templates/reviews/feedback_list_partial.html`, `templates/reviews/feedback_form.html` — **sem** alterar predicados de quem pode dar ciência
- [ ] T028 [US3] Garantir mensagem pós-reprovação acionável coerente com FR-007/US2 em painel/hub (`templates/dashboard/personal.html` / `templates/reviews/avaliacao_detail.html` via guidance já existente)
- [ ] T029 [US3] Validar US3 via quickstart C3–C4 / L3

**Checkpoint**: US3 independentemente testável sem tocar regras de feedback/avaliação

---

## Phase 6: User Story 4 — Checklist RH pré-abertura (Priority: P2)

**Goal**: Checklist avisório de blockers (usuário sem área/cargo; cargo sem competências/pesos) com links; Abrir intacto

**Independent Test**: Com/sem blockers na lista de ciclos; POST Abrir = mesmo comportamento pré-feature (quickstart R1–R3)

### Implementation for User Story 4

- [ ] T030 [P] [US4] Implementar builder read-only `RhPreOpenChecklist` em `apps/reviews/services/guidance.py` (ou helper sibling) conforme `contracts/rh-checklist-advisory.md` — **sem** condicionar `open_cycle`
- [ ] T031 [US4] Injetar checklist no context de listagem em `apps/cycles/views.py` (só `get_context_data` / flags) — **sem** alterar `CicloOpenView` / comportamento de abertura
- [ ] T032 [P] [US4] Renderizar checklist avisório + links em `templates/cycles/ciclo_list.html` e `templates/cycles/ciclo_list_partial.html` (**nunca** soft-disable Abrir)
- [ ] T033 [P] [US4] Reforçar links/contexto na superfície pending em `apps/organization/views.py` + `templates/organization/user_pending_list.html` / `user_pending_list_partial.html` se necessário (só apresentação)
- [ ] T034 [US4] Validar US4 via quickstart R1–R3 (Abrir intacto; checklist só aviso)

**Checkpoint**: US4 independentemente testável; abertura = regra vigente

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Aceite escritório, mobile legível, gate final denylist + regressão

- [ ] T035 [P] Percorrer quickstart.md completo (Ana / Bruno / Marina) e marcar SC-001…SC-006 em `specs/008-cycle-guidance-ux/quickstart.md` (aceite sem demos verbais — FR-015)
- [ ] T036 [P] Revisar mobile legível (stack vertical; stepper compacto) em `templates/components/stage_stepper.html` + superfícies Meu painel / hub / checklist (SC-006)
- [ ] T037 Confirmar `nav_menu.html` diff limitado a badge (sem reordenação de grupos IA) via `git diff templates/components/nav_menu.html`
- [ ] T038 Gate final SC-002 / FR-013: `git diff` em serviços de regra de negócio = **vazio** (mesmos paths da T023: stage/cycle/approval/scope/evaluation mutators/models/migrations/urls) **e** pytest stage+scope verdes: `python manage.py test tests.test_stage_machine tests.test_scope tests.test_reject_stage_invariant tests.test_can_advance_post_correction tests.test_post_rejection tests.test_production_ux tests.test_guidance_mapping tests.test_leader_pending_count`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: imediato
- **Foundational (Phase 2)**: após Setup — **bloqueia** todas as stories
- **US1 (Phase 3)**: após Foundational
- **US2 (Phase 4)**: após Foundational; reusa partials/DTO da US1 no hub; MVP só após US1+US2 + **T023**
- **US3 (Phase 5)**: após MVP gate T023 (recomendado); não depende de US4
- **US4 (Phase 6)**: após MVP gate T023; independente de US3
- **Polish (Phase 7)**: após US3+US4 desejados; **T038** obrigatório antes de declarar done

### User Story Dependencies

- **US1 (P1)**: sem dependência de outras stories
- **US2 (P1)**: integra guidance/partials da US1; testável sozinha no hub/nav
- **US3 (P2)**: após MVP; só templates/views context
- **US4 (P2)**: após MVP; checklist isolado

### Within Each Story

- Fundação (DTO/serviço) antes de includes de template
- Context na view antes do template consumir
- Validação quickstart no fim da story
- Gates T023 / T038 bloqueiam merge se diff denylist ≠ vazio ou pytest falhar

### Parallel Opportunities

- T002∥T003; T005∥T006; T008∥T009; T014 paralelo a includes após partials
- T017∥T018; T024∥T025∥T026; T030∥T032∥T033
- Após T023: US3 e US4 em paralelo por pessoas diferentes

---

## Parallel Example: User Story 1

```bash
# Partials em paralelo:
Task: "Completar markup de templates/components/next_step.html"
Task: "Completar markup de templates/components/stage_stepper.html"

# Depois: context dashboard → personal.html; context detail → avaliacao_detail.html
```

## Parallel Example: User Story 2

```bash
# Contagem + testes em paralelo:
Task: "Implementar LeaderPendingBadge em guidance.py / pending_counts.py"
Task: "Cobrir soma em tests/test_leader_pending_count.py"

# Depois: context_processors → nav_link/nav_menu; hub CTA; FR-007 goals
```

## Parallel Example: pós-MVP (US3 ∥ US4)

```bash
Task: "UI faltam N / sticky em templates/reviews/leader_assessment.html"
Task: "Checklist avisório em templates/cycles/ciclo_list.html"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 Setup → Phase 2 Foundational  
2. Phase 3 US1 → Phase 4 US2  
3. **STOP**: executar **T023** (diff denylist vazio + pytest stage/scope)  
4. Demo/MVP se T023 PASS  

### Incremental Delivery

1. MVP (US1+US2) + T023  
2. US3 → quickstart ações longas  
3. US4 → checklist RH avisório  
4. Polish + **T038**  

### Parallel Team Strategy

1. Time fecha Setup + Foundational juntos  
2. Dev A: US1 → Dev B prepara pending_counts/tests US2  
3. Após T023: Dev A US3 ∥ Dev B US4  
4. Juntos: T035–T038  

---

## Notes

- [P] = arquivos diferentes, sem dependência incompleta  
- Toda task de story DEVE ter path de arquivo allowlist  
- Task que proponha `advance_stage` / approve-reject / `calcular_*` / AuthZ / models / migrations → **REJEITAR**  
- Ouro: desligar guidance/CSS ⇒ mesmos POSTs e resultados de negócio  
- Commit por task ou grupo lógico; não pular T023/T038  
