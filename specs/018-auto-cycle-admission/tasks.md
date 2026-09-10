# Tasks: Abertura Automática de Ciclos por Admissão

**Input**: Design documents from `/specs/018-auto-cycle-admission/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme plan Project Structure + quickstart V1–V8 e contratos (`auto-cohort-open`, `marco-eligibility`, `multi-open-ciclo`, `governance-surface`, `backend-scope-authz`). Pytest-django; **sem** TDD obrigatório — testes na mesma fase da story após a fatia implementável.

**Organization**: Tasks por user story. Sequência obrigatória do plan: Fundação (multi-open + origem/coorte + calendário BR + predicado marco) → US1+US2 P1 (Beat + coorte idempotente + bootstrap só futuro) → US3 P1 (prazo 20d + alerta não-bloqueante) → US4 P1 (governança RH + AuthZ) → US5 P2 (manual 015 + regressão) → Polish. **MVP = Fundação + US1–US4**. US5 = proteção de arquivo e compatibilidade.

## Escopo inválido (REJEITAR task/PR)

| Zona | Exemplos proibidos |
|------|--------------------|
| Opção B | Lote único sem ritmo por admissão |
| Bootstrap atrasado | Recuperar/abrir marcos passados no go-live ou no dia a dia |
| Feriados locais | Estaduais/municipais; lib `holidays`/`workalendar` sem Complexity Tracking |
| AuthZ no cliente | UI decide elegibilidade/abertura/alerta/visibilidade |
| Lote via HTTP | Pageview/admin “disparar mês” como caminho primário (Beat é o disparo) |
| Papel / app novos | `is_rh`, app Django nova, DRF/SPA |
| Domínio alheio | Stage/fórmulas/9-box/PDI/hierarquia além do necessário a multi-open + governança |
| Visual paralelo | Segunda paleta/fonte “só automático”; rose em alerta ciclo aberto (amber) |

**Permitido**: estender `apps/cycles` (models/services/tasks/views/forms/migrations), `apps/core/calendar_br.py`, `apps/reviews/services/enrollment.py`, `apps/goals/forms.py` (`get_open_ciclo(s)`), `apps/notifications` (Tipo + e-mail alerta), `apps/audit` (`write_audit_log`), `apps/dashboard` / `apps/core/context_processors.py` (multi-open honesto), `config/celery.py`, templates `templates/cycles/`, testes em `tests/test_*.py` listados no plan. Escopo/AuthZ: [contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md). UI: [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md).

**Teste de ouro**: esconder botão ≠ AuthZ; HTTP da governança **não** abre a coorte do mês; reexecução no mesmo 1º dia útil = 0 ciclos/Avaliações duplicados; pessoa com ciclo aberto gera alerta e **não** atrasa os demais; bootstrap = 0 marcos atrasados.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US5 conforme spec.md
- Paths relativos à raiz do repositório

## Path Conventions

Monólito Django na raiz: `apps/cycles/`, `apps/core/`, `apps/reviews/`, `apps/goals/`, `apps/notifications/`, `apps/audit/`, `apps/dashboard/`, `templates/cycles/`, `templates/notifications/`, `config/`, `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar contratos e baseline de código antes de implementar

- [X] T001 Confirmar artefatos e gates em `specs/018-auto-cycle-admission/{plan,spec,research,data-model,quickstart}.md` + `contracts/{backend-scope-authz,ui-visual-consistency,auto-cohort-open-contract,marco-eligibility-contract,multi-open-ciclo-contract,governance-surface-contract,non-goals-denylist}.md` (sequência Fundação→US1–US5; clarifications 2026-09-09 fechadas; MVP=US1–US4)
- [X] T002 [P] Mapear baseline vivo: `apps/cycles/{models,exceptions,views,forms}.py`, `apps/cycles/services/{cycle,eligibility}.py`, `apps/reviews/services/enrollment.py` (`ensure_avaliacao_for_user`), `apps/goals/forms.py` (`get_open_ciclo`), `apps/core/context_processors.py`, `apps/dashboard/services/ciclo_options.py`, `apps/notifications/{models,tasks,emails}.py`, `apps/audit/services.py`, `config/celery.py`, templates `templates/cycles/{ciclo_list,ciclo_list_partial,_ciclo_card,ciclo_detail}.html` + `templates/dashboard/_ciclo_selector.html` — anotar pontos de `_validate_single_open` / `CycleAlreadyOpenError` / enrollment sem `ciclo=` → [contracts/baseline-vivo.md](./contracts/baseline-vivo.md)

