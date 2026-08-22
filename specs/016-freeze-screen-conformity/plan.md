# Implementation Plan: Conformidade visual das telas ao Freeze v2

**Branch**: `016-freeze-screen-conformity` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-freeze-screen-conformity/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). Clarifications 2026-08-21 + decisão **B1** são fechadas. **Não** gera `tasks.md` (isso é `/speckit-tasks`).

## Summary

Auditoria e remediação de **conformidade visual** nas superfícies autenticadas do inventário fechado Category A (excelente — painel gerencial + charts Freeze) e Category B (decente + extensão pontual **B1** Table-frame listas). Não é redesign, não reabre Freeze A/B/C/D, não toca AuthZ/escopo/máquina de estados/fórmulas.

Abordagem: consumir `docs/design-system.md` + includes canônicos (`button`, `input`, `card`, `badge_status`, `empty_state`, `.table-frame`, `_chart_block`, `pagination`); remediar violações tela a tela; P1 = progresso de ciclo (admin + `ciclo_detail`) como `bar_horizontal` mono + amber só no gargalo; P2 = cadastros B com cap/colunas/ações B1; P3 = filtros/paginação na fonte única. Qualquer necessidade visual ausente do Freeze (exceto B1 já aprovada) = **ESCALATE / STOP**.

Contratos visuais **reusados, não reabertos**: `specs/009-persona-visual-redesign/contracts/{chart-catalog,managerial-panel,cycle-managerial-detail}.md` e `specs/012-gerencial-historico-legado/contracts/density-history-empty.md`. Única adição documental: seção Table-frame · listas B em `docs/design-system.md` (FR-017).

## Sequenciamento (obrigatório)

```text
Fundação: allowlist/denylist + checklist A/B + registrar B1 no DS (tokens)
        │
        ▼
US1 P1 — Progresso ciclo (admin + ciclo_detail) Freeze A/D
        │
        ▼
US2 P1 — Inventário Category A (painel gerencial + charts)
        │
        ▼
US3 P2 — Inventário Category B (forms + listas B1)
        │
        ▼
US4 P3 — Paginação/filtros na fonte única (pagination.html)
```

US2 pode paralelizar telas A **depois** do gate de progresso (US1) estável. US3 não inventa chart/KPI. US4 só se B precisar de controles — correção de token **uma vez** em `templates/components/pagination.html`.

## Non-Goals / Mandato Freeze

> Operacional: [contracts/path-allowlist.md](./contracts/path-allowlist.md) + [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md) + [contracts/table-frame-listas-b.md](./contracts/table-frame-listas-b.md).

**PROIBIDO**: reinventar token/cor/sombra/componente/chart fora do Freeze; “adaptar” Figma Verdee; telas fora do inventário (expectativas/metas/PDI/avaliações colaborador, listas de ciclo, auditoria, notificações, nav, shell, login/`base_auth`); relaxar `get_visible_users` / `ScopedObjectMixin` / predicados; mudar queryset de escopo, permissões, stage, approval, fórmulas; models/migrations; SPA/DRF/lib nova Chart.

**PERMITIDO**: templates/CSS/JS de chart **já existentes** no inventário; context de apresentação sem mudar significado de counts; documentação B1 no DS; rebuild Tailwind se `input.css` ganhar classe B1.

**ESCALATE / STOP**: se a remediação exigir qualquer decisão visual **ausente** de `docs/design-system.md` e da B1 aprovada — parar e perguntar; não criar ilha de estilo.

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (constituição cita 5.x — desvio já conhecido do monólito; sem novo desvio nesta feature)

**Primary Dependencies**: Django full stack (DTL + HTMX + Tailwind CSS CLI); Chart.js **4.5.1** já no monólito via `dashboard_charts.js` + `_chart_block`. Sem DRF, SPA, nova lib, plugin npm.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **zero models/migrations**. Leitura dos QS já autorizados pelas views existentes.

**Testing**: pytest-django de superfícies (regressão stage/scope/reject **sem** alterar asserts de domínio); aceite visual guiado [quickstart.md](./quickstart.md) por persona + checklist A vs B.

**Target Platform**: Web autenticado; desktop-first; viewport ~375px sem scroll horizontal da página (scroll de tabela B só **dentro** do `.table-frame`).

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Sem agregação nova pesada; reuso de payloads/builders existentes. Sem Celery novo.

**Constraints**:
- Inventário fechado A/B + mapa persona (spec)
- Freeze-only + B1; ESCALATE se faltar token
- AuthZ/escopo intocáveis (Constitution II)
- Apresentação only — zero regra de negócio
- Componentes canônicos only; paginação na fonte única
- Category A full-bleed; B lista cap ≠ form cap

