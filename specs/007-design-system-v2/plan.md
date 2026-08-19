# Implementation Plan: Design System v2 — Polish Visual

**Branch**: `007-design-system-v2` | **Date**: 2026-08-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-design-system-v2/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Elevar a qualidade visual do **app autenticado** e atualizar o Design System para **Freeze v2** (tipografia display/UI self-hosted, botões, cards/KPI, table-frame, empty states, polish de charts 005 e matriz 006), **sem** novas capacidades de negócio, rotas, models, migrations ou libs front. Login e `base_auth` são **OUT duro** (FR-002).

Abordagem: tokens tipográficos novos sob escopo `.app-shell` em `base.html` (Inter global intocado para auth); refinamentos em `templates/components/*` e superfícies piloto; Chart.js options + CSS do bloco; classes/ARIA na ninebox; evidência before/after 5–8 pilotos + checklist OUT; dualidade `docs/design-system.md` ↔ `static/src/input.css` fechada na mesma entrega. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django (projeto vigente; constituição cita 5.x — desvio já conhecido nos planos anteriores)

**Primary Dependencies**: Django full stack (DTL); HTMX 2.x; Tailwind CSS CLI (`static/src/input.css` → `static/css/tailwind.css`); Chart.js **4.5.1** (já usado); JS local `dashboard_charts.js`, `ninebox_matrix.js`, `modal.js`. **Sem** novas libs UI/chart/SPA.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **sem schema change**, sem queries de negócio novas.

**Testing**: Aceite principal = revisão guiada before/after + [quickstart.md](./quickstart.md) + [contracts/out-checklist.md](./contracts/out-checklist.md). Sem suite TDD visual obrigatória. Smoke dos happy paths 005/006.

**Target Platform**: Web app autenticado (desktop-first; mobile existente)

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Scan humano ≤ 10 s por piloto (SC-001); fontes self-hosted com `font-display: swap`; sem endpoints/agregações novas.

**Constraints**:
- Zero lógica de negócio / AuthZ / fórmulas
- Tipografia v2 **não** vaza para login/`base_auth`
- UI não autoriza
- Freeze reaberto **com decisão explícita desta spec** → fecha Freeze v2 na mesma entrega (FR-009)
- Superfície de código allowlisted ([research R4](./research.md))

**Scale/Scope**: 5 user stories (US1–US5 / P1–P5); 5–8 superfícies piloto autenticadas; shell leve opcional após P1–P4

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | Só DTL + HTMX + Tailwind CLI + JS local; Chart.js e fontes = reuso/asset, não libs UI novas (Complexity Tracking). |
| II. Segurança e Escopo no Backend | ✅ PASS | Zero mudança AuthZ/escopo; polish não altera gates 006 nem views de domínio. |
| III. Imutabilidade e Integridade | ✅ PASS | Sem writes de domínio; sem FKs/snapshots. |
| IV. Modularidade por Domínio | ✅ PASS | UI compartilhada em `templates/components` + CSS; drawer ninebox permanece em `talent`; sem app novo. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Nenhuma fórmula/`nota_final`/aderência alterada; charts não mudam payloads. |
| VI. Performance Assíncrona | ✅ PASS | Sem agregações novas; só apresentação. |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind CLI preservados. |

**Decisão de Freeze**: Reabertura **explícita** via spec 007; entrega fecha **Freeze v2** (doc + CSS + components) — conforme regra 4 do Freeze 004 / FR-009.

**Tensão docs vs código**: Mitigada atualizando `docs/design-system.md` e `static/src/input.css` (+ components) na mesma PR.

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos são de apresentação/isolamento (sem API REST). `data-model.md` declara zero models Django. OUT documentado em contracts; sem exceções injustificadas.

## Project Structure

### Documentation (this feature)

```text
specs/007-design-system-v2/
├── plan.md                 # This file
├── research.md             # Phase 0
├── data-model.md           # Phase 1 (entidades de apresentação)
├── quickstart.md           # Phase 1 validação
├── contracts/
│   ├── freeze-v2.md
│   ├── auth-surface-isolation.md
│   ├── chart-visual-polish.md
│   ├── ninebox-visual-only.md
│   ├── path-allowlist.md          # T004 — gate de paths permitidos/proibidos
│   └── out-checklist.md
├── evidence/before-after/  # Screenshots + README (US5)
├── checklists/
└── tasks.md                # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root) — allowlist

```text
docs/design-system.md              # Freeze → v2

static/
├── src/input.css                  # tokens display/ui + escopo .app-shell; chart height/rhythm
├── fonts/                         # Inter (existente) + Fraunces + Source Sans 3 (novos WOFF2)
├── css/tailwind.css               # rebuild CLI
└── js/
    ├── dashboard_charts.js        # options visuais apenas
    └── ninebox_matrix.js          # feedback visual / ARIA suporte apenas

templates/
├── base.html                      # body.app-shell (+ head tipografia se preciso)
├── components/
│   ├── button.html
│   ├── card.html                  # KPI
│   ├── empty_state.html
│   ├── badge_status.html
│   ├── sidebar.html               # opcional pós P1–P4 (densidade/tipo)
│   └── topbar.html                # idem
├── dashboard/
│   ├── admin.html / team.html / personal.html
│   └── _chart_block.html
├── talent/
│   ├── matrix.html
│   └── partials/_cell.html / _person_card.html / _drawer.html
├── cycles/ciclo_list*.html
├── reviews/avaliacao_list*.html
└── pdi/pdi_detail.html / pdi_form.html
```

**Explicitamente fora da árvore de mudança**: `templates/accounts/base_auth.html`, `templates/accounts/login.html`, `apps/*/services`, models, migrations, urls/views de negócio.

**Structure Decision**: Monólito existente. Trabalho 100% apresentação/tokens/docs. Sem novos apps, endpoints ou schema.

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Chart.js já no projeto (não é lib nova) | Polish FR-005 exige options da lib já adotada em 005 | Reimplementar charts em SVG/CSS puro destruiria contrato 005 |
| JS local ninebox/charts | Feedback visual e Chart init já existem | Reescrever em templates puros quebra interatividade/altura responsiva |
| Fontes Fraunces + Source Sans 3 (assets) | Hierarquia display vs UI (US1); self-host | Só escala Inter insuficiente para SC-005; CDN externo viola política local |
| Dualidade doc ↔ CSS | Natureza de design tokens no stack Tailwind | Um arquivo não serve HTML e referência humana |
| Django 6.x vs constituição 5.x | Já no projeto / planos 001–006 | Downgrade sem benefício |

## Ordem de entrega (P1→P5)

1. **Foundational**: fontes self-host + tokens + `.app-shell` + draft Freeze v2 (isolamento login) — base US1  
2. **US1 P1**: tipografia display/UI nas superfícies piloto autenticadas  
3. **US2 P2**: `button`, KPI/`card`, table-frame, `empty_state`  
4. **US3 P3**: polish Chart.js options + `_chart_block` / CSS altura  
5. **US4 P4**: polish visual matriz (grade, cards, drawer domínio, drag/empty)  
6. **US5 P5**: Freeze v2 final + evidência 5–8 pilotos + checklist OUT  
7. **Shell leve** (opcional): densidade/tipografia sidebar/topbar se couber — sem redesign IA nav  

Não gerar `tasks.md` aqui (`/speckit-tasks`).
