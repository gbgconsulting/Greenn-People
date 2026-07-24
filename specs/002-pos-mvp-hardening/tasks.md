# Tasks: Hardening Operacional Pós-MVP

**Input**: Design documents from `/specs/002-pos-mvp-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Solicitados explicitamente (FR-022 / US6 / `contracts/production-ux-test-contract.md`). Suíte formal em Phase 8 (US6), cobrindo também pós-reprovação, mid-cycle e admin approve.

**Organization**: Tasks agrupadas por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: User story (US1–US6); Setup/Foundational/Polish sem label de story
- Incluir caminhos de arquivo exatos nas descrições

## Path Conventions

Monólito Django: `config/`, `apps/<domain>/`, `templates/`, `static/`, `tests/`, `docs/` na raiz do repositório.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparar tooling de testes e estrutura documental de ops sobre o monólito já existente

- [X] T001 Adicionar `pytest` e `pytest-django` em `requirements.txt` e configurar `pytest.ini` (ou seção `[tool.pytest.ini_options]` em `pyproject.toml`) com `DJANGO_SETTINGS_MODULE=config.settings.dev` e `pythonpath=.`
- [X] T002 [P] Criar `tests/__init__.py` e `tests/conftest.py` com fixtures reutilizáveis (admin, líder, colaborador com hierarquia, ciclo aberto, avaliação + metas)
- [X] T003 [P] Criar diretório `docs/ops/` (README curto apontando futuros `backup.md` e checklist de deploy)

**Checkpoint**: `pytest --collect-only` (ou equivalente) reconhece o pacote `tests/` sem falhar por settings

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infra compartilhada que BLOQUEIA as user stories — auditoria de status de Meta (ator real em US1/US4)

**⚠️ CRITICAL**: Nenhuma user story deve começar antes desta fase

- [X] T004 Incluir tracking de `Meta.status` e `Meta.status_resultado` em `apps/audit/signals.py` (novo `META_TRACKED_FIELDS` + connect nos receivers existentes) para AuditLog append-only com `audit_actor`
- [X] T005 Confirmar que `reject_meta` / `reject_resultado` em `apps/goals/services/approval.py` não chamam `advance_stage` nem alteram `Avaliacao.etapa` (ajuste mínimo se houver regressão)

**Checkpoint**: Mudança de status de Meta gera AuditLog; rejeição não retrocede etapa — base pronta para US1–US6

---

## Phase 3: User Story 1 — Destravar item reprovado sem retroceder a etapa (Priority: P1) 🎯 MVP

**Goal**: Colaborador corrige e reenvia meta/resultado reprovado; itens aprovados e etapa agregada intactos; CTA claro (sem dead-end)

**Independent Test**: Reprovar meta (e depois resultado) em Avaliação na etapa correspondente; editar só o item; reenviar/reaprovar; etapa não retrocede (quickstart C1–C2)

### Implementation for User Story 1

- [X] T006 [US1] Garantir que `reject_meta` / `reject_resultado` em `apps/goals/services/approval.py` persistem `reprovada`/`reprovado` sem auto-`reopen()` e sem mutar etapa (conforme `contracts/post-rejection-contract.md`)
- [X] T007 [US1] Ao salvar correção de meta com `status=reprovada` na etapa `aprovacao_metas`, chamar `Meta.reopen()` em `apps/goals/views.py` / `apps/goals/forms.py` (update de conteúdo elegível)
- [X] T008 [US1] Estender `meta_progress_editable` em `apps/goals/forms.py` para permitir edição quando `status_resultado=reprovado` e etapa = `aprovacao_resultados` (além de `resultados`)
- [X] T009 [US1] Em `MetaProgressUpdateView` / `MetaProgressForm` (`apps/goals/views.py`, `apps/goals/forms.py`), ao salvar progresso elegível pós-reprovação, chamar `Meta.reopen_resultado()` → `pendente`
- [X] T010 [P] [US1] Exibir próximo passo acionável (corrigir / reenviar / reaprovar) em `templates/goals/partials/meta_row.html` e `templates/goals/meta_list_partial.html` quando item estiver reprovado
- [X] T011 [US1] Verificar que `can_advance` / `advance_stage` em `apps/cycles/services/stage.py` seguem exigindo 100% aprovados + ≥1 meta após correções (sem alteração da lista canônica de etapas)

**Checkpoint**: US1 funcional e testável de forma independente (MVP operacional)

---

## Phase 4: User Story 2 — Avaliação automática mid-cycle (Priority: P1)

**Goal**: Cadastro/ativação de colaborador ativo com ciclo aberto cria Avaliação inicial idempotente; sem ciclo aberto, no-op

**Independent Test**: Ciclo aberto + ativar/cadastrar ativo → 1 Avaliação; segundo save sem duplicata; sem ciclo → 0 (quickstart C3)

### Implementation for User Story 2

- [X] T012 [US2] Criar `ensure_avaliacao_for_user` em `apps/reviews/services/enrollment.py` (`get_or_create` com `etapa=input_metas`; retorna `None` se user inativo ou sem ciclo `aberto`) conforme `contracts/mid-cycle-enrollment-contract.md`
- [X] T013 [US2] Invocar `ensure_avaliacao_for_user` após commit em `RegisterForm.save` em `apps/accounts/forms.py` quando o usuário fica ativo
- [X] T014 [US2] Invocar `ensure_avaliacao_for_user` em `UserUpdateForm` / `UserUpdateView` (`apps/organization/forms.py`, `apps/organization/views.py`) quando `is_active` passa a `True`
- [X] T015 [US2] Alinhar `open_cycle` em `apps/cycles/services/cycle.py` para reutilizar `ensure_avaliacao_for_user` (ou manter batch `get_or_create` equivalente) sem duplicar avaliações

**Checkpoint**: US2 independente; admitidos mid-cycle cobertos no ciclo aberto

---

## Phase 5: User Story 3 — Catálogos soft-delete + offboarding com reatribuição em lote (Priority: P2)

**Goal**: Soft-delete + unicidade entre ativos para Área/Cargo/Escala/Competência; reatribuição em lote de liderados antes de desativar gestor

**Independent Test**: Desativar catálogo em uso sem hard-delete; duplicata ativa rejeitada; reatribuir N liderados e só então desativar gestor (quickstart C4)

### Implementation for User Story 3

- [X] T016 [P] [US3] Adicionar `is_active` (default True) e `UniqueConstraint(nome, condition=Q(is_active=True))` em `Escala` e `Competencia` em `apps/competencies/models.py` + migration
- [X] T017 [P] [US3] Adicionar `UniqueConstraint(nome, condition=Q(is_active=True))` em `Area` e `Cargo` em `apps/organization/models.py` + migration
- [X] T018 [US3] Converter `AreaDeleteView` / `CargoDeleteView` em `apps/organization/views.py` (e templates de confirmação) para soft-delete (`is_active=False`) em vez de hard-delete
- [X] T019 [US3] Converter `EscalaDeleteView` / delete de Competência em `apps/competencies/views.py` para soft-delete; atualizar forms em `apps/competencies/forms.py` e `apps/organization/forms.py` para seletores `filter(is_active=True)`
- [X] T020 [US3] Implementar `reassign_direct_reports` em `apps/accounts/services/offboarding.py` (transação, valida `to_manager` ativo ≠ `from_manager`, atualiza todos liderados ativos) conforme `contracts/catalog-offboarding-contract.md`
- [X] T021 [US3] Expor UI de reatribuição em lote (form + view + template) no fluxo de edição/desativação do gestor em `apps/organization/views.py` / `apps/organization/forms.py` / `templates/organization/` (ou `templates/accounts/`)
- [X] T022 [US3] Preservar bloqueio de desativação com liderados ativos em `apps/accounts/models.py` (`_validate_deactivation_without_active_reports`) e garantir que só libera após lote completo + AuditLog de `line_manager_id`

**Checkpoint**: Catálogos íntegros; offboarding com reassign em lote operacional

---

## Phase 6: User Story 4 — Aprovação por administrador (gestor ausente) (Priority: P2)

**Goal**: Admin aprova/reprova no lugar do gestor com ator real na auditoria; líderes comuns fora do escopo continuam bloqueados

**Independent Test**: Admin aprova com gestor presente → status ok + AuditLog.actor=admin; líder fora do escopo → negado (quickstart C5)

### Implementation for User Story 4

- [ ] T023 [US4] Atualizar `_ensure_approver` em `apps/goals/services/approval.py` para permitir `approver.is_admin` sempre (líderes não-admin só se `line_manager`) conforme `contracts/admin-approval-contract.md`
- [ ] T024 [P] [US4] Exibir botões aprovar/reprovar para `request.user.is_admin` em `templates/goals/partials/meta_row.html` (itens `pendente`) sem surface de bypass para líder comum
- [ ] T025 [US4] Garantir que views `MetaApproveView` / `MetaRejectView` (e equivalentes de resultado) em `apps/goals/views.py` rejeitam ação inválida (já aprovado / etapa inelegível) sem AuditLog de sucesso falso; ator = admin via `audit_actor`

**Checkpoint**: Override RH funcional sem enfraquecer escopo hierárquico

---

## Phase 7: User Story 5 — Lembretes dedupe + PDI atraso coerente (Priority: P3)

**Goal**: Jobs de lembrete não reenviam indevidamente; extensão de prazo recalcula atraso e audita

**Independent Test**: Rodar job 2× mesma janela → 1 envio; estender prazo de ação atrasada → status não-atrasado + audit (quickstart C6)

### Implementation for User Story 5

- [ ] T026 [US5] Adicionar campos `referencia` e `janela` (+ índice composto com destinatario/tipo) em `NotificacaoLog` em `apps/notifications/models.py` + migration
- [ ] T027 [US5] Implementar `already_sent` e atualizar tasks em `apps/notifications/tasks.py` / `apps/notifications/emails.py` para skip se log `enviado` com mesma chave ou pendente resolvido (conforme `contracts/reminders-pdi-contract.md`)
- [ ] T028 [US5] Implementar recálculo de atraso ao alterar `prazo` em `apps/pdi/models.py` e/ou `apps/pdi/forms.py` / serviço em `apps/pdi/services/` (`atrasada` + prazo ≥ hoje → `pendente`; prazo ainda passado permanece atrasada)
- [ ] T029 [US5] Incluir `prazo` em `ACAO_PDI_TRACKED_FIELDS` em `apps/audit/signals.py` (status já tracked)

**Checkpoint**: SC-005/SC-006 atendíveis via jobs e alteração de prazo

---

## Phase 8: User Story 6 — Prontidão produção, testes automatizados e polish UX (Priority: P3)

**Goal**: Health + static/backup docs; suíte pytest de escopo/stage/pós-reprovação/mid-cycle/admin; loading/empty/modal a11y

**Independent Test**: `GET /health/` 200; backup doc aplicável; `pytest` falha em violações; UI com loading/empty/modal (quickstart C7)

### Tests for User Story 6 ⚠️

> Escrever testes que falhem nas violações listadas em `contracts/production-ux-test-contract.md`; implementar/ajustar código até passarem.

- [ ] T030 [P] [US6] Criar `tests/test_scope.py` cobrindo `get_visible_users` / IDOR em DetailView (`ScopedObjectMixin` → 404 + audit)
- [ ] T031 [P] [US6] Criar `tests/test_stage_machine.py` cobrindo `can_advance` / `advance_stage` com pré-condições inválidas
- [ ] T032 [P] [US6] Criar `tests/test_post_rejection.py` cobrindo etapa inalterada após reject, reopen, itens irmãos intactos e regra 100%
- [ ] T033 [P] [US6] Criar `tests/test_mid_cycle_enrollment.py` cobrindo `ensure_avaliacao_for_user` (cria / não duplica / no-op sem ciclo)
- [ ] T034 [P] [US6] Criar `tests/test_admin_approval.py` cobrindo approve admin + `AuditLog.actor` e negação a líder fora do escopo
- [ ] T035 [P] [US6] Criar `tests/test_catalog_offboarding.py` cobrindo soft-delete, unicidade ativos e bloqueio/reatribuição de liderados

### Implementation for User Story 6

- [ ] T036 [US6] Implementar view `GET /health/` (DB `SELECT 1`; 200 ok / 503 se DB falhar) em `apps/core/views.py` (ou equivalente) e registrar em `config/urls.py` conforme `contracts/production-ux-test-contract.md`
- [ ] T037 [P] [US6] Definir `STATIC_ROOT` (e WhiteNoise **ou** nota de reverse-proxy) em `config/settings/prod.py` / `requirements.txt` se necessário; documentar `collectstatic` em `docs/ops/`
- [ ] T038 [P] [US6] Escrever `docs/ops/backup.md` com frequência/retenção mínimas e procedimento PostgreSQL aplicável
- [ ] T039 [US6] Criar indicador HTMX compartilhado (`templates/components/htmx_indicator.html` ou equivalente) e aplicar `hx-indicator` nas ações partials críticas de metas/PDI
- [ ] T040 [US6] Criar partial `templates/components/empty_state.html` com CTA condicional e aplicar em listas vazias de metas, ações PDI e catálogos
- [ ] T041 [US6] Endurecer acessibilidade de modal em `templates/components/modal.html` + JS mínimo em `static/js/modal.js` (focus, Escape, restore no trigger; `role="dialog"` `aria-modal="true"`)

**Checkpoint**: Go-live checklist + suíte crítica + polish UX nas telas críticas

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validação end-to-end e limpeza final

- [ ] T042 Executar cenários C1–C7 de `specs/002-pos-mvp-hardening/quickstart.md` e corrigir gaps encontrados
- [ ] T043 [P] Rodar `pytest tests/ -q` e `python manage.py check` com settings de prod-like onde couber; corrigir falhas
- [ ] T044 [P] Revisar mensagens de UI (pt-BR) e labels de CTAs pós-reprovação / empty states nas templates tocadas

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — iniciar imediatamente
- **Foundational (Phase 2)**: Depende do Setup — BLOQUEIA todas as user stories
- **User Stories (Phases 3–8)**: Dependem da Foundational
  - Podem seguir em paralelo se houver capacidade (com cuidado em arquivos compartilhados)
  - Ou sequencialmente por prioridade: P1 (US1→US2) → P2 (US3→US4) → P3 (US5→US6)
- **Polish (Phase 9)**: Depende das stories desejadas concluídas

### User Story Dependencies

- **US1 (P1)**: Após Foundational — independente (MVP)
- **US2 (P1)**: Após Foundational — independente de US1
- **US3 (P2)**: Após Foundational — independente
- **US4 (P2)**: Após Foundational — compartilha `apps/goals/services/approval.py` e `meta_row.html` com US1 (sincronizar se paralelo)
- **US5 (P3)**: Após Foundational — independente
- **US6 (P3)**: Após Foundational — testes formalizam comportamentos de US1–US4; ideal após MVP, mas pode redigir testes em paralelo e implementar asserts conforme stories fecham

### Within Each User Story

- Models/migrations antes de services
- Services antes de views/forms
- Views/forms antes de templates
- Em US6: testes podem ser escritos em paralelo; implementação health/static/UX em seguida

### Parallel Opportunities

- T002 ∥ T003 (Setup)
- T016 ∥ T017 (models catálogo)
- T024 pode paralelizar com trabalho de auditoria já feito em T004
- T030–T035 (suite de testes) em paralelo entre si
- T037 ∥ T038 (docs ops)
- Após Foundational: desenvolvedores distintos em US2 / US3 / US5 enquanto outro fecha US1+US4 em `goals/`

---

## Parallel Example: User Story 1

```bash
# Após T006–T009 (backend reopen/elegibilidade), UI e stage check em paralelo:
Task: "CTAs pós-reprovação em templates/goals/partials/meta_row.html"
Task: "Verificar can_advance 100% em apps/cycles/services/stage.py"
```

## Parallel Example: User Story 6

```bash
# Suite de testes em paralelo:
Task: "tests/test_scope.py"
Task: "tests/test_stage_machine.py"
Task: "tests/test_post_rejection.py"
Task: "tests/test_mid_cycle_enrollment.py"
Task: "tests/test_admin_approval.py"
Task: "tests/test_catalog_offboarding.py"

