# Tasks: Gestão de Desempenho, PDI e Talentos

**Input**: Design documents from `/specs/001-gestao-desempenho-talentos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Opcionais — research R10 e plan.md preveem pytest-django apenas nas sprints finais; nenhuma tarefa de teste TDD nesta lista.

**Organization**: Tasks agrupadas por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: User story (US1–US5); Setup/Foundational/Polish sem label de story
- Incluir caminhos de arquivo exatos nas descrições

## Path Conventions

Monólito Django: `config/`, `apps/<domain>/`, `templates/`, `static/` na raiz do repositório.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Migrar o esqueleto atual (`core/` settings) para a estrutura do plan.md e preparar tooling

- [X] T001 Migrar pacote Django `core/` para `config/` (settings, urls, wsgi, asgi) e atualizar `manage.py` para `config.settings.dev`
- [X] T002 Criar split de settings em `config/settings/base.py`, `config/settings/dev.py`, `config/settings/prod.py` e `config/settings/__init__.py`
- [X] T003 Adicionar `django-environ` em `requirements.txt`, criar `.env.example` e carregar `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, Redis e e-mail em `config/settings/base.py`
- [X] T004 [P] Configurar `LANGUAGE_CODE = 'pt-br'` e `TIME_ZONE = 'America/Sao_Paulo'` em `config/settings/base.py`
- [X] T005 Criar pacotes vazios `apps/core/`, `apps/accounts/`, `apps/organization/`, `apps/competencies/`, `apps/goals/`, `apps/cycles/`, `apps/reviews/`, `apps/pdi/`, `apps/talent/`, `apps/dashboard/`, `apps/notifications/`, `apps/audit/` com `apps.py` e registrar em `INSTALLED_APPS` em `config/settings/base.py`
- [X] T006 [P] Adicionar `celery` e `redis` em `requirements.txt`; criar `config/celery.py` e autodiscover em `config/__init__.py`
- [X] T007 [P] Configurar Tailwind CLI standalone: `static/src/input.css`, output `static/css/tailwind.css`, `tailwind.config.js` alinhado a `docs/design-system.md`
- [X] T008 [P] Configurar `ruff` (PEP 8, aspas simples) com `pyproject.toml` ou `ruff.toml` na raiz
- [X] T009 [P] Configurar `TEMPLATES['DIRS']` e `STATICFILES_DIRS` apontando para `templates/` e `static/` na raiz em `config/settings/base.py`

**Checkpoint**: `python manage.py check` passa com settings de dev; estrutura de apps registrada

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura compartilhada que BLOQUEIA todas as user stories — auth, escopo, organização, competências, ciclo/avaliação base, auditoria, UI shell

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase

