# Contract: Baseline Chart.js + shape (pré-US1)

**Feature**: `009-persona-visual-redesign`  
**Task**: T002  
**Registrado**: 2026-08-11  
**Objetivo**: Congelar o estado **atual** (antes de T006/T007/T008) de Chart.js **4.5.1** e do shape em `dashboard_charts.js` / `_chart_block.html` / `chart_payloads.py`, para regressão de significado (FR-001/002) e comparação quickstart §1.2.

**Regra**: este documento descreve o *as-is*. Ampliações (`bar_horizontal`, `area`, valor central doughnut) entram só nas tasks Foundational — **sem** lib nova e **sem** tocar denylist.

### Confirmação T002 (2026-08-11)

- [x] CDN Chart.js **4.5.1** UMD pinada nas páginas com gráfico (`extra_js`); **não** em `base.html`
- [x] Shape atual documentado abaixo bate com o código nos três paths allowlist
- [x] Types implementados hoje: `bar` | `doughnut` | `doughnut_or_bar` | `bar_grouped` — **sem** `bar_horizontal` / `area` / plugin de valor central ainda
- [x] Status Triad de negócio e campos canônicos (`has_data` / `labels` / `values` / `series` / `colors` / `legend_items`) registrados para não regressão
- [x] Nenhuma alteração em denylist; nenhuma lib nova

---

## 1. Lib / CDN (pin)

| Campo | Valor |
|-------|-------|
| Lib | Chart.js |
| Versão | **4.5.1** |
| Bundle | UMD minificado (`dist/chart.umd.min.js`) |
| CDN | jsDelivr |

**String canônica** (já em uso):

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js" defer></script>
<script src="{% static 'js/dashboard_charts.js' %}" defer></script>
```

| Template | Carrega Chart.js 4.5.1 + `dashboard_charts.js` |
|----------|-----------------------------------------------|
| `templates/dashboard/admin.html` | Sim |
| `templates/dashboard/team.html` | Sim |
| `templates/dashboard/personal.html` | Sim |
| `templates/base.html` | **Não** |
| structure / adherence / ciclo detail | **Não** (alvo US2/US3) |

---

## 2. `static/js/dashboard_charts.js` (as-is)

**Papel**: init Chart a partir de `json_script` via `canvas[data-chart-payload]`; só se `has_data === true`.

| Aspecto | Baseline atual |
|---------|----------------|
| Types resolvidos | `doughnut` / `doughnut_or_bar` → Chart `doughnut`; demais single-series → `bar`; `bar_grouped` → multi-série |
| Horizontal | Só adaptativo em `bar_grouped` no viewport estreito (`indexAxis: 'y'` se `labels.length > 2`) — **não** há `type: 'bar_horizontal'` |
| Area | **Ausente** |
| Valor central doughnut | **Ausente** (só `cutout: '68%'`) |
| Status Triad | `#059669` / `#d97706` / `#e11d48` |
| GROUPED_DEFAULTS | `nivel_esperado: #64748b`, `nota_atual: #059669` |
| Null | Preservado (`skipNull` / `asNullableNumber`) — não inventa 0 |
| Empty | `has_data !== true` → não chama `new Chart` |
| Options DS v2 | Fonte UI, grid sutil, tooltip chrome, `borderRadius` / `maxBarThickness`, legenda com texto+valor em doughnut |

---

## 3. `templates/dashboard/_chart_block.html` (as-is)

**Parâmetros**: `chart`, `script_id?`, `title?`, `extra_class?`.

| Aspecto | Baseline atual |
|---------|----------------|
| Wrapper | `<figure>` com borda/surface-card (`rounded-xl border border-line`) |
| Título | `font-display` se `chart_title` |
| Com dados | `.dashboard-chart-canvas` + `<canvas data-chart-payload>` |
| Legenda textual | `figcaption` + `legend_items` (itens simples ou `parts` agrupados) |
| Sem dados | `components/empty_state.html` com `empty_message` |
| Payload embutido | `{{ chart\|json_script:payload_id }}` sempre que `chart` + `payload_id` |
| Mini-KPI | **Ausente** no bloco (KPI fica na página vizinha via `card`) |

---

## 4. `apps/dashboard/chart_payloads.py` (as-is)

**Papel**: helpers de formatação (sem fórmulas de negócio).

### Shape canônico emitido

```json
{
  "id": "string",
  "type": "bar | doughnut | doughnut_or_bar | bar_grouped",
  "has_data": true,
  "title": "string",
  "labels": ["..."],
  "values": [1, 2],
  "series": [{"key": "...", "label": "...", "values": [], "color": "#optional"}],
  "colors": ["#optional"],
  "keys": ["optional"],
  "legend_items": [{"label": "...", "value": "...", "color": "#optional"} | {"label": "...", "parts": [...]}],
  "empty_message": "string",
  "total": 0
}
```

- `has_data: false` → `labels` / `values` / `series` / `colors` / `keys` / `legend_items` vazios; `total: 0`.
- Types **ainda não** emitidos pelo Python como first-class: `bar_horizontal`, `area`.

### API pública (baseline)

| Função | Uso |
|--------|-----|
| `series_payload` | Série única (`bar` / `doughnut` / `doughnut_or_bar`) + `total` + `legend_items` |
| `empty_series_payload` | Empty honesto |
| `grouped_series_payload` | Multi-série (`bar_grouped`); `None` → JSON null |
| `aderencia_distribution_payload` | Alta/média/baixa + Status Triad (`doughnut_or_bar` default) |
| `categorical_counts_payload` | Mapa chave→contagem ordenado |
| `count_by_ordered_keys` / `colors_for_keys` | Agrupamento / cores auxiliares |

**Constantes Status Triad**: `#059669` / `#d97706` / `#e11d48` (alta / média / baixa).

---

## 5. Non-goals deste baseline

- Implementar tipos novos (→ T006 / T007 / `chart-catalog.md`)
- Alterar markup mini-KPI (→ T008)
- Trocar CDN / major / lib
- Mutar domínio (denylist)

---

## Referências

- Catálogo-alvo (pós-fundação): [chart-catalog.md](./chart-catalog.md)
- Loading histórico (005): `specs/005-dashboard-charts/contracts/chart-script-loading.md`
- Allowlist: [path-allowlist.md](./path-allowlist.md)