**Scale/Scope**: 4 user stories (P1: US1–US2; P2: US3; P3: US4); ~7 superfícies A + 4 entidades B (lista+form); ~1 extensão documental (B1).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio / Gate | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | Só DTL/HTMX/Tailwind + Chart.js 4.5.1 já presente; sem lib nova. |
| II. Segurança e Escopo no Backend | ✅ PASS | **Gate explícito**: zero alteração em `scope.py`, `get_visible_users`, `ScopedObjectMixin`, mixins de admin/líder, predicados de queryset. Remediação = templates/CSS/JS presentation. Diff nesses paths = **ERROR**. |
| III. Imutabilidade e Integridade | ✅ PASS | Zero writes de domínio; zero FKs/snapshots/migrations. |
| IV. Modularidade por Domínio | ✅ PASS | UI em templates por app; componentes em `core`/`templates/components`; charts em `dashboard`. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Sem tocar `nota_final_lider`, etapas, approval; counts de pipeline já existentes. |
| VI. Performance Assíncrona | ✅ PASS | Sem cálculo novo no request; aderência continua snapshot Celery existente. |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind; Chart.js pontual já justificado. |
| **Freeze / inventário (feature gate)** | ✅ PASS | Allowlist fechada; denylist Verdee/nav/login/telas fora; B1 única extensão DS; ESCALATE documentado. |
| **Apresentação ≠ domínio (feature gate)** | ✅ PASS | Teste de ouro: desligar CSS/charts não muda AuthZ, etapa, aprovação, notas nem visible set. |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos = allowlist + denylist + B1 Table-frame; `data-model.md` declara zero models novos; progresso = auditoria/remediação do payload/bloco já previstos em 009/012 — sem fórmula nova.

## Project Structure

### Documentation (this feature)

```text
specs/016-freeze-screen-conformity/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── path-allowlist.md
│   ├── non-goals-denylist.md
│   ├── table-frame-listas-b.md
│   └── canonical-components-baseline.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks — NÃO criado aqui
```

### Source Code (repository root)

```text
# Category A — apresentação
templates/dashboard/
├── admin.html
├── team.html
├── team_list_partial.html
├── adherence.html
├── adherence_list_partial.html
├── structure.html
├── personal.html
├── _chart_block.html          # reuso; fora de partials HTMX
├── _ciclo_selector.html
└── _visao_toggle.html
templates/cycles/ciclo_detail.html
templates/talent/matrix.html
templates/talent/partials/_cell.html
templates/talent/partials/_drawer.html
templates/talent/partials/_person_card.html

# Category B — cadastros
templates/organization/
├── area_list.html / area_list_partial.html / area_form.html
├── cargo_list.html / cargo_list_partial.html / cargo_form.html
├── user_list.html / user_list_partial.html / user_form.html
└── user_pending_list.html / user_pending_list_partial.html   # correlata Usuários
templates/competencies/
├── competencia_list.html / competencia_list_partial.html / competencia_form.html
# escala_* FORA desta rodada (não inseparável)

# Canônicos compartilhados
templates/components/
├── button.html / input.html / card.html / badge_status.html
├── empty_state.html / pagination.html   # fonte única US4
# .table-frame em static/src/input.css

apps/dashboard/{views.py,chart_payloads.py}   # só se payload de apresentação falhar auditoria
apps/cycles/views.py                          # só context presentation em CicloDetailView
# DENYLIST: scope.py, stage.py, cycle.py open/close, approval, evaluation mutators, adherence fórmula

docs/design-system.md    # + seção Table-frame · listas B (B1) — FR-017
static/src/input.css     # só se B1 exigir classe utilitária documentada
static/css/tailwind.css  # rebuild se input.css mudar
static/js/dashboard_charts.js  # só se auditoria exigir ajuste presentation-only

tests/                   # regressão scope/stage/reject; testes de superfície presentation
```

**Structure Decision**: Monólito Django existente; escopo = templates + componentes + DS (+ CSS mínimo). Sem app nova, sem rota nova.

## Complexity Tracking

> Nenhuma violação de Constituição a justificar.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

**Nota (não é violação)**: Extensão documental **B1** é exceção explícita de FR-002 já aprovada na spec — registrada em [contracts/table-frame-listas-b.md](./contracts/table-frame-listas-b.md) e no DS na mesma entrega. Qualquer *outra* decisão visual nova = ERROR / STOP.
