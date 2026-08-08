# Implementation Plan: Orientação de Próximo Passo no Ciclo (Guidance UX)

**Branch**: `008-cycle-guidance-ux` | **Date**: 2026-08-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-cycle-guidance-ux/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Reduzir fricção de orientação no ciclo de desempenho (colaborador / líder / RH) com bloco **Próximo passo**, **stepper** de 6 etapas, hierarquia de CTAs no hub da avaliação, badge único de pendências do líder e checklist avisório pré-abertura — **somente apresentação**. Abordagem: serviço puro de leitura `apps/reviews/services/guidance.py` que **deriva** `{title, body, cta_label, cta_url_name, cta_kwargs, blocked_reason}` a partir de `Avaliacao.etapa` / ciclo / papel já existentes; partials em `templates/components`; context builders nas views atuais. **Zero** models, migrations, URLs de domínio, fórmulas, AuthZ ou mudança de máquina de estados. Teste de ouro: desligar CSS/guidance não altera nenhum resultado de negócio. Ver [research.md](./research.md), [contracts/](./contracts/).

## Non-Goals / Denylist de lógica

> Espelha **FR-013** e a invariante não-negociável do input do plano. Detalhe operacional: [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md).

**PROIBIDO** (mesmo “por UX” ou “parece melhor”):

| Zona | Exemplos |
|------|----------|
| Regras de negócio / domínio | avanço, bloqueio, elegibilidade nova |
| Máquina de estados | `can_advance` / `advance_stage` / semântica de etapa |
| Aprovação / reprovação / reabertura / mid-cycle / offboarding | services e views de mutação |
| Fórmulas | nota, aderência, 9-box, desempenho/potencial |
| AuthZ / escopo | `get_visible_users`, `ScopedObjectMixin`, permissões “quem pode” |
| Persistência de regra | models, migrations, campos novos de regra |
| Contratos de domínio | URLs/rotas/endpoints de negócio novos ou alterados |
| Semântica de fluxo | feedback/ciente, PDI status, abertura de ciclo |
| Navegação IA | reorganizar grupos Governança / Cadastros / Sistema |
| Auth polish | `accounts/login`, `base_auth` |

**PERMITIDO apenas**:

- Copy, hierarquia visual de CTAs, stepper, badges de contagem
- Context/view helpers e serviço de **LEITURA** que deriva orientação do estado já existente
- Templates/components; CSS mínimo de apresentação (`input.css` só se classes mínimas do stepper)
- Contagens que **reutilizam** as mesmas queries/regras de elegibilidade já vigentes (não inventar elegibilidade)

Se uma task/solução exigir mudar regra → **REJEITAR** e documentar como fora de escopo.

## Technical Context

**Language/Version**: Python 3.x / Django (projeto vigente; constituição cita 5.x)

**Primary Dependencies**: Django full stack (DTL); HTMX; Tailwind CSS CLI (`static/src/input.css` → `static/css/tailwind.css`). Sem DRF, sem libs UI novas, sem SPA.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **sem schema change**. Zero models/migrations nesta feature.

**Testing**: Unitários do mapeamento etapa→orientação e contagem de pendências (derivação only) em `tests/`; **regressão obrigatória** da suíte stage/scope existente (`tests/test_stage_machine.py`, `tests/test_scope.py`, e correlatos) — MUST continuar PASS **sem** mudança de comportamento. Sem TDD visual obrigatório; aceite por [quickstart.md](./quickstart.md) por persona.

**Target Platform**: Web app autenticado; desktop aceite primário; mobile legível (stack vertical; stepper compactável).

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Derivação sync leve no request (leituras + contagens no escopo já resolvido); **não** introduzir agregações pesadas novas nem Celery para guidance. Badge do líder: SC-005 ≤ 5 s percepção após load (contagem deve reutilizar predicados existentes, não varreduras novas caras).

**Constraints**:
- Constitution: Django-first, DTL+HTMX+Tailwind, sem DRF, AuthZ só no backend (UI não autoriza)
- Zero models/migrations (research confirma desnecessidade — ver Phase 0)
- Preferir `apps/reviews/services/guidance.py` (puro leitura) + `templates/components`
- Context builders nas views dashboard/reviews/cycles/goals **existentes** — sem novas rotas de negócio
- Contrato explícito etapa → orientação (derivação read-only; zero write de etapa/status)
- Checklist RH = superfície **informativa**; abertura continua pela regra já existente (`open_cycle` / `CicloOpenView` intocados em comportamento)
- Constitution Check **FALHA** se o design tocar services de avanço/cálculo/AuthZ

