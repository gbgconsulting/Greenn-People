# Contract: Chart visual polish (005)

**Feature**: `007-design-system-v2` · US3  
**Refs**: FR-005, FR-006, FR-013; specs/005 contracts

## Escopo

Polish visual dos charts já existentes. **Não** muda dados, endpoints, lib ou Status Triad semântica.

## Pode mudar

| Camada | Path | Exemplos |
|---|---|---|
| Chart.js options | `static/js/dashboard_charts.js` | `font.family/size/color/weight`, grid color, `borderRadius`, `maxBarThickness`, cutout, tooltip chrome, legend padding |
| Bloco CSS | `static/src/input.css` (`.dashboard-chart-canvas`) | altura/ritmo responsivo |
| Markup visual | `templates/dashboard/_chart_block.html` | padding, radius, shadow mínima, tipografia do título/figcaption |
| Empty visual | via `empty_state` | acabamento; `has_data` continua false |

## Deve permanecer igual

| Item | Path / regra |
|---|---|
| Shape JSON | `has_data`, `labels`, `values`, `series`, `colors`, `legend_items`, `type` |
| Builders / views | `apps/dashboard/chart_payloads.py`, views de dashboard |
| URLs | `apps/dashboard/urls.py` — zero endpoints novos |
| Lib / versão | Chart.js **4.5.1** CDN; sem lib nova |
| Status Triad + labels textuais | cores de negócio + figcaption / legend callbacks |
| Empty honesto | sem séries inventadas quando `has_data !== true` |
| Superfícies de script | admin / team / personal apenas (não `base.html`) |

## Critérios de aceite visual

1. Before/after perceptível em eixos, legendas, tooltips, espaçamento, grid, radius/thickness, altura.  
2. Empty continua honesto + polish v2.  
3. Rótulos textuais além da cor preservados (a11y mínima).

## Smoke funcional (regressão 005)

Abrir admin (e time se aplicável) com e sem dados; totais/KPIs não inventados; Chart.js não sobe no `base.html`.
