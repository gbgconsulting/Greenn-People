# Contract: Catálogo de charts por propósito (US1)

**Feature**: `009-persona-visual-redesign`  
**Lib**: Chart.js **4.5.1** UMD · Init: `static/js/dashboard_charts.js` · Bloco: `templates/dashboard/_chart_block.html`  
**Baseline as-is (pré-T006/T007/T008)**: [chart-baseline.md](./chart-baseline.md)  
**Alinha a**: [spec.md](../spec.md) FR-001 / FR-002 / FR-003 / FR-014 · Freeze A · [plan.md](../plan.md) · research R1/R3 · allowlist fundação/US1 em [path-allowlist.md](./path-allowlist.md)

### Confirmação T003 (2026-08-11)

- [x] Catálogo por propósito = Freeze A / FR-001 (doughnut+valor central; `bar_horizontal`; `area`; multi-série / `bar_grouped` / `radar` quando shape já existir)
- [x] Shape canônico compatível com baseline (FR-002); empty honesto via `has_data` (FR-003); Status Triad inalterada; paleta ampliada só no acabamento
- [x] Chart.js **4.5.1** apenas; sem lib nova; sem plugin npm — valor central doughnut via plugin inline no IIFE (research R1)
- [x] Loading só em `extra_js` das superfícies (nunca `base.html`); US2/US3 consomem o mesmo init — referência allowlist-only

---

## Shape canônico (compatível com 005/007)

```json
{
  "id": "string",
  "type": "bar | doughnut | doughnut_or_bar | bar_grouped | bar_horizontal | area | radar",
  "has_data": true,
  "title": "string",
  "labels": ["..."],
  "values": [1, 2],
  "series": [{"key": "...", "label": "...", "values": [], "color": "#optional"}],
  "colors": ["#optional"],
  "legend_items": [{"label": "...", "value": "...", "color": "#optional"}],
  "empty_message": "string",
  "total": 0
}
```

- `has_data !== true` → não instancia Chart; empty via `empty_state`.
- Status Triad de negócio: `#059669` / `#d97706` / `#e11d48` — **inalterada** para categorias de status.
- Paleta ampliada / gradientes: **só** acabamento (área fill, tipografia, séries não-semânticas).

---

## Catálogo por propósito

| Propósito | `type` | Superfícies tipicas |
|-----------|--------|---------------------|
| Aderência (distribuição) | `doughnut` (+ valor central = total ou % destaque) | admin, adherence, ciclo detalhe |
| Ranking pendências / atenção | `bar_horizontal` | team, structure (lacunas), ciclo |
| Tendência temporal | `area` | quando série temporal já existir no domínio; senão não inventar |
| Comparativo multi-série (barras) | `bar_grouped` | quando o caller preferir barras agrupadas |
| Comparativo multi-série (radar) | `radar` | personal gaps (esperado × nota) |
| Contagem categórica | `bar` ou `bar_horizontal` | progresso etapas, escopo |

---

## Loading de script

- CDN Chart.js 4.5.1 + `dashboard_charts.js` no `{% block extra_js %}` da página.
- **Nunca** em `templates/base.html`.
- Após US2: também `structure.html` e `adherence.html` (reabertura B).
- Após US3: `ciclo_detail.html`.

---

## Acabamento limpo (default — alinhado ao DS)

Init em `static/js/dashboard_charts.js` (presentation-only; **sem** mudar shape/métricas):

| Tipo | Eixo de valor / grid | Leitura |
|------|----------------------|---------|
| `bar` / `bar_horizontal` | Off | Datalabel inline na barra (+ mini-KPI); **sem** figcaption duplicando label+valor |
| `bar_grouped` (curto) | Off | Datalabel + legenda Chart.js (séries) + figcaption com `parts` se útil |
| `bar_grouped` (muitos pontos) | Off | Tooltip + figcaption (evita saturação de labels) |
| `radar` (gap pessoal) | Escala `r` mínima | Legenda Chart.js (2 séries); **sem** figcaption — detalhe na tabela irmã |
| `area` | Off | Labels de categoria + tooltip (+ legenda se multi-série) |
| `doughnut` | N/A | Valor central + legenda texto+valor (figcaption) |

Categoria: só labels textuais (sem grid). Continua Chart.js **4.5.1** / plugin inline — sem lib nova.

---

## Non-goals deste contrato

- Trocar lib; mudar CDN major; plugin npm de charts; inventar métrica; endpoint REST para séries; tocar denylist (stage/approval/fórmulas/AuthZ/models/migrations).