# Ops em paralelo:
Task: "STATIC_ROOT / WhiteNoise em config/settings/prod.py"
Task: "docs/ops/backup.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational
3. Completar Phase 3: User Story 1
4. **STOP and VALIDATE**: quickstart C1–C2
5. Demo do fluxo pós-reprovação

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → destravar ciclo no dia a dia (MVP desta feature)
3. US2 → cobertura mid-cycle (SC-002)
4. US3 + US4 → RH/offboarding e gestor ausente
5. US5 + US6 → ruído operacional, go-live e regressão automatizada
6. Polish → quickstart completo

### Parallel Team Strategy

1. Time fecha Setup + Foundational junto
2. Em seguida:
   - Dev A: US1 → US4 (goals/approval)
   - Dev B: US2 (enrollment) + US5 (notifications/pdi)
   - Dev C: US3 (catálogos/offboarding) + US6 testes/ops/UX
3. Integrar e validar quickstart C1–C7

---

## Notes

- [P] = arquivos diferentes, sem dependência de tarefas incompletas
- Labels [US1]–[US6] mapeiam às user stories do `spec.md`
- Não alterar fórmula de `nota_final_lider` nem lista canônica de etapas
- Sem DRF/SPA; escopo permanece no backend
- Commit após cada task ou grupo lógico; validar checkpoint da story antes de avançar prioridade
- Evitar: tarefas vagas, conflito no mesmo arquivo entre story paralelas sem coordenação
