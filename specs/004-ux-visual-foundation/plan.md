# Implementation Plan: Fundação Visual e UX Estável

**Branch**: `004-ux-visual-foundation` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-ux-visual-foundation/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Estabelecer e congelar a fundação visual/UX do Greenn People a partir do baseline operacional limpo (sem WIP Impeccable): progressive disclosure da Administração (Governança / Cadastros / Sistema) com destaque a Ciclos e Aderência; hierarquia escaneável nos dashboards time + pessoal sem novos KPIs/gráficos; consistência em login/PDI/avaliações/forms preservando HTMX; contexto mínimo de ciclo na topbar via context processor + `get_open_ciclo()`; a11y mínima do shell (skip link, `aria-current`, focus-visible, focus trap, indicador HTMX) sem libs novas; evidência before/after em 7 telas-piloto e freeze em `docs/design-system.md`.

Abordagem: mudanças scoped por superfície/padrão (DTL + Tailwind + JS mínimo em `modal.js`); zero models/migrations; zero APIs REST. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (projeto; constituição cita 5.x — desvio já conhecido; ver Complexity Tracking)

**Primary Dependencies**: Django full stack (DTL); HTMX 2.x (CDN vigente); Tailwind CSS CLI (`static/src/input.css` → `static/css/tailwind.css`); JS local `static/js/modal.js`. Sem DRF, sem libs de chart, sem package a11y novo.

**Storage**: SQLite (dev) / PostgreSQL (prod) — **sem schema change**. Leitura de `cycles.Ciclo` (`status=ABERTO`) apenas.

**Testing**: pytest-django para regressões leves se necessário (ex.: context processor retorna ciclo / None); aceite principal = revisão guiada + checklist teclado ([quickstart.md](./quickstart.md)). Screenshots em `evidence/before-after/`.

**Target Platform**: Web app autenticado (desktop-first; mobile drawer existente)

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Scan humano < 5 s (SC-001/002); topbar +1 query simples de ciclo aberto por request autenticado (aceitável)

**Constraints**: Escopo/segurança e cálculos **inalterados**; UI não autoriza; uma superfície/padrão por vez; OUT: gráficos novos, 9-box interativa, SPA/DRF, novas métricas, WIP Impeccable, landing marketing; stack obrigatória DTL+HTMX+Tailwind CLI

**Scale/Scope**: 7 telas-piloto (conjunto A); 6 user stories P1–P2; components em `templates/components/` + docs + CSS tokens

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | Só DTL/HTMX/Tailwind/JS vanilla; context processor nativo; sem DRF/SPA/libs chart/a11y npm. |
| II. Segurança e Escopo no Backend | ✅ PASS | Nav/topbar não mudam regras de visibilidade; `{% if user.is_* %}` e views/`ScopedObjectMixin` intactos (FR-014). |
| III. Imutabilidade e Integridade | ✅ PASS | Sem writes de domínio; sem alteração de FKs/`PROTECT`/snapshots. |
| IV. Modularidade por Domínio | ✅ PASS | UI compartilhada em `templates/` + `apps.core` (context processor); sem app novo; sem mover domínio de ciclo nesta feature. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Nenhuma fórmula/`nota_final_lider`/etapa alterada. |
| VI. Performance Assíncrona | ✅ PASS | Sem agregações novas síncronas; query única de ciclo aberto; dashboards usam dados já expostos. |
| Stack obrigatória | ✅ PASS | Django + DTL + HTMX + Tailwind CLI. |

**Tensão docs vs código (não é violação)**: tokens vivem em `docs/design-system.md` **e** `static/src/input.css`/utilitários Tailwind. Mitigação: freeze atualiza doc e CSS na mesma entrega; fonte documental canônica = `docs/design-system.md` ([R2](./research.md)).

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Contratos são UI/HTMX/a11y (sem API REST). `data-model.md` declara zero mudança de modelo. Nenhum item OUT justificado como exceção.

## Project Structure

### Documentation (this feature)

```text
specs/004-ux-visual-foundation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0
├── data-model.md        # Phase 1 (sem models novos)
├── quickstart.md        # Phase 1 validação
├── contracts/           # Phase 1 contratos UI
│   ├── admin-nav-grouping.md
│   ├── topbar-cycle-context.md
│   ├── a11y-shell.md
│   └── htmx-pilot-surfaces.md
├── evidence/before-after/  # Screenshots + README (US6)
├── checklists/
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
templates/
├── base.html                    # skip link, #main-content, HTMX a11y hook
├── accounts/login.html          # piloto 04
├── components/
│   ├── nav_menu.html            # US1 grupos Admin + aria-current
│   ├── sidebar.html
│   ├── topbar.html              # US4 contexto ciclo
│   ├── htmx_indicator.html      # US5 rótulo acessível
│   ├── modal.html
│   ├── empty_state.html         # consistência US2/US3
│   ├── button.html / input.html / badge_status.html / card.html
├── dashboard/
│   ├── personal.html            # piloto 03
│   ├── team.html + team_list_partial.html  # piloto 02
├── cycles/ciclo_list*.html      # piloto 05
├── pdi/pdi_detail.html + partials  # piloto 06
└── reviews/avaliacao_list*.html # piloto 07

apps/core/
└── context_processors.py        # NOVO: injeta ciclo aberto (leitura)

static/
├── src/input.css                # tokens + focus-visible
└── js/modal.js                  # focus trap Tab

docs/design-system.md            # expandir + Freeze (fonte da verdade)

config/settings/base.py          # registrar context processor
```

**Structure Decision**: Monólito Django existente. Trabalho concentrado em templates/`components`, CSS tokens, `modal.js` e um context processor em `core`. Sem novos apps, models ou endpoints.

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Django 6.0.7 vs constituição (Django 5.x) | Já no `requirements.txt` e planos 001–003 | Downgrade sem benefício |
| `get_open_ciclo` permanece em `apps.goals.forms` | Evitar refactor amplo fora do escopo visual | Mover para `cycles` agora aumentaria superfície sem ganho UX imediato |
| Docs (`design-system.md`) + CSS (`input.css`) dual | Natureza de design tokens no stack Tailwind | Um só arquivo não serve HTML classes e referência humana |

## Ordem de entrega (P1→P2)

1. Scaffold evidência before (7 telas) — US6  
2. Shell Admin Governança/Cadastros/Sistema + destaque Ciclos/Aderência — US1  
3. Hierarquia dashboards time + pessoal — US2  
4. Documentação incremental de tokens — US6 (parcial)  
5. Consistência login / PDI / avaliações / forms + HTMX — US3  
6. Topbar ciclo via context processor — US4  
7. A11y shell/modal/indicator — US5  
8. After shots + Freeze em `docs/design-system.md` — US6  

Detalhamento de tarefas: `/speckit-tasks` (não este comando).
