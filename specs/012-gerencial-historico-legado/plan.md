# Implementation Plan: Visualizações Gerenciais e Históricas Pós-Legado

**Branch**: `012-Visualização-pós-legado` (spec dir `012-gerencial-historico-legado`) | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-gerencial-historico-legado/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos de design em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). Clarifications 2026-08-14 são **decisões fechadas** — não reabrir. **Não** gera `tasks.md` (isso é `/speckit-tasks`).

## Summary

Após a 011 (~57 ciclos encerrados + ~700 cabeçalhos sem nota), os painéis 005/007/009 saturam, misturam arquivo com operação e fazem fallback silencioso para um ciclo encerrado. Esta fatia **separa** a home operacional (ciclo **aberto** ou empty honesto) do arquivo/tendência **explícitos**, com pipeline de etapas como visual principal, teto Top-N + “Outros” (N=8), estética Freeze v2 leve, e US3 P2 de tendência de **etapa/conclusão** (`area`, últimos 8 ciclos no escopo) via `?visao=historico` nas URLs já existentes.

Abordagem: apresentação Django (DTL + HTMX + Tailwind) + Chart.js **4.5.1** já no monólito; reuso de `chart_payloads`, `_chart_block`, `dashboard_charts.js`, `.managerial-panel`. Zero models/migrations; AuthZ intacta; denylist de domínio. Agregação síncrona; Celery só se medição exigir. Freeze D em `docs/design-system.md` na mesma entrega (FR-019). Ver [research.md](./research.md).

## Sequenciamento (obrigatório)

```text
Fundação densidade/empty/Freeze D
        │
        ▼
US1 P1 (admin + lista/detalhe ciclo + pessoal densidade)
        │
        ▼
US2 P1 (time / estrutura / aderência)  ── mesmo bloco + default aberto
        │
        ▼
US3 P2 (visao=historico → area etapa/conclusão; empty aderência/gap)
```

US2 consome helpers de US1. US3 não começa antes do default operacional estar estável (senão a tendência vira a home). Pessoal: só teto/empty/estética na fundação/US1 — **sem** tendência.

## Non-Goals / Denylist de lógica

> Espelha **FR-018**. Operacional: [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md) + [contracts/path-allowlist.md](./contracts/path-allowlist.md).

**PROIBIDO**: `stage.py`; `cycle.py` (open/close); `approval.py`; mutators `evaluation.py`; `adherence.py` (fórmulas); `scope.py`; snapshots write-once; migrations de nota; 6.5.5; PDI; métrica nova; SPA/DRF; lib/plugin npm; rota de histórico; tendência em `dashboard/personal`; fixtures `data/legado-solides/raw/`.

**PERMITIDO**: context/views de leitura; Top-N; builder de tendência de etapa; templates; JS local Chart.js 4.5.1; Freeze D + `input.css` se necessário.

Contratos visuais **reusados, não reabertos**: `specs/009-persona-visual-redesign/contracts/{chart-catalog,managerial-panel,cycle-managerial-detail}.md`.

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (constituição cita 5.x — desvio já conhecido do monólito)

**Primary Dependencies**: Django full stack (DTL + HTMX + Tailwind CSS CLI); **Chart.js 4.5.1** (CDN jsDelivr, só em páginas com gráfico via `extra_js`). Sem DRF, sem SPA, sem nova lib de gráficos, sem plugin npm.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **zero models/migrations**. Leitura de `Ciclo`, `Avaliacao`, `AderenciaSnapshot`; estrutura via `get_visible_users`. Sem schema de nota.

**Testing**: pytest-django das superfícies dashboard/ciclo; regressão `test_stage_machine` / `test_scope` / `test_reject_stage_invariant`; fixtures em `tests/` (nunca `data/legado-solides/raw/`). Aceite guiado [quickstart.md](./quickstart.md).

**Target Platform**: Web autenticado; desktop-first; ~375px legível (KPI → visual → drill, sem scroll horizontal do canvas).

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Agregações leves síncronas; SC-001 < 3 s percebidos com dump 011 e zero ciclo aberto. Aderência só via snapshot Celery existente. Task nova só com evidência de peso.