**Checkpoint**: Contratos e pontos de extensão identificados; zero código de feature ainda

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Multi-open + campos de coorte + calendário BR + predicado de marco + modelos de run/evento — **BLOQUEIA** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase.

- [X] T003 Remover invariante single-open: apagar/`no-op` `Ciclo._validate_single_open` em `apps/cycles/models.py` (`clean`/`save`) e ajustar `open_cycle` em `apps/cycles/services/cycle.py` para **não** levantar `CycleAlreadyOpenError` por existência de outro `aberto` (manter proteção de reabrir o **mesmo** ciclo se aplicável) — [contracts/multi-open-ciclo-contract.md](./contracts/multi-open-ciclo-contract.md)
- [X] T004 [P] Estender `Ciclo` em `apps/cycles/models.py` com `origem` (`manual`\|`automatico`, default `manual`) e `marco_competencia` (DateField null); `UniqueConstraint` em (`origem=automatico`, `marco_competencia`) quando preenchido; migration aditiva em `apps/cycles/migrations/` — **sem** `RunPython` que abra ciclos; **sem** alterar `CustomUser.data_entrada` ([data-model.md](./data-model.md))
- [X] T005 [P] Criar `apps/core/calendar_br.py` com feriados nacionais (fixos + móveis via Páscoa), `is_business_day(d)` e `first_business_day_of_month(year, month)` — **sem** dependência externa nova ([research.md](./research.md) R3)
- [X] T006 [P] Criar `apps/cycles/services/marco.py` com `next_future_marco(data_entrada, ref_date)` e helpers de elegibilidade automática do mês (`user_eligible_for_auto_marco` / listagem de candidatos) conforme [contracts/marco-eligibility-contract.md](./contracts/marco-eligibility-contract.md) — predicado 015 em `apps/cycles/services/eligibility.py` **intacto**
- [X] T007 Criar modelos `AutoCycleRun` e `AutoCycleEvent` (append-only nos events) em `apps/cycles/models.py` + migration aditiva (`on_delete=PROTECT` nas FKs) conforme [data-model.md](./data-model.md)
- [X] T008 [P] Introduzir `get_open_ciclos()` e documentar `get_open_ciclo()` como default (primeiro de `get_open_ciclos()` por `-data_inicio`) em `apps/goals/forms.py`; alinhar `apps/dashboard/services/ciclo_options.py` para grupo `operacional` = **todos** os abertos; estender `apps/core/context_processors.py` com `ciclos_abertos` + default sem mentir singular
- [X] T009 Em `apps/reviews/services/enrollment.py`, exigir `ciclo=` explícito em caminhos de **criação** nova quando houver ambiguidade multi-open; ramo automático sempre recebe o ciclo da coorte; predicado por `origem` (manual 015 vs auto marco) — sem escolher silenciosamente “o aberto errado”
- [X] T010 [P] Estender `NotificacaoLog.Tipo` em `apps/notifications/models.py` com tipo de alerta ciclo ainda aberto (ex.: `alerta_ciclo_ainda_aberto`); migration aditiva em `apps/notifications/migrations/` — sem alterar tipos existentes

**Checkpoint**: Multi-open possível; schema de coorte/run/evento migrável; calendário + predicado de marco testáveis em isolamento; foundation pronta para US1+

---

## Phase 3: User Story 1 — Abrir o lote do mês no 1º dia útil (Priority: P1) 🎯 MVP

**Goal**: No 1º dia útil do mês, abrir **um** ciclo automático da coorte e matricular todos os elegíveis cujo próximo marco futuro é aquele mês; sem data = fora; idempotente  
**Independent Test**: 10 elegíveis julho + sem data + marco agosto; no 1º dia útil de julho → 1 ciclo auto + exatamente 10 Avaliações; reexecução = 0 duplicatas; dia não-útil = noop (quickstart V1/V2; SC-001/SC-005)

### Implementation for User Story 1

