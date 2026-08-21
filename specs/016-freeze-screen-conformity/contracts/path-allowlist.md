# Contract: Path allowlist / denylist

**Feature**: `016-freeze-screen-conformity`  
**Fonte**: [plan.md](../plan.md) + [non-goals-denylist.md](./non-goals-denylist.md) + [spec.md](../spec.md)  
**Uso**: Antes de editar qualquer arquivo, confirmar path na **allowlist**. Diff em path da **denylist** (comportamento / fora de inventário) = falha de aceite.

**Formato**: alinhado a `specs/009-persona-visual-redesign/contracts/path-allowlist.md`.

---

## Escopo inválido (REJEITAR task/PR)

- AuthZ / `get_visible_users` / `ScopedObjectMixin` / relaxar predicados ou ampliar QS
- Máquina de estados, open/close ciclo, approval, fórmulas, aderência %, 9-box
- Models / migrations de domínio
- SPA, DRF, nova lib de gráficos, Chart ≠ 4.5.1
- Shell / nav / login / `base_auth` / Figma Verdee
- Telas fora do inventário A/B (expectativas, metas, PDI, avaliações colaborador, listas de ciclo, audit, notifications, escalas CRUD, objetivos)
- Decisão visual nova além de B1; reabrir Freeze A/B/C/D

---

## Allowlist — fundação / compartilhado

| Path | Notas |
|------|-------|
| `docs/design-system.md` | **Somente** seção Table-frame · listas B (B1); sem reabrir A/B/C/D |
| `static/src/input.css` | Só se B1 exigir utilitário documentado |
| `static/css/tailwind.css` | Rebuild se `input.css` mudar |
| `templates/components/button.html` | Consumo; ajuste só se Freeze exigir e for fonte canônica |
| `templates/components/input.html` | idem |
| `templates/components/card.html` | KPI chrome; sem sombra |
| `templates/components/badge_status.html` | Semântica Freeze; sem chip ad hoc |
| `templates/components/empty_state.html` | Kinds D |
| `templates/components/pagination.html` | **Fonte única** US4 |
| `templates/dashboard/_chart_block.html` | Bloco chart; fora de partials HTMX |
| `static/js/dashboard_charts.js` | Presentation-only se auditoria exigir |
| `apps/dashboard/chart_payloads.py` | Só se shape presentation falhar auditoria — **sem** mudar significado de counts |

---

## Allowlist — Category A (US1 + US2)

| Path | Notas |
|------|-------|
| `templates/dashboard/admin.html` | P1 progresso + painel gerencial |
| `templates/cycles/ciclo_detail.html` | P1 progresso + painel ciclo |
| `templates/dashboard/team.html` | Painel líder |
| `templates/dashboard/team_list_partial.html` | Drill; **sem** `_chart_block` |
| `templates/dashboard/adherence.html` | Status Triad only |
| `templates/dashboard/adherence_list_partial.html` | Sem chart |
| `templates/dashboard/structure.html` | Cobertura ≠ aderência |
| `templates/dashboard/personal.html` | Meu painel; sem tendência nova |
| `templates/dashboard/_ciclo_selector.html` | Chrome se necessário |
| `templates/dashboard/_visao_toggle.html` | Chrome se necessário |
| `templates/talent/matrix.html` | Ninebox polish Freeze only |
| `templates/talent/partials/_cell.html` | idem |
| `templates/talent/partials/_drawer.html` | idem |
| `templates/talent/partials/_person_card.html` | idem |
| `apps/dashboard/views.py` | Context presentation only; mixins AuthZ intactos |
| `apps/cycles/views.py` | `CicloDetailView` presentation only |
| `apps/talent/views.py` | Só se context presentation mínimo; **sem** AuthZ |

`apps/dashboard/urls.py` / `apps/cycles/urls.py` / `apps/talent/urls.py`: **sem** path novo.

---

## Allowlist — Category B (US3)

| Path | Notas |
|------|-------|
| `templates/organization/area_list.html` | Cap B1 `max-w-5xl` |
| `templates/organization/area_list_partial.html` | `table-fixed` + ações |
| `templates/organization/area_form.html` | Manter `max-w-lg` + canônicos |
| `templates/organization/cargo_list.html` | Cap B1 |
| `templates/organization/cargo_list_partial.html` | Separador ações sem `\|` |
| `templates/organization/cargo_form.html` | `max-w-lg` |
| `templates/organization/user_list.html` | Cap B1 `max-w-6xl` (>4 cols) |
| `templates/organization/user_list_partial.html` | Colunas proporcionais |
| `templates/organization/user_form.html` | `max-w-lg` |
| `templates/organization/user_pending_list.html` | Correlata Usuários (CTA) |
| `templates/organization/user_pending_list_partial.html` | B1 |
| `templates/competencies/competencia_list.html` | Cap B1 |
| `templates/competencies/competencia_list_partial.html` | B1 |
| `templates/competencies/competencia_form.html` | `max-w-lg` |
| `apps/organization/views.py` | **Proibido** mudar QS/AuthZ; só se template context presentation |
| `apps/competencies/views.py` | idem |