- [X] T010 Criar `TimeStampedModel` abstrato em `apps/core/models.py`
- [ ] T011 [P] Implementar helpers HTMX `is_htmx` e `htmx_response` em `apps/core/htmx.py` conforme `contracts/htmx-contract.md`
- [ ] T012 [P] Implementar `ScopedObjectMixin` em `apps/core/mixins.py` conforme `contracts/scope-contract.md`
- [ ] T013 Criar `templates/base.html` com HTMX CDN, CSRF `hx-headers`, sidebar/topbar includes e bloco `content`
- [ ] T014 [P] Criar componentes DTL em `templates/components/button.html`, `input.html`, `card.html`, `badge_status.html`, `sidebar.html`, `topbar.html`, `modal.html`
- [ ] T015 [P] Criar `templates/404.html` e `templates/403.html` com mensagem genérica de acesso
- [ ] T016 Implementar `CustomUser` (`USERNAME_FIELD=email`, FKs `cargo`/`area`/`line_manager`, `is_admin`, `email_confirmado_em`, validações FR-028) em `apps/accounts/models.py` e `AUTH_USER_MODEL` em settings
- [ ] T017 Implementar `get_visible_users`, `user_in_scope` e `get_scope_level` em `apps/accounts/services/scope.py` (BFS ORM, `contracts/scope-contract.md`)
- [ ] T018 Implementar auth: `RegisterForm` (@greenn.com.br), `RegisterView`, `LoginView`, `LogoutView`, `PasswordResetView`, `ConfirmEmailView` em `apps/accounts/views.py` / `forms.py` / `urls.py`
- [ ] T019 Criar models `Area` e `Cargo` em `apps/organization/models.py` com `clean()` anti-ciclo em `parent`
- [ ] T020 Implementar CRUD admin de áreas/cargos e listagem/edição de usuários (`UserListView`, `PendingUsersListView`) em `apps/organization/views.py` e `apps/organization/urls.py`
- [ ] T021 [P] Criar models `Escala`, `Competencia`, `CargoCompetencia` em `apps/competencies/models.py`
- [ ] T022 Implementar CRUD de escalas/competências e `CargoCompetenciaUpdateView` em `apps/competencies/views.py` e `apps/competencies/urls.py`
- [ ] T023 Criar model `Ciclo` em `apps/cycles/models.py` (constraint app: um ciclo `aberto`) e serviços `open_cycle` / `close_cycle` em `apps/cycles/services/cycle.py` (abertura cria `Avaliacao` para `is_active=True`)
- [ ] T024 Criar model `Avaliacao` em `apps/reviews/models.py` (`unique_together` ciclo+usuario, campo `etapa`) e migration inicial
- [ ] T025 Implementar máquina de estados `can_advance` / `advance_stage` / `is_cycle_closed` em `apps/cycles/services/stage.py` conforme `contracts/stage-machine-contract.md`
- [ ] T026 Criar model `AuditLog` append-only em `apps/audit/models.py`, signals em `apps/audit/signals.py`, admin read-only e `log_scope_denied` usado pelo `ScopedObjectMixin`
- [ ] T027 Incluir URLconfs dos apps em `config/urls.py` e expor rotas públicas de accounts + shell de dashboard autenticado mínimo em `apps/dashboard/views.py` (`PersonalDashboardView` em `/`)

**Checkpoint**: Admin consegue cadastrar área/cargo/competências, registrar usuário, abrir ciclo (cria avaliações); login por e-mail funciona; escopo e auditoria base disponíveis

---

## Phase 3: User Story 1 — Colaborador entende expectativas e registra desempenho (Priority: P1) 🎯 MVP

**Goal**: Colaborador visualiza competências/nível esperado e metas ligadas a objetivos; registra progresso e conclui autoavaliação

**Independent Test**: Criar colaborador com cargo+competências, ciclo aberto com metas/objetivo; verificar expectativas, progresso e autoavaliação isolados (quickstart Cenário 1)

### Implementation for User Story 1

- [ ] T028 [P] [US1] Criar model `ObjetivoEstrategico` em `apps/goals/models.py` (FK `Ciclo` PROTECT)
- [ ] T029 [P] [US1] Criar model `Meta` em `apps/goals/models.py` (`status`, `status_resultado`, `progresso` 0–100, regras FR-026)
- [ ] T030 [P] [US1] Criar model `AvaliacaoCompetencia` em `apps/reviews/models.py` (snapshots `peso_utilizado` / `nivel_esperado_utilizado` write-once no `save()`)
- [ ] T031 [US1] Implementar `ExpectationsView` em `apps/goals/views.py` e template `templates/goals/expectations.html` (competências+nível esperado+metas; mensagem de vínculo pendente se sem cargo)
- [ ] T032 [US1] Implementar CRUD de metas do colaborador (`MetaListView`, `MetaCreateView`, `MetaForm`) em `apps/goals/views.py` / `forms.py` com `ScopedObjectMixin` e URLs em `apps/goals/urls.py`
- [ ] T033 [US1] Implementar `MetaProgressUpdateView` + `MetaProgressForm` em `apps/goals/` (somente etapa `resultados`, HTMX partial `#meta-row-<pk>`)
- [ ] T034 [US1] Implementar `create_competency_lines` em `apps/reviews/services/evaluation.py` (copia snapshots ao entrar em `avaliacao`)
- [ ] T035 [US1] Implementar `SelfAssessmentView` + `SelfAssessmentForm` em `apps/reviews/views.py` / `forms.py` e template `templates/reviews/self_assessment.html`
- [ ] T036 [US1] Implementar `AdvanceStageView` para avanço colaborador (`input_metas` → `aprovacao_metas`, `resultados` → `aprovacao_resultados`) em `apps/reviews/views.py` com auditoria de `etapa`
- [ ] T037 [US1] Exibir nível esperado e nota atual no dashboard pessoal / expectativas em `templates/dashboard/personal.html` e `templates/goals/expectations.html` (FR-005)