- [X] T011 [US1] Implementar `open_auto_cohort` (ou equivalente) em `apps/cycles/services/auto_cohort.py`: `get_or_create` ciclo `origem=automatico` + `marco_competencia=YYYY-MM-01`; `data_inicio` = dia útil; `data_fim` = +20 dias; `ensure_avaliacao_for_user(user, ciclo=coorte)` para matriculáveis; `write_audit_log` na criação; status/events em `AutoCycleRun`/`AutoCycleEvent` ([contracts/auto-cohort-open-contract.md](./contracts/auto-cohort-open-contract.md))
- [X] T012 [US1] Criar task `run_auto_cycle_admission_daily` em `apps/cycles/tasks.py`: criar run → se não for 1º dia útil → `noop` + event `noop_dia` → senão orquestrar elegíveis + abertura idempotente; clock injetável para testes
- [X] T013 [US1] Registrar Beat `auto-cycle-admission-daily` em `config/celery.py` (ex.: 00:30, após overdue PDI) apontando para `apps.cycles.tasks.run_auto_cycle_admission_daily` — HTTP **não** é disparo primário
- [X] T014 [P] [US1] Contar/registrar ativos sem `data_entrada` como `pendencia_sem_admissao` no run (sem matricular) em `apps/cycles/services/auto_cohort.py`
- [X] T015 [US1] Cobrir lote + idempotência + noop de dia não-útil em `tests/test_auto_cohort_open.py` e calendário em `tests/test_calendar_br.py` (1º dia útil, feriado nacional, fim de semana) + predicado em `tests/test_marco_eligibility.py`

**Checkpoint**: US1 independentemente testável; MVP do lote automático

---

## Phase 4: User Story 2 — Bootstrap seguro para quem já tem tempo de casa (Priority: P1) 🎯 MVP

**Goal**: Legado com anos de casa só entra no **próximo marco futuro**; zero recuperação de marcos passados; sem admissão continua fora até cadastrar  
**Independent Test**: Admitido jan/2022; ref=set/2026 → próximo marco = jan/2027; 0 ciclos/Avaliações atrasados; entra só no 1º dia útil de jan/2027 (quickstart V3; SC-002)  
**Dependência**: `next_future_marco` (T006) + task (T012)

### Implementation for User Story 2

- [X] T016 [US2] Garantir em `apps/cycles/services/marco.py` + `auto_cohort.py` que a rotina **nunca** materializa k passados: go-live no meio do mês após o 1º dia útil **não** abre aquele mês “atrasado”; correção de `data_entrada` só considera próximo marco futuro a partir da correção ([research.md](./research.md) R5)
- [X] T017 [US2] Cobrir bootstrap zero-backfill em `tests/test_auto_bootstrap_no_backfill.py` (admissão antiga; meio do mês; sem data legado; pós-correção sem recuperar passado) alinhado a FR-005 / SC-002

**Checkpoint**: US1+US2 = automação segura para produção (lote + bootstrap)

---

## Phase 5: User Story 3 — Prazo de 20 dias e alerta sem travar a esteira (Priority: P1) 🎯 MVP

**Goal**: Ciclo automático com `data_fim` = ativação + 20 dias corridos; pessoa com ciclo aberto gera alerta RH e **não** recebe nova Avaliação automática; lote dos demais abre normalmente  
**Independent Test**: Coorte A aberta; no marco seguinte 1 pessoa ainda com aberto + ≥1 outro elegível → alerta + coorte B + demais matriculados; alertada sem nova Avaliação; `data_fim` = +20 (quickstart V4; SC-003/SC-004)

### Implementation for User Story 3

- [X] T018 [US3] Em `apps/cycles/services/auto_cohort.py`, particionar candidatos: com ≥1 ciclo `aberto` → events `alerta_ciclo_aberto` **sem** matricular (FR-008); demais → matrícula; alerta **nunca** aborta/adia o lote ([contracts/auto-cohort-open-contract.md](./contracts/auto-cohort-open-contract.md))
- [X] T019 [P] [US3] Implementar envio de e-mail aos `is_admin` ativos em `apps/notifications/emails.py` + task/helper em `apps/notifications/tasks.py` com dedupe `already_sent` (destinatário+tipo+referência+janela do dia); templates `templates/notifications/email/alerta_ciclo_ainda_aberto_{subject,body}.{txt,html}` reusando `templates/emails/base.html`
- [X] T020 [US3] Confirmar na criação da coorte que `data_fim = data_inicio + timedelta(days=20)` (corridos) e que atraso pós-prazo fica sinalizável para governança (rose só atraso real) — sem auto-close hard obrigatório nesta feature
- [X] T021 [US3] Cobrir alerta não-bloqueante + prazo 20d + dedupe de e-mail em `tests/test_auto_open_cycle_alert.py`

**Checkpoint**: Prazo e esteira não-bloqueante verificáveis; US1–US3 prontos

---

## Phase 6: User Story 4 — Governança RH com observabilidade (Priority: P1) 🎯 MVP

