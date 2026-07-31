# Contract: Carregamento da lib de chart + empty/loading

**Feature**: `005-dashboard-charts`  
**Objetivo**: Chart.js só onde há gráfico; empty/loading honestos; documentação FR-013.

## Onde o script MAY carregar

| Template / rota | Slice | Chart.js + `dashboard_charts.js` |
|---|---|---|
| `dashboard/admin.html` (`dashboard:admin`) | 1 MVP | SIM |
| `dashboard/team.html` (`dashboard:team`) | 2 | SIM |
| `dashboard/personal.html` (`dashboard:personal`) | 3 | SIM |
| `base.html` (global) | — | **NÃO** |
| Outras páginas (aderência lista, estrutura, ciclos, etc.) | — | **NÃO** (salvo decisão futura documentada) |

## Versão pinada (T002)

| Campo | Valor |
|---|---|
| Lib | Chart.js |
| Versão | **4.5.1** (linha 4.x estável; npm `latest` em 2026-07-30) |
| Bundle | UMD minificado (`dist/chart.umd.min.js`) |
| CDN | jsDelivr |

**String CDN canônica** (copiar nos `{% block extra_js %}` de admin → team → personal):

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js" defer></script>
```

## Mecânica

1. Página-alvo sobrescreve `{% block extra_js %}`:
   - `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js" defer></script>`
   - `<script src="{% static 'js/dashboard_charts.js' %}" defer></script>`
2. Payload via `{{ chart_*|json_script:"..." }}` no body.
3. Init só se `has_data === true` e o canvas/elemento existir.

## Empty vs loading

| Estado | Comportamento |
|---|---|
| Empty (`has_data: false`) | Mensagem PT-BR (`empty_state` ou bloco equivalente); **sem** Chart com zeros inventados |
| Loading | Não usar gráfico “zerado” como placeholder; listas HTMX mantêm `hx-indicator` próprio |
| Com dados | Canvas + legenda/rótulos textuais (cores triad + texto) |

## Documentação (SC-007)

Na entrega do MVP, registrar em `docs/design-system.md` (nota de consumo, sem reabrir Freeze de marca):

- Nome e versão da lib
- Lista das rotas/templates que a carregam

## Fora

- Bundle npm; carregar Chart.js em todas as páginas; API REST “/api/charts/…”.
