# Implementation Plan: 9-box Interativa (Matriz de Talentos)

**Branch**: `006-ninebox-interativa` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-ninebox-interativa/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Transformar a matriz 9-box estática (`TalentMatrixView` + `templates/talent/matrix.html`) em superfície operacional fatiável: drawer in-matrix (HTMX) para inspecionar/salvar potencial e toggle `visivel_ao_colaborador`; drag-and-drop (HTML5 nativo) que altera **somente potencial**; leitura no escopo para gerente/admin; sem SPA/DRF, sem novas fórmulas, zero migrations, consumindo Freeze 004.

Abordagem: partials DTL + endpoints HTMX reutilizando `upsert_classification`, `derive_desempenho`, `calculate_quadrante` e toggle (view/serviço equivalente); JS local mínimo só para DnD + a11y do drawer. `classify` permanece fallback (FR-013). Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (projeto; constituição cita 5.x — desvio já conhecido)

**Primary Dependencies**: Django full stack (DTL + HTMX 2.0.4 CDN + Tailwind CSS CLI). JS local mínimo (`static/js/ninebox_matrix.js` ou equivalente) **somente** para HTML5 drag-and-drop + init/foco do drawer. Sem DRF, sem SPA, sem Chart.js, sem lib de drag.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **zero models/migrations**. Persistência via `ClassificacaoTalento` existente (`potencial`, `desempenho` derivado, `quadrante`, `visivel_ao_colaborador`).

**Testing**: pytest-django para permissão/escopo/IDOR + contratos HTMX/drag se necessário; aceite principal = revisão guiada (SC-001–007) + [quickstart.md](./quickstart.md). Script legado `scripts/validate_t070.py` como regressão de acesso à matriz.

**Target Platform**: Web app autenticado (desktop-first para drag; mobile consultável + calibração via drawer — FR-010)

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Calibração admin ≤ 1 min/pessoa via drawer (SC-001); feedback imediato sem full page reload obrigatório; upsert pontual (sem agregação pesada / sem Celery nesta feature — Princípio VI N/A para writes leves).

**Constraints**: Escopo/segurança 100% backend (`RequiresAdminMixin` escrita; `RequiresManagerOrAdminMixin` + `get_visible_users` leitura); UI não autoriza; fórmulas `derive_desempenho` / `calculate_quadrante` **inalteradas** (só recalcular após potencial válido); gate `visivel_ao_colaborador` default False; Freeze 004 consumido (sem redesenhar shell/nav/topbar/marca); OUT da spec respeitado.

**Scale/Scope**: 3 user stories (P1 drawer MVP → P2 drag → P3 read-only/a11y/empty); domínio `apps/talent` + templates/static; `classify` fallback mantido.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | DTL + HTMX + Tailwind; partials HTML (não JSON/DRF); drag = HTML5 nativo sem lib; sem SPA. |
| II. Segurança e Escopo no Backend | ✅ PASS | Escrita: `RequiresAdminMixin` + `upsert_classification` (`PermissionDenied`); leitura matriz: `RequiresManagerOrAdminMixin` + `get_visible_users`; IDOR coberto nos contracts; UI não é fonte de AuthZ. |
| III. Imutabilidade e Integridade | ✅ PASS | Zero mudança de FKs/`PROTECT`; auditoria append-only existente (signals) continua cobrindo potencial/visibilidade; sem histórico visual novo. |
| IV. Modularidade por Domínio | ✅ PASS | Trabalho em `apps/talent` (+ `core` só se drawer canônico mínimo); reuso de `accounts.services.scope` sem mover domínio. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | `derive_desempenho` / `calculate_quadrante` intactos; desempenho nunca editado por drag/drawer como valor livre. |
| VI. Performance Assíncrona | ✅ PASS | Writes pontuais síncronos (upsert/toggle); sem agregação pesada no request; Celery não exigido. |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind CLI; JS mínimo local alinhado à constituição (sem dependência externa nova). |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos são partials HTMX + payload de drag potencial-only (sem API REST pública). `data-model.md` declara zero models/migrations. OUT explícito respeitado (sem edição livre de desempenho, sem Chart.js, sem redesign Freeze).