**Goal**: Admin vê entrantes, sem admissão, alertas de ciclo aberto e falhas da rotina; líder/colaborador 403; auditoria append-only reconstruível  
**Independent Test**: Após lote com elegíveis/sem-data/alerta, admin lê contagens/detalhes em linguagem RH; não-admin 403; AuditLog/events presentes (quickstart V5; SC-006/SC-007)

### Implementation for User Story 4

- [X] T022 [US4] Criar `apps/cycles/services/governance.py` com queries agregadas do período (entrantes/`matricula`, pendências sem admissão, alertas, falhas, runs) a partir de `AutoCycleRun`/`AutoCycleEvent`
- [X] T023 [US4] Adicionar views admin de governança em `apps/cycles/views.py` (`RequiresAdminMixin`/`AdminCyclesMixin` apenas) + rotas em `apps/cycles/urls.py`; Form/filtros leves em `apps/cycles/forms.py` se necessário — **sem** processar lote do mês na request ([contracts/governance-surface-contract.md](./contracts/governance-surface-contract.md), [contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md))
- [X] T024 [P] [US4] Criar templates `templates/cycles/auto_governance.html` (+ partials se HTMX) no DNA de listagens de ciclos: Fraunces h1, Source Sans 3, Lush Professional, `rounded-lg`, KPIs Status Triad (emerald/amber/rose), um CTA primário soberano, empty states guiados, copy RH (FR-022) — [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md)
- [X] T025 [US4] Linkar governança a partir de `templates/cycles/ciclo_list.html` / `_ciclo_card.html` (copy multi-open honesta + entrada à superfície) sem segundo CTA primário competindo
- [X] T026 [US4] Garantir `write_audit_log` na criação do ciclo automático e events append-only suficientes para reconstruir quem/quando/por quê (FR-016) em `apps/cycles/services/auto_cohort.py` + `apps/audit/services.py`
- [X] T027 [US4] Cobrir AuthZ + superfície em `tests/test_auto_governance_authz.py` (admin 200 com blocos; líder/colaborador 403; sem leak de fila org)

**Checkpoint**: MVP completo (US1–US4) — automação + governança aceitáveis para RH

---

## Phase 7: User Story 5 — Abertura manual e histórico intactos (Priority: P2)

**Goal**: Manual 015 coexiste com automático aberto; ciclos encerrados intocados; edição de `data_entrada` não apaga Avaliação; UI/seletor multi-open honestos  
**Independent Test**: Abrir manual com auto aberto → ambos `aberto`; encerrado não reprocessado; editar data → Avaliação permanece; seletor lista N abertos (quickstart V6/V7; SC-008/SC-009)

### Implementation for User Story 5

- [ ] T028 [US5] Atualizar regressões 015 em `tests/test_open_cycle_admission_cutoff.py` (e correlatos) que assertavam `CycleAlreadyOpenError` por segundo aberto — passar a esperar convivência manual+auto / N abertos; manter corte `admitidos_ate` obrigatório na abertura manual
- [ ] T029 [P] [US5] Ajustar copy/UI multi-open em `templates/cycles/ciclo_list.html`, `_ciclo_card.html`, `ciclo_detail.html` e `templates/dashboard/_ciclo_selector.html` / badges de origem — sem mentir “só um ciclo vigente” ([contracts/multi-open-ciclo-contract.md](./contracts/multi-open-ciclo-contract.md))
- [ ] T030 [US5] Cobrir convivência multi-open + enrollment com `ciclo=` explícito em `tests/test_multi_open_ciclo.py`; snapshot: editar `data_entrada` pós-matrícula não apaga Avaliação; rotina em ciclo encerrado = 0 create/delete (SC-008)
- [ ] T031 [US5] Smoke denylist: confirmar que stage/fórmulas/PDI/escopo hierárquico e non-goals (Opção B, backfill, feriado municipal, papel novo) permanecem fora — checklist alinhado a [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md)

**Checkpoint**: Arquivo e manual 015 protegidos; multi-open honesto no produto

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validação ponta a ponta e consistência visual/observabilidade

