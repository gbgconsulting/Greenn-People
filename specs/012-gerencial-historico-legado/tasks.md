---
description: "Task list for feature implementation"
---

# Tasks: Visualizações Gerenciais e Históricas Pós-Legado

**Input**: Design documents from `/specs/012-gerencial-historico-legado/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme research R14, path-allowlist (seção Testes), SC-007 e quickstart.md. Fixtures via `tests/conftest.py` / factories (N de ciclos 12–20 para teto). **MUST NOT** ler `data/legado-solides/raw/`. Regressão `test_stage_machine` / `test_scope` / `test_reject_stage_invariant` **sem** alterar asserts de domínio.

**Organization**: Tasks por user story. Sequência obrigatória do plan: Fundação → US1 P1 → US2 P1 → US3 P2. **MVP = Fundação + US1**. US2 consome helpers de US1. US3 **não** começa antes do default operacional estável.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que proponha alterar denylist ([contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md) / [contracts/path-allowlist.md](./contracts/path-allowlist.md)) é **INVÁLIDA**:

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de estados | `apps/cycles/services/stage.py` |
| Abrir / fechar ciclo | `apps/cycles/services/cycle.py`; views open/close |
| Aprovação | `apps/goals/services/approval.py` |
| Avaliação / notas | Mutators `apps/reviews/services/evaluation.py`; 6.5.5; `nota_final_lider` |
| Aderência (fórmula) | `apps/dashboard/services/adherence.py` (`compute_adherence`); nova task Celery |
| AuthZ / escopo | `apps/accounts/services/scope.py`; `get_visible_users`; mixins |
| Snapshots / schema | Write-once; migrations de nota; PDI |
| Stack | SPA, DRF, lib nova de gráfico, Chart ≠ 4.5.1, plugin npm |
| Rotas | Página `/historico/`; path novo em `apps/dashboard/urls.py` / `apps/cycles/urls.py` |
| Pessoal | Tendência / `visao=historico` em `dashboard/personal` |
| Freeze | Reabrir A/B/C de paleta/shell além da incrementação D |

**Permitido apenas** a allowlist em [contracts/path-allowlist.md](./contracts/path-allowlist.md). **Teste de ouro**: desligar CSS/charts/toggle **não** muda etapa, aprovação, notas, visible, open/close nem snapshots.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US3 conforme spec.md
- Paths relativos à raiz; cada task cita path **allowlist** e reforça **denylist intacta**

## Path Conventions

Monólito Django na raiz. Apresentação em `apps/dashboard` + context mínimo em `apps/cycles/views.py`. Zero models/migrations. Chart.js **4.5.1** já no monólito.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar contratos e criar esqueleto do builder de tendência (preenchido na US3)  
**Pré-requisito**: imediato — spec 011 aplicada no ambiente de validação; 005/007/009 no código

- [X] T001 Confirmar allowlist/denylist congeladas em `specs/012-gerencial-historico-legado/contracts/path-allowlist.md` e `contracts/non-goals-denylist.md` (constantes do plan: `DENSITY_TOP_N=8`, `HISTORY_DEFAULT_N=8`, query `visao=historico`; sem path novo; denylist inclui `stage.py` / `cycle.py` / `adherence.py` fórmula / `scope.py`)
- [X] T002 Criar stub `apps/dashboard/services/history.py` com docstring da API pública `build_stage_history(visible, ciclos)` — **recebe** QS `visible` já resolvido + lista ≤ N ciclos; **MUST NOT** chamar `get_visible_users`; **MUST NOT** chamar `compute_adherence`; corpo ainda `NotImplementedError` (allowlist; denylist intacta)

**Checkpoint**: Contratos congelados; módulo `history` importável; zero alteração de domínio

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Densidade Top-N, empty kinds, seletor agrupado e Freeze D — **BLOQUEIA** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. Zero alteração em denylist. Zero fallback silencioso ainda (isso é US1).

### Tests for Foundation (TDD)

> **NOTE: Escrever estes testes PRIMEIRO e garantir que FALHAM antes da implementação**

- [X] T003 [P] Adicionar testes de `top_n_with_others` em `tests/test_chart_payloads.py`: (a) contagens → soma residual `"Outros"`; (b) cobertura % → `sum(com)/sum(total)` do residual, **não** média de percentuais; (c) gap `bar_grouped` → Top-N por \|gap\| com nota, resto omitido sem média inventada; (d) etapas / Status Triad **não** passam pelo corte; (e) N=8; fixtures 12–20 categorias; **nunca** `data/legado-solides/raw/` (allowlist testes; denylist intacta)

### Implementation for Foundation

- [X] T004 Implementar constantes `DENSITY_TOP_N = 8`, `HISTORY_DEFAULT_N = 8`, `OTHERS_LABEL = "Outros"` e helper `top_n_with_others` em `apps/dashboard/chart_payloads.py` (shape 009 intacto: `has_data` / `labels` / `values` / `series`; denylist intacta)
- [X] T005 Aplicar `top_n_with_others` em `coverage_bar_payload` em `apps/dashboard/chart_payloads.py` **antes** de emitir labels (cobertura ponderada no residual; etapas/`categorical_counts_payload` e doughnut de aderência **fora** deste corte; denylist intacta)
- [X] T006 Adicionar cópias canônicas dos empty kinds (`operacional`, `escopo`, `sem_dado`, `sem_nota`) em `apps/dashboard/chart_payloads.py` (ex. `EMPTY_KIND_COPY`) para reuso pelas views; `_chart_block.html` continua: `has_data !== true` → `templates/components/empty_state.html`, sem gráfico fantasma (allowlist; denylist intacta)
- [X] T007 [P] Formalizar Freeze D em `docs/design-system.md` (FR-019): teto Top-N+Outros, default operacional vs `visao=historico`, taxonomia de empty, leveza (grid off, pouco ink, `area` tendência, `bar_horizontal` ranking, doughnut+centro). **Não** reabrir Freeze A/B/C de paleta/shell; catálogo 009 permanece referência (allowlist; denylist intacta)
- [X] T008 [P] Criar `apps/dashboard/services/ciclo_options.py` com `resolve_operational_ciclo(request)` (default `get_open_ciclo()`; `?ciclo=<pk>` só intenção explícita; **MUST NOT** fallback para encerrado) e `grouped_ciclo_options(q=)` (`<optgroup>` Operacional / Arquivo; arquivo por `-data_inicio`; se arquivo > 20, filtro GET `q` no nome) — builders **recebem** visible; denylist `scope.py` intacta
- [X] T009 Criar include `templates/dashboard/_ciclo_selector.html` consumindo `grouped_ciclo_options` (GET completo da página, **não** HTMX no chart; denylist intacta)
- [X] T010 [P] Tokens de toggle/seletor em `static/src/input.css` **somente** se T007 exigir classe nova; se exigir, rebuild `static/css/tailwind.css` na mesma entrega. Se não exigir, registrar skip na task. **Não** tocar `static/js/dashboard_charts.js` com `htmx:afterSwap` (init permanece `DOMContentLoaded`; Chart.js 4.5.1; denylist intacta)
  **SKIP 2026-08-14**: T007/Freeze D não exige classe nova (`docs/design-system.md` § Incrementação D e Tokens CSS). Seletor T009 já consome `.form-control`, utilitários (`font-ui`, `text-ink-muted`) e `button.html`. `static/src/input.css` e `static/css/tailwind.css` intocados. `dashboard_charts.js` intocado (init `DOMContentLoaded`; Chart.js 4.5.1; sem `htmx:afterSwap`). Denylist intacta.

**Checkpoint**: Helper Top-N testado; empty kinds canônicos; seletor agrupado reutilizável; Freeze D documentado; user stories podem começar

---

## Phase 3: User Story 1 - Marina opera o ciclo vigente sem o arquivo legado explodir a tela (Priority: P1) 🎯 MVP

**Goal**: Painel admin, lista/detalhe de ciclo e pessoal usam ciclo **aberto** como default; empty operacional honesto sem fallback silencioso; KPIs não misturam arquivo; pipeline de etapas é o visual principal; Top-N no pessoal; arquivo só por seletor explícito

**Independent Test**: Com dump da 011 (ou fixtures 12–20 ciclos encerrados) e **zero** ciclo aberto, GET `/dashboard/admin/` mostra empty operacional leve — nenhum encerrado selecionado em silêncio, sem gráfico fantasma. Ao abrir um ciclo operacional, pipeline e KPIs refletem **somente** esse ciclo. Pessoal tem Top-N + empty, **sem** toggle de tendência. Quickstart §1.

### Tests for User Story 1 (TDD) ⚠️

> **NOTE: Escrever estes testes PRIMEIRO e garantir que FALHAM antes da implementação**

- [X] T011 [P] [US1] Criar `tests/test_dashboard_operational_default.py`: admin sem ciclo aberto → empty `operacional`, **nenhum** `ciclo_indicador`/encerrado implícito, sem payload de labels do arquivo; admin com aberto → KPIs/pipeline só desse ciclo; `percentual_encerrados` **não** é KPI de saúde; `?ciclo=` explícito carrega arquivo sem virar default da home (allowlist testes; denylist intacta)
- [X] T012 [P] [US1] Estender `tests/test_ciclo_detail.py`: cabeçalho `concluida` sem nota → empty `sem_nota` em desempenho/gap/aderência; pipeline de etapa MAY permanecer; copy **não** trata como “100% saudável de desempenho”; AuthZ `AdminCyclesMixin` intacta (allowlist testes; denylist intacta)
- [X] T013 [P] [US1] Estender `tests/test_chart_payloads.py` (ou o arquivo de T011) para gap pessoal: Top-N por \|gap\| entre competências **com nota**; resto omitido; `null` ≠ 0; **sem** série `visao=historico` no pessoal (allowlist testes; denylist intacta)

### Implementation for User Story 1

- [X] T014 [US1] Remover fallback `ciclo_indicador` em `AdminDashboardView.get_context_data` em `apps/dashboard/views.py` (trecho `ciclo_aberto or Ciclo.objects.filter(status=ENCERRADO)...first()`); default = `resolve_operational_ciclo` de T008; denylist intacta
- [X] T015 [US1] Substituir KPIs de `_ciclos_resumo` / `percentual_encerrados` em `apps/dashboard/views.py` e `templates/dashboard/admin.html`: 1–3 KPIs do **ciclo aberto** (totais/gargalo de pipeline, pendências, “sem avaliação”); arquivo, se aparecer, é copy/seletor (“N ciclos no arquivo”), nunca % de governança (FR-004; denylist intacta)
- [X] T016 [US1] Reordenar `templates/dashboard/admin.html`: visual principal = `bar_horizontal` de etapas (`chart_ciclo_progresso`); doughnut de aderência **só** com snapshot real, senão empty `sem_nota`/`sem_dado`; hierarquia KPI → pipeline → drill; empty operacional de página quando não há aberto (usar cópias T006; denylist intacta)
- [X] T017 [US1] Incluir `templates/dashboard/_ciclo_selector.html` em `templates/dashboard/admin.html` e injetar `grouped_ciclo_options` no context de `AdminDashboardView` em `apps/dashboard/views.py` (`?ciclo=` explícito; home **não** defaulta no escolhido na próxima visita sem query; denylist intacta)
- [X] T018 [US1] Destacar ciclo aberto vs arquivo em `CicloListView` / `templates/cycles/ciclo_list.html` (agrupamento visual; paginação `paginate_by=20` do mixin intacta); confirmar `templates/cycles/ciclo_list_partial.html` **não** inclui `_chart_block` (FR-017; `apps/cycles/urls.py` intocável; denylist intacta)
- [X] T019 [US1] Ajustar apresentação em `CicloDetailView` (`apps/cycles/views.py`) e `templates/cycles/ciclo_detail.html`: pipeline principal; cobertura já com Top-N via T005; aderência/gap empty `sem_nota` se cabeçalho legado sem desempenho; copy de KPI de conclusão = processo/etapa, não saúde de nota; **sem** rota nova (denylist intacta)
- [X] T020 [US1] Aplicar Top-N por \|gap\| em `PersonalDashboardView._chart_gaps_competencia` em `apps/dashboard/views.py` (competências com nota; resto omitido; `null` permanece `null`); empty honesto de gap/nota já existente; **MUST NOT** ler `visao=` (allowlist; denylist intacta)
- [X] T021 [US1] Garantir densidade + empty + estética Freeze D em `templates/dashboard/personal.html` **sem** toggle/query de tendência; Chart.js 4.5.1 só via `extra_js` vigente (FR-016; denylist intacta)

**Checkpoint**: US1 funcional e testável sozinha — admin/lista/detalhe/pessoal com default aberto, empty honesto e densidade. MVP demonstrável.

---

## Phase 4: User Story 2 - Bruno vê o time no ciclo operacional com pipeline e painel gerencial (Priority: P1)

**Goal**: Time, estrutura e aderência seguem o mesmo default aberto + empty operacional + seletor explícito + Top-N; cobertura ≠ aderência; pipeline do escopo (incl. “sem avaliação”); charts fora do swap HTMX

**Independent Test**: Líder com escopo e ciclo aberto vs sem ciclo; zero dado fora de `get_visible_users`; nenhum gráfico saturado; empty honesto quando aplicável; paginação HTMX não quebra o canvas. Quickstart §2.

**Depends on**: Fundação + helpers/seletor de US1 (T008/T009/T014). AuthZ das views **inalterada**.

### Tests for User Story 2 (TDD) ⚠️

- [X] T022 [P] [US2] Estender `tests/test_dashboard_operational_default.py`: `TeamDashboardView` / estrutura / aderência sem ciclo aberto → empty `operacional` (sem série inventada nem encerrado implícito); com aberto → pipeline/KPIs só do escopo; `?ciclo=` explícito; líder sem subordinados → empty `escopo` (allowlist testes; denylist intacta)
- [X] T023 [P] [US2] Estender `tests/test_structure_coverage.py`: cobertura área/cargo com >8 categorias → ≤8 rótulos + `"Outros"` ponderado; cobertura ≠ aderência (labels/seções); builder continua **recebendo** `visible` (allowlist testes; denylist intacta)

### Implementation for User Story 2

- [X] T024 [US2] Passar `TeamDashboardView` em `apps/dashboard/views.py` para `resolve_operational_ciclo` (T008): sem aberto → empty operacional (já há ramo `ciclo is None` em `_scope_status_counts`; garantir payload `has_data=false`); `?ciclo=` só explícito; ranking/atenção com densidade se houver eixo longo; **não** chamar `get_visible_users` de outro usuário (denylist intacta)
- [X] T025 [US2] Atualizar `templates/dashboard/team.html`: 1–3 KPIs → pipeline `bar_horizontal` (etapas + `sem_avaliacao`) → drill; empty operacional; include `_ciclo_selector.html`; **sem** `_chart_block` em `templates/dashboard/team_list_partial.html` (FR-017; denylist intacta)
- [X] T026 [US2] Refatorar `StructureDashboardView._resolve_ciclo` em `apps/dashboard/views.py` para `resolve_operational_ciclo`; injetar `grouped_ciclo_options`; densidade já em `coverage_bar_payload` (T005); empty operacional em `templates/dashboard/structure.html` quando não há aberto; seletor agrupado substitui `<select>` plano de ciclos; cobertura ≠ aderência preservada (allowlist `structure.py` só densidade; denylist `adherence.py` fórmula intacta)
- [X] T027 [US2] Refatorar `AdherenceListView._resolve_ciclo` em `apps/dashboard/views.py` para `resolve_operational_ciclo`; doughnut **só** com snapshot, senão empty `sem_dado`/`sem_nota`; seletor agrupado em `templates/dashboard/adherence.html`; confirmar `templates/dashboard/adherence_list_partial.html` **sem** chart; **MUST NOT** chamar `compute_adherence` (denylist intacta)

**Checkpoint**: US1 e US2 independentes — homes gerenciais defaultam aberto; empty honesto; densidade; HTMX de lista íntegro. Default operacional estável → US3 pode começar.

---

## Phase 5: User Story 3 - Evolução histórica entre ciclos no escopo do gestor (Priority: P2)

**Goal**: Modo `?visao=historico` nas URLs já existentes (admin, time, detalhe de ciclo) mostra `area` de etapa/conclusão dos últimos 8 ciclos do escopo; aderência/gap empty até haver dado; pessoal **sem** tendência; sem rota nova

**Independent Test**: Sem `visao=` a home continua operacional. Com `?visao=historico`, tendência N≤8; `?ciclos=` honra o teto; empty `sem_nota` em gap/aderência; pessoal não expõe o modo; nenhuma URL `/historico/`. Quickstart §3.

**Depends on**: US1 + US2 (default operacional estável). **Não** começa antes.

### Tests for User Story 3 (TDD) ⚠️

- [X] T028 [P] [US3] Criar `tests/test_dashboard_history_mode.py`: GET admin/time **sem** `visao=` → operacional (não tendência); `?visao=historico` → `type: area`, ≤ `HISTORY_DEFAULT_N` ciclos, escopo do usuário; `?visao=historico&ciclos=` → só ids pedidos, cap 8, **nunca** ~57; lacuna → `null` não 0; séries de nota/gap/aderência `has_data=false` + empty `sem_nota`; pessoal MUST NOT honrar `visao=historico`; **nenhuma** rota `/historico/` (allowlist testes; denylist intacta)
- [X] T029 [P] [US3] Estender `tests/test_ciclo_detail.py` para `?visao=historico` na página existente (`cycles/<pk>/`): área de etapa/conclusão cap N; empty local de desempenho; resto da página intacto; AuthZ intacta (allowlist testes; denylist intacta)

### Implementation for User Story 3

- [X] T030 [US3] Implementar `build_stage_history(visible, ciclos)` em `apps/dashboard/services/history.py`: Count `Avaliacao.etapa` (+ `sem_avaliacao`) e/ou fração `concluida` por ciclo da janela; payload `grouped_series_payload` / `series_payload` com `type: area`; janela default últimos `HISTORY_DEFAULT_N` por `data_inicio`/`pk`; `?ciclos=` parseado e capado no mesmo N; ponto ausente = `null`; `has_data=false` se a janela no escopo não tem cabeçalhos úteis; **recebe** `visible`; **MUST NOT** `compute_adherence` nem inventar nota (allowlist; denylist intacta)
- [X] T031 [US3] Ligar modo histórico em `AdminDashboardView` e `TeamDashboardView` em `apps/dashboard/views.py`: se `request.GET.get('visao') == 'historico'`, KPIs da janela (evoluiu / estável / sem dado, 1–3) + chart `area` no slot de visual principal; senão comportamento US1/US2 inalterado; admin = visible admin; líder = `get_visible_users` sem o próprio (já na view); **sem** path novo em `apps/dashboard/urls.py` (denylist intacta)
- [X] T032 [US3] Ligar o mesmo modo em `CicloDetailView` em `apps/cycles/views.py` (query na URL existente; `apps/cycles/urls.py` intocável); tendência org cap N; pipeline do `pk` permanece no modo operacional (denylist intacta)
- [X] T033 [US3] Adicionar toggle (link GET `visao=historico`, request completo, **não** HTMX no canvas) em `templates/dashboard/admin.html`, `templates/dashboard/team.html` e `templates/cycles/ciclo_detail.html`; empty `sem_nota` nas séries de aderência/gap do modo histórico; **MUST NOT** adicionar toggle em `templates/dashboard/personal.html` nem em estrutura/aderência nesta fatia (clarification; denylist intacta)

**Checkpoint**: Todas as user stories independentemente funcionais; histórico só por intenção explícita; home operacional intacta

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 100% charts da fatia, regressão de domínio, quickstart e Freeze D fechado

- [ ] T034 [P] Conferir 100% das superfícies com chart (admin, time, estrutura, aderência, `ciclo_list`/`ciclo_detail`, pessoal) contra [contracts/density-history-empty.md](./contracts/density-history-empty.md): teto de densidade, empty honesto, leveza Freeze D, doughnut+centro, `bar_horizontal` ranking, `area` tendência, sem figcaption duplicando label+valor, ~375px sem scroll horizontal do canvas (SC-004 / SC-005 / SC-006)
- [ ] T035 [P] Rodar regressão **sem** alterar asserts: `pytest tests/test_stage_machine.py tests/test_scope.py tests/test_reject_stage_invariant.py` (SC-007); diff denylist vazio (`stage.py`, `cycle.py`, `approval.py`, mutators `evaluation.py`, `adherence.py`, `scope.py`, `tasks.py`, `apps/pdi/**`, migrations de nota)
- [ ] T036 Validar sequência de `specs/012-gerencial-historico-legado/quickstart.md` (gates 0–4) e comandos pytest listados; evidências sugeridas (empty operacional, pipeline do aberto, `area` N≤8, pessoal sem tendência)
- [ ] T037 Confirmar `static/js/dashboard_charts.js`: Chart.js **4.5.1**, init `DOMContentLoaded`, **sem** `htmx:afterSwap`, **sem** plugin npm; `base.html` sem Chart.js global; partials HTMX ainda sem `_chart_block` (FR-017)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — começar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — **BLOQUEIA** todas as user stories
- **User Story 1 (Phase 3)**: Depende da Fundação — MVP
- **User Story 2 (Phase 4)**: Depende da Fundação + seletor/default de US1 (T008/T009/T014)
- **User Story 3 (Phase 5)**: Depende de US1 **e** US2 — default operacional estável (senão a tendência vira a home)
- **Polish (Phase 6)**: Depende das stories desejadas (mínimo US1 para MVP; US1+US2+US3 para 100%)

### User Story Dependencies

- **User Story 1 (P1)**: Após Fundação — sem dependência de outras stories
- **User Story 2 (P1)**: Após Fundação; consome `resolve_operational_ciclo` / `_ciclo_selector` / Top-N de cobertura da Fundação/US1; testável no recorte time/estrutura/aderência
- **User Story 3 (P2)**: Após US1+US2; preenche o stub `history.py`; toggle só em admin/time/`ciclo_detail`

### Within Each User Story

- Testes (TDD) MUST ser escritos e FALHAR antes da implementação
- Helpers/constantes (Fundação) antes de views
- Views antes de templates que consomem o context novo
- Story completa antes da próxima prioridade (US3 especialmente)

### Parallel Opportunities

- T003 ∥ T007 ∥ T008 ∥ T010 (arquivos distintos) após T001; T004 → T005 → T006 sequenciais em `chart_payloads.py`
- T011 ∥ T012 ∥ T013 (três arquivos de teste US1)
- T022 ∥ T023 (testes US2)
- T028 ∥ T029 (testes US3)
- T034 ∥ T035 (polish)
- Após Fundação, US1 é o caminho crítico; US2 **não** deve avançar em `views.py` em paralelo com US1 (mesmo arquivo `apps/dashboard/views.py`)
- Templates `personal.html` (T021) pode seguir em paralelo com `ciclo_list.html` (T018) depois de T020/T014

---

## Parallel Example: User Story 1

```bash
# Testes US1 em paralelo (arquivos distintos):
Task: "Criar tests/test_dashboard_operational_default.py"
Task: "Estender tests/test_ciclo_detail.py (empty sem_nota)"
Task: "Estender tests/test_chart_payloads.py (gap pessoal Top-N)"

# Depois, implementação sequencial em views.py, templates em paralelo quando arquivos diferem:
Task: "Remover ciclo_indicador em apps/dashboard/views.py"
Task: "KPIs + pipeline em templates/dashboard/admin.html"
# Em paralelo após T014:
Task: "Destacar aberto vs arquivo em templates/cycles/ciclo_list.html"
Task: "Top-N gap em PersonalDashboardView + templates/dashboard/personal.html"
```

---

## Parallel Example: User Story 2

```bash
# Testes US2 em paralelo:
Task: "Estender tests/test_dashboard_operational_default.py (time/estrutura/aderência)"
Task: "Estender tests/test_structure_coverage.py (Top-N cobertura)"

# Views no mesmo apps/dashboard/views.py → sequencial T024 → T026 → T027
# Templates distintos podem seguir cada view:
Task: "templates/dashboard/team.html + team_list_partial.html"
Task: "templates/dashboard/structure.html"
Task: "templates/dashboard/adherence.html + adherence_list_partial.html"
```

---

## Parallel Example: User Story 3

```bash
# Testes US3 em paralelo:
Task: "Criar tests/test_dashboard_history_mode.py"
Task: "Estender tests/test_ciclo_detail.py (visao=historico)"

# Implementação: history.py primeiro, depois views (mesmo arquivo, sequencial), templates em paralelo:
Task: "Implementar build_stage_history em apps/dashboard/services/history.py"
Task: "Ligar visao=historico em AdminDashboardView + TeamDashboardView"
Task: "Ligar visao=historico em CicloDetailView"
# Templates:
Task: "Toggle GET em admin.html / team.html / ciclo_detail.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRITICAL — bloqueia stories)
3. Completar Phase 3: User Story 1
4. **STOP and VALIDATE**: Independent Test US1 + quickstart §1 (SC-001 / SC-002 parciais)
5. Demo RH se pronto — operação pós-legado utilizável sem US3

### Incremental Delivery

1. Setup + Foundational → Top-N, empty kinds, seletor, Freeze D
2. US1 → admin/lista/detalhe/pessoal — **MVP**
3. US2 → time/estrutura/aderência no mesmo bloco de default aberto
4. **STOP**: default operacional estável (plan: US3 não começa antes)
5. US3 → `visao=historico` etapa/conclusão N=8
6. Polish → 100% charts + regressão denylist + quickstart

### Parallel Team Strategy

1. Time completa Setup + Foundational juntos
2. Após Fundação:
   - Dev A: US1 (`AdminDashboardView`, admin.html, ciclos)
   - Dev B: testes US1 em arquivos de teste (T011–T013) e depois pessoal (T020/T021) — **não** editar `views.py` ao mesmo tempo que A
3. Após US1: Dev A fecha US2 views; Dev B templates team/structure/adherence
4. Após US1+US2: US3 (`history.py` → views → toggle)

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- [Story] mapeia US1/US2/US3 para rastreabilidade
- Clarifications 2026-08-14 são **fechadas** — não reabrir (métrica US3 = etapa/conclusão; modo = query nas URLs existentes; pessoal sem tendência)
- Calibrar N 8→5 ou 8→10 é apresentação, **não** reabre a spec
- Commit após cada task ou grupo lógico
- Parar em qualquer checkpoint para validar a story
- Evitar: fallback silencioso, `percentual_encerrados` como saúde, plotar ~57 ciclos, tendência no pessoal, rota `/historico/`, mutar denylist, `htmx:afterSwap` no chart, `data/legado-solides/raw/` no CI
