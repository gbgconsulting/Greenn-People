# Research: Design System v2 — Polish Visual

**Branch**: `007-design-system-v2` | **Date**: 2026-08-06

Pesquisa consolidada a partir de [spec.md](./spec.md), constituição, Freeze 004 (`docs/design-system.md`), inventário de auth (`base_auth` / `base.html` / `input.css`), charts 005 e ninebox 006. Todos os itens do Technical Context foram resolvidos (sem `NEEDS CLARIFICATION` remanescente).

**Natureza fixa**: apenas polish visual + Freeze v2. Qualquer decisão que exija produto novo fica **OUT**, não vira plano de implementação.

---

## R1 — Tipografia v2 (display + UI) self-hosted

- **Decision**: Introduzir **duas famílias** no app autenticado:
  - **Display**: **Fraunces** (optical sizing, serif expressiva, SIL OFL) — títulos de página, valores KPI grandes, headlines de empty.
  - **UI**: **Source Sans 3** (legível, neutra, SIL OFL) — corpo, labels, botões, nav, tabelas, axes/tooltips de chart quando aplicados via options.
  - Manter **Inter** como default global de `body` / `--font-sans` (legado compartilhado com auth).
- **Rationale**: Spec exige hierarquia perceptível vs Inter plano (US1/SC-005); self-host alinhado ao padrão já usado (`static/fonts/InterVariable.woff2`); pares OFL evitam licença comercial; Fraunces + Source Sans 3 foge dos clichês AI (Inter único / serif terracotta genérico) e combina com a marca emerald/teal sem redesign de paleta.
- **Alternatives considered**:
  - Trocar `--font-sans` global para a UI v2 — **rejeitado** (vaza para login; FR-002).
  - Manter Inter + só pesos/escala — rejeitado (SC-005 pede hierarquia tipográfica citada; Inter único já é o baseline 004).
  - Plus Jakarta Sans / Manrope como UI — aceitáveis; Source Sans 3 preferido por leitura densa em tabelas/forms e familiaridade admin.
  - DM Serif Display / Newsreader como display — viáveis; Fraunces escolhida por variável óptica e personalidade sem parecer “marketing brochure”.
  - Google Fonts CDN em runtime — rejeitado (política local já em vigor no Freeze).

**Implementação (não nesta fase, só direção)**: WOFF2 em `static/fonts/`; `@font-face` + tokens `--font-display` / `--font-ui` em `input.css`; utilitários Tailwind `font-display` / `font-ui`; aplicação sob escopo autenticado (R2).

---

## R2 — Isolamento tipográfico: login / `base_auth` NÃO herdam

### Inventário (estado atual)

| Superfície | Template | CSS linkado | Tipografia efetiva |
|---|---|---|---|
| Auth | `templates/accounts/base_auth.html` (+ `login.html`, reset, etc.) | Só `static/css/tailwind.css` | Inter via `@layer base { body { font-sans } }` + `--font-sans` |
| Autenticado | `templates/base.html` | Mesmo `tailwind.css` + HTMX/modal | Mesmo Inter global; shell via includes |

Conclusão factual: **árvores de template já separadas**; **CSS tipográfico não**. Qualquer mudança de `--font-sans` ou `body { font-sans }` em `input.css` vaza para login.

### Decision

1. **NÃO alterar** `--font-sans: Inter…` nem o `@apply font-sans` do `body` global.
2. Em `templates/base.html`, marcar o shell autenticado com classe dedicada no `<body>` (ex.: `app-shell`).
3. Em `input.css`, declarar `@font-face` das famílias v2 + tokens `@theme` (`--font-display`, `--font-ui`) **sem** sobrescrever o default do `body`.
4. Aplicar tipografia v2 sob `.app-shell` (ex.: `.app-shell { font-family: var(--font-ui), … }`) e utilitários `font-display` em títulos/KPI nos templates piloto / components usados só no path autenticado.
5. **PROIBIDO** editar `templates/accounts/base_auth.html`, `templates/accounts/login.html` ou qualquer override tipográfico no path auth.
6. Aceite FR-002/SC-002: diff vazio nesses arquivos + comparação visual login before = after.

- **Rationale**: Reusa isolamento estrutural já existente; zero mudança de markup auth; isolamento comprovável por seletor/classe e checklist OUT.
- **Alternatives considered**:
  - Segunda folha CSS só em `base.html` — possível, mas duplica tokens; preferir tokens no mesmo `input.css` com escopo `.app-shell`.
  - Carregar fontes só no `extra_head` de `base.html` sem escopo CSS — **insuficiente**: se o `body` global mudar, auth ainda herda; e `@font-face` no CSS compartilhado é OK desde que **não** reatribua o default do `body`.
  - Copiar login para CSS próprio — rejeitado (produto/out of scope; FR-002 diz intocado, não “migrado”).