**Scale/Scope**: 4 user stories (US1–US2 P1; US3–US4 P2); superfícies: Meu painel, hub avaliação, nav líder, self/leader/feedback, ciclo_list + user_pending; go-live alvo 06/09/2026

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | DTL + HTMX + Tailwind CLI; serviço puro Python de leitura; sem DRF/SPA/libs UI |
| II. Segurança e Escopo no Backend | ✅ PASS | Sem mudança AuthZ; badge **reusa** `get_visible_users` / predicados existentes; UI não “libera” ação |
| III. Imutabilidade e Integridade | ✅ PASS | Zero writes de domínio; sem FKs/snapshots novos |
| IV. Modularidade por Domínio | ✅ PASS | Guidance mapeamento em `reviews` (dono de `Avaliacao.etapa`); components em `core`/templates; cycles/org só contexto de listagem |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Nenhuma fórmula; stepper/orientação **não** alteram `can_advance` / notas / 9-box |
| VI. Performance Assíncrona | ✅ PASS | Sem agregação pesada nova; sem Celery para guidance |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind preservados |

### Gate extra desta feature (obrigatório)

| Regra | Status | Critério de falha |
|---|---|---|
| Guidance é derivação read-only | ✅ PASS | Qualquer write de `etapa`/status/aprovação no design → **ERROR** |
| Denylist de services | ✅ PASS | Toclar `cycles/services/stage.py`, formulas de `reviews/services/evaluation.py` (cálculo), `goals/services/approval.py`, `accounts/services/scope.py` (alteração) → **ERROR** gate |
| Checklist RH avisório | ✅ PASS | Soft-disable / trava nova de `open_cycle` → **ERROR** / fora de escopo |
| Sem schema | ✅ PASS | Model/migration proposto → **ERROR** (salvo prova mínima em research — não aplicável) |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos em `contracts/` codificam derivação, allowlist/denylist e checklist avisório. `data-model.md` declara **zero** models Django novos. Sem Complexity Tracking (sem violações).

## Project Structure

### Documentation (this feature)

```text
specs/008-cycle-guidance-ux/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1 (entidades de apresentação)
├── quickstart.md           # Phase 1 validação por persona
├── contracts/
│   ├── non-goals-denylist.md      # FR-013 espelhado
│   ├── path-allowlist.md          # Allowlist / denylist de paths
│   ├── guidance-derivation.md     # Contrato etapa→orientação (read-only)
│   ├── leader-pending-badge.md    # Soma de pendências (reuso elegibilidade)
│   └── rh-checklist-advisory.md   # Checklist informativo vs abertura
├── checklists/
└── tasks.md                # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root) — allowlist

```text
apps/reviews/services/guidance.py          # NOVO — puro leitura: mapa etapa→orientação + helpers de apresentação
apps/reviews/services/pending_counts.py    # OPCIONAL — ou funções no mesmo guidance.py; só contagem read-only
apps/core/context_processors.py            # Estender: badge líder (leitura) — sem AuthZ nova
# Views existentes — apenas get_context_data / flags de apresentação:
apps/dashboard/views.py                    # PersonalDashboardView (+ team se contexto)
apps/reviews/views.py                      # Detail / self / leader / feedback (copy/progress UI)
apps/goals/views.py                        # Coerência hint `_proximo_passo_pos_reprovacao` (sem mudar regra)
apps/cycles/views.py                       # ciclo_list: contexto checklist avisório
apps/organization/views.py                 # user_pending: links/checklist se já for superfície

templates/components/
├── next_step.html                         # NOVO — bloco Próximo passo
├── stage_stepper.html                     # NOVO — stepper 6 etapas (shared)
├── nav_link.html                          # Slot opcional badge_count (apresentação)
└── nav_menu.html                          # Exibir badge no item líder — SEM reordenar grupos

templates/dashboard/personal.html
templates/reviews/avaliacao_detail.html
templates/reviews/self_assessment.html     # US3: progresso
templates/reviews/leader_assessment.html   # US3: faltam N + sticky
templates/reviews/feedback_*.html          # US3: ciente óbvio
templates/goals/…                          # Só se alinhar hint existente (FR-007)
templates/cycles/ciclo_list.html (+ partial)
templates/organization/user_pending*.html  # US4 se superfície RH

static/src/input.css                       # SOMENTE classes mínimas do stepper (se utilitários insuficientes)
static/css/tailwind.css                    # rebuild CLI

tests/
├── test_guidance_mapping.py               # NOVO — mapa etapa→ação / estados especiais
├── test_leader_pending_count.py           # NOVO — soma = fontes elegíveis (predicados existentes)
└── (regressão sem alteração de assert de negócio):
    test_stage_machine.py, test_scope.py, test_reject_stage_invariant.py,
    test_can_advance_post_correction.py, test_post_rejection.py, test_production_ux.py
```

**Explicitamente fora** (denylist de paths — ver contracts): `apps/*/models.py`, `**/migrations/**`, `apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py` (comportamento), `apps/goals/services/approval.py`, alteração de `accounts/services/scope.py`, formulas de cálculo em `evaluation.py`, `apps/*/urls.py` (rotas de domínio novas), `templates/accounts/*`, redesign de agrupamento em `nav_menu.html` além do badge.

**Structure Decision**: Monólito existente. Feature 100% apresentação + serviço de leitura. Sem app novo, sem endpoint de negócio, sem schema. Home do guidance: **`apps/reviews/services/guidance.py`** (decisão confirmada — `Avaliacao.etapa` e `build_fr005_context` já residem em reviews).

## Complexity Tracking

> Nenhuma violação constitucional a justificar.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
