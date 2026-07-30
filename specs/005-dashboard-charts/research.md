# Research: Visualizações Gráficas nos Dashboards

**Branch**: `005-dashboard-charts` | **Date**: 2026-07-30

Pesquisa consolidada a partir de [spec.md](./spec.md), constituição, Freeze em [`docs/design-system.md`](../../docs/design-system.md), código atual de `apps/dashboard` e templates. Todos os itens do Technical Context foram resolvidos (sem `NEEDS CLARIFICATION` remanescente).

---

## R1 — Biblioteca de gráfico (Chart.js vs ApexCharts vs nativo)

- **Decision**: Adotar **Chart.js 4.x** (UMD via jsDelivr), carregado **somente** nas páginas/templates de dashboard que renderizam gráfico (`admin`, depois `team`, depois `personal`). Documentar versão + superfícies (FR-013 / SC-007).
- **Rationale**: Suficiente para barras, doughnut/pie e legendas textuais; API simples; bundle menor e menos opinionado que ApexCharts; encaixa em monólito DTL sem SPA. Constitution I exige justificativa: HTML/CSS puro não cobre séries + tooltips + rótulos acessíveis com o mesmo esforço; reinventar canvas/SVG aumentaria complexidade acima da lib.
- **Alternatives considered**:
  - **ApexCharts** — rejeitado: mais pesado, estilos default competem com Freeze emerald/amber/rose, features (zoom, brush) fora do escopo.
  - **Barras HTML/CSS / SVG manual** — rejeitado como solução principal: frágil para multi-série, legendas e responsivo; pode complementar empty/legend tables.
  - **Plotly / ECharts** — rejeitado: overkill e footprint grande.
  - **Sem lib (só cards)** — rejeitado: não atende FR-001 / SC-002.

---

## R2 — Como passar dados (contexto Django vs endpoint HTMX)

- **Decision**: **Preferir contexto da página** + filtro Django `json_script` (ou `<script type="application/json">` em include) com payload tipado por painel. JS de init (`static/js/dashboard_charts.js`) lê o JSON e chama `new Chart(...)`. **Sem** API REST pública / DRF. **Sem** endpoint HTMX só para “buscar série do gráfico” no MVP.
- **Rationale**: Spec Assumptions + FR-008; views já montam resumos; evita superfície de autorização nova; gráficos do admin/pessoal são full-page (não dependem do partial da lista).
- **Alternatives considered**:
  - Endpoint HTMX mínimo interno retornando JSON — reservado só se no futuro um partial precisar re-renderizar o chart sem reload; **não** no caminho crítico.
  - Inline `var data = {...}` no template — funciona, mas `json_script` é mais seguro (escaping).
  - DRF / fetch SPA — rejeitado (OUT + constituição).

**Regra time (slice 2)**: agregação do chart MUST usar o queryset completo de `get_visible_users` (mesmo filtro da view), **não** `object_list` da página HTMX atual — senão o gráfico mentiria ao paginar.

---

## R3 — Mapeamento exato das fontes de dados atuais

### Admin (MVP / US1)

| Visualização | Fonte existente | Formatação para chart (não é fórmula nova) |
|---|---|---|
| Distribuição de aderência | `AderenciaSnapshot` do ciclo (`ciclo_aberto` ou `ciclo_indicador`); faixas via `aderencia_status()` em `apps/dashboard/views.py` (`≥80` alta, `≥50` media, else baixa) | Contar snapshots por `alta` / `media` / `baixa`; labels + cores triad |
| Progresso do ciclo | `Avaliacao` no `ciclo_indicador`; etapas = `Avaliacao.Etapa`; cards já usam `_avaliacoes_resumo` (`concluidas` / `total`) | **Preferência**: `Count` por `etapa` (barras/funil simples). Alternativa aceitável: concluídas vs não (reuso direto de `_avaliacoes_resumo`) |
| Tabela menor aderência | `snapshots_destaque` (já no context) | **Preservar** — sem mudança de dados |
| Média / cards | `aderencia_resumo`, `ciclos_resumo`, `avaliacoes_resumo` | Permanecem; charts complementam |

