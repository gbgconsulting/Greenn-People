# Tasks: Visualizações Gráficas nos Dashboards

**Input**: Design documents from `/specs/005-dashboard-charts/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Aceite principal = revisão guiada + [quickstart.md](./quickstart.md) (SC-001–007). Sem TDD obrigatório. Incluir apenas verificação de regressão dos testes de escopo existentes no slice 2 (SC-004) — sem suite nova de contract tests.

**Organization**: Tasks agrupadas por user story (US1 admin MVP → US2 time → US3 pessoal) para entrega incremental (FR-012).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: User story (US1–US3); Setup/Foundational/Polish sem label de story
- Incluir caminhos de arquivo exatos nas descrições

## Path Conventions

Monólito Django: `apps/dashboard/`, `templates/dashboard/`, `static/js/`, `docs/`, `tests/` na raiz do repositório.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar superfície de trabalho e criar esqueleto compartilhado de chart (zero apps/models novos)

- [X] T001 Confirmar escopo de código: zero models/migrations; trabalho só em `apps/dashboard/views.py` (+ helper de payload se separado), `templates/dashboard/`, `static/js/dashboard_charts.js` e nota em `docs/design-system.md` — conforme [plan.md](./plan.md) e [data-model.md](./data-model.md)
- [X] T002 [P] Definir versão pinada Chart.js 4.x (jsDelivr UMD) alinhada a [contracts/chart-script-loading.md](./contracts/chart-script-loading.md) e anotar a string CDN escolhida para uso nos templates
- [X] T003 [P] Criar esqueleto vazio `static/js/dashboard_charts.js` (arquivo local de init; ainda sem lógica completa)

**Checkpoint**: Superfície e vendor definidos; JS local existe

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infra compartilhada de payload + init + bloco de UI — **bloqueia** todas as user stories

**⚠️ CRITICAL**: Nenhuma user story de chart começa antes desta fase

- [X] T004 Implementar init Chart.js em `static/js/dashboard_charts.js`: ler payloads via `json_script` / `document.getElementById`, criar `Chart` só se `has_data === true`, legendas/tooltips com labels textuais (FR-007); não desenhar zeros fictícios
- [X] T005 [P] Criar include reutilizável `templates/dashboard/_chart_block.html` (canvas + título + slot/`json_script` id + empty via `templates/components/empty_state.html` quando `has_data` falso) conforme [contracts/chart-script-loading.md](./contracts/chart-script-loading.md)
- [X] T006 Extrair helpers de formatação de payload (cores Status Triad `#059669` / `#d97706` / `#e11d48`, shape `has_data`/`labels`/`values`/`empty_message`) em `apps/dashboard/chart_payloads.py` (ou funções privadas no topo de `apps/dashboard/views.py` se preferir colocalizar) — **sem** novas fórmulas de negócio; só contagem/agrupamento

**Checkpoint**: Foundation pronta — slices US1→US3 podem começar

---

## Phase 3: User Story 1 — Marina vê distribuição de aderência e progresso do ciclo (Priority: P1) 🎯 MVP

**Goal**: Dashboard admin com ≥2 visualizações gráficas (aderência por faixas + progresso/etapas), tabela de menor aderência preservada, empty states honestos, Chart.js só nesta página no MVP

**Independent Test**: Admin autenticado + ciclo/snapshots/avaliações → `/dashboard/admin/` mostra os dois charts + `snapshots_destaque`; sem dados → empty PT-BR sem números inventados ([contracts/admin-charts.md](./contracts/admin-charts.md); SC-001/002/005)

### Implementation for User Story 1