---

## R3 — Tokens v2 e dualidade doc ↔ CSS

- **Decision**: Manter dualidade Freeze: `docs/design-system.md` (canônica) ↔ `static/src/input.css`. Na mesma entrega: status **Freeze v2**; tipografia display/UI; refinamentos de button/KPI/table-frame/empty; seção charts polish; seção ninebox polish. Tokens de cor Status Triad e paleta emerald **permanecem** salvo ajuste mínimo de tipografia/espaço.
- **Rationale**: FR-009; padrão já legitimado em 004 (research R2); constituição I (sem DESIGN.md paralelo).
- **Alternatives considered**: Criar `DESIGN.md` — rejeitado. Reabrir paleta completa — rejeitado (fora; polish ≠ rebrand).

---

## R4 — Components e superfícies piloto (allowlist de código)

- **Decision**: Superfície de código **permitida**:

| Área | Paths |
|---|---|
| Freeze | `docs/design-system.md` |
| Tokens / fontes | `static/src/input.css`, `static/fonts/*` (novos WOFF2), rebuild `static/css/tailwind.css` |
| Components | `templates/components/button.html`, `badge_status.html`, `empty_state.html`, `card.html` (KPI), includes de table-frame se classes viverem no CSS; shell `sidebar.html` / `topbar.html` **só densidade/tipografia após P1–P4** |
| Shell autenticado | `templates/base.html` (classe `app-shell` + eventual head de tipografia) |
| Pilotos | `dashboard/admin.html`, `team.html`, `personal.html`, `_chart_block.html`; `talent/matrix.html` + `_cell.html`, `_person_card.html`, `_drawer.html`; `cycles/ciclo_list*.html`; `reviews/avaliacao_list*.html`; `pdi/pdi_detail.html`, `pdi_form.html` |
| Charts JS | `static/js/dashboard_charts.js` — **somente** options visuais |
| Ninebox JS | `static/js/ninebox_matrix.js` — **somente** classes/ARIA/feedback visual |

- **PROIBIDO**: `apps/*/services`, AuthZ, queries, models/migrations, rotas/views novas, deps front novas, `templates/accounts/login.html`, `base_auth.html`, redesign de grupos Governança/Cadastros/Sistema.

- **Referência de implementação (T004)**: [contracts/path-allowlist.md](./contracts/path-allowlist.md) — gate único allowlist/denylist para edições nesta feature.

- **Rationale**: FR-011–013; US1–US5; delimitação explícita evita “aproveitar” para produto.
- **Alternatives considered**: Expandir para todas as telas do monólito — rejeitado (piloto 5–8 + Freeze; resto consome tokens por herança do shell).

---

## R5 — Charts: polish só via Chart.js options + CSS do bloco

- **Decision**: Polish limitado a:

  | Permitido | Como |
  |---|---|
  | Fontes eixos/legendas/tooltips | `font.family` / size / color / weight nas options (apontar `--font-ui` / stacks) |
  | Grid lines sutis | `scales.*.grid.color`, `drawBorder` |
  | Radius / thickness barras | `borderRadius`, `borderWidth`, `maxBarThickness` |
  | Doughnut cutout / padding | options + layout |
  | Tooltip chrome | `backgroundColor`, `cornerRadius`, `padding`, `titleFont` |
  | Altura / ritmo do bloco | `.dashboard-chart-canvas` em `input.css`; classes do `<figure>` / `figcaption` em `_chart_block.html` |
  | Empty | classes no `empty_state` include — dados continuam `has_data === false` |

  **Inalterado**: shape JSON (`has_data`, `labels`, `values`, `series`, `colors`, `legend_items`, `type`); Status Triad hex de negócio; `chart_payloads.py` / views / urls; CDN Chart.js 4.5.1; rótulos textuais + figcaption.

- **Rationale**: FR-005/006/013; inventário mostra que fonts/grid/radius já são parâmetros options; altura já é CSS.
- **Alternatives considered**: Nova lib de chart / datalabels plugin npm — rejeitado (FR-012). Mudar payloads para “mais bonitos” — rejeitado (produto/dados).

---

## R6 — Ninebox: visual-only vs contratos 006

### Allowlist (visual only)

- Classes Tailwind em grade / person cards / aside drawer / empty
- Feedback drag (`opacity`, `ring-*`, `cursor-grab`) — refinar cores/espessura/timing visual sem mudar handlers
- Tipografia/densidade dos cards e headers de célula
- ARIA de suporte visual (rótulos, `sr-only`) sem remover comportamento a11y existente
- Shell do drawer de domínio `talent` (não modal global)