## Project Structure

### Documentation (this feature)

```text
specs/006-ninebox-interativa/
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0
├── data-model.md        # Phase 1 (zero models novos)
├── quickstart.md        # Phase 1 validação SC-001–007
├── contracts/           # Phase 1
│   ├── htmx-drawer-partials.md
│   ├── drag-persist.md
│   ├── authz-scope.md
│   └── a11y-matrix-drawer.md
├── checklists/
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
apps/talent/
├── views.py                 # TalentMatrixView + ClassifyTalentView + ToggleVisibilityView
│                            # (+ views/actions HTMX: drawer GET, save potencial, toggle, move)
├── urls.py                  # rotas existentes + endpoints HTMX internos
├── forms.py                 # ClassificacaoForm (reuso potencial)
├── models.py                # ClassificacaoTalento — leitura/write fields existentes (sem migration)
└── services/
    └── classification.py    # upsert_classification, derive_desempenho, calculate_quadrante
                             # (+ opcional toggle_classification_visibility)

apps/core/
├── mixins.py                # RequiresAdminMixin / RequiresManagerOrAdminMixin (reuso)
└── htmx.py                  # is_htmx / padrões de resposta (reuso estilo PDI)

apps/accounts/services/scope.py  # get_visible_users (leitura matriz)

templates/talent/
├── matrix.html              # grade + #matrix-drawer + filtros
├── classify.html            # fallback FR-013 (mantido)
├── my_classification.html   # gate colaborador intacto
└── partials/                # novos
    ├── _drawer.html
    ├── _cell.html           # (ou equivalente)
    └── _person_card.html

static/js/
└── ninebox_matrix.js        # HTML5 DnD + init; degradação mobile

templates/components/        # button, badge_status, empty_state, input — consumir Freeze
docs/design-system.md        # nota canônica mínima de drawer lateral se introduzido
```

**Structure Decision**: Monólito Django existente. Sem apps/models/endpoints REST novos. Partials HTMX no domínio `talent`; DnD em JS local. Slices FR-014: US1 drawer → US2 drag → US3 read-only/a11y.

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Django 6.0.7 vs constituição (Django 5.x) | Já no `requirements.txt` e planos 001–005 | Downgrade sem benefício |
| JS local para DnD (além de HTMX) | Spec exige drag; HTML5 DnD não é declarativo HTMX | Lib SortableJS: dependência externa injustificada (Princípio I) |
| Drawer lateral novo (vs modal centrado) | Spec exige painel in-matrix; `components/modal.html` é centrado `max-w-lg` | Forçar modal: fere FR-001 / UX de calibração na grade |

## Ordem de entrega (FR-014)

1. **Foundational** — Partials (`_person_card`, `_cell`, shell `#matrix-drawer`); extrair builder de `matriz_rows` se necessário; endpoints HTMX esqueleto; tokens Freeze.
2. **Slice 1 / MVP (US1 P1)** — Abrir drawer; salvar potencial via `upsert_classification`; toggle visibility (HTMX); refresh célula/grade + toasts; `classify` como link secundário/fallback.
3. **Slice 2 (US2 P2)** — HTML5 DnD potencial-only + persist; política snap (research R4); revert on error; mobile degrada para drawer.
4. **Slice 3 (US3 P3)** — Drawer read-only para não-admin; empty/loading honestos; a11y teclado/foco; rótulos além da cor; alternativa ao drag = drawer.
5. **Polish mínimo + quickstart** — Nota em `docs/design-system.md` se drawer for canônico; validação SC-001–007.

Detalhamento de tarefas: `/speckit-tasks` (não este comando).