- [ ] T007 [US1] Implementar builder `chart_aderencia_distribuicao` em `apps/dashboard/views.py` (`AdminDashboardView.get_context_data`): contar snapshots do mesmo ciclo de `_aderencia_resumo` / `_snapshots_destaque` via `aderencia_status()` existente (`alta`/`media`/`baixa`) — [contracts/admin-charts.md](./contracts/admin-charts.md)
- [ ] T008 [US1] Implementar builder `chart_ciclo_progresso` em `apps/dashboard/views.py` (`AdminDashboardView`): `Count` por `Avaliacao.Etapa` no `ciclo_indicador` (preferência) ou fatias concluídas/pendentes alinhadas a `_avaliacoes_resumo` — mesmos totais dos cards
- [ ] T009 [US1] Incluir os dois charts em `templates/dashboard/admin.html` via `_chart_block.html` + `{{ ...|json_script:"..." }}`; preservar renderização de `snapshots_destaque` (FR-003)
- [ ] T010 [US1] Carregar Chart.js (CDN pinada) + `{% static 'js/dashboard_charts.js' %}` somente no `{% block extra_js %}` de `templates/dashboard/admin.html` — **não** alterar `templates/base.html` (FR-013)
- [ ] T011 [US1] Garantir empty states honestos no admin (sem snapshot / sem avaliações / sem ciclo): `has_data: false` + mensagem PT-BR; canvas não inicializa com série fictícia (FR-006)
- [ ] T012 [US1] Documentar lib + versão + superfície `dashboard/admin.html` em `docs/design-system.md` (nota de consumo Freeze; sem reabrir marca) — SC-007 MVP

**Checkpoint**: MVP demonstrável só com US1 (FR-012 slice 1)

---

## Phase 4: User Story 2 — Líder vê status do escopo em gráfico (Priority: P2)

**Goal**: Dashboard time com chart de status agregado do escopo (`get_visible_users` completo); HTMX da lista intacto; zero vazamento

**Independent Test**: Líder com subordinados → `/dashboard/team/` chart alinhado a etapas; paginar lista não altera/destrói chart; IDs ⊆ escopo; empty honesto ([contracts/team-charts.md](./contracts/team-charts.md), [contracts/htmx-dashboard-surfaces.md](./contracts/htmx-dashboard-surfaces.md); SC-003/004)

### Implementation for User Story 2

- [ ] T013 [US2] Implementar builder `chart_escopo_status` em `apps/dashboard/views.py` (`TeamDashboardView.get_context_data`): agregar etapas (+ bucket `sem_avaliacao`) sobre **todo** o queryset de `get_queryset()` / `get_visible_users` — **não** usar só `object_list` paginado ([research.md](./research.md) R2/R3)
- [ ] T014 [US2] Incluir chart em `templates/dashboard/team.html` **fora** de `#list-container` / `templates/dashboard/team_list_partial.html`; preservar `hx-target` / `hx-swap` / ids HTMX existentes (FR-011)
- [ ] T015 [US2] Estender `{% block extra_js %}` de `templates/dashboard/team.html` com Chart.js CDN + `dashboard_charts.js` (mesmo padrão do admin)
- [ ] T016 [US2] Empty states do escopo (sem membros / sem ciclo / sem dados úteis) em `templates/dashboard/team.html` via payload `has_data: false` + `empty_state`
- [ ] T017 [US2] Atualizar nota FR-013 em `docs/design-system.md` incluindo `dashboard/team.html`; confirmar `dashboard:structure` **fora** do slice (métrica ≠ etapa)
- [ ] T018 [US2] Rodar regressão de escopo: `pytest tests/test_scope.py` (e correlatos de dashboard se existirem) — SC-004; smoke manual: paginar lista HTMX e confirmar chart estável

**Checkpoint**: US1 + US2 independentes; lista HTMX intacta

---

## Phase 5: User Story 3 — Colaborador vê gaps esperado × nota (Priority: P3)

**Goal**: Painel pessoal com barras comparativas esperado × nota a partir de `competencias_resumo`; 9-box intacta; empty sem inventar gaps

**Independent Test**: Colaborador com notas → `/` (personal) mostra gap gráfico coerente com texto; sem notas → empty; sem `classificacao` → 9-box continua oculta ([contracts/personal-charts.md](./contracts/personal-charts.md); FR-005/009)

### Implementation for User Story 3

- [ ] T019 [US3] Implementar builder `chart_gaps_competencia` em `apps/dashboard/views.py` (`PersonalDashboardView.get_context_data`) a partir de `competencias_resumo` (`nivel_esperado` / `nota_atual`); `has_data: false` se vínculo pendente, lista vazia ou sem notas comparáveis — sem alterar `build_fr005_context` em `apps/reviews/services/evaluation.py` além do necessário para reexpor o já calculado
- [ ] T020 [US3] Incluir chart grouped-bar em `templates/dashboard/personal.html` via `_chart_block.html` + `json_script`; **não** alterar regra `{% if classificacao %}` / `get_visible_classification_for_collaborator` (FR-009)
- [ ] T021 [US3] Estender `{% block extra_js %}` de `templates/dashboard/personal.html` com Chart.js CDN + `dashboard_charts.js`
- [ ] T022 [US3] Empty state PT-BR na área de gaps quando `has_data: false`; `null` em `nota_atual` não vira nota inventada
- [ ] T023 [US3] Atualizar nota FR-013 em `docs/design-system.md` listando também `dashboard/personal.html`

