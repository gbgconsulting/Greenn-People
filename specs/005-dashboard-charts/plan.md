# Implementation Plan: Visualizações Gráficas nos Dashboards

**Branch**: `005-dashboard-charts` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-dashboard-charts/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Adicionar visualizações gráficas leves sobre métricas **já existentes** nos dashboards admin, time e pessoal — distribuição de aderência por faixas (`alta`/`media`/`baixa`), progresso de avaliações/etapas do ciclo, status agregado do escopo e gaps esperado × nota — sem novas fórmulas, sem SPA/DRF e sem 9-box interativa.

Abordagem: Chart.js (CDN versionado, só em templates de dashboard com gráfico) + payloads preparados no contexto Django / `json_script`; reutilizar `apps/dashboard` e `build_fr005_context`; consumir Freeze 004. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (projeto; constituição cita 5.x — desvio já conhecido)

**Primary Dependencies**: Django full stack (DTL + HTMX 2.0.4 CDN + Tailwind CSS CLI); **Chart.js 4.x** (CDN jsDelivr, carregado **somente** em páginas de dashboard com gráfico — FR-013). Sem DRF, sem SPA.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **zero models/migrations**. Leitura de `AderenciaSnapshot`, `Avaliacao`, contexto pessoal existente.

**Testing**: pytest-django para regressão de escopo/payloads se necessário; aceite principal = revisão guiada (SC-001–007) + [quickstart.md](./quickstart.md).

**Target Platform**: Web app autenticado (desktop-first; gráficos legíveis via scroll no mobile)

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Scan humano ≤ 10 s (SC-001/003); agregações de chart = `Count`/`group by` leves ou reuso de queries já feitas — **sem** recalcular aderência no request (Princípio VI).

**Constraints**: Escopo/segurança e cálculos **inalterados**; UI não autoriza; Freeze 004 consumido (sem reabrir shell/nav/topbar/marca); HTMX de listas/partials preservado; OUT: 9-box interativa, novas métricas/snapshots, Impeccable, export/relatórios, dashboards novos.

**Scale/Scope**: 3 user stories (P1 admin MVP → P2 time → P3 pessoal); superfícies existentes `dashboard:admin|team|personal` (+ correlatos só se mesma métrica já exposta).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS (exceção documentada) | DTL + HTMX + Tailwind; dados via contexto/partials; **sem** SPA/DRF. Chart.js justificado: canvas/SVG acessível + séries rotuladas excedem HTML/CSS puro com custo menor que reinventar (FR-013 + Complexity Tracking). |
| II. Segurança e Escopo no Backend | ✅ PASS | Charts consomem só o que as views já autorizam (`Requires*Mixin`, `get_visible_users`); UI não filtra autoridade; time agrega sobre o mesmo queryset de escopo (não a página HTMX). |
| III. Imutabilidade e Integridade | ✅ PASS | Zero writes de domínio; zero mudança de FKs/`PROTECT`/snapshots. |
| IV. Modularidade por Domínio | ✅ PASS | Trabalho em `apps/dashboard` + templates `dashboard/` + helpers de formatação; reuso de `reviews.services.evaluation` / `talent` sem mover domínio. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Faixas via `aderencia_status()` já existente; gaps = pares já em `competencias_resumo`; sem alterar `nota_final_lider`/etapas. |
| VI. Performance Assíncrona | ✅ PASS | Snapshots de aderência continuam Celery-only; request só conta/formata o já persistido ou campos já lidos. |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind CLI; Chart.js = dependência pontual documentada (não substitui stack). |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos são payloads de visualização + loading de script (sem API REST pública). `data-model.md` declara zero models/migrations. OUT explícito respeitado.

## Project Structure

### Documentation (this feature)

```text
specs/005-dashboard-charts/
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0
├── data-model.md        # Phase 1 (zero models novos)
├── quickstart.md        # Phase 1 validação SC-001–007
├── contracts/           # Phase 1
│   ├── admin-charts.md
│   ├── team-charts.md
│   ├── personal-charts.md
│   ├── chart-script-loading.md
│   └── htmx-dashboard-surfaces.md
├── checklists/
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
apps/dashboard/
├── views.py                 # Admin/Team/Personal (+ helpers de payload chart)
├── models.py                # AderenciaSnapshot (leitura only — sem migration)
├── services/
│   ├── adherence.py         # intacto (Celery)
│   └── structure.py         # intacto; correlato structure NÃO no slice 2 (métrica ≠ etapa)
└── urls.py                  # rotas existentes (sem API pública nova)

apps/reviews/services/evaluation.py   # build_fr005_context / competencias_resumo (reuso)
apps/talent/services/classification.py # get_visible_classification_for_collaborator (9-box intacta)

templates/dashboard/
├── admin.html               # MVP: 2 charts + tabela menor aderência
├── team.html                # slice 2: chart status escopo
├── team_list_partial.html   # HTMX preservado
├── personal.html            # slice 3: barras gap
└── _chart_*.html            # includes opcionais (canvas + empty + json_script)

static/js/
└── dashboard_charts.js      # init Chart.js a partir de JSON embutido (sem fetch REST)

docs/design-system.md        # consumir Freeze; nota FR-013 (lib + superfícies) — sem reabrir marca
```

**Structure Decision**: Monólito Django existente. Sem apps/models/endpoints REST novos. Chart vendor via CDN no `{% block extra_js %}` das páginas-alvo; init em JS local mínimo. Slices: US1 admin → US2 team → US3 personal.

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Django 6.0.7 vs constituição (Django 5.x) | Já no `requirements.txt` e planos 001–004 | Downgrade sem benefício |
| Chart.js (lib externa pontual) | Gráficos rotulados/acessíveis em canvas com pouco JS; nativo DTL insuficiente para séries + tooltips + a11y sem reinventar | Barras HTML/CSS puras: frágeis para multi-série, legendas e responsivo; ApexCharts mais pesado/opinionado |
| CDN Chart.js (como HTMX) | Alinha ao vendor JS já usado (`htmx.org@2.0.4` em `base.html`); pin de versão | Vendor local: válido depois se política de offline mudar; não bloqueia MVP |

## Ordem de entrega (FR-012)

1. **Slice 1 / MVP (US1 P1)** — `AdminDashboardView`: (a) distribuição aderência por faixas; (b) progresso avaliações/etapas; preservar tabela `snapshots_destaque`; empty states honestos; documentar lib (SC-007).
2. **Slice 2 (US2 P2)** — `TeamDashboardView`: status agregado do escopo (`get_visible_users`); zero vazamento; HTMX da lista intacto. **Structure**: fora (não expõe a mesma métrica de etapa/status do time).
3. **Slice 3 (US3 P3)** — `PersonalDashboardView`: barras gap esperado × nota; empty se sem dados; 9-box intacta.

Detalhamento de tarefas: `/speckit-tasks` (não este comando).