Confirm delete B: permitido polish chrome (`area_confirm_delete`, `cargo_confirm_delete`, `competencia_confirm_delete`) se tocados no mesmo fluxo visual — sem lógica.

---

## Allowlist — testes / artefatos

| Path | Notas |
|------|-------|
| `tests/test_stage_machine.py` | Regressão — **não** alterar regras |
| `tests/test_scope.py` | Regressão |
| `tests/test_reject_stage_invariant.py` | Regressão |
| `tests/test_*dashboard*` / `test_ciclo_detail*` / novos presentation | Asserts de markup/payload presentation |
| `specs/016-freeze-screen-conformity/**` | Artefatos da feature |

---

## Denylist de paths (espelha non-goals)

Ver [non-goals-denylist.md](./non-goals-denylist.md).

### Zona cinza

| Path | Regra |
|------|-------|
| `apps/*/urls.py` | Sem rota nova |
| `templates/competencies/escala_*.html` | **FORA** — não inseparável |
| `templates/competencies/cargo_competencia_form.html` | **FORA** desta rodada |
| `templates/cycles/ciclo_list*.html` | **FORA** (lista ciclo = rodada futura) |
| `templates/accounts/**` / `base_auth` | FORA |
| `templates/components/nav_menu.html` / shell | FORA |

---

## Inventário A/B fechado → paths (T001)

Cruzamento com [spec.md](../spec.md) (inventários US2/US3 + mapa persona). **Fechado 2026-08-21** — não expandir sem nova decisão de produto.

| Superfície (spec) | Paths allowlist | Cap / notas |
|-------------------|-----------------|-------------|
| Painel admin | `templates/dashboard/admin.html` (+ chrome `_ciclo_selector` / `_visao_toggle` se necessário) | Category A full-bleed |
| Painel do time | `team.html`, `team_list_partial.html` | Sem `_chart_block` no partial |
| Aderência | `adherence.html`, `adherence_list_partial.html` | Status Triad only |
| Estrutura | `structure.html` | Cobertura ≠ aderência |
| Matriz de talentos | `talent/matrix.html` + partials `_cell` / `_drawer` / `_person_card` | Polish Freeze only |
| Ciclo (detalhe) | `cycles/ciclo_detail.html` | Presentation only |
| Meu painel | `personal.html` | Sem tendência nova |
| Áreas | `area_list.html`, `area_list_partial.html`, `area_form.html` | Lista `max-w-5xl`; form `max-w-lg` |
| Cargos | `cargo_list.html`, `cargo_list_partial.html`, `cargo_form.html` | idem |
| Usuários | `user_list*.html`, `user_form.html`, `user_pending_list*.html` | Lista `max-w-6xl` (>4 cols) |
| Competências | `competencia_list*.html`, `competencia_form.html` | Escalas / `cargo_competencia_form` = **FORA** |

**Explicitamente fora (existem no repo; não allowlist)**: `ciclo_list*`, `ciclo_form`, `objetivo_*`, `escala_*`, `cargo_competencia_form`, `reassign_reports.html`, `talent/classify.html`, `talent/my_classification.html`, `accounts/**`, shell/nav/login.

Fundação compartilhada (componentes, `_chart_block`, `chart_payloads`, `dashboard_charts.js`, DS B1, `pagination.html`) permanece na allowlist de fundação acima — só apresentação.

---

## Confirmação T001 (2026-08-21)

- [x] Allowlist = só apresentação (templates/CSS/JS/context); sem paths de AuthZ/stage/approval/models
- [x] Inventário A (7) e B (4 entidades + pendentes) mapeados 1:1 acima
- [x] Denylist cruzada em [non-goals-denylist.md](./non-goals-denylist.md) — domínio / Verdee / fora-inventário intocáveis
- [x] Escopo inválido no topo deste arquivo espelha FR-002 / FR-014

Baseline de consumo dos paths de fundação (canônicos + Chart.js 4.5.1): [canonical-components-baseline.md](./canonical-components-baseline.md) (T003).

---

## Checklist de revisão de diff

- [ ] Todo path ∈ allowlist da story
- [ ] `scope.py` / `get_visible_users` = diff vazio
- [ ] Sem migrations / models
- [ ] Chart.js permanece 4.5.1
- [ ] DS só ganhou seção B1 (ou diff vazio se já documentado na mesma PR)
- [ ] Nenhuma tela fora do inventário A/B
- [ ] Paginação: no máximo um include fonte alterado