**Checkpoint**: Três slices entregues e independentemente utilizáveis

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validação ponta a ponta, a11y suficiente e guardrails finais

- [ ] T024 Validar checklist [quickstart.md](./quickstart.md) (MVP admin + time + pessoal + SC-001–007) e anotar gaps se houver
- [ ] T025 [P] Verificar viewport móvel (~375px): charts admin/time/pessoal consultáveis por scroll com rótulos legíveis (SC-006); ajustar só altura/grid mínima nos templates de dashboard se necessário — sem tocar shell/nav/topbar
- [ ] T026 [P] Confirmar que `templates/base.html` **não** carrega Chart.js; páginas fora de admin/team/personal não incluem o script
- [ ] T027 Garantir que séries/faixas têm legenda ou texto além da cor (Status Triad + labels) nos três painéis (FR-007)
- [ ] T028 Revisar OUT: zero endpoints REST novos, zero migrations, structure sem chart, 9-box sem interação nova

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — começar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — **BLOQUEIA** todas as user stories
- **User Story 1 (Phase 3)**: Depende da Phase 2 — **MVP**
- **User Story 2 (Phase 4)**: Depende da Phase 2; idealmente após US1 (padrão visual/init validado), mas independentemente testável
- **User Story 3 (Phase 5)**: Depende da Phase 2; sequencial após US2 na entrega (FR-012), independentemente testável
- **Polish (Phase 6)**: Depende dos slices desejados (mínimo US1 para MVP)

### User Story Dependencies

- **User Story 1 (P1)**: Após Foundational — sem dependência de US2/US3
- **User Story 2 (P2)**: Após Foundational — reutiliza `dashboard_charts.js` / `_chart_block.html`; não depende de dados do admin
- **User Story 3 (P3)**: Após Foundational — reutiliza init compartilhado; não altera US1/US2

### Within Each User Story

- Payload/builder na view → template + `json_script` → `extra_js` → empty states → doc FR-013 da superfície
- Story completa e validável antes do próximo slice prioritário

### Parallel Opportunities

- T002 ∥ T003 (Setup)
- T005 ∥ T004 após esqueleto (Foundational: include template vs JS init em arquivos distintos)
- Após Foundational, com capacidade: US2/US3 em paralelo teoricamente (arquivos de template/view distintos por painel), mas entrega recomendada P1→P2→P3
- T025 ∥ T026 (Polish)

---

## Parallel Example: User Story 1

```bash
# Após T007–T008 (payloads no context), em sequência no mesmo template:
Task: "Incluir charts + json_script em templates/dashboard/admin.html"
Task: "extra_js Chart.js só em templates/dashboard/admin.html"
Task: "Empty states has_data false no admin"
```

## Parallel Example: User Story 2

```bash
# Arquivos distintos após builder pronto:
Task: "Chart fora do HTMX em templates/dashboard/team.html"
Task: "Atualizar docs/design-system.md com team.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: quickstart MVP + SC-002/007
5. Demo admin utilizável sozinho (FR-012)

### Incremental Delivery

1. Setup + Foundational → foundation pronta
2. US1 → demo RH (MVP)
3. US2 → demo liderança + regressão escopo
4. US3 → demo colaborador
5. Polish → quickstart completo

### Parallel Team Strategy

1. Time fecha Setup + Foundational junto
2. Depois: Dev A em US1 (crítico path); Dev B pode esboçar builders US2/US3 em branches sem merge até init estável
3. Integrar na ordem P1 → P2 → P3

---

## Notes

- [P] = arquivos distintos, sem depender de tarefa incompleta no mesmo arquivo
- Zero models/migrations; zero API REST; Chart.js só em admin → team → personal
- Faixas/etapas/gaps = formatação do já existente (`aderencia_status`, `Avaliacao.Etapa`, `competencias_resumo`)
- Não reabrir Freeze 004 (shell/nav/topbar/marca) nem WIP Impeccable
- Commit após cada task ou grupo lógico; validar checkpoint antes do próximo slice
)
