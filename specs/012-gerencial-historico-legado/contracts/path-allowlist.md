# Contract: Path allowlist / denylist

**Feature**: `012-gerencial-historico-legado`  
**Fonte**: [plan.md](../plan.md) + [non-goals-denylist.md](./non-goals-denylist.md)  
**Uso**: Antes de editar qualquer arquivo, confirmar path na **allowlist** da story. Diff em path da **denylist** (comportamento de domínio) = falha de aceite.

**Formato**: alinhado a `specs/009-persona-visual-redesign/contracts/path-allowlist.md`.

### Confirmação T001 (2026-08-14)

- [x] Allowlist cobre só apresentação + composição leve (`chart_payloads`, `history.py` recebendo `visible`, views/templates dashboard/ciclo, tokens/Freeze D)
- [x] Denylist de domínio intocável espelhada em [non-goals-denylist.md](./non-goals-denylist.md): `stage.py` / `cycle.py` (open-close) / `adherence.py` (fórmula) / `scope.py` / approval / mutators evaluation / snapshots / stack
- [x] Constantes do plan congeladas nesta feature (calibração de apresentação; não reabre spec):

| Constante | Valor |
|-----------|-------|
| `DENSITY_TOP_N` | **8** |
| `HISTORY_DEFAULT_N` | **8** |
| Label residual | `"Outros"` |
| Query modo | `visao=historico` |
| Query janela | `ciclos=<ids>` (cap = `HISTORY_DEFAULT_N`) |

- [x] **Sem path novo**: `apps/cycles/urls.py` e `apps/dashboard/urls.py` fora de alteração de rota; MUST NOT `/historico/`
- [x] Alinhado a `plan.md`, `tasks.md` (“Escopo inválido”), FR-018 / FR-019, `density-history-empty.md` e `non-goals-denylist.md`

---

## Escopo inválido (REJEITAR task/PR)

- `stage.py` / `cycle.py` (open/close) / `approval.py` / mutators `evaluation.py` / `adherence.py` (fórmulas) / `scope.py`
- Snapshots write-once; migrations de nota; 6.5.5; PDI
- SPA, DRF, nova lib de gráficos, plugin npm, Chart ≠ 4.5.1
- Rota nova de histórico; tendência em `dashboard/personal`
- Relaxar AuthZ; reabrir shell/nav/login; reabrir Freeze A/B/C além da incrementação D documentada

---

## Allowlist compartilhada (fundação US1 — densidade, empty, Freeze D)

| Path | Notas |
|------|-------|
| `apps/dashboard/chart_payloads.py` | `top_n_with_others`; constantes `DENSITY_TOP_N` / `HISTORY_DEFAULT_N`; shape 009 intacto |
| `apps/dashboard/services/history.py` | **Novo** builder de tendência etapa/conclusão; **recebe** `visible` + ciclos; leitura `Avaliacao` |
| `apps/dashboard/services/structure.py` | Só aplicar densidade nos payloads de cobertura; receber `visible`; **não** mudar `get_visible_users` |
| `static/js/dashboard_charts.js` | Leveza (grid off já existente); **sem** plugin npm; **sem** `htmx:afterSwap` nesta fatia |
| `templates/dashboard/_chart_block.html` | Empty/insight; charts **fora** de partials HTMX |
| `templates/components/empty_state.html` | Copy dos kinds operacional / sem_nota |
| `templates/components/card.html` | KPIs (1–3); sem misturar arquivo |
| `docs/design-system.md` | Freeze D: densidade + histórico + empty + leveza (FR-019) |
| `static/src/input.css` | Só se toggle/seletor exigir classe; rebuild `static/css/tailwind.css` na mesma entrega |

---

## Allowlist por story

### US1 P1 — Marina / admin operacional + densidade 100%

| Path | Notas |
|------|-------|
| `apps/dashboard/views.py` | `AdminDashboardView`: remover fallback `ciclo_indicador`; KPIs só ciclo aberto; seletor agrupado; empty operacional |
| `templates/dashboard/admin.html` | Pipeline = visual principal; KPIs sem % encerrados do arquivo; toggle histórico (markup; comportamento US3) |
| `apps/cycles/views.py` | `CicloListView` / `CicloDetailView` **só** contexto de apresentação (destaque aberto, densidade cobertura, empty sem_nota) |
| `templates/cycles/ciclo_list.html` | Aberto vs arquivo; paginação intacta |
| `templates/cycles/ciclo_list_partial.html` | Sem `_chart_block` |
| `templates/cycles/ciclo_detail.html` | Pipeline principal; empty desempenho; opt-in histórico (US3) |
| `templates/dashboard/personal.html` | Densidade + empty + estética; **sem** `visao=historico` |
| `apps/dashboard/views.py` (`PersonalDashboardView`) | Top-N competências; empty gap; sem tendência |

`apps/cycles/urls.py` e `apps/dashboard/urls.py`: **sem** path novo.

### US2 P1 — Bruno / time + estrutura + aderência

| Path | Notas |
|------|-------|
| `apps/dashboard/views.py` | `TeamDashboardView`: empty operacional; seletor explícito; pipeline principal; ranking Top-N |
| `templates/dashboard/team.html` | Painel gerencial; toggle histórico (US3) |
| `templates/dashboard/team_list_partial.html` | Drill HTMX; **sem** chart |
| `templates/dashboard/structure.html` | Empty operacional; seletor agrupado; cobertura Top-N; cobertura ≠ aderência |
| `templates/dashboard/adherence.html` | Empty operacional; doughnut só com snapshot; seletor agrupado |
| `templates/dashboard/adherence_list_partial.html` | Sem chart |

AuthZ das views **inalterada** (mixins vigentes).

### US3 P2 — Tendência etapa/conclusão

| Path | Notas |
|------|-------|
| `apps/dashboard/services/history.py` | Série `area`; N=8; `null` em lacunas; empty aderência/gap |
| `apps/dashboard/views.py` | Admin/Team: `visao=historico` + cap `ciclos=` |
| `apps/cycles/views.py` | `CicloDetailView`: mesmo modo na página existente |
| Templates admin / team / `ciclo_detail` | Toggle; chart `area`; empty `sem_nota` nas séries de desempenho |

MUST NOT: `templates/dashboard/personal.html` tendência; MUST NOT nova URL.

---

## Testes (allowlist)

| Path | Notas |
|------|-------|
| `tests/test_chart_payloads.py` | Estender Top-N + Outros + `null` |
| `tests/test_structure_coverage.py` | Densidade cobertura |
| `tests/test_ciclo_detail.py` | Empty sem_nota; modo histórico; AuthZ intacta |
| `tests/test_dashboard_operational_default.py` | **Novo** — sem fallback silencioso; empty operacional; KPIs |
| `tests/test_dashboard_history_mode.py` | **Novo** — cap N; escopo; empty gap |
| `tests/test_stage_machine.py` | Regressão — **não** alterar regras |
| `tests/test_scope.py` | Regressão |
| `tests/test_reject_stage_invariant.py` | Regressão |

Fixtures: `tests/conftest.py` / factories locais. MUST NOT ler `data/legado-solides/raw/`.

---

## Denylist de paths (espelha non-goals)

Ver [non-goals-denylist.md](./non-goals-denylist.md). Qualquer mudança de comportamento nesses arquivos = fora de escopo.