- [ ] T032 [P] Rodar suite quickstart em `specs/018-auto-cycle-admission/quickstart.md` (V1–V8) via pytest dos módulos listados + revisão visual vs [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md)
- [ ] T033 [P] Revisar falha parcial: event `falha` + run `parcial`/`falha` em `apps/cycles/services/auto_cohort.py` sem Avaliações órfãs do marco; reexecução idempotente
- [ ] T034 Confirmar Constitution Check do [plan.md](./plan.md) ainda PASS (I–VI + visual); HTTP governança só lê; Beat é o disparo; zero lib de feriados externa
- [ ] T035 [P] Management command opcional de ops/teste (invocar rotina com `--date`) em `apps/cycles/management/commands/` **sem** substituir o Beat como caminho de produção

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — começar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — **BLOQUEIA** todas as user stories
- **US1 (Phase 3)**: Depende da Fundação
- **US2 (Phase 4)**: Depende de T006 + task US1 (T012); pode fechar em paralelo com polish de US1 após T012
- **US3 (Phase 5)**: Depende de `auto_cohort` (T011) + tipo notificação (T010)
- **US4 (Phase 6)**: Depende de modelos run/evento (T007) + runs reais da rotina (US1/US3)
- **US5 (Phase 7)**: Depende de Fundação multi-open (T003/T008); ideal após US1 para fixture auto+manual
- **Polish (Phase 8)**: Após stories desejadas (MVP = até US4)

### User Story Dependencies

- **US1 (P1)**: Após Fundação — núcleo do lote
- **US2 (P1)**: Após predicado marco + task — bootstrap; independentemente testável
- **US3 (P1)**: Após abertura de coorte — alerta/prazo; não bloqueia regressão de US1
- **US4 (P1)**: Após persistência de runs/events — governança; AuthZ isolável
- **US5 (P2)**: Após multi-open fundacional — convivência/regressão

### Within Each User Story

- Serviços/modelo antes de task/views
- Task Beat antes de depender de runs reais na governança
- Implementação antes dos testes da story (nesta feature)
- Story completa antes de subir prioridade seguinte no caminho crítico

### Parallel Opportunities

- T002 ∥ preparação de leitura de contratos
- T004 ∥ T005 ∥ T006 ∥ T010 (após T003 ou em paralelo se não tocar nos mesmos arquivos de save)
- T014 ∥ documentação de Beat após T011/T012 iniciados
- T019 ∥ T020 após particionamento T018 definido
- T024 ∥ T022 (template vs service) após contrato de dados
- T029 ∥ T028 (UI vs testes 015)
- T032 ∥ T033 ∥ T035 no polish

---

## Parallel Example: User Story 1

```bash
# Após Fundação, em paralelo onde arquivos diferem:
Task: "Criar apps/core/calendar_br.py + tests/test_calendar_br.py"
Task: "Criar apps/cycles/services/marco.py + tests/test_marco_eligibility.py"

# Sequencial no caminho crítico do lote:
Task: "Implementar apps/cycles/services/auto_cohort.py"
Task: "Criar apps/cycles/tasks.py + registrar config/celery.py"
Task: "Cobrir tests/test_auto_cohort_open.py"
```

## Parallel Example: User Story 4

```bash
Task: "Criar apps/cycles/services/governance.py"
Task: "Criar templates/cycles/auto_governance.html (+ partials)"
# Depois integrar views/urls e AuthZ tests
```

---

## Implementation Strategy

### MVP First (US1–US4)

1. Phase 1 Setup  
2. Phase 2 Fundação (multi-open + schema + calendário + marco + runs)  
3. Phase 3 US1 — lote no 1º dia útil  
4. Phase 4 US2 — bootstrap zero-backfill  
5. Phase 5 US3 — prazo 20d + alerta não-bloqueante  
6. Phase 6 US4 — governança + AuthZ  
7. **STOP and VALIDATE**: quickstart V1–V5 + Constitution gates  
8. Demo RH se pronto  

### Incremental Delivery

1. Fundação → multi-open + predicado prontos  
2. +US1 → lote automático demonstrável  
3. +US2 → go-live seguro  
4. +US3 → contrato operacional RH (prazo/alerta)  
5. +US4 → MVP governável  
6. +US5 → arquivo/manual 015 + UI multi-open  
7. Polish → V1–V8 verdes  

### Parallel Team Strategy

1. Time fecha Setup + Fundação junto  
2. Dev A: US1+US2 (task/coorte/bootstrap)  
3. Dev B: US3 (alerta/e-mail) após T011  
4. Dev C: US4 (governança UI) após T007  
5. Qualquer um: US5 regressões multi-open/015  

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta  
- [USn] mapeia à story do spec.md  
- Clarifications Session 2026-09-09 são **fechadas** — não reabrir em tasks/PRs  
- Commit após cada task ou grupo lógico  
- Parar em qualquer checkpoint para validar a story isoladamente  
- Evitar: disparo HTTP do mês, backfill de marcos, segunda identidade visual, AuthZ só na UI  