### Denylist (não mexer)

| Contrato 006 | Itens intocáveis |
|---|---|
| `drag-persist.md` | POST só `potencial`; ignore desempenho na gravação; snap; Esc/fora = zero POST; sem SortableJS |
| `authz-scope.md` | Admin write; gerente read-only; líder 403; `get_visible_users`; IDOR 403 |
| `htmx-drawer-partials.md` | Targets `#matrix-drawer`, URLs move/drawer/toggle, shape HTMX, filtros ciclo/área/cargo |
| `a11y-matrix-drawer.md` | Trap/Escape/restore; alternativa drawer ao drag; loading ≠ empty |

- **Rationale**: FR-007/013/015; US4.
- **Alternatives considered**: Promover drawer canônico global — ver R7. Alterar copy de regra de calibração — rejeitado (negócio).

---

## R7 — Drawer canônico global

- **Decision**: **Default = não**. Drawer da matriz permanece domínio `talent` com polish visual. Não criar `templates/components/drawer.html` nesta feature.
- **Rationale**: Spec Assumptions; Freeze 004 já documenta drawer in-matrix como domínio; promover canônico = produto/infra UI além de polish.
- **Alternatives considered**: Extrair drawer compartilhado agora — rejeitado (escopo; risco de regressão HTMX).

---

## R8 — Verdee / Impeccable (FR-014)

- **Decision**: **Ignorar como baseline**. Cherry-pick peça a peça **opcional** e só se um item isolado (ex. densidades de botão já parcialmente alinhadas) melhorar o polish sem portar marketing Verdee nem reaplicar stash Impeccable.
- **Rationale**: FR-014 + Out of Scope; Freeze 004 já rejeitou Impeccable e limitou Verdee a referência.
- **Alternatives considered**: Portar guia Verdee — rejeitado. Reaplicar WIP Impeccable — rejeitado.

---

## R9 — Shell sidebar/topbar

- **Decision**: Após P1–P4, se couber, apenas densidade/tipografia sob `.app-shell` **sem** redesign de IA nav (grupos Governança/Cadastros/Sistema intactos — FR-008). Não bloqueia MVP se adiado depois de US1–US4 na mesma feature; chrome ainda pode entrar na evidência before/after como referência.
- **Rationale**: Spec Assumptions + FR-008.
- **Alternatives considered**: Reorganizar nav — rejeitado (OUT).

---

## R10 — Evidência before/after + checklist OUT

- **Decision**: Scaffold em `specs/007-design-system-v2/evidence/before-after/` (padrão 004: `NN-<slug>-before.png` / `after.png`). **5–8 pilotos autenticados**, **sem login** na evidência de melhoria. Checklist OUT formalizado em [contracts/out-checklist.md](./contracts/out-checklist.md).
- **Rationale**: FR-010/015; SC-001–003/006.
- **Pilotos sugeridos**:

| # | Slug | Superfície |
|---|---|---|
| 01 | dashboard-admin-charts | Admin + charts |
| 02 | dashboard-team | Time |
| 03 | dashboard-pessoal | Pessoal / gaps |
| 04 | talent-matrix | Matriz 9-box |
| 05 | lista-ciclos | Lista ciclos |
| 06 | pdi-ou-form | PDI detail ou form comum |
| 07 | avaliacoes-list | Lista avaliações (opcional) |
| 08 | shell-chrome | Sidebar/topbar (opcional se P9) |

Verificação auxiliar: screenshot de login **inalterado** (prova SC-002), fora do set de “melhoria perceptível”.

---

## R11 — Complexity / reuso (não são libs novas)

| Item | Classificação |
|---|---|
| Chart.js 4.5.1 (já no projeto) | Reuso — polish de options apenas |
| `dashboard_charts.js` / `ninebox_matrix.js` | JS local existente |
| Fraunces + Source Sans 3 (WOFF2) | **Assets tipográficos** self-hosted, não framework UI |
| HTMX / Tailwind CLI / DTL | Stack obrigatória inalterada |

Nenhuma dependência npm/CDN nova autorizada.

---

## OUT explícito (não planejar)

- Login / `base_auth` / copy narrativo auth
- Novas rotas, views, models, migrations, permissões, métricas, campos, flags, Celery, serializers
- Alpine / React / Sortable / DRF / GraphQL / nova chart lib
- Redesign IA nav; dark mode; WCAG formal completa
- Impeccable como base; marketing Verdee completo
- Drawer canônico global (salvo decisão futura fora desta feature)
- Mudanças em AuthZ, fórmulas 9-box, payloads/endpoints 005/006