Empty admin: zero snapshots → empty da distribuição (não inventar faixas); zero avaliações / sem ciclo → empty do progresso.

### Time (US2)

| Visualização | Fonte existente | Formatação |
|---|---|---|
| Status do escopo | `TeamDashboardView.get_queryset()` = `get_visible_users` excl. self, ativos; `Avaliacao` do `ciclo_aberto` por membro (já monta `membros_resumo` na página) | Contagem por `avaliacao.etapa` (e bucket “sem avaliação”) sobre **todo** o escopo |

**Correlato estrutura**: `StructureDashboardView` expõe `leaders_with_adherence` + lacunas área/cargo — **não** a mesma métrica de etapa/status do time. **Fora do slice 2** (FR/assumptions: correlatos só se mesma métrica).

### Pessoal (US3)

| Visualização | Fonte existente | Formatação |
|---|---|---|
| Gap competência | `build_fr005_context` → `competencias_resumo[]` com `nivel_esperado`, `nota_atual` | Barras comparativas (duas séries ou grouped bar); gap visual = diferença dos valores **já** expostos (não altera cálculo de nota) |
| 9-box | `get_visible_classification_for_collaborator` | **Intacto** — feature não altera `visivel_ao_colaborador` nem UI da matriz |

Empty pessoal: sem competências / todas `nota_atual` nulas / vínculo pendente → empty honesto na área do gráfico.

---

## R4 — Acessibilidade (rótulos além da cor)

- **Decision**: Toda série/faixa MUST ter (1) label textual na legenda Chart.js, (2) valores numéricos visíveis (datalabels nativos via tooltip + tabela-resumo ou `aria`/`figcaption` com os totais), (3) cores da **Status Triad** do Freeze: alta/emerald, média/amber, baixa/rose (hex alinhados a `docs/design-system.md`). Informação **não** depende só da cor (FR-007).
- **Rationale**: Spec edge case daltonismo; a11y “suficiente” (não auditoria WCAG formal).
- **Alternatives considered**:
  - Só cor + tooltip — rejeitado (FR-007).
  - Lib a11y npm — rejeitado (fora do escopo; 004 também evitou).

Padrão de empty: reutilizar `templates/components/empty_state.html` com mensagem em português; loading: não confundir com zero — charts só inicializam quando o JSON indica `has_data: true`.

---

## R5 — Vendor local vs CDN

- **Decision**: **CDN jsDelivr** com versão pinada **`chart.js@4.5.1`** (`https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js`), no `{% block extra_js %}` das páginas-alvo — **não** em `base.html`. Init em arquivo local `static/js/dashboard_charts.js`. Ver [contracts/chart-script-loading.md](./contracts/chart-script-loading.md).
- **Rationale**: Mesmo padrão de vendor JS do projeto (HTMX 2.0.4 via jsDelivr em `base.html`). Escopo de carga mínimo (FR-013).
- **Alternatives considered**:
  - Copiar UMD para `static/vendor/chart.umd.min.js` — alternativa válida se política de offline/CSP endurecer; não bloqueia MVP.
  - npm/bundler — rejeitado (projeto usa Tailwind CLI standalone, sem pipeline JS SPA).

Documentação mínima na entrega MVP: parágrafo em `docs/design-system.md` (ou nota no freeze “consumir”) listando lib, versão e templates que incluem o script (SC-007) — **sem** reabrir redesign de chrome.

---

## R6 — Layout vs Freeze 004

- **Decision**: Consumir tokens/componentes congelados; apenas ajustes mínimos de grid/altura do canvas nas seções de dashboard. **Não** alterar `nav_menu`, `topbar`, `sidebar`, marca ou WIP Impeccable.
- **Rationale**: FR-010; Freeze declara gráficos como consumidores.

---

## R7 — HTMX existente

- **Decision**: Partials `team_list_partial.html` / `adherence_list_partial.html` e `#list-container` permanecem; chart vive **fora** da region HTMX (seção irmã no template pai) para não ser destruído em swap de lista.
- **Rationale**: FR-011; ver [contracts/htmx-dashboard-surfaces.md](./contracts/htmx-dashboard-surfaces.md).