**Constraints**: Escopo só no backend; imutabilidade de histórico; default = aberto; histórico só explícito; N=8 (densidade e tendência); denylist de domínio; reuso do catálogo 009; FR-019 DS na mesma entrega.

**Scale/Scope**: 3 user stories (P1: US1–US2; P2: US3); ~57 ciclos encerrados + ~700 cabeçalhos sem nota no ambiente de validação; superfícies admin, time, estrutura, aderência, lista/detalhe de ciclo, pessoal (disciplina visual sem US3).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | DTL + HTMX + Tailwind; Chart.js 4.5.1 já no monólito (sem lib nova); query `visao=` em vez de SPA/rota nova; sem DRF. |
| II. Segurança e Escopo no Backend | ✅ PASS | Mixins vigentes; builders **recebem** `visible`; UI não autoriza; `scope.py` / `get_visible_users` intocáveis. |
| III. Imutabilidade e Integridade | ✅ PASS | Zero writes de domínio; zero FKs/`PROTECT`/snapshots/migrations de nota. |
| IV. Modularidade por Domínio | ✅ PASS | Charts/tendência em `dashboard`; detalhe/lista em `cycles` (só apresentação); `core` empty/card. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Sem alterar `nota_final_lider`, etapas, approval; tendência = Count de etapa/`concluida` já persistidos; cobertura ≠ aderência. |
| VI. Performance Assíncrona | ✅ PASS | Aderência continua Celery→`AderenciaSnapshot` (não recalcular % no request). Pipeline/Top-N/tendência ≤8 ciclos = Counts sync leves (FR-020). Celery novo só sob medição. |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind; Chart.js pontual já justificado em 005/009; agregações `Count`/`annotate` portáveis SQLite/PG. |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos = densidade/histórico/empty + allowlist/denylist; `data-model.md` declara zero models novos e zero schema de nota; US3 é query na URL existente. Princípio VI honrado sem violar FR-020: cálculo pesado de aderência **não** entra no request; o restante é composição leve — alinhado ao precedente 009 R8.

## Project Structure

### Documentation (this feature)

```text
specs/012-gerencial-historico-legado/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── density-history-empty.md
│   ├── path-allowlist.md
│   └── non-goals-denylist.md
├── checklists/
└── tasks.md             # /speckit-tasks — NÃO criado aqui
```

### Source Code (repository root)

```text
apps/dashboard/
├── views.py                    # Admin/Team/Structure/Adherence/Personal — default aberto, empty, visao=
├── chart_payloads.py           # + top_n_with_others; DENSITY_TOP_N; HISTORY_DEFAULT_N
├── services/
│   ├── structure.py            # Densidade na cobertura (recebe visible)
│   ├── history.py              # NOVO — tendência etapa/conclusão (recebe visible)
│   └── adherence.py            # INTOCÁVEL (fórmula)
├── tasks.py                    # INTOCÁVEL
└── urls.py                     # sem path novo

apps/cycles/
├── views.py                    # CicloListView / CicloDetailView — só apresentação
├── urls.py                     # INTOCÁVEL (sem rota de histórico)
└── services/stage.py, cycle.py # DENYLIST

apps/accounts/services/scope.py # DENYLIST
apps/goals/services/approval.py # DENYLIST
apps/reviews/services/evaluation.py  # mutators DENYLIST

templates/
├── dashboard/
│   ├── _chart_block.html       # Reuso; fora de partials HTMX
│   ├── admin.html              # US1 + toggle US3
│   ├── team.html               # US2 + toggle US3
│   ├── structure.html          # US2 densidade/empty
│   ├── adherence.html          # US2 empty snapshot
│   ├── personal.html           # Densidade/empty/estética; sem US3
│   ├── team_list_partial.html  # Sem chart
│   └── adherence_list_partial.html
├── cycles/
│   ├── ciclo_list.html
│   ├── ciclo_list_partial.html # Sem chart
│   └── ciclo_detail.html       # Pipeline + empty sem_nota + toggle US3
└── components/
    ├── card.html
    └── empty_state.html

static/
├── js/dashboard_charts.js      # Catálogo 009; leveza; init DOMContentLoaded
└── src/input.css               # Só se Freeze D exigir token

docs/design-system.md           # Freeze D (densidade / histórico / empty / leveza)

tests/
├── test_dashboard_operational_default.py  # novo
├── test_dashboard_history_mode.py         # novo
├── test_chart_payloads.py                 # estender
├── test_structure_coverage.py
├── test_ciclo_detail.py
├── test_stage_machine.py                  # regressão
├── test_scope.py
└── test_reject_stage_invariant.py
```

