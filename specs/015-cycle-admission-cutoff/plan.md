# Implementation Plan: Elegibilidade de Ciclo por “Admitidos até”

**Branch**: `015-cycle-admission-cutoff` (git local pode divergir; artefatos em `specs/015-cycle-admission-cutoff/`) | **Date**: 2026-08-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-cycle-admission-cutoff/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos de design em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). Clarifications Session 2026-08-20 são **decisões fechadas** — **NÃO** reabrir, **NÃO** marcar NEEDS CLARIFICATION. **Não** gera `tasks.md` (isso é `/speckit-tasks`). **Não** reescreve `spec.md`.

## Summary

Na abertura operacional, o RH informa **Admitidos até** (`Ciclo.admitidos_ate`). O backend matricula **somente** ativos com `CustomUser.data_entrada` preenchida e `≤` ao corte (inclusivo). A **mesma** regra governa `ensure_avaliacao_for_user` (mid-cycle). Avaliação já criada = snapshot (nunca apagar por mudança de data). Ciclos 011/arquivo com `admitidos_ate=NULL` permanecem válidos sem reprocessar.

Abordagem: **1** migration aditiva `AddField` em `Ciclo`; predicado único `user_eligible_for_ciclo`; gate em `open_cycle`; preview de **3 contagens** agregadas (admin only, DTL+HTMX); mensagem de sucesso sem “todos os ativos”; management command operacional de **backfill** de `data_entrada` vazia a partir de `backup_colaboradores` (“Data admissão”), sem UI e sem mutar o importer 010 “full”. Denylist explícita: stage / approval / evaluation / adherence / talent / pdi / scope / 012 / imports 010–014. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (alinhar `requirements.txt`; constituição cita 5.x — Complexity Tracking)

**Primary Dependencies**: Django 6.0.7 full stack (DTL + HTMX + Tailwind CLI); **sem** DRF/SPA; **sem** lib nova; openpyxl **já** na 010 — reuso **somente** via `apps/accounts/services/legacy_import/parse_xlsx.py` + `dates.parse_legacy_date` no backfill (não no caminho HTTP de abertura)

**Storage**: SQLite (dev) → PostgreSQL (prod); **UMA** migration aditiva: `Ciclo.admitidos_ate` `DateField(null=True, blank=True)`. `CustomUser.data_entrada` **intacta** (tipo/null/unique). Zero M2M, zero tabela de participantes, zero FK nova Avaliacao↔Ciclo, zero `RunPython` de elegibilidade histórica

**Testing**: pytest-django — atualizar `tests/conftest.py` (`ciclo_aberto`), `tests/test_mid_cycle_enrollment.py`; novos testes de `open_cycle` / gate / preview AuthZ / backfill / mensagem; regressão denylist (`test_stage_machine`, `test_scope`, rejeição, fórmula) **sem** alterar asserts alheios. Gate: `git diff` vazio nos paths da denylist (exceto allowlist desta feature)

**Target Platform**: Monólito Django — UI admin de ciclos (`AdminCyclesMixin` / `RequiresAdminMixin`) + CLI operacional (`manage.py`) para backfill; locale `pt-BR`

**Project Type**: Monólito Django (apps `cycles`, `reviews`, `accounts`) — sem app nova

**Performance Goals**: Abertura **síncrona** como hoje (batch N ativos via `ensure`); preview = agregações `Count`/`filter` leves; backfill one-shot síncrono (CLI); **sem** Celery novo para o corte (Princípio VI — volume já aceito no open vigente)

**Constraints**: Backend = fonte da regra (FR-015); UI só coleta + preview; preview **sem** lista nominativa; AuthZ = mesmo gate admin de ciclos; NÃO alterar `get_visible_users` / `ScopedObjectMixin` / hierarquia; checklist 008 permanece avisório; imports 010/011/013/014 **não** exigem corte nem chamam `open_cycle`

**Scale/Scope**: US1–US5 (P1 abertura/preview/mid-cycle/backfill; P2 denylist histórico); FR-001…FR-024; SC-001…SC-009. Pré-req operacional: backfill antes do primeiro corte em produção com legado

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Violação não justificada BLOQUEIA.*