**Checkpoint**: US1 funcional e testável de forma independente (MVP)

---

## Phase 4: User Story 2 — Líder avalia a equipe com critérios objetivos (Priority: P1)

**Goal**: Líder aprova metas/resultados no escopo, registra feedback, avalia competências e obtém nota consolidada reproduzível

**Independent Test**: Time sob um líder; aprovar metas/resultados; notas por competência; nota consolidada; IDOR fora do escopo → 404 + audit (quickstart Cenário 2)

### Implementation for User Story 2

- [ ] T038 [P] [US2] Implementar `approve_meta` / `reject_meta` (e equivalentes de resultado) em `apps/goals/services/approval.py` (aprovador = `line_manager` ou `is_admin` se sem gestor)
- [ ] T039 [US2] Implementar `MetaApproveView` e `MetaRejectView` (HTMX `#meta-row-<pk>`) em `apps/goals/views.py`
- [ ] T040 [US2] Implementar `normalize_score`, `calcular_nota_final_lider` e `calcular_nota_final_autoavaliacao` em `apps/reviews/services/evaluation.py` conforme `contracts/calculation-contract.md`
- [ ] T041 [US2] Implementar `LeaderAssessmentView` + `LeaderAssessmentForm` em `apps/reviews/views.py` / `forms.py` e template `templates/reviews/leader_assessment.html`
- [ ] T042 [P] [US2] Criar model `Feedback` em `apps/reviews/models.py` (`tipo`, `conteudo`, `ciente_em`)
- [ ] T043 [US2] Implementar `FeedbackListView`, `FeedbackCreateView` e `FeedbackAcknowledgeView` em `apps/reviews/views.py` com escopo e histórico
- [ ] T044 [US2] Completar `AdvanceStageView` para etapas de líder (`aprovacao_metas` → `resultados`, `aprovacao_resultados` → `avaliacao` com side-effect de snapshots, `avaliacao` → `feedback`)
- [ ] T045 [US2] Implementar `TeamDashboardView` em `apps/dashboard/views.py` e `templates/dashboard/team.html` (somente `is_leader`, lista escopo)
- [ ] T046 [US2] Garantir `AvaliacaoListView` / `AvaliacaoDetailView` com `ScopedObjectMixin` em `apps/reviews/views.py` (IDOR → Http404 + `log_scope_denied`)

**Checkpoint**: US1 e US2 independentes e funcionais

---

## Phase 5: User Story 3 — PDI colaborador e líder (Priority: P2)

**Goal**: Espaço de PDI com ações, prazos e status; líder propõe ações; atualizações com `updated_at`

**Independent Test**: Criar/atualizar ações de PDI como colaborador e líder sem depender do ciclo aberto (quickstart Cenário 3)

### Implementation for User Story 3

- [ ] T047 [P] [US3] Criar models `PDI` e `AcaoPDI` em `apps/pdi/models.py`
- [ ] T048 [P] [US3] Implementar `calculate_pdi_progress` em `apps/pdi/services/progress.py`
- [ ] T049 [US3] Implementar CRUD `PDIListView`, `PDICreateView`, `PDIDetailView` com `ScopedObjectMixin` em `apps/pdi/views.py` e `apps/pdi/urls.py`
- [ ] T050 [US3] Implementar CRUD HTMX de ações (`AcaoPDIForm`, partials `templates/pdi/acao_list_partial.html`, modal create) em `apps/pdi/views.py` conforme `contracts/htmx-contract.md`
- [ ] T051 [US3] Implementar atualização de status inline de `AcaoPDI` (HTMX) com persistência de `updated_at` e auditoria em `apps/pdi/views.py`
- [ ] T052 [US3] Criar task Celery Beat `mark_overdue_pdi_actions` em `apps/pdi/tasks.py` (status `atrasada` quando `prazo < today`)

