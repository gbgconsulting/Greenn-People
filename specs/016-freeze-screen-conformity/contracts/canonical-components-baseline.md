# Contract: Baseline — componentes canônicos + Chart.js 4.5.1

**Feature**: `016-freeze-screen-conformity`  
**Status**: Baseline congelada (Setup T003) — referência de remediação US1–US4  
**Fonte**: [research.md](../research.md) R5 + [plan.md](../plan.md) + Freeze em `docs/design-system.md`  
**Não reabre**: Freeze A/B/C/D; catálogo 009; densidade 012; denylist de domínio

---

## Escopo

Registrar **quais** includes/arquivos são a fonte canônica desta rodada e **quais** restrições de Chart.js valem antes de qualquer remediação.

**Regra operacional**: remediação de telas A/B = consumir estes paths. HTML/CSS/JS equivalente solto = violação. Faltar token/componente/tipo de chart fora deste baseline **e** fora de B1 → **ESCALATE / STOP**.

**Não** altera implementação nestes arquivos nesta task — só congela a referência.

---

## Componentes canônicos (DTL includes)

| Path | Papel na remediação | Variantes / notas Freeze |
|------|---------------------|--------------------------|
| `templates/components/button.html` | CTAs de header, forms, empty CTA | `primary` \| `secondary` \| `outlined` \| `loading`; `href` ou `<button>`; HTMX via params |
| `templates/components/input.html` | Campos de form B | Label + input ~48px; estados default/error/disabled |
| `templates/components/card.html` | KPI chrome / mini-KPI | Frame fino (`border-line` + `surface-card`); **sem sombra** |
| `templates/components/badge_status.html` | Status / aderência triad | Status Triad emerald/amber/rose + neutro slate; sem chip ad hoc |
| `templates/components/empty_state.html` | Empty honesto (telas + `_chart_block`) | Headline display + mensagem UI; CTA só se caller passar |
| `templates/components/pagination.html` | **Fonte única** US4 | `page_obj` + HTMX `#list-container`; sem segunda implementação |

### Classes CSS canônicas (não são includes, mas baseline Freeze)

| Classe | Onde | Uso nesta feature |
|--------|------|-------------------|
| `.form-control` | `static/src/input.css` | Filtros/selects onde o include `input.html` não cabe |
| `.table-frame` | `static/src/input.css` | Chrome de tabela B (contrato B1) |

---

## Charts — stack pinada

| Item | Valor congelado |
|------|-----------------|
| Lib | Chart.js **somente** |
| Versão | **4.5.1** (UMD minificado) |
| CDN | `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js` |
| Plugin npm | **Proibido** (plugins inline em `dashboard_charts.js` apenas) |
| Lib nova / SPA / DRF | **Proibido** |

### Superfícies que já pinam `@4.5.1` via `extra_js` (auditado 2026-08-21)

- `templates/dashboard/admin.html`
- `templates/dashboard/team.html`
- `templates/dashboard/structure.html`
- `templates/dashboard/adherence.html`
- `templates/dashboard/personal.html`
- `templates/cycles/ciclo_detail.html`

`base.html` **não** carrega Chart.js global. Partials HTMX de drill **não** incluem `_chart_block`.

---

## Pipeline de apresentação (chart)

| Path | Papel | Restrições nesta feature |
|------|-------|--------------------------|
| `apps/dashboard/chart_payloads.py` | Shape presentation (`has_data`, `labels`/`values`/`series`, `legend_items`, empty kinds, Top-N) | Só se auditoria exigir ajuste de **shape**; **sem** mudar significado de counts / AuthZ / fórmulas |
| `templates/dashboard/_chart_block.html` | Bloco reutilizável: title → insight → (mini-KPI \| canvas) → figcaption / `empty_state` | Fora de partials HTMX; sem sombra; empty via `has_data` falso |
| `static/js/dashboard_charts.js` | Init Chart a partir de `json_script` + `data-chart-payload` | Init em `DOMContentLoaded`; **sem** `htmx:afterSwap` no canvas; catálogo 009 types only; mono teal + amber só quando payload/highlight indicar |

Types canônicos (referência 009 + radar gap pessoal): `bar` \| `doughnut` \| `doughnut_or_bar` \| `bar_grouped` \| `bar_horizontal` \| `area` \| `radar`.

Empty kinds canônicos (012 / payloads): `operacional` \| `escopo` \| `sem_dado` \| `sem_nota`.

---

## Política de edição (allowlist)

Estes paths ∈ [path-allowlist.md](./path-allowlist.md) fundação. Podem ser tocados **somente** se auditoria US1–US4 exigir remediação presentation-only.

| Permitido | Proibido |
|-----------|----------|
| Ajuste Freeze-compliant no include fonte | Inventar segundo botão/badge/empty/paginação paralelo |
| Shape presentation em `chart_payloads` | Mudar semântica de negócio / QS |
| Options/plugins inline em `dashboard_charts.js` | Chart ≠ 4.5.1; plugin npm; lib nova |
| Markup `_chart_block` alinhado Freeze D | Barra HTML fake; série fictícia; chart em partial HTMX |

Denylist operacional: [non-goals-denylist.md](./non-goals-denylist.md) — **intocada** por esta baseline.

---

## Confirmação T003 (2026-08-21)

Arquivos existiam e foram inspecionados; Chart.js pinado em `@4.5.1` nas 6 superfícies com chart; sem lib nova.

| Path | Presente | Baseline |
|------|----------|----------|
| `templates/components/button.html` | ✅ | CTAs Freeze |
| `templates/components/input.html` | ✅ | Forms B |
| `templates/components/card.html` | ✅ | KPI / mini-KPI sem sombra |
| `templates/components/badge_status.html` | ✅ | Status Triad |
| `templates/components/empty_state.html` | ✅ | Empty honesto |
| `templates/components/pagination.html` | ✅ | Fonte única US4 |
| `templates/dashboard/_chart_block.html` | ✅ | Bloco chart |
| `static/js/dashboard_charts.js` | ✅ | Init `DOMContentLoaded`; Chart 4.5.1 UMD |
| `apps/dashboard/chart_payloads.py` | ✅ | Shape presentation only |

- [x] Componentes canônicos listados e paths confirmados no repo
- [x] Chart.js **4.5.1** pinado (CDN jsDelivr) nas superfícies A com chart
- [x] Pipeline `_chart_block` + `dashboard_charts.js` + `chart_payloads.py` registrado
- [x] Sem lib nova / sem plugin npm / denylist não editada
- [x] Remediação futura = consumo deste baseline (+ B1 para listas)

**Regra operacional**: divergência de componente ou Chart ≠ 4.5.1 = violação de escopo 016.
