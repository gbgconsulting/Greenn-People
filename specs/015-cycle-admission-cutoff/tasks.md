---
description: "Task list for feature implementation"
---

# Tasks: Elegibilidade de Ciclo por “Admitidos até”

**Input**: Design documents from `/specs/015-cycle-admission-cutoff/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme plan.md §Testes nomeados, SC-001…SC-009 e quickstart — `tests/test_open_cycle_admission_cutoff.py` (novo), `tests/test_mid_cycle_enrollment.py` (atualizar), `tests/test_backfill_data_entrada.py` (novo), `tests/conftest.py` (`ciclo_aberto`), regressão denylist **sem** alterar asserts alheios. Gate: `git diff` vazio nos paths da denylist (exceto allowlist 015).

**Organization**: Tasks por user story. Sequência: Setup → Fundação (schema + predicado + ensure) → US1 P1 abertura → US2 P1 preview → US3 P1 mid-cycle → US4 P1 backfill → US5 P2 denylist/histórico → Polish. **MVP = Fundação + US1** (abrir só elegíveis). US2/US3/US4 também P1 — entregar em seguida; US5 é gate de não-regressão.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que proponha alterar denylist ([contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md)) é **INVÁLIDA**:

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de etapas | `apps/cycles/services/stage.py`; `can_advance` / `advance_stage` |
| Encerramento | Mutar regra de `close_cycle` em `apps/cycles/services/cycle.py` |
| Aprovação | `apps/goals/services/approval.py` |
| Fórmulas | `apps/reviews/services/evaluation.py` |
| Aderência / 9-box | `apps/dashboard/services/adherence.py`; mutators `apps/talent/` |
| AuthZ / escopo | `apps/accounts/services/scope.py`; `get_visible_users`; `ScopedObjectMixin` |
| PDI produto | `apps/pdi/views.py` / `urls.py` / `forms.py` / `overdue.py` / `progress.py` / `tasks.py` |
| UI 012 | Rotas/templates históricas 012; **não** mudar comportamento de `apps/dashboard/urls.py` além do necessário (diff vazio preferido) |
| Imports 010–014 | Exigir `admitidos_ate` ou chamar `open_cycle` em importadores |
| Schema | M2M participantes; FK nova Avaliacao↔Ciclo; `AlterField` em `data_entrada`; `RunPython` de elegibilidade histórica |
| Stack | DRF, SPA, Celery novo para o corte, lib nova, UI de upload de backfill |
| Produto fora | Hard-block checklist 008; forçar inelegível; desfazer Avaliacao por data; tornar `data_entrada` obrigatória no RegisterForm |

**Permitido (allowlist)**: `Ciclo.admitidos_ate` + migration `0003_*`; `eligibility.py`; `open_cycle` (+ imports); `CycleMissingCutoffError`; forms/views/templates de abertura + preview HTMX; `ensure_avaliacao_for_user`; pacote `admission_backfill/` + `backfill_data_entrada`; extensão mínima `parse_xlsx`/`report` para “Data admissão”; testes e contrato 002 mid-cycle. Ver allowlist completa em [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md).

**Teste de ouro**: abertura exige corte; matrícula só elegíveis; snapshot nunca apaga Avaliacao; ciclos 011/`admitidos_ate=NULL` intactos; backfill só preenche `data_entrada` vazia e **não** abre/fecha ciclo; checklist 008 continua avisório; denylist = diff de comportamento vazio.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US5 conforme spec.md
- Paths relativos à raiz do monólito Django

## Path Conventions

Monólito Django na raiz (`apps/cycles`, `apps/reviews`, `apps/accounts`, `templates/cycles/`, `tests/`). Sem app nova. openpyxl **somente** via `apps/accounts/services/legacy_import/parse_xlsx.py` no backfill.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar contratos e criar esqueleto dos módulos novos  
**Pré-requisito**: imediato — `plan.md` / `spec.md` / contracts já existem

- [X] T001 Confirmar allowlist/denylist e contratos congelados em `specs/015-cycle-admission-cutoff/contracts/` (`eligibility-predicate-contract.md`, `open-cycle-cutoff-contract.md`, `preview-counts-contract.md`, `admission-backfill-command-contract.md`, `migration-safety.md`, `non-goals-denylist.md`) — uma AddField; predicado único; sem M2M; sem AlterField `data_entrada`; sem Celery/DRF/SPA
- [X] T002 [P] Criar stub `apps/cycles/services/eligibility.py` com `user_eligible_for_ciclo` e `preview_admission_counts` levantando `NotImplementedError` (API pública conforme research R3/R5)
- [X] T003 [P] Criar pacote stub `apps/accounts/services/admission_backfill/` (`__init__.py`, `resolve.py`, `importer.py` com `NotImplementedError`) e stub `apps/accounts/management/commands/backfill_data_entrada.py` conforme [contracts/admission-backfill-command-contract.md](./contracts/admission-backfill-command-contract.md)

**Checkpoint**: Módulos novos importáveis; denylist congelada; zero persistência ainda

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema aditivo + predicado + gate no `ensure` — **BLOQUEIA** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. `close_cycle` e denylist intactos.

- [X] T004 Adicionar campo `admitidos_ate = models.DateField('admitidos até', null=True, blank=True)` em `apps/cycles/models.py` conforme [data-model.md](./data-model.md) e research R1 — **sem** AlterField em outros campos; independente de `data_inicio`/`data_fim`
- [X] T005 Criar **única** migration aditiva `apps/cycles/migrations/0003_ciclo_admitidos_ate.py` (`AddField` only) conforme [contracts/migration-safety.md](./contracts/migration-safety.md) — **zero** `RunPython` de elegibilidade; **zero** M2M/tabela participantes
- [X] T006 [P] Adicionar `CycleMissingCutoffError(CycleError)` em `apps/cycles/exceptions.py` conforme [contracts/open-cycle-cutoff-contract.md](./contracts/open-cycle-cutoff-contract.md)
- [X] T007 Implementar `user_eligible_for_ciclo(user, ciclo) -> bool` em `apps/cycles/services/eligibility.py` conforme [contracts/eligibility-predicate-contract.md](./contracts/eligibility-predicate-contract.md): ativo ∧ `data_entrada` NOT NULL ∧ `admitidos_ate` NOT NULL ∧ `data_entrada <= admitidos_ate` (inclusivo); fail-closed se corte NULL
- [X] T008 Estender `ensure_avaliacao_for_user` em `apps/reviews/services/enrollment.py` para chamar `user_eligible_for_ciclo` antes de criar — inelegível → `None` (no-op); existente → retorna sem remover; ciclo encerrado → `None`; denylist intacta (`stage.py` / `evaluation.py` / `scope.py` **não** tocados)
- [X] T009 Atualizar fixture `ciclo_aberto` em `tests/conftest.py` para setar `admitidos_ate` (e garantir `data_entrada` nos users de fixture quando necessário) **antes** de `open_cycle`, para a suite vigente não quebrar com o novo gate

**Checkpoint**: Migração aplicável; predicado unit-testável; `ensure` falha fechado sem elegibilidade; foundation pronta para US1–US5

---

## Phase 3: User Story 1 — Abrir ciclo só com elegíveis pelo corte (Priority: P1) 🎯 MVP

**Goal**: RH informa “Admitidos até”; `open_cycle` exige corte; matricula só elegíveis; mensagem sem “todos os ativos”; um ciclo aberto intacto  
**Independent Test**: Abrir com corte D e base controlada (entrada ≤ D, > D, sem data, inativos) → 1 Avaliacao por elegível, 0 nos demais; sem corte → erro visível, status não abre, 0 Avaliações; mensagem sem “todos os ativos” / “colaboradores ativos” genérico  
**Allowlist**: `cycle.py::open_cycle`, `CicloOpenView`, forms/templates de abertura, `exceptions.py`, testes novos — **proibido** mutar `close_cycle` / checklist 008 hard-block

### Tests for User Story 1

> **NOTE: Escrever estes testes primeiro; garantir FAIL antes da implementação completa de T012–T014**

- [X] T010 [P] [US1] Criar `tests/test_open_cycle_admission_cutoff.py` cobrindo: elegíveis/inelegíveis na abertura; sem corte → `CycleMissingCutoffError` / status intacto / 0 Avaliações; um-aberto intacto; mensagem de sucesso **sem** “todos os ativos” / “colaboradores ativos” genérico (conforme plan §Testes)

### Implementation for User Story 1

- [X] T011 [US1] Estender `open_cycle(ciclo, *, admitidos_ate: date | None = None)` em `apps/cycles/services/cycle.py` conforme [contracts/open-cycle-cutoff-contract.md](./contracts/open-cycle-cutoff-contract.md): ordem atomic lock → um-aberto/já-aberto → exigir corte → persistir `admitidos_ate` → `status=aberto` → batch `ensure_avaliacao_for_user`; sem corte → `CycleMissingCutoffError` **antes** de abrir; **MUST NOT** alterar regra de `close_cycle`
- [X] T012 [US1] Atualizar `CicloOpenView` em `apps/cycles/views.py` para ler `admitidos_ate` do POST, passar a `open_cycle`, capturar `CycleMissingCutoffError` com `messages.error` visível, e trocar mensagem de sucesso para refletir elegibilidade do corte (não “todos os ativos”)
- [X] T013 [P] [US1] Expor campo date “Admitidos até” no fluxo de abertura em `apps/cycles/forms.py` e `templates/cycles/ciclo_list.html` / `ciclo_list_partial.html` (e `ciclo_form.html` opcional só para pré-preencher — gate permanece em `open_cycle`, não no save do create)
- [X] T014 [US1] Validar US1 via cenários SC-001/SC-002/SC-008 e `pytest tests/test_open_cycle_admission_cutoff.py -q`; confirmar checklist 008 permanece avisório (única trava **nova** = ausência de corte)

**Checkpoint**: US1 independentemente testável — MVP de abertura com corte

---

## Phase 4: User Story 2 — Preview honesto antes de abrir (Priority: P1)

**Goal**: No fluxo admin de abertura, preview com 3 contagens agregadas (elegíveis / admissão posterior / sem data); AuthZ = mesmo gate admin; sem lista nominativa; sem step extra além do POST Abrir  
**Independent Test**: Base conhecida + D → 3 contagens batem; líder/colaborador/anônimo → 403/login; HTML sem e-mails/nomes  
**Allowlist**: `eligibility.py` preview, view/URL/partial HTMX sob `AdminCyclesMixin` — **proibido** rota pública / DRF / lista de pessoas

### Tests for User Story 2

- [X] T015 [P] [US2] Estender `tests/test_open_cycle_admission_cutoff.py` (ou módulo dedicado no mesmo arquivo) com AuthZ de preview: admin 200 + 3 contagens; líder/colaborador 403; anônimo redirect; resposta **sem** lista de e-mails/nomes

### Implementation for User Story 2

- [X] T016 [US2] Implementar `preview_admission_counts(admitidos_ate: date) -> dict` em `apps/cycles/services/eligibility.py` com agregações ORM: `elegiveis`, `excluidos_admissao_posterior`, `sem_data_entrada` (somente `is_active=True`; inativos fora) conforme [contracts/preview-counts-contract.md](./contracts/preview-counts-contract.md)
- [X] T017 [US2] Criar `CicloOpenPreviewView(AdminCyclesMixin, …)` em `apps/cycles/views.py` + rota `cycles:ciclo_open_preview` em `apps/cycles/urls.py` (somente se necessário; **MUST NOT** alterar rotas 012/histórico) retornando partial HTMX com **apenas** as 3 contagens
- [X] T018 [P] [US2] Criar/atualizar partial em `templates/cycles/` (ex.: `ciclo_open_preview_partial.html`) e integrar região de preview + disparo HTMX no fluxo de abertura em `templates/cycles/ciclo_list.html` / `ciclo_list_partial.html` — informativo; sem confirmação em duas etapas além do POST Abrir
- [X] T019 [US2] Validar US2 via SC-006 e testes de AuthZ do T015; confirmar payload sem PII nominativa

**Checkpoint**: US2 independentemente testável; preview admin-only alinhado à regra

---

## Phase 5: User Story 3 — Matrícula mid-cycle com a mesma elegibilidade (Priority: P1)

**Goal**: Cadastro/reativação / correção de `data_entrada` usam o mesmo predicado via `ensure`; snapshot = Avaliacao existente permanece; ciclo encerrado → 0  
**Independent Test**: Ciclo aberto com D — elegível → 1; > D / sem data → 0; encerrado → 0; corrigir data sem Avaliacao → pode criar 1; editar data após matrícula → Avaliacao permanece  
**Allowlist**: `enrollment.py` (já gated na fundação), `tests/test_mid_cycle_enrollment.py`, contrato 002 — **proibido** apagar Avaliacao; **proibido** mudar `get_visible_users` / forms AuthZ

### Tests for User Story 3

- [X] T020 [P] [US3] Atualizar `tests/test_mid_cycle_enrollment.py` para o predicado 015: ativo elegível; entrada > D / sem data → `None`; snapshot (editar `data_entrada` após matrícula **não** remove Avaliacao); ciclo encerrado → 0

### Implementation for User Story 3

- [X] T021 [US3] Confirmar/ajustar pontos de invocação mid-cycle (RegisterForm / UserUpdateForm em `apps/accounts/forms.py` e `apps/organization/forms.py`) para continuar chamando `ensure_avaliacao_for_user` **sem** mudar AuthZ — elegibilidade só no backend; `data_entrada` permanece opcional no RegisterForm (FR-009)
- [X] T022 [P] [US3] Atualizar `specs/002-pos-mvp-hardening/contracts/mid-cycle-enrollment-contract.md` para documentar elegibilidade = predicado 015 e que `open_cycle` deixa de matricular “todos os ativos”
- [X] T023 [US3] Validar US3 via SC-003/SC-004 e `pytest tests/test_mid_cycle_enrollment.py -q`; confirmar zero remoção/desfazer etapa por mudança de data

**Checkpoint**: US1+US3 — abertura e mid-cycle compartilham o mesmo predicado

---

## Phase 6: User Story 4 — Backfill da data de entrada a partir do backup (Priority: P1)

**Goal**: Comando `backfill_data_entrada` preenche só `data_entrada` vazia a partir de “Data admissão”; dry-run / atomic / idempotente; sem UI; sem abrir/fechar ciclo  
**Independent Test**: Dry-run 0 writes; persist só NULL; 2ª run delta 0; data já preenchida intacta; amostra mascarada; spy sem `open_cycle`/`close_cycle`/`ensure`/`advance_stage`  
**Allowlist**: `admission_backfill/**`, comando, extensão mínima `parse_xlsx`/`report` — **proibido** mutar importer 010 “full”; **proibido** UI de upload

### Tests for User Story 4

- [X] T024 [P] [US4] Criar `tests/test_backfill_data_entrada.py`: dry-run 0 writes; persist só `NULL`; idempotência delta 0; não chama `open_cycle`/`close_cycle`/`ensure_avaliacao_for_user`/`advance_stage`; amostra mascarada; demais campos intactos

### Implementation for User Story 4

- [X] T025 [P] [US4] Estender `apps/accounts/services/legacy_import/parse_xlsx.py` o mínimo necessário para ler coluna **“Data admissão”** (reuso `_load_sheet_rows` / headers); parse de datas via `parse_legacy_date` em `apps/accounts/services/legacy_import/dates.py` — **MUST NOT** reabrir allowlist do importer 010 full
- [X] T026 [US4] Implementar match + parse em `apps/accounts/services/admission_backfill/resolve.py` (e-mail iexact → `solides_id`/`canonicalize_id`; órfão/ambíguo sem inventar User) conforme [contracts/admission-backfill-command-contract.md](./contracts/admission-backfill-command-contract.md)
- [X] T027 [US4] Implementar orquestração dry-run/persist/report em `apps/accounts/services/admission_backfill/importer.py`: preenche só `data_entrada` NULL; `transaction.atomic` no persist; **MUST NOT** tocar nome/email/área/cargo/gestor/`is_active`; **MUST NOT** chamar open/close/ensure/advance
- [X] T028 [P] [US4] Estender `apps/accounts/services/legacy_import/report.py` com seções/totais do backfill + amostra mascarada (padrão 010) se necessário para o relatório do comando
- [X] T029 [US4] Completar management command `apps/accounts/management/commands/backfill_data_entrada.py` com `--colaboradores` obrigatório, `--dry-run`, `--report-file`; exit 0/1; CLI fina sem regra de domínio; sem UI
- [X] T030 [US4] Validar US4 via SC-007 e `pytest tests/test_backfill_data_entrada.py -q`; confirmar imports 010/011/013/014 **não** exigem corte

**Checkpoint**: Backfill operacional pronto para produção com legado (pré-req do corte)

---

## Phase 7: User Story 5 — Ciclos históricos e denylist intactos (Priority: P2)

**Goal**: Ciclos encerrados/`admitidos_ate=NULL` intactos; imports 010–014 sem exigir corte; denylist de comportamento vazia; checklist 008 avisório  
**Independent Test**: Ciclo 011/arquivo sem corte = mesmo conjunto de Avaliações; `pytest` stage/scope/rejeição/fórmula verde **sem** mudar asserts; `git diff` denylist vazio  
**Allowlist**: apenas asserts/fixtures que assumiam “todos os ativos” (atualizar de propósito) — **proibido** “corrigir” denylist mudando produto

### Tests / Gates for User Story 5

- [ ] T031 [P] [US5] Rodar regressão denylist: `pytest tests/test_stage_machine.py tests/test_scope.py` (+ rejeição/fórmula vigentes) `-q` **sem** alterar asserts de negócio alheios; atualizar **somente** testes que assumiam matrícula = todos os ativos para o novo contrato
- [ ] T032 [US5] Validar ciclo encerrado/importado com `admitidos_ate IS NULL` permanece com o mesmo conjunto de Avaliações (0 criações/remoções por “reler” elegibilidade) — teste dedicado em `tests/test_open_cycle_admission_cutoff.py` ou fixture 011 sample
- [ ] T033 [US5] Gate gold: `git diff` vs base da feature nos paths denylist (`apps/cycles/services/stage.py`, `close_cycle`, `apps/goals/services/approval.py`, `apps/reviews/services/evaluation.py`, `apps/dashboard/services/adherence.py`, `apps/accounts/services/scope.py`, `apps/talent/`, PDI produto listado no contract, `apps/dashboard/urls.py`) = **vazio de comportamento**; allowlist restrita aos paths 015; confirmar checklist 008 ainda avisório na abertura

**Checkpoint**: SC-005 / SC-009 — histórico e denylist protegidos

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validação E2E e limpeza cross-cutting após US1–US5

- [ ] T034 [P] Executar validação ponta a ponta de `specs/015-cycle-admission-cutoff/quickstart.md` (backfill dry-run → persist → abrir com preview → mid-cycle → histórico → AuthZ → gold)
- [ ] T035 [P] Rodar suite focada: `pytest tests/test_open_cycle_admission_cutoff.py tests/test_mid_cycle_enrollment.py tests/test_backfill_data_entrada.py -q` e confirmar SC-001…SC-009 cobertos
- [ ] T036 Revisar diff final: zero AlterField em `data_entrada`; zero M2M; zero Celery/DRF/SPA; mensagem de abertura alinhada a FR-013; `CustomUser.data_entrada` e RegisterForm opcional intactos

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências
- **Foundational (Phase 2)**: Depende do Setup — **BLOQUEIA** todas as user stories
- **US1 (Phase 3)**: Depende da Fundação — 🎯 MVP
- **US2 (Phase 4)**: Depende da Fundação; idealmente após campo de abertura da US1 (mesmo fluxo UI), mas serviço de contagens pode paralelizar com T011 após T007
- **US3 (Phase 5)**: Depende da Fundação (T008); testes mid-cycle após predicado estável; pode paralelizar com US2
- **US4 (Phase 6)**: Depende do Setup (stubs); **independente** de US1–US3 no código — pode paralelizar após Fundação
- **US5 (Phase 7)**: Depende de US1–US4 desejadas estarem integradas (gate final de não-regressão)
- **Polish (Phase 8)**: Depende das stories entregues

### User Story Dependencies

- **US1 (P1)**: Após Fundação — núcleo MVP
- **US2 (P1)**: Após Fundação (+ UI de abertura da US1 para preview no mesmo fluxo)
- **US3 (P1)**: Após Fundação (ensure já gated); valida caminhos mid-cycle / snapshot
- **US4 (P1)**: Independente funcionalmente (accounts/CLI); pré-req **operacional** de produção com legado
- **US5 (P2)**: Gate de proteção — após mudanças allowlist estabilizadas

### Within Each User Story

- Testes (quando listados) → implementação → validação SC
- Models/migration antes de serviços que os usam
- Predicado antes de `open_cycle` / preview / mid-cycle asserts
- Story complete antes do gate US5 / Polish

### Parallel Opportunities

- T002 ∥ T003 (stubs)
- T006 ∥ T004/T005 (exceção vs model/migration em arquivos distintos; migration após model)
- T010 testes US1 ∥ preparação de forms (após Fundação)
- T015 ∥ T016 (testes AuthZ vs serviço de contagens)
- T020 ∥ T022 (testes mid-cycle vs doc contrato 002)
- T024 ∥ T025 ∥ T028 (testes / parse / report em arquivos distintos)
- US2 ∥ US3 ∥ US4 após Fundação (times diferentes)
- T034 ∥ T035 no Polish

---

## Parallel Example: User Story 1

```bash
# Após Fundação (T004–T009):
Task: "Criar tests/test_open_cycle_admission_cutoff.py (T010)"
Task: "Expor campo Admitidos até em forms/templates (T013)"

# Sequencial após testes vermelhos:
Task: "Estender open_cycle com gate de corte (T011)"
Task: "Atualizar CicloOpenView + mensagem (T012)"
Task: "Validar US1 / SC-001 SC-002 SC-008 (T014)"
```

## Parallel Example: User Story 4

```bash
Task: "Criar tests/test_backfill_data_entrada.py (T024)"
Task: "Estender parse_xlsx para Data admissão (T025)"
Task: "Estender report.py seções backfill (T028)"

# Depois:
Task: "resolve.py match + parse (T026)"
Task: "importer.py dry-run/persist (T027)"
Task: "comando backfill_data_entrada (T029)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (schema + predicado + ensure + conftest)
3. Completar Phase 3: US1 (open_cycle + UI + mensagem + testes)
4. **STOP and VALIDATE**: SC-001 / SC-002 / SC-008
5. Demo MVP de coorte por admissão na abertura

### Incremental Delivery

1. Setup + Fundação → predicado e schema prontos
2. US1 → MVP abertura
3. US2 → preview honesto
4. US3 → mid-cycle alinhado + contrato 002
5. US4 → backfill legado (habilita produção)
6. US5 → gold denylist / histórico
7. Polish → quickstart E2E

### Parallel Team Strategy

1. Time fecha Setup + Fundação juntos
2. Depois:
   - Dev A: US1 → US2 (UI abertura/preview)
   - Dev B: US3 (enrollment/testes mid-cycle)
   - Dev C: US4 (backfill CLI)
3. Todos: US5 gate + Polish

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- [USn] mapeia para user stories do spec.md
- Backend = fonte da regra (FR-015); UI só coleta + preview
- Clarifications Session 2026-08-20 **fechadas** — não reabrir
- Commit após cada task ou grupo lógico
- Parar em qualquer checkpoint para validar a story
- Evitar: hard-block 008, M2M, AlterField `data_entrada`, Celery para o corte, lista nominativa no preview