**Checkpoint**: US3 testável independentemente do ciclo

---

## Phase 6: User Story 4 — RH centraliza ciclos e monitora aderência (Priority: P2)

**Goal**: Admin abre/encerra ciclos, monitora aderência via snapshot e vê lacunas agregadas por área/cargo

**Independent Test**: Abrir ciclo (avaliações para ativos), painel de aderência, encerrar ciclo bloqueando avanços, visão agregada (quickstart Cenário 4)

### Implementation for User Story 4

- [ ] T053 [US4] Implementar CRUD de ciclos + `CicloOpenView` / `CicloCloseView` em `apps/cycles/views.py` e templates `templates/cycles/`
- [ ] T054 [US4] Implementar CRUD de `ObjetivoEstrategico` sob ciclo em `apps/cycles/views.py` (ou `apps/goals/`) e rotas `/cycles/<pk>/objectives/`
- [ ] T055 [P] [US4] Criar model `AderenciaSnapshot` em `apps/dashboard/models.py`
- [ ] T056 [US4] Implementar task `calculate_adherence_snapshot` em `apps/dashboard/tasks.py` e schedule Beat diário em `config/celery.py`
- [ ] T057 [US4] Implementar `AdherenceListView` e `AdminDashboardView` em `apps/dashboard/views.py` lendo snapshots (sem recálculo síncrono)
- [ ] T058 [US4] Implementar `StructureDashboardView` e visão agregada de lacunas de competências por área/cargo em `apps/dashboard/views.py` / `templates/dashboard/`
- [ ] T059 [US4] Ao encerrar ciclo, bloquear `advance_stage` (`CycleClosedError`) e marcar avaliações incompletas para indicador de conclusão em `apps/cycles/services/cycle.py`

**Checkpoint**: Governança RH operacional; US1–US4 estáveis

---

## Phase 7: User Story 5 — Identificação de talentos e potencial (Priority: P3)

**Goal**: Matriz 9-box desempenho × potencial no escopo do gestor, com filtros por área/cargo

**Independent Test**: Avaliações consolidadas + potencial admin; matriz filtrável no escopo (quickstart Cenário 5)

### Implementation for User Story 5

- [ ] T060 [P] [US5] Criar model `ClassificacaoTalento` em `apps/talent/models.py` (`unique_together` usuario+ciclo)
- [ ] T061 [US5] Implementar `derive_desempenho`, `calculate_quadrante` e `upsert_classification` em `apps/talent/services/classification.py`
- [ ] T062 [US5] Implementar `TalentMatrixView` com filtros área/cargo e escopo hierárquico em `apps/talent/views.py` e `templates/talent/matrix.html`
- [ ] T063 [US5] Implementar `ClassifyTalentView` e `ToggleVisibilityView` (admin) em `apps/talent/views.py` e `apps/talent/urls.py`
- [ ] T064 [US5] Respeitar `visivel_ao_colaborador` na UI do colaborador em `apps/talent/views.py` / templates

**Checkpoint**: Todas as user stories independentemente funcionais

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Notificações, auditoria UI, qualidade, validação end-to-end e preparação de entrega

