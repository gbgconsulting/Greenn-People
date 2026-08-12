# Contract: Padrão canônico “painel gerencial” (Freeze C)

**Feature**: `009-persona-visual-redesign`  
**Docs canônicos**: `docs/design-system.md` (atualizar na mesma entrega) · tokens: `static/src/input.css`  
**Alinha a**: [spec.md](../spec.md) FR-004 / FR-005 / FR-006 / FR-011 · Freeze B/C · [plan.md](../plan.md) · research R4/R7 · catálogo [chart-catalog.md](./chart-catalog.md) · allowlist US2 (+ tokens/DS) em [path-allowlist.md](./path-allowlist.md)

### Confirmação T003 (2026-08-11)

- [x] Composição KPI + visual + tabela/drill + ações = Freeze C / FR-004; tabela não é visão principal
- [x] Destaque/ranking acionável + links a ações já existentes = FR-005 (sem inventar fluxo AuthZ)
- [x] Estrutura: **cobertura** área/cargo = visual principal; lacunas/pendências = secundário acionável — FR-006 / Freeze B (sem misturar com aderência)
- [x] Docs A/B/C + tokens `input.css` na mesma entrega = FR-011 / SC-006; implementação allowlist-only (sem shell/auth/denylist)

---

## Composição

Ordem visual (desktop e empilhamento mobile ~375px: KPI → visual → tabela):

1. **KPI(s)** — `templates/components/card.html` (1–3 cards)
2. **Visualização** — `templates/dashboard/_chart_block.html` (catálogo US1)
3. **Drill-down** — tabela `.table-frame` / lista HTMX / ranking acionável
4. **Ações** — links para superfícies já existentes (avaliações, lacunas, pending users, etc.)

Tabela **não** é a visão principal; se remover o gráfico/KPIs, a pergunta “onde estamos?” deve ficar mais difícil — não o contrário.

---

## Aplicação por superfície

| Superfície | KPI | Visual principal | Secundário / drill |
|------------|-----|------------------|--------------------|
| Time | contagens etapa / pendências | chart status (US1; preferir `bar_horizontal` para atenção) | ranking/destaque acionável + `team_list_partial` |
| Estrutura | cobertura % ou totais área/cargo | chart **cobertura** (métrica principal) | lacunas/pendências **secundárias** + líderes |
| Aderência | média / distribuição | doughnut (+ valor central) | lista snapshots (HTMX partial) |
| Ciclo RH | progresso / blockers count | progresso + cobertura + aderência ([cycle-managerial-detail.md](./cycle-managerial-detail.md)) | checklist 008 + tabelas |

---

## Empty

Cada seção com empty próprio (`empty_state`); sem inventar ranking/cobertura/séries fictícias (FR-003).

---

## Documentação Freeze

Registrado em `docs/design-system.md` (T004 · FR-011 / SC-006):

- [x] Reabertura **A** (charts expressivos + paleta acabamento) — seção **Reabertura formal A/B/C** + **Charts polish**
- [x] Reabertura **B** (`structure.html` no slice; cobertura ≠ aderência)
- [x] Reabertura **C** (este padrão — seção **Painel gerencial**)
- [x] Texto “Fora do slice: structure.html” herdado de 005 removido / substituído pela tabela de superfícies 009
- [x] Tokens `.managerial-panel` (`gap-6` / `sm:gap-8`) + `.dashboard-chart-canvas` em `static/src/input.css` (+ rebuild `static/css/tailwind.css`) — **T005**
