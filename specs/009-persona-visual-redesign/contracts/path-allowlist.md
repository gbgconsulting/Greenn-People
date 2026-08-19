# Contract: Path allowlist / denylist

**Feature**: `009-persona-visual-redesign`  
**Fonte**: [plan.md](../plan.md) + [non-goals-denylist.md](./non-goals-denylist.md)  
**Uso**: Antes de editar qualquer arquivo, confirmar path na **allowlist** da story. Diff em path da **denylist** (comportamento de domínio) = falha de aceite.

**Formato**: alinhado a `specs/008-cycle-guidance-ux/contracts/path-allowlist.md` e à seção “Escopo inválido” de `tasks.md` 008.

### Confirmação T001 (2026-08-11)

- [x] Allowlist cobre só apresentação + composição leve (`chart_payloads`, `structure.py` recebendo `visible`, `CicloDetailView` GET, tokens/DS)
- [x] Denylist de domínio intocável: stage / approval / fórmulas / AuthZ (`scope.py`) / models / migrations / `cycle.py` open-close / stack / shell-auth
- [x] Alinhado a `plan.md`, `tasks.md` (“Escopo inválido”), FR-012 / FR-014 e `non-goals-denylist.md`
- [x] Paths allowlisted existentes no monólito verificados; `ciclo_detail.html` é **novo** (US3) — ok na allowlist

---

## Escopo inválido (REJEITAR task/PR)

- Máquina de estados (`stage.py`, avanço/reabertura semântica)
- Aprovação / reprovação / mid-cycle
- Fórmulas de nota, aderência %, 9-box
- AuthZ / mutação de `get_visible_users` / `ScopedObjectMixin`
- Models / migrations de domínio
- SPA, DRF, nova lib de gráficos
- Shell/nav IA / login / `base_auth` (exceto consumo incidental de tokens)

---

## Allowlist por story

### Fundação compartilhada (antes de US2/US3; parte de US1 + DS)

| Path | Notas |
|------|-------|
| `static/js/dashboard_charts.js` | Catálogo tipos (doughnut center, bar_horizontal, area); paleta acabamento |
| `templates/dashboard/_chart_block.html` | Markup bloco; mini-KPI/legenda se markup |
| `apps/dashboard/chart_payloads.py` | Types/shape; sem mudar significado Status Triad |
| `static/src/input.css` | Tokens / `.dashboard-chart-canvas` / wrapper painel gerencial |
| `static/css/tailwind.css` | Via rebuild CLI |
| `docs/design-system.md` | Reabertura A/B/C + padrão painel gerencial |
| `templates/components/card.html` | KPI do painel (só apresentação) |
| `templates/components/empty_state.html` | Empty honesto |
| `templates/components/button.html` | Só se CTA visual |

### US1 — Charts modernos (P1, fundação)

| Path | Notas |
|------|-------|
| `templates/dashboard/personal.html` | Chart + mini-KPI vizinho |
| `templates/dashboard/team.html` | Chart expressivo (acima da tabela) |
| `templates/dashboard/admin.html` | Doughnut/progresso polish |
| `apps/dashboard/views.py` | Personal/Team/Admin — só context/`type` payload |

### US2 — Painéis líder (P1, após US1)

| Path | Notas |
|------|-------|
| `templates/dashboard/team.html` | Composição painel gerencial |
| `templates/dashboard/team_list_partial.html` | Tabela como drill-down |
| `templates/dashboard/structure.html` | **Entra no slice charts**; cobertura = visual principal |
| `templates/dashboard/adherence.html` | KPI + doughnut + lista |
| `templates/dashboard/adherence_list_partial.html` | Drill-down HTMX |
| `apps/dashboard/views.py` | Structure/Adherence/Team context KPIs/payloads |
| `apps/dashboard/services/structure.py` | Composição cobertura read-only; **receber** `visible`; não alterar `get_visible_users` |

### US3 — Visão gerencial de ciclo (P1, após US1)

| Path | Notas |
|------|-------|
| `apps/cycles/views.py` | **Novo** `CicloDetailView` (GET, `AdminCyclesMixin`) + link context na list se preciso |
| `apps/cycles/urls.py` | **Somente** adicionar `path('<pk>/', …, name='ciclo_detail')` — sem mudar open/close/CRUD |
| `templates/cycles/ciclo_detail.html` | **Novo** painel |
| `templates/cycles/ciclo_list.html` | Link para detalhe |
| `templates/cycles/ciclo_list_partial.html` | Link/ação de abrir detalhe se aplicável |
| `apps/reviews/services/guidance.py` | **Só leitura** — reusar `build_rh_pre_open_checklist` (sem mudar advisory) |
| Builders em `apps/dashboard/chart_payloads.py` / `structure.py` | Reuso para seções do detalhe |