**Structure Decision**: Monólito Django existente. Toda a lógica nova é apresentação em `apps/dashboard` (+ context mínimo em `cycles` views). Sem novos apps, sem novas URLs, sem schema.

## Complexity Tracking

> Nenhuma violação de Constituição que exija gate de exceção nova. Chart.js já justificado em 005; query `visao=` não é AuthZ nova.

| Item | Nota |
|------|------|
| Django 6.x vs constituição 5.x | Desvio pré-existente do monólito — não introduzido por 012 |
| Princípio VI vs Counts no request | Mesmo precedente 009: aderência via snapshot; resto leve. US3 cap N=8. Celery novo só com evidência (FR-020) |
| `get_open_ciclo` em `apps/goals/forms.py` | Reuso as-is; **não** mover nesta fatia |

## Mapa story → templates / views / builders

| Story | Templates / partials | JS / CSS / DS | Views / builders |
|-------|----------------------|---------------|------------------|
| **Fundação** | `_chart_block.html`, `empty_state.html`, `card.html` | `dashboard_charts.js`; `docs/design-system.md` Freeze D; `input.css` se token | `chart_payloads.top_n_with_others`; constantes N=8 |
| **US1** P1 | `admin.html`; `ciclo_list.html` (+ partial sem chart); `ciclo_detail.html`; `personal.html` (densidade only) | Chart.js 4.5.1 já no `extra_js` | `AdminDashboardView` (matar `ciclo_indicador`); seletor agrupado; KPIs operacionais; `CicloListView`/`CicloDetailView` apresentação; `PersonalDashboardView` Top-N |
| **US2** P1 | `team.html` + `team_list_partial`; `structure.html`; `adherence.html` + partial | Mesmo init; charts fora do swap HTMX | Team/Structure/Adherence: default aberto, empty, seletor, Top-N cobertura/ranking |
| **US3** P2 | admin / team / `ciclo_detail` — toggle | `type: area` já no catálogo | `services/history.py`; `visao=historico`; empty `sem_nota` aderência/gap |

## Escopo de agregações e `get_visible_users`

| Builder | Entrada | Proibido |
|---------|---------|----------|
| `top_n_with_others` | labels/values já contados | Inventar métrica; média de % de cobertura |
| `build_structure_coverage` + densidade | `visible` da view + ciclo | Recalcular visible; misturar aderência |
| `history.py` tendência | `visible` + lista ≤ N ciclos | `compute_adherence`; plotar arquivo completo; 0 em lacuna |
| Views admin/team | Mixins + `get_open_ciclo()` / `?ciclo=` / `?visao=` | Fallback silencioso para encerrado |

## Constantes de apresentação (calibradas no plan)

| Constante | Valor | Spec |
|-----------|-------|------|
| `DENSITY_TOP_N` | **8** | Faixa ~5–10; nunca eixos crus de dezenas |
| `HISTORY_DEFAULT_N` | **8** | N pequeno; nunca ~57 ciclos |
| Label residual | `"Outros"` | Contagens/cobertura ponderada |
| Query modo | `visao=historico` | Clarification: modo/query, não página |
| Query janela | `ciclos=<ids>` | Cap = `HISTORY_DEFAULT_N` |

Mudar 8→5 ou 8→10 é calibração de apresentação, **não** reabre a spec.

## Constitution Check (pós-Phase 1)

Reavaliado após `research.md`, `data-model.md`, `contracts/` e `quickstart.md`: **PASS** em I–VI e stack. Sem Complexity Tracking de violação nova.
