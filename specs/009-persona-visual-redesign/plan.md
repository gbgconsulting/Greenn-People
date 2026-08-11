# Implementation Plan: Redesign Visual por Persona (Painéis Gerenciais)

**Branch**: `009-redesign-ux-persona` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-persona-visual-redesign/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Elevaar a leitura gerencial por persona (colaborador / líder / Admin RH) **sem** mudar máquina de estados, AuthZ, fórmulas nem a stack: Chart.js **4.5.1** + DTL + HTMX + Tailwind. Fundação = **US1** (catálogo de charts expressivos em `dashboard_charts.js` / `_chart_block.html` / `chart_payloads.py`). Em seguida **US2** (painéis líder: time/estrutura/aderência no padrão KPI + visual + tabela) e **US3** (página nova `cycles/<pk>/` para RH). P2 polish colaborador; P3 cadastros best-effort até 03/09. Reabertura Freeze A/B/C documentada em `docs/design-system.md` + tokens em `static/src/input.css` na mesma entrega. Ver [research.md](./research.md).

## Sequenciamento (obrigatório)

```text
US1 (charts fundação) ──► US2 (painéis líder) ──► US3 (detalhe ciclo RH)
                              │
                              └── consomem _chart_block + dashboard_charts.js + payloads
P2 (colaborador) pode avançar em paralelo após tokens/DS da fundação visual.
P3 somente após P1+P2, se houver tempo até 03/09.
```

## Non-Goals / Denylist de lógica

> Espelha **FR-012** / **FR-014**. Operacional: [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md) + [contracts/path-allowlist.md](./contracts/path-allowlist.md).

**PROIBIDO**: máquina de estados; aprovação/reprovação; fórmulas de nota/aderência/%; mutação de `get_visible_users` / `ScopedObjectMixin`; models/migrations de domínio; SPA/DRF; nova lib de gráficos; reabrir shell/nav/login.

**PERMITIDO**: templates/partials/JS de apresentação; builders de payload/composição leve; `CicloDetailView` + rota GET (US3); updates DS + `input.css`.

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (constituição cita 5.x — desvio já conhecido do monólito)

**Primary Dependencies**: Django full stack (DTL + HTMX + Tailwind CSS CLI); **Chart.js 4.5.1** (CDN jsDelivr, só em páginas com gráfico via `extra_js`). Sem DRF, sem SPA, sem nova lib de gráficos.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **zero models/migrations de domínio**. Leitura de `AderenciaSnapshot`, `Avaliacao`, estrutura via `get_visible_users`.

**Testing**: pytest-django para payloads/escopo/regression; aceite guiado SC-001–007 + [quickstart.md](./quickstart.md).

**Target Platform**: Web autenticado; desktop-first; ~375px legível (empilhamento KPI → visual → tabela).

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Agregações leves síncronas; aderência só via snapshot Celery existente; sem recalcular % de aderência no request.

**Constraints**: Escopo só no backend; imutabilidade de histórico; US1 antes de US2/US3; DS + `input.css` na mesma entrega de padrão/token novo; P3 não bloqueia release.

**Scale/Scope**: 5 user stories (P1: US1–3; P2: US4; P3: US5 best-effort); superfícies dashboard + ciclo detalhe + polish P2/P3.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | DTL + HTMX + Tailwind; Chart.js 4.5.1 já no monólito (sem lib nova); sem DRF/SPA. |
| II. Segurança e Escopo no Backend | ✅ PASS | Views líder continuam `get_visible_users` sem alterá-lo; agregações recebem o `visible` já resolvido; ciclo detalhe usa `AdminCyclesMixin`/`RequiresAdminMixin` (AuthZ vigente de ciclos). |
| III. Imutabilidade e Integridade | ✅ PASS | Zero writes de domínio; zero mudança de FKs/`PROTECT`/snapshots históricos. |
| IV. Modularidade por Domínio | ✅ PASS | Charts/payloads em `dashboard`; detalhe de ciclo em `cycles`; components em `core`/templates. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Sem alterar `nota_final_lider`, etapas, approval; cobertura = composição de Counts já autorizados. |
| VI. Performance Assíncrona | ✅ PASS | Aderência continua Celery→`AderenciaSnapshot`; charts/cobertura sync leves; Celery novo só sob evidência. |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind; Chart.js pontual documentado; SQLite/PG parity nas agregações (`Count`/`annotate` portáveis). |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos = UI + payloads + allowlist; `data-model.md` declara zero models novos; rota US3 é DetailView read-only admin-only.

## Project Structure

### Documentation (this feature)

```text
specs/009-persona-visual-redesign/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── path-allowlist.md
│   ├── non-goals-denylist.md
│   ├── chart-catalog.md
│   ├── managerial-panel.md
│   └── cycle-managerial-detail.md
├── checklists/
└── tasks.md             # /speckit-tasks — NÃO criado aqui
```

### Source Code (repository root)