### US4 — Colaborador P2

| Path | Notas |
|------|-------|
| `templates/goals/expectations.html` | Freeze polish + CTA |
| `templates/goals/meta_list.html` | idem |
| `templates/goals/meta_list_partial.html` | idem |
| `templates/goals/partials/meta_row.html` | idem |
| `templates/reviews/avaliacao_list.html` | idem |
| `templates/reviews/avaliacao_list_partial.html` | idem |
| `templates/reviews/avaliacao_detail.html` | Chrome only; **não** reimplementar guidance 008 |
| `templates/pdi/pdi_list.html` | idem |
| `templates/pdi/pdi_list_partial.html` | idem |
| `templates/pdi/pdi_detail.html` | idem |
| `templates/pdi/pdi_form.html` | polish form chrome |
| `templates/talent/my_classification.html` | idem |
| Views goals/reviews/pdi/talent | Context CTA mínimo — **sem** predicados AuthZ novos |

### US5 — Cadastros/Sistema P3 (best-effort)

| Path | Notas |
|------|-------|
| `templates/organization/area_*.html` | Tipografia / table-frame / empty |
| `templates/organization/cargo_*.html` | idem |
| `templates/organization/user_*.html` | idem (incl. pending) |
| `templates/competencies/*.html` | list/form chrome |
| `templates/audit/*.html` | idem |
| `templates/notifications/*.html` | idem |

### Tests

| Path | Notas |
|------|-------|
| `tests/test_*chart*.py` / novos `tests/test_persona_panels*.py` | Payloads, empty, types |
| `tests/test_structure*.py` / cobertura | Escopo: subset de `get_visible_users` |
| `tests/test_ciclo_detail*.py` | AuthZ admin; 404/negado para não-admin |
| Regressão existente | stage/scope/approval/evaluation **PASS** sem asserts de negócio alterados |

### Artefatos da feature

Tudo sob `specs/009-persona-visual-redesign/`.

---

## Denylist (proibido — comportamento / domínio)

| Path / padrão | Motivo |
|---------------|--------|
| `apps/*/models.py` | Schema / regra persistida |
| `**/migrations/**` | Schema |
| `apps/cycles/services/stage.py` | Máquina de estados |
| `apps/cycles/services/cycle.py` | open/close comportamento |
| `apps/goals/services/approval.py` | Aprovação |
| `apps/accounts/services/scope.py` | Alterar AuthZ/escopo |
| `apps/core/mixins.py` (`ScopedObjectMixin` semântica) | AuthZ |
| Mutators / fórmulas em `apps/reviews/services/evaluation.py` | Cálculo |
| `apps/dashboard/services/adherence.py` / `tasks.py` | Recalcular aderência no request ou mudar fórmula (salvo bugfix não relacionado) |
| `templates/accounts/**` / `base_auth` | Auth polish |
| Redesign IA em `nav_menu.html` (grupos/ordem) | OUT |
| Nova lib Chart / SPA / DRF | Stack |

### Zona cinza (permitido só com cuidado)

| Path | Regra |
|------|-------|
| `apps/cycles/urls.py` | **Apenas** rota GET `ciclo_detail`; proibido alterar rotas open/close/edit/delete |
| `apps/dashboard/urls.py` | Preferir **não** mudar; structure/adherence já existem |
| `apps/dashboard/tasks.py` | Nova task só com evidência de peso + Complexity Tracking |
| `templates/components/next_step.html` / `stage_stepper.html` | Consumir; não contradizer mapa 008 |

---

## Checklist de revisão de diff

- [ ] Nenhum arquivo em denylist de comportamento alterado em semântica
- [ ] `get_visible_users` / `scope.py` = diff vazio (ou só imports não relacionados)
- [ ] Sem migrations / models de domínio
- [x] Chart.js permanece 4.5.1; sem lib nova (T043 · 2026-08-12)
- [ ] US2/US3 só após catálogo US1 utilizável
- [ ] `docs/design-system.md` + `input.css` atualizados se padrão/token novo
- [ ] P3 ausente não falha aceite se P1+P2 ok até 03/09
