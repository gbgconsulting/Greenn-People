# Contract: Visão gerencial de ciclo (US3)

**Feature**: `009-persona-visual-redesign`  
**URL**: `GET /cycles/<pk>/` · name: `ciclo_detail`  
**AuthZ**: `AdminCyclesMixin` = `LoginRequiredMixin` + `RequiresAdminMixin` (mesmo gate das demais views de ciclo). Não inventar Scoped por usuário em `Ciclo` — isto **é** o “equivalente vigente” do FR-007 (research R5); **sem** mutar `ScopedObjectMixin` / `get_visible_users`.  
**Alinha a**: [spec.md](../spec.md) FR-007 / FR-008 / FR-012 / FR-013 · [plan.md](../plan.md) US3 · [managerial-panel.md](./managerial-panel.md) · [chart-catalog.md](./chart-catalog.md) · allowlist US3 em [path-allowlist.md](./path-allowlist.md)

### Confirmação T003 (2026-08-11)

- [x] Página de detalhe nova `cycles/<pk>/` (`ciclo_detail`), link desde `ciclo_list.html` (+ partial) — **não** accordion/inline (FR-007); template real do monólito = `ciclo_list.html` (não `cycle_list.html` da copy da clarificação)
- [x] Seções: progresso etapa + cobertura área/cargo + aderência + checklist 008 avisório (FR-007/008) no padrão painel gerencial
- [x] AuthZ admin-only vigente; open/close/`cycle.py`/stage/approval intactos; zero models/migrations (FR-012 + data-model)
- [x] Agregações = composição/reuso de payloads (`chart_payloads` / cobertura estrutura) no request; Chart.js 4.5.1 + catálogo US1; allowlist-only

---

## Entrada

- Link a partir de `templates/cycles/ciclo_list.html` (e `ciclo_list_partial.html` se apropriado).
- **Não** accordion/inline na lista como substituto da página.

---

## Contexto mínimo da `CicloDetailView`

| Chave | Fonte |
|-------|-------|
| `object` / `ciclo` | `Ciclo` do `pk` |
| `chart_ciclo_progresso` | Contagem `Avaliacao.etapa` no ciclo → payload catálogo |
| `chart_cobertura_*` / KPIs cobertura | Composição área/cargo (mesmo builder da estrutura, `visible` = todos ativos se admin) |
| `chart_aderencia_distribuicao` | `AderenciaSnapshot` do ciclo → `aderencia_distribution_payload` |
| `rh_pre_open_checklist` | `build_rh_pre_open_checklist()` — **avisório** (008) |
| Empty por seção | `has_data` / listas vazias |

Copy/visibilidade de seções MAY adaptar-se a ciclo rascunho / aberto / encerrado **sem** alterar quem pode abrir/fechar.

---

## Comportamento inalterado

- `CicloOpenView` / `CicloCloseView` e `apps/cycles/services/cycle.py` — sem mudança de política.
- Checklist **não** passa a hard-block abrir ciclo (FR-008).
- Sem migration; sem campo novo em `Ciclo`.

---

## Template

`templates/cycles/ciclo_detail.html` (**novo**) no padrão painel gerencial ([managerial-panel.md](./managerial-panel.md)); carrega Chart.js 4.5.1 + `dashboard_charts.js` em `extra_js` ([chart-catalog.md](./chart-catalog.md)).

---

## Teste de aceite AuthZ

| Quem | Resultado |
|------|-----------|
| Admin | 200 + seções |
| Não-admin autenticado | 403/redirect conforme `RequiresAdminMixin` vigente |
| Anônimo | redirect login |