| Princípio | Status | Evidência no design |
|---|---|---|
| **I. Simplicidade Django-First** | ✅ PASS | DTL + HTMX + `ModelForm`/POST Django; predicado + `open_cycle`/`ensure` em serviços; management command para backfill. Sem DRF, SPA, lib nova. openpyxl só no parse legado já justificado (010). |
| **II. Segurança e Escopo no Backend** | ✅ PASS | Elegibilidade e criação de Avaliação **só** no backend. Abrir / preview / gravar corte: `AdminCyclesMixin` + `RequiresAdminMixin` (mesmo 403). Preview = contagens agregadas, **sem** PII de lista. **MUST NOT** alterar `get_visible_users`, `ScopedObjectMixin`, `scope.py`. Líder/colaborador não acessam preview do corte. |
| **III. Imutabilidade e Integridade** | ✅ PASS | Snapshot = Avaliacao existente permanece (FR-006). Zero apagar/desfazer por mudança de `data_entrada`. `on_delete=PROTECT` intacto. Ciclos encerrados sem corte: zero reprocessamento. Auditoria: valor rastreável em `Ciclo.admitidos_ate`; **não** inventar AuditLog paralelo (Ciclo hoje não está em `audit.signals` — ver research R-audit). |
| **IV. Modularidade por Domínio** | ✅ PASS | Domínios: `cycles` (campo + open + preview), `reviews.enrollment` (ensure + predicado compartilhado), `accounts` (`data_entrada` + comando backfill). Sem app nova. Predicado preferencialmente em `cycles` ou módulo fino compartilhado sem ciclo de import inverso — ver research R-predicado. |
| **V. Reprodutibilidade de Cálculos** | ✅ PASS | Fórmulas / etapa / aprovação **intocadas**. Diff vazio em `evaluation.py`, `stage.py`, `approval.py`. |
| **VI. Performance Assíncrona** | ✅ PASS | Sem Celery novo para o corte. Abertura continua síncrona (precedente vigente). Preview = aggregations leves na request admin. Backfill = CLI one-shot. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos formalizam predicado, gate de abertura, preview AuthZ, backfill, denylist com paths, migration-safety. Clarifications 2026-08-20 não reabertas. **Zero** NEEDS CLARIFICATION residual.

**FAIL do plan se**: UI decide elegibilidade; preview público/lista nominativa; AlterField em `data_entrada`; M2M/participantes; Celery/DRF/SPA; hard-block do checklist 008; alterar scope/hierarquia.

## Project Structure

### Documentation (this feature)

```text
specs/015-cycle-admission-cutoff/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── eligibility-predicate-contract.md
│   ├── open-cycle-cutoff-contract.md
│   ├── preview-counts-contract.md
│   ├── admission-backfill-command-contract.md
│   ├── non-goals-denylist.md
│   └── migration-safety.md
├── checklists/
│   └── requirements.md  # já existe — plan NÃO reescreve spec.md
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created by /speckit-plan)
```

### Contratos externos a ESTENDER (não substituir)

```text
specs/002-pos-mvp-hardening/contracts/mid-cycle-enrollment-contract.md
  → ESTENDER: elegibilidade = predicado 015; open_cycle deixa de “todos ativos”
specs/008-cycle-guidance-ux/contracts/rh-checklist-advisory.md
  → PERMANECE avisório; única trava NOVA = ausência de admitidos_ate
```

### Source Code (repository root)

```text
apps/
├── cycles/
│   ├── models.py                 # AddField: admitidos_ate
│   ├── forms.py                  # campo / form de abertura (mínimo)
│   ├── views.py                  # CicloOpenView (+ preview HTMX se rota dedicada)
│   ├── exceptions.py             # CycleMissingCutoffError (nome canônico no research)
│   ├── services/
│   │   ├── cycle.py              # open_cycle: gate + save corte + batch ensure
│   │   └── eligibility.py        # NOVO: user_eligible_for_ciclo + preview counts
│   ├── migrations/
│   │   └── 0003_ciclo_admitidos_ate.py   # ÚNICA migration desta feature
│   └── templates cycles/         # campo + preview + mensagem (lista/abrir)
├── reviews/
│   └── services/enrollment.py    # ensure_avaliacao_for_user: aplicar predicado
├── accounts/
│   ├── models.py                 # data_entrada INTÁVEL (sem AlterField)
│   ├── services/legacy_import/   # REUSO: parse_legacy_date; parse XLSX coluna;
│   │                             # report mask — NÃO mutar importer 010 “full”
│   └── services/admission_backfill/   # NOVO: resolve + importer dry-run/persist
│       └── management/commands/backfill_data_entrada.py
├── organization/forms.py         # UserUpdateForm — SEM mudança de AuthZ; ensure já chama
├── accounts/forms.py             # RegisterForm — data_entrada continua opcional (default)
└── core/mixins.py                # RequiresAdminMixin — INTÁVEL (só reuso)

# DENYLIST (diff vazio de comportamento — ver contracts/non-goals-denylist.md)
apps/cycles/services/stage.py
apps/cycles/services/cycle.py::close_cycle   # close intacto (open muda)
apps/goals/services/approval.py
apps/reviews/services/evaluation.py
apps/dashboard/services/adherence.py
apps/accounts/services/scope.py
apps/talent/
apps/pdi/   (exceto se backfill não toca — diff vazio)
apps/dashboard/urls.py + superfície 012
```