```text
apps/dashboard/
├── views.py                  # Personal/Team/Structure/Adherence/Admin — context KPIs/charts
├── chart_payloads.py         # Shape canônico + novos types (bar_horizontal, area, center value)
├── services/
│   ├── structure.py          # Reuso + composição cobertura (receive visible QS)
│   └── adherence.py          # Intacto (Celery compute)
├── tasks.py                  # Intacto (snapshots diários)
└── urls.py                   # rotas existentes (structure passa a carregar Chart)

apps/cycles/
├── views.py                  # + CicloDetailView (AdminCyclesMixin, DetailView GET)
├── urls.py                   # + path '<pk>/' name ciclo_detail (somente US3)
└── …                         # open/close/stage services INTACTOS

templates/
├── dashboard/
│   ├── _chart_block.html     # Reuso US1–3
│   ├── personal.html         # US1 (+ polish)
│   ├── team.html             # US1/US2
│   ├── structure.html        # US2 (entra no slice charts — reabertura B)
│   ├── adherence.html        # US2
│   └── admin.html            # US1
├── cycles/
│   ├── ciclo_list.html       # Link para detalhe (US3)
│   └── ciclo_detail.html     # Novo painel gerencial RH
└── components/
    ├── card.html             # KPIs
    ├── empty_state.html
    ├── next_step.html        # Consumo 008 — não reimplementar
    └── …

static/
├── js/dashboard_charts.js    # Catálogo tipos + valor central doughnut
└── src/input.css             # Tokens / .managerial-panel / chart canvas se necessário

docs/design-system.md         # Freeze v2: reabertura A/B/C + painel gerencial
```

**Structure Decision**: Monólito Django existente. Charts e painéis líder em `apps/dashboard` + templates; visão gerencial de ciclo como DetailView em `apps/cycles` consumindo builders de payload compartilhados. Sem novos apps.

## Complexity Tracking

> Nenhuma violação de Constituição que exija gate de exceção nova. Chart.js já justificado em 005; rota `cycles/<pk>/` é superfície de leitura admin alinhada à AuthZ vigente (não é AuthZ nova).

| Item | Nota |
|------|------|
| Django 6.x vs constituição 5.x | Desvio pré-existente do monólito — não introduzido por 009 |
| URL nova `ciclo_detail` | Explicitamente exigida pela spec FR-007; allowlist US3; denylist mantém open/close/stage |

## Mapa story → templates / partials / JS

| Story | Templates / partials | JS / CSS | Views / builders |
|-------|----------------------|----------|------------------|
| **US1** (fundação) | `_chart_block.html`, `personal.html`, `team.html`, `admin.html`; `components/empty_state.html`, `components/card.html` (mini-KPI vizinho) | `static/js/dashboard_charts.js`; Chart.js 4.5.1 CDN nos `extra_js`; `static/src/input.css` se altura/legenda/tokens | `chart_payloads.py` (types/palette finish); views personal/team/admin só payload/`type` |
| **US2** | `team.html` + `team_list_partial.html`; `structure.html`; `adherence.html` + `adherence_list_partial.html`; reuso `_chart_block` + `card` | Mesmo `dashboard_charts.js` (structure/adherence passam a carregar CDN+init); `input.css` wrapper painel | `StructureDashboardView` / `AdherenceListView` / `TeamDashboardView` — context KPIs + payloads; composição cobertura em `structure.py`/`chart_payloads` recebendo `visible` |
| **US3** | **Novo** `ciclo_detail.html`; `ciclo_list.html` (+ partial se link); includes `_chart_block`, checklist RH (008) | Chart.js + `dashboard_charts.js` no detalhe | **Novo** `CicloDetailView`; `urls.py` `cycles/<pk>/`; reuso `build_rh_pre_open_checklist` + payloads admin/estrutura |
| **US4** P2 | `goals/expectations.html`, `goals/meta_list.html` (+ partials), `reviews/avaliacao_list.html` (+ detail se polish de chrome), `pdi/pdi_*.html`, `talent/my_classification.html` | Só tokens/classes via `input.css` se preciso | Context mínimo CTA — **sem** novo mapa guidance |
| **US5** P3 | `organization/area_*`, `cargo_*`, `user_*`, `competencies/*`, `audit/*`, `notifications/*` | Visual-only | Sem mudança de CRUD/AuthZ |

## Escopo de agregações e `get_visible_users`

1. **Não alterar** `apps/accounts/services/scope.py` nem assinatura/comportamento de `get_visible_users`.
2. Structure/Team/Adherence: views resolvem `visible` como hoje e **passam** o QS/ids aos builders.
3. Cobertura área/cargo: Counts sobre `visible` + `Avaliacao` do ciclo filtrado — composição, não fórmula de nota.
4. Aderência panels: ler `AderenciaSnapshot` já filtrado (admin vê todos; manager/leader via `lider__in=visible`).
5. Ciclo detalhe RH: gate `RequiresAdminMixin` (como list/CRUD de ciclos); agregações do `ciclo` do `pk` sem relaxar AuthZ.

## Atualização Freeze (obrigatória na entrega do contrato visual)

- `docs/design-system.md`: reabrir A (charts expressivos + paleta acabamento), B (incluir `structure.html`), C (painel gerencial canônico).
- `static/src/input.css`: quaisquer classes/tokens novos do padrão painel/chart na **mesma** PR/entrega, com rebuild `tailwind.css`.