- [ ] T065 [P] Criar model `NotificacaoLog` em `apps/notifications/models.py` e tasks de e-mail (lembrete etapa/PDI) em `apps/notifications/tasks.py`
- [ ] T066 [P] Implementar `NotificacaoLogListView` em `apps/notifications/views.py` e `AuditLogListView` com filtros em `apps/audit/views.py`
- [ ] T067 Garantir `paginate_by = 20` em todas as `ListView` dos apps e partials HTMX de paginação
- [ ] T068 [P] Revisar UI responsiva e design system em `templates/` e `static/css/tailwind.css` (sprints de refino)
- [ ] T069 [P] Documentar setup local (venv, migrate, Tailwind watch, Celery) em `README.md` alinhado a `specs/001-gestao-desempenho-talentos/quickstart.md`
- [ ] T070 Executar validação manual dos 5 cenários de `quickstart.md` e checks constitucionais (escopo, snapshots, audit append-only, dashboard < 2s)
- [ ] T071 [P] Preparar `requirements.txt` / settings para PostgreSQL (sem recursos exclusivos SQLite) conforme plan.md
- [ ] T072 [P] Adicionar `Dockerfile` e `docker-compose.yml` (app + Redis + Postgres) nas sprints finais
- [ ] T073 Configurar `pytest-django`, `tests/factories.py` e suíte inicial de escopo/máquina de estados em `tests/` (sprints finais, research R10)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — começar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — BLOQUEIA todas as user stories
- **US1 (Phase 3)**: Depende da Foundational — MVP
- **US2 (Phase 4)**: Depende da Foundational; integra dados de US1 mas é testável com fixtures próprias
- **US3 (Phase 5)**: Depende da Foundational (auth + escopo); independente do ciclo aberto
- **US4 (Phase 6)**: Depende da Foundational; beneficia-se de US1/US2 para dados de aderência reais
- **US5 (Phase 7)**: Depende de notas consolidadas (US2) para valor pleno
- **Polish (Phase 8)**: Após as stories desejadas

### User Story Dependencies

- **US1 (P1)**: Após Phase 2 — sem dependência de outras stories
- **US2 (P1)**: Após Phase 2 — usa metas/avaliações; testável com seed mínimo
- **US3 (P2)**: Após Phase 2 — paralelo a US1/US2 possível
- **US4 (P2)**: Após Phase 2 — UI admin de ciclo pode completar o open/close mínimo da fundação
- **US5 (P3)**: Idealmente após US2 (nota_final_lider)

### Within Each User Story

- Models antes de services
- Services antes de views/URLs
- Partials HTMX após views base
- Story completa antes de subir prioridade (salvo paralelismo explícito)

### Parallel Opportunities

- Phase 1: T004, T006, T007, T008, T009 em paralelo após T001–T003
- Phase 2: T011/T012/T014/T015 em paralelo; T021 em paralelo a organization após T010
- Após Phase 2: US3 pode avançar em paralelo a US1; US4 UI de ciclo em paralelo parcial
- Dentro de stories: models marcados [P] em paralelo

---

## Parallel Example: User Story 1

```bash
# Models em paralelo:
Task: "Criar model ObjetivoEstrategico em apps/goals/models.py"
Task: "Criar model Meta em apps/goals/models.py"
Task: "Criar model AvaliacaoCompetencia em apps/reviews/models.py"

# Depois, em sequência:
Task: "ExpectationsView + templates"
Task: "Meta CRUD + progresso HTMX"
Task: "SelfAssessment + advance stage colaborador"
```

## Parallel Example: User Story 3

```bash
Task: "Models PDI e AcaoPDI em apps/pdi/models.py"
Task: "calculate_pdi_progress em apps/pdi/services/progress.py"
# Depois CRUD + HTMX partials
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (CRÍTICO)
3. Completar Phase 3: US1
4. **STOP e VALIDAR**: quickstart Cenário 1
5. Demo interna se pronto

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → MVP transparência
3. US2 → justiça na avaliação
4. US3 → PDI (pode intercalado)
5. US4 → governança RH
6. US5 → 9-box
7. Polish → notificações, Docker, testes

### Parallel Team Strategy

1. Time fecha Setup + Foundational junto
2. Dev A: US1 → US2
3. Dev B: US3 (PDI)
4. Dev C: US4 (ciclos/dashboard) após Ciclo/Avaliacao base
5. US5 após nota consolidada disponível

---

## Notes

- [P] = arquivos distintos, sem dependência de tarefa incompleta
- Labels [US1]–[US5] mapeiam para stories em `spec.md`
- Sem tarefas de teste por story (pytest só em T073 / sprints finais)
- Commit após cada tarefa ou grupo lógico
- Parar em qualquer checkpoint para validar a story
- Evitar: tarefas vagas, conflitos no mesmo arquivo, dependências cruzadas que quebrem independência
