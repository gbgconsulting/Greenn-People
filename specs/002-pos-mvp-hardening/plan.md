# Implementation Plan: Hardening Operacional Pós-MVP

**Branch**: `002-pos-mvp-hardening` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-pos-mvp-hardening/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Endurecer o monólito Django atual (DTL + HTMX + Tailwind CLI + Celery/Redis) preenchendo lacunas operacionais pós-MVP ~130 colaboradores / ~6 gestores: (P1) fluxo pós-reprovação de meta/resultado sem retroceder etapa agregada; (P1) criação automática de Avaliação mid-cycle; (P2) soft-delete + unicidade de catálogos e reatribuição em lote no offboarding; (P2) aprovação/reprovação por admin com auditoria do ator real; (P3) dedupe de lembretes, recálculo de atraso de PDI, prontidão de produção (health/static/backup), testes de escopo/máquina de estados e polish HTMX (loading/empty/modal a11y). Sem DRF/SPA; preservar fórmula de nota, etapas canônicas, um ciclo aberto por vez, escopo no backend e histórico imutável.

Abordagem: serviços de domínio existentes (`goals.services.approval`, `cycles.services.stage/cycle`, `accounts`, `audit`) serão estendidos; models ganham constraints/campos mínimos; UI permanece partials HTMX. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7

**Primary Dependencies**: Django 6.0.7 (full stack, sem DRF); HTMX; Tailwind CSS CLI standalone; Celery + Redis; Celery Beat; django-environ (já no projeto)

**Storage**: SQLite (desenvolvimento) → PostgreSQL (produção); apenas ORM Django; `UniqueConstraint` com `condition` (compatível SQLite/PostgreSQL)

**Testing**: pytest-django + helpers em `tests/` (primeira suíte formal focada em escopo + stage machine + pós-reprovação); smoke legado `scripts/validate_t070.py` permanece como referência

**Target Platform**: Aplicação web interna (browser); locale `pt-br`, timezone `America/Sao_Paulo`; deploy com health check e static files em produção

**Project Type**: Web application (monólito Django full stack)

**Performance Goals**: Páginas comuns < 2s; jobs Celery de lembretes/PDI idempotentes; reatribuição em lote de liderados em uma transação (~dezenas de registros)

**Constraints**: Sem SPA/API REST como superfície; lógica de permissão só no backend; fórmula `nota_final_lider` e lista canônica de etapas imutáveis nesta feature; `on_delete=PROTECT` em FKs históricas; um ciclo aberto por vez; código EN / UI pt-BR; CBVs quando possível

**Scale/Scope**: ~130 colaboradores, ~6 gestores; 6 user stories (P1–P3); alterações concentradas em `goals`, `cycles`, `accounts`, `organization`, `competencies`, `notifications`, `pdi`, `audit`, `core`, `config`, templates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | Sem DRF/SPA; soft-delete via `is_active` + views; health em view Django; WhiteNoise só se necessário para static em prod (justificado em Complexity Tracking se adotado). |
| II. Segurança e Escopo no Backend | ✅ PASS | Admin override restrito a `is_admin` em `approval._ensure_approver`; líderes comuns continuam sob `get_visible_users` + `ScopedObjectMixin`; exceção não amplia visão genérica. |
| III. Imutabilidade e Integridade | ✅ PASS | Soft-delete de catálogos (sem hard-delete destrutivo); `PROTECT` preservado; `AuditLog` append-only; track de `Meta.status`/`status_resultado`, `AcaoPDI.prazo` e `line_manager` em lote. |
| IV. Modularidade por Domínio | ✅ PASS | Serviços nas apps existentes; sem novo app; contratos por domínio em `contracts/`. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Fórmula de nota inalterada; etapa agregada nunca retrocede; avanço continua exigindo 100% aprovação + ≥1 item. |
| VI. Performance Assíncrona | ✅ PASS | Lembretes permanecem em Celery Beat; dedupe no job; sem cálculos pesados no request. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos formalizam pós-reprovação, mid-cycle, catálogos/offboarding, override admin, lembretes/PDI e prontidão sem camadas extras.

## Project Structure

### Documentation (this feature)

```text
specs/002-pos-mvp-hardening/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
config/                         # settings, urls, celery
├── settings/{base,dev,prod}.py
├── celery.py
└── urls.py                     # + health endpoint

apps/
├── core/                       # mixins, componentes UI (loading/empty/modal a11y)
├── accounts/                   # activate/create → Avaliação mid-cycle; reassign_direct_reports
├── organization/               # Area/Cargo soft-delete + UniqueConstraint ativos
├── competencies/               # Escala/Competencia is_active + soft-delete + unicidade
├── goals/                      # reopen wired; eligibility de edição pós-reprovação; admin approval
├── cycles/                     # stage machine (inalterada semanticamente); open_cycle reuse
├── reviews/                    # Avaliacao unique (ciclo, usuario) — get_or_create mid-cycle
├── pdi/                        # recalc atraso ao alterar prazo
├── notifications/              # dedupe NotificacaoLog + tasks
├── audit/                      # track Meta status + AcaoPDI.prazo
├── talent/ / dashboard/        # sem mudança de regra nesta feature
└── ...

templates/
├── components/                 # modal a11y, indicator, empty-state
└── goals|pdi|accounts|.../     # CTAs pós-reprovação, bulk reassign, empty states

tests/                          # pytest-django: scope, stage, post-rejection, mid-cycle
docs/
└── ops/                        # backup / produção (novo)
```

**Structure Decision**: Manter monólito e apps da constituição. Esta feature é hardening incremental sobre serviços já existentes — espelha a estrutura documentada em `001-gestao-desempenho-talentos/plan.md`, adicionando `tests/` formal e `docs/ops/` para operação.

## Complexity Tracking

> Preenchido apenas onde há desvio justificado ou nota de constituição já conhecida

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Django 6.0.7 vs constituição (Django 5.x) | Já ratificado no plano 001 e no `requirements.txt` | Downgrade sem benefício |
| WhiteNoise (opcional prod) | Servir `collectstatic` atrás do processo WSGI quando não há CDN/nginx no path do app | Nginx-only exige documento de deploy; se o deploy for container único, WhiteNoise evita dependência de reverse-proxy só para static — adotar só se necessário no quickstart/ops |
| Track audit de `Meta.status` / `status_resultado` | FR-015 exige ator real em aprovação admin; Meta hoje não está nos signals | Log só na view perde alteração via shell/admin e falha auditoria uniforme |