**Structure Decision**: Corte e predicado em `cycles`; matrícula mid-cycle continua em `reviews.enrollment` chamando o predicado; backfill operacional novo em `accounts` (dados de pessoa), sem reabrir allowlist da 010 além do necessário para ler “Data admissão” e gravar `data_entrada` vazia.

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Django 6.0.7 vs constituição (Django 5.x) | Já ratificado nos planos 001–014 e em `requirements.txt` | Downgrade sem benefício |
| openpyxl no backfill (Princípio I) | Já justificado na 010; fonte é OOXML | Nova lib / CSV — rejeitado; esta fatia **não** adiciona dependência |
| Abertura síncrona (Princípio VI) | Precedente vigente; volume N ativos já aceito; spec assume síncrono | Celery só para o corte — **proibido** (FR + constituição VI nesta feature) |
| Pacote backfill novo vs mutar importer 010 | Isolar US4; não reabrir allowlist 010 | Mutar importer “full” — rejeitado (risco de regressão 010; FR-018) |

## FR → âncora (aceite do plan)

| FR | Âncora |
|---|---|
| FR-001, FR-002, FR-014 | [open-cycle-cutoff-contract.md](./contracts/open-cycle-cutoff-contract.md), [data-model.md](./data-model.md) |
| FR-003…FR-006, FR-024 | [eligibility-predicate-contract.md](./contracts/eligibility-predicate-contract.md) |
| FR-007…FR-010 | [migration-safety.md](./contracts/migration-safety.md), [data-model.md](./data-model.md) |
| FR-011…FR-013, FR-015 | [preview-counts-contract.md](./contracts/preview-counts-contract.md), [open-cycle-cutoff-contract.md](./contracts/open-cycle-cutoff-contract.md) |
| FR-016, FR-017 | [admission-backfill-command-contract.md](./contracts/admission-backfill-command-contract.md) |
| FR-018…FR-023 | [non-goals-denylist.md](./contracts/non-goals-denylist.md) |
| FR-020, FR-021 | research R-authz / R-audit; preview + campo no ciclo |

## Testes nomeados (criar / atualizar)

| Área | Testes |
|---|---|
| Fixture | Atualizar `tests/conftest.py::ciclo_aberto` — setar `admitidos_ate` antes de `open_cycle` |
| Abertura | `tests/test_open_cycle_admission_cutoff.py` (novo): elegíveis/inelegíveis; sem corte → status não abre + 0 Avaliações; um-aberto intacto; mensagem sem “todos os ativos” / “colaboradores ativos” genérico |
| Enrollment | Atualizar `tests/test_mid_cycle_enrollment.py`: ativo elegível; entrada > D / sem data → None; snapshot (editar data após matrícula não remove Avaliacao) |
| Predicado | Unitário `user_eligible_for_ciclo` (borda inclusiva; inativo; NULL) |
| Preview AuthZ | Admin 200 + 3 contagens; líder/colaborador/anônimo 403/redirect; resposta sem lista de e-mails/nomes |
| Backfill | `tests/test_backfill_data_entrada.py` (novo): dry-run 0 writes; persist só NULL; idempotência delta 0; não chama open/close/ensure/advance; amostra mascarada |
| Regressão denylist | `test_stage_machine`, `test_scope`, rejeição, fórmula — **verdes sem mudar asserts**; gold diff vazio nos paths da denylist |
| Contrato 002 | Atualizar asserts/docs de mid-cycle-enrollment para o predicado 015 |

## Non-goals (resumo — detalhe em contract)

Filtros de cadastro; paginação 15; redesign/Freeze; M2M de exceções; forçar inelegível; desfazer Avaliacao; hard-block checklist 008; Celery novo para o corte; tornar `data_entrada` obrigatória no banco/RegisterForm; backfill via UI de upload; reprocessar ciclos 011.
