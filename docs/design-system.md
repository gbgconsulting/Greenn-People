# Design System

Identidade visual moderna, clara e responsiva, aplicada de forma consistente em todas as telas via Tailwind CSS dentro do Django Template Language (template base + componentes reutilizáveis via `{% include %}`).

## Fontes de tokens (dualidade)

| Papel | Arquivo | Uso |
|---|---|---|
| Fonte documental (canônica) | Este arquivo (`docs/design-system.md`) | Tabelas, padrões de componente, seção **Freeze** |
| Tokens CSS / tema Tailwind | `static/src/input.css` (`@theme`, `@layer`) | Variáveis semânticas e base tipográfica em runtime |

Não criar `DESIGN.md` na raiz: a documentação de design deste projeto vive aqui. Alterações de token devem atualizar **doc e CSS na mesma entrega** para evitar divergência.

---

## Freeze

**Status:** **Freeze v2** (feature `007-design-system-v2` · FR-009 / SC-004). Substitui o congelamento de `004-ux-visual-foundation` para as decisões listadas abaixo. Twin técnico: `static/src/input.css` (+ components/templates/JS tocados na mesma entrega).

Este documento é a **fonte da verdade** de tokens e padrões de UI do Greenn People. O v2 **reabriu** tipografia e acabamento visual no app autenticado com decisão explícita da feature 007; login/`base_auth` ficam **fora** (isolamento). Demais superfícies devem **consumir** o conjunto documentado (e os includes em `templates/components/`), sem inventar ilhas de estilo.

### Cobertura Freeze v2

| Área | Contrato |
|---|---|
| Tipografia | Display (**Fraunces**) + UI (**Source Sans 3**) no app autenticado (`.app-shell`); Inter permanece default global / auth (`--font-sans` intocado) — seção **Tipografia** |
| Botões | Ritmo/pesos/hover/focus refinados; mesmas variantes semânticas (`primary` \| `secondary` \| `outlined` \| `loading`) — seção **Botões (DS v2)** |
| Cards / KPI / table-frame / empty | Densidade/hierarquia v2; composição limpa (sem sombra excessiva) — seções **KPI / cartões**, **Table-frame**, **Empty states** |
| Charts polish | Options Chart.js + CSS/markup do bloco; sem novas métricas/libs — seção **Charts polish (DS v2)** |
| Ninebox polish | Visual-only (grade, cards, drawer domínio, drag/ARIA); contratos 006 intactos — seção **Ninebox polish (DS v2)** |
| Shell | Estrutura IA Governança/Cadastros/Sistema **inalterada**; densidade/tipografia no chrome (`sidebar` / `topbar` / `.shell-brand` / `.nav-link*`) sob `.app-shell` (T044) |
| Auth | Login / `base_auth` **OUT** desta feature — isolamento documentado; `--font-sans` / `body { font-sans }` não mudam |

### Experimento Figma (branch `experiment/ds-figma-button-input`)

Referência visual: [Verdee \| Guia de Estilo](https://www.figma.com/design/LqU1eWkoTW4tbSw9LqARHl/Verdee-%7C-Guia-de-Estilo--Copy---c%C3%B3pia-?node-id=0-1) — **não** é fonte da verdade e **não** reabre este Freeze até decisão explícita de produto.

| Recurso do guia | Onde no código | Notas |
|---|---|---|
| Buttons/Medium (~48px) + Outlined / Loading | `button.html` (`primary` \| `secondary` \| `outlined` \| `loading`) | Tokens emerald/teal do People mantidos |
| Input (~48px, hover de borda) | `input.html` + `.form-control` | Estados error/disabled preservados |
| Anatomia de chrome (densidade / CTAs) | `sidebar.html`, `topbar.html`, `nav_link.html`, `.nav-link*` | Header marketing Verdee **não** portado; shell admin People permanece |

### Escopo congelado

| Área | Onde está definido |
|---|---|
| Paleta e tokens semânticos | Seção Paleta + `@theme` em `static/src/input.css` |
| Tipografia | Seção Tipografia (v2: Fraunces display + Source Sans 3 UI sob `.app-shell`; Inter global/auth; escala e pesos documentados) |
| Shell Admin (Governança / Cadastros / Sistema) + destaque Ciclos/Aderência | Seção Shell |
| Topbar (ciclo aberto / fallback) | Seção Shell / Topbar |
| Botões, inputs, badges, empty states, KPI/cards, table-frame | Seções DS v2 acima + componentes; inputs baseline; badges Status Triad intacto |
| Charts polish (options Chart.js + bloco CSS/markup) | Seção **Charts polish (DS v2)**; contrato consumo 005 abaixo |
| Ninebox polish (grade, cards, drawer domínio, drag/empty) | Seção **Ninebox polish (DS v2)**; contrato consumo 006 abaixo |
| Focus-visible, skip link, modal trap, indicador HTMX | Seção Focus-visible e a11y |

Evidência before/after das telas-piloto v2: `specs/007-design-system-v2/evidence/before-after/` (baseline 004 permanece em `specs/004-ux-visual-foundation/evidence/before-after/`).

### Regras após o freeze

1. **Consumir, não reinventar** — novos gráficos, matriz 9-box e demais telas reutilizam tokens, hierarquia tipográfica/espacial e componentes canônicos deste doc.
2. **Doc ↔ CSS juntos** — mudança de token ou padrão atualiza `docs/design-system.md` e `static/src/input.css` (e components afetados) na mesma entrega.
3. **Sem reabrir Freeze v2** — não reinventar tipografia display/UI, variantes de botão, chrome de KPI/table-frame/empty, charts polish ou ninebox polish fora deste contrato; não reaplicar WIP Impeccable nem redesenhar o chrome de navegação como pré-requisito de features de visualização.
4. **Exceções** — só com decisão explícita de produto que atualize este Freeze (status + tabela de cobertura) na mesma mudança.

### Gráficos no dashboard (consumo · FR-013 / SC-007)

Feature `005-dashboard-charts`: visualizações **consomem** Status Triad e componentes deste Freeze (`empty_state`, tipografia/espacial dos cards). **Não** reabre marca, shell, nav, topbar nem inventa ilha de estilo. Acabamento visual v2 (eixos, tooltips, altura do bloco): ver seção **Charts polish (DS v2)**.

| Campo | Valor |
|---|---|
| Lib | Chart.js |
| Versão | **4.5.1** (UMD minificado) |
| CDN | jsDelivr — `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js` |
| Init local | `static/js/dashboard_charts.js` |
| Cores de série | Status Triad — alta `#059669` / média `#d97706` / baixa `#e11d48` + labels textuais |
| Acessibilidade (FR-007) | Legenda Chart.js com texto; `figcaption`/`legend_items` com rótulo + valor (não só cor) |

**Superfícies que carregam o script** (`{% block extra_js %}` da página — **nunca** em `templates/base.html`):

| Template | Rota | Slice |
|---|---|---|
| `templates/dashboard/admin.html` | `dashboard:admin` | 1 MVP |
| `templates/dashboard/team.html` | `dashboard:team` | 2 |
| `templates/dashboard/personal.html` | `dashboard:personal` (`/`) | 3 |

**Fora do slice**: `dashboard:structure` (`StructureDashboardView` / `templates/dashboard/structure.html`) **não** carrega Chart.js nesta feature — métricas de aderência/lacunas de área-cargo ≠ distribuição de etapas do time.

### Matriz 9-box interativa (consumo · FR-012 / research R10)

Feature `006-ninebox-interativa`: a matriz **consome** tokens e componentes deste Freeze (`button`, `badge_status`, `empty_state`, `input` / `.form-control`, `htmx_indicator`). **Não** reabre marca, shell, nav, topbar nem inventa ilha de estilo. Acabamento visual v2 (grade, person cards, drawer de domínio, drag/empty): ver seção **Ninebox polish (DS v2)**.

| Campo | Valor |
|---|---|
| Template | `templates/talent/matrix.html` |
| Rota | `talent:matrix` |
| Grade | Partials `_cell.html` / `_person_card.html` (ids `#cell-{desempenho}-{potencial}`) |
| Drawer (conteúdo) | `templates/talent/partials/_drawer.html` via HTMX → `#matrix-drawer` |
| Init local | `static/js/ninebox_matrix.js` — HTML5 DnD + a11y do drawer (espelha `modal.js`) |
| Lib DnD / SPA | Nenhuma (HTML5 nativo; sem SortableJS / Chart.js / DRF) |

**Superfície que carrega o script** (`{% block extra_js %}` da página — **nunca** em `templates/base.html`):

| Template | Rota | Script |
|---|---|---|
| `templates/talent/matrix.html` | `talent:matrix` | `static/js/ninebox_matrix.js` |

**Convenção DOM** (coordenada com o JS):

| Id / data | Papel |
|---|---|
| `#matrix-results` | Região com `aria-busy`; loading ≠ empty definitivo |
| `#ninebox-matrix` | Grade; `data-ciclo-id` / `data-admin` / `data-move-url-template` |
| `#ninebox-matrix-empty` | Empty Freeze quando zero classificados no filtro/escopo |
| `#matrix-drawer` | Target HTMX (`innerHTML`) do painel lateral |
| `#matrix-drawer-indicator` / `#matrix-loading-indicator` | Indicadores **fora** do swap target |
| `[data-user-pk]` | Cards; células `#cell-{D}-{P}` |

#### Padrão mínimo — drawer lateral in-matrix

Nesta entrega o drawer **não** é componente Freeze compartilhado (`templates/components/drawer.html`). É shell de domínio em `talent` (research R10). Se/quando promover a canônico, preservar este mínimo:

| Aspecto | Padrão |
|---|---|
| Layout | Painel lateral sticky (`xl:w-80`) ao lado da grade — **não** reusar `#modal-container` / `modal.html` (shell centrado) |
| Abertura / escrita | HTMX: `hx-get` / `hx-post` → `#matrix-drawer`; partials HTML; toasts via `HX-Trigger` → `showMessage` |
| Componentes | `button`, `badge_status`, `empty_state` (placeholder idle), `input` / `.form-control`, `htmx_indicator` |
| Modos | Write (`drawer_writable`) só admin; read-only para gerente — sem inventar controles paralelos |
| A11y | `role="dialog"` + `aria-modal`; foco ao abrir; focus trap Tab; Escape fecha; restore no card trigger (paridade com modal) |
| Loading / empty | `aria-busy` + indicador local ≠ empty definitivo de filtro; idle do drawer = “Selecione uma pessoa…” |
| Mobile / drag | Em `pointer: coarse` / viewport estreito: sem DnD; calibração completa via drawer (FR-010) |
| Fallback | Link secundário → `talent:classify` (FR-013); página clássica intacta |

**Fora**: redesenhar sidebar/topbar/marca; Impeccable; promover `drawer.html` canônico sem decisão de produto; JSON/SPA para o painel.

## Paleta de cores

| Uso | Tailwind | Hex aproximado |
|---|---|---|
| Primária (gradiente) | `from-emerald-600 to-teal-500` | #059669 → #14b8a6 |
| Primária hover | `from-emerald-700 to-teal-600` | #047857 → #0d9488 |
| Fundo principal | `bg-slate-50` / token `--color-surface` | #f8fafc |
| Fundo de cartões | `bg-white` / token `--color-surface-card` | #ffffff |
| Texto principal | `text-slate-800` / token `--color-ink` | #1e293b |
| Texto secundário | `text-slate-500` / token `--color-ink-muted` | #64748b |
| Bordas | `border-slate-200` / token `--color-line` | #e2e8f0 |
| Sucesso / aderência alta | `text-emerald-600` / `bg-emerald-50` | — |
| Alerta / aderência média | `text-amber-600` / `bg-amber-50` | — |
| Crítico / aderência baixa | `text-rose-600` / `bg-rose-50` | — |

Tokens semânticos em `static/src/input.css` (`@theme static`): `--color-surface`, `--color-surface-card`, `--color-ink`, `--color-ink-muted`, `--color-line`, `--background-image-brand-gradient`, `--background-image-brand-gradient-hover`. Utilitários equivalentes: `bg-surface`, `bg-surface-card`, `text-ink`, `text-ink-muted`, `border-line`, `bg-brand-gradient` / `bg-brand-gradient-hover`. O `body`, `.table-frame` e `.form-control` usam esses tokens; classes `slate-*` nos templates permanecem equivalentes hex.

## Tipografia

**Status:** Parte do **Freeze v2**. Escala tipográfica completa (famílias, tokens, pesos, usos display vs UI) alinhada a `static/src/input.css`.

Twin CSS obrigatório: `@font-face` + `@theme` (`--font-sans` / `--font-display` / `--font-ui`) + seletor `.app-shell` em `static/src/input.css`. Utilitários Tailwind: `font-sans`, `font-display`, `font-ui`.

### Famílias (self-hosted, `font-display: swap`)

| Papel | Família | Token / utilitário | Onde vive | Arquivo |
|---|---|---|---|---|
| Global / auth (inalterado) | **Inter** | `--font-sans` / `font-sans` | `body` global; login e `base_auth` (sem `.app-shell`) | `static/fonts/InterVariable.woff2` |
| Display (autenticado) | **Fraunces** | `--font-display` / `font-display` | Títulos de página, headlines de KPI e ênfase tipográfica nas superfícies piloto | `static/fonts/FrauncesVariable.woff2` |
| UI (autenticado) | **Source Sans 3** | `--font-ui` / `font-ui` | Corpo, controles e chrome sob `.app-shell` | `static/fonts/SourceSans3Variable.woff2` |

As três faces são variáveis (range `font-weight: 100 900` no `@font-face`); na UI usamos só os pesos da tabela abaixo.

### Tokens CSS (contrato)

| Token | Valor (`@theme`) | Utilitário | Pode mudar nesta feature? |
|---|---|---|---|
| `--font-sans` | `Inter, ui-sans-serif, system-ui, sans-serif` | `font-sans` | **Não** — protege login/`base_auth` |
| `--font-display` | `Fraunces, ui-serif, Georgia, 'Times New Roman', serif` | `font-display` | Sim (só display autenticado) |
| `--font-ui` | `'Source Sans 3', ui-sans-serif, system-ui, sans-serif` | `font-ui` | Sim (default sob `.app-shell`) |

`body` continua com `@apply … font-sans text-sm …`. Em templates autenticados, **não** substituir Inter global por Fraunces/Source Sans fora de `font-display` / `.app-shell`.

### Isolamento `.app-shell`

1. `templates/base.html` aplica `class="app-shell"` no `<body>` **apenas** do shell autenticado.
2. Em CSS: `.app-shell { font-family: var(--font-ui); }` — default tipográfico UI no app logado (herança = Source Sans 3; `font-ui` explícito só quando precisar forçar a família).
3. `--font-sans` e `@apply font-sans` no `body` global **não mudam** (contrato auth: login continua Inter).
4. `templates/accounts/base_auth.html` / `login.html` **não** recebem `app-shell` e **não** entram no diff desta feature.

### Quando usar Display vs UI

| Papel | Família | Aplicar | Não usar em |
|---|---|---|---|
| **Display** | Fraunces via `font-display` | `h1` de página; títulos de seção (`h2`); valor numérico de KPI; ênfase tipográfica de um dado-chave (ex.: quadrante) | Corpo de texto, labels, tabelas, botões, inputs, nav, badges, empty copy |
| **UI** | Source Sans 3 via `.app-shell` (herança) ou `font-ui` | Corpo, subtítulos de apoio, labels, thead, controles, chrome, links de ação | Títulos que precisam de ênfase display (aí combina `font-display` + tamanho/peso) |
| **Global / auth** | Inter via `font-sans` | Login, `base_auth`, qualquer superfície **sem** `.app-shell` | App autenticado (já coberto por `.app-shell`) |

Regra prática: sob `.app-shell`, o default já é UI; **adicione** `font-display` só onde a hierarquia visual precisar de Fraunces.

### Escala tipográfica (tamanho × peso × família)

| Nível | Classes canônicas | Família efetiva | Uso |
|---|---|---|---|
| Página (H1) | `font-display text-2xl font-semibold text-slate-800` | Fraunces | Título principal da tela (`h1`) |
| Seção / cartão (H2) | `font-display text-lg font-medium text-slate-800` | Fraunces | Cabeçalho de bloco / seção |
| KPI valor | `font-display text-2xl font-semibold tabular-nums text-slate-800` | Fraunces | Número destaque do card KPI |
| Ênfase display menor | `font-display text-lg font-semibold` (+ cor do contexto) | Fraunces | Dado-chave curto (ex. nome de ciclo na lista, rótulo de quadrante) |
| Corpo | `text-sm` (+ `text-slate-500` ou `text-slate-600` conforme hierarquia) | Source Sans 3 (`.app-shell`) / Inter (auth) | Parágrafos, descrições sob o título |
| Label de formulário / meta | `text-sm font-medium text-slate-700` | UI | Labels de campo |
| Auxiliar / KPI label | `text-xs uppercase tracking-wide text-slate-500` | UI | Rótulos curtos acima do valor KPI |
| Meta / dt | `text-xs font-medium uppercase tracking-wide text-slate-400` | UI | Definições de perfil, legendas sutis |
| Thead / tabular | `text-xs uppercase tracking-wide text-slate-500` + células `text-sm` | UI | Cabeçalhos e corpo de tabela |
| Ênfase em UI | `font-medium` ou `font-semibold` (sem `font-display`) | UI | Nomes em linha, % em tabela, links de ação |

### Pesos canônicos

| Peso | Classe | Onde |
|---|---|---|
| Regular (400) | (default) | Corpo `text-sm`, textos auxiliares |
| Medium (500) | `font-medium` | Títulos de seção display, labels, thead, links de ação, nav ativa padrão |
| Semibold (600) | `font-semibold` | H1 de página, valor KPI, ênfase display menor, % / nomes fortes em tabela |
| Bold (700+) | — | **Evitar** na UI autenticada v2; não faz parte da escala canônica |

Variáveis WOFF2 cobrem 100–900; a escala de produto restringe-se a **regular / medium / semibold**.

### Referência rápida (cópias prontas)

```html
<!-- Página -->
<h1 class="font-display text-2xl font-semibold text-slate-800">…</h1>
<p class="mt-1 text-sm text-slate-500">…</p>

<!-- Seção -->
<h2 class="font-display text-lg font-medium text-slate-800">…</h2>
<p class="mt-0.5 text-sm text-slate-500">…</p>

<!-- KPI (card) -->
<p class="text-xs uppercase tracking-wide text-slate-500">…</p>
<p class="font-display text-2xl font-semibold tabular-nums text-slate-800">…</p>
```

Pilotos US1 alinhados a esta escala: `templates/dashboard/{admin,team,personal}.html`, `templates/cycles/ciclo_list.html` (+ partial), `templates/pdi/{pdi_detail,pdi_form}.html`, `templates/components/card.html` (valor KPI).

---

## Shell: hierarquia da navegação Admin

Superfície: `templates/components/nav_menu.html` (include em `sidebar.html` desktop + drawer mobile). Autorização continua no backend / `{% if user.is_* %}` — a UI só organiza e destaca.

### Seções cumulativas (fora de Admin)

Ordem vertical: **Colaborador** → **Líder** → **Gerente** → grupos Admin (se `user.is_admin`).

Cabeçalhos de seção: classe `.nav-section-label` (equiv. `text-xs font-medium uppercase tracking-wide text-slate-400`).
Links: `templates/components/nav_link.html` + classes `.nav-link` / `.nav-link--emphasis`.

### Grupos Admin (`user.is_admin`)

Progressive disclosure em três grupos (contrato `admin-nav-grouping.md`):

| Grupo | Peso | Itens |
|---|---|---|
| **Governança** | Ênfase | Ciclos, Aderência (se não manager), Painel admin, Estrutura/Matriz (quando já condicionados) |
| **Cadastros** | Padrão | Áreas, Cargos, Usuários, Competências |
| **Sistema** | Secundário | Auditoria, Notificações |

### Destaque P1 — Ciclos e Aderência

Perceptivelmente mais fortes que itens de Cadastros/Sistema:

| Aspecto | Classes |
|---|---|
| Marker | `border-l-2 border-emerald-500` |
| Peso | `font-semibold` |
| Texto idle | `text-slate-800` (vs `text-slate-600` nos demais) |
| Ativo | `bg-emerald-50 text-emerald-800` |

Itens padrão (Cadastros / Sistema / Painel admin): `text-slate-600 hover:bg-slate-50`; ativo `bg-emerald-50 font-medium text-emerald-700`.

### Item ativo (todas as seções)

Classes visuais **e** `aria-current="page"` no link correspondente a `request.path` (contrato `a11y-shell.md`).

### Topbar

- Uma linha: contexto de ciclo aberto (`ciclo_aberto.nome`) ou fallback “Sem ciclo aberto”; truncar no mobile com `title`.
- Sem filtros, listas ou CTAs novos de ciclo.
- Usuário + logout à direita; toggle do drawer no mobile.
- Densidade v2 (T044): altura `h-14`; chip de ciclo com `tracking-tight` / label `uppercase tracking-wider`; tipografia UI herdada de `.app-shell`.

### Chrome / marca (T044)

- `.shell-brand`: `font-display` + gradiente de marca (sidebar desktop/mobile + topbar mobile).
- Sidebar: largura `w-60`, header e nav com padding mais compacto; **sem** reordenar grupos nem itens (`nav_menu.html` intacto — FR-008).
- Links: `.nav-link` / `.nav-section-label` com tracking e `py` ligeiramente mais densos; ênfase P1 e `aria-current` preservados.

---

## Botões (DS v2)

**Status:** Parte do **Freeze v2**. Ritmo, pesos, hover/focus refinados. Variantes semânticas **inalteradas** (`primary` \| `secondary` \| `outlined` \| `loading`) — sem novas variantes de negócio.

Componente canônico: `templates/components/button.html`.

### Anatomia comum

| Aspecto | Padrão v2 |
|---|---|
| Altura / padding | Buttons/Medium: `h-12` + `px-5` + `rounded-lg` + `gap-2` |
| Tipografia | `font-ui text-sm tracking-tight` (Source Sans 3 sob `.app-shell`) |
| Transição | `transition-colors` |
| Focus | `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface` |
| Disabled / loading | Opacidade 50% + `disabled` / `aria-busy` / `pointer-events-none` (âncora) |

### Variantes

| Variante | Uso | Pesos / chrome | Hover |
|---|---|---|---|
| `primary` (default) | CTA / ação principal | `font-semibold` + `bg-brand-gradient` + `text-white` + `shadow-sm` | `hover:bg-brand-gradient-hover` + `hover:shadow` |
| `secondary` | Cancelar / ação secundária | `font-medium` + `bg-white` + `border border-slate-200` + `text-slate-700` | `hover:border-slate-300` + `hover:bg-slate-100` |
| `outlined` | Terciária / logout | `font-medium` + `border border-emerald-600` + `bg-transparent` + `text-emerald-700` | `hover:border-emerald-700` + `hover:bg-emerald-50` + `hover:text-emerald-800` |
| `loading` | Submit em andamento | Igual **primary** + spinner (`h-4 w-4` border branco) | Bloqueado (`disabled` / `aria-busy="true"`) |

Primary usa **semibold**; secondary/outlined usam **medium** — hierarquia de peso sem trocar a semântica da variante.

### Parâmetros

`label`, `variant`, `type`, `href` (renderiza `<a>`), `disabled`, `hx_get` / `hx_target` / `hx_swap` / `hx_indicator` (defaults para modal + `#htmx-indicator`), `attrs`, `extra_class`.

```html
{% include "components/button.html" with label="Salvar" variant="primary" type="submit" %}
{% include "components/button.html" with label="Cancelar" variant="secondary" %}
{% include "components/button.html" with label="Sair" variant="outlined" type="submit" %}
```

**Não** inventar ilhas de estilo de botão nas superfícies-piloto — preferir o include. **Não** adicionar variantes de negócio novas nesta feature.

---

## Inputs e formulários

Componente canônico: `templates/components/input.html`.

| Elemento | Classes / padrão |
|---|---|
| Label | `block text-sm font-medium text-slate-700 mb-1` |
| Campo | `h-12 w-full rounded-lg border border-slate-200 px-3 text-sm` (+ `hover:border-slate-300`) |
| Foco (campo) | `focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent` (e `:focus-visible` global no CSS) |
| Erro | `border-rose-300` + anel `focus:ring-rose-500`; mensagem `text-xs text-rose-600` com `role="alert"` |
| Disabled | `disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500` |
| Help | `text-xs text-slate-500` via `aria-describedby` |

Utilitário CSS `.form-control` em `input.css` para filtros/selects alinhados ao mesmo anel emerald.

```html
{% include "components/input.html" with label="E-mail" name="email" type="email" %}
```

---

## Badges de status

Componente: `templates/components/badge_status.html`.

**Status:** Parte do **Freeze v2**. Tipografia/densidade UI (`font-ui text-xs … leading-none tracking-tight`); **Status Triad hex/semântica intactos**.

Forma: `inline-flex items-center rounded-md px-2 py-0.5 font-ui text-xs font-medium leading-none tracking-tight`.

| Semântica | Status aceitos | Classes |
|---|---|---|
| Positivo / alto | `concluida`, `concluido`, `aprovada`, `aprovado`, `alta`, `ativo` | `bg-emerald-50 text-emerald-700` |
| Atenção / médio | `em_andamento`, `pendente`, `media` | `bg-amber-50 text-amber-700` |
| Crítico / baixo | `atrasada`, `reprovada`, `reprovado`, `baixa` | `bg-rose-50 text-rose-700` |
| Neutro | `arquivado` e demais | `bg-slate-100 text-slate-600` |

`label` opcional sobrescreve o texto padrão em português. Usar o include em listas, PDI e KPIs — não duplicar chips ad hoc.

---

## Empty states (DS v2)

**Status:** Parte do **Freeze v2**. Acabamento honest/acionável — tipografia display + UI, ritmo vertical; **sem** chrome de card. Dados vazios continuam honestos (padrão 004/005); sem inventar conteúdo.

Componente: `templates/components/empty_state.html`.

| Aspecto | Padrão v2 |
|---|---|
| Container | `flex flex-col items-center justify-center px-4 py-8 text-center` + `role="status"` |
| Headline (`title`, opcional) | `font-display text-base font-medium tracking-tight text-slate-800` |
| Mensagem (`message`, obrigatória) | `max-w-sm font-ui text-sm leading-relaxed text-slate-500` (+ `mt-1.5` se houver título) |
| CTA | `mt-5` + botão **primary** via `button.html` quando o caller passa `cta_label` |

CTA: `cta_href` (link) **ou** `cta_hx_get` (HTMX → modal por default) **ou** `cta_attrs` só. O caller decide permissão — o empty **não** autoriza.

```html
{% include "components/empty_state.html" with title="Sem metas" message="Nenhuma meta cadastrada neste ciclo." cta_label="Nova meta" cta_href=create_url %}
```

Preferir empty acionável onde a lista/KPI já tem ação de domínio (criar meta/ação); polish visual **não** altera `has_data` nem payloads.

---

## KPI / cartões (DS v2)

**Status:** Parte do **Freeze v2**. Densidade e hierarquia KPI refinadas; preferir **composição limpa** a cardificar excessivamente (sem sombra no frame).

Componente: `templates/components/card.html`.

| Aspecto | Padrão v2 |
|---|---|
| Container | `rounded-xl border border-line bg-surface-card p-4` — **sem** `shadow-sm` |
| Label KPI | `text-xs uppercase tracking-wide text-slate-500` (UI) |
| Valor | `font-display text-2xl font-semibold tabular-nums tracking-tight text-slate-800` |
| Título de bloco | `font-display text-lg font-medium text-slate-800` |
| Body auxiliar | `text-sm leading-snug text-slate-500` (UI sob `.app-shell`) |
| Badge no KPI | `badge_status` + `badge_label` ao lado do label (com `value`) ou como conteúdo principal |

Tokens de surface (`border-line` / `bg-surface-card`) alinhados a `@theme` em `input.css` — equivalentes a slate-200 / white.

Grid típico first viewport: `grid grid-cols-1 md:grid-cols-3 gap-4` com cards KPI — **sem** novos gráficos, métricas ou queries; só hierarquia tipográfica/espacial dos dados já expostos.

```html
{% include "components/card.html" with label="Aderência" value="86%" badge_status="alta" %}
```

Dashboards piloto (`admin` / `team` / `personal`) consomem este include; não marcar KPIs com classes de card ad hoc.

---

## Table-frame (DS v2)

**Status:** Parte do **Freeze v2**. Chrome leve (borda + surface, **sem** sombra) + densidade anatômica nos filhos `table`/`th`/`td`. Twin CSS em `static/src/input.css` (`@layer components`).

### Wrapper

| Classe | Contrato |
|---|---|
| `.table-frame` | `overflow-x-auto rounded-xl border border-line bg-surface-card` |

### Anatomia (filhos)

| Seletor | Padrão |
|---|---|
| `.table-frame table` | `min-w-full divide-y divide-line text-left text-sm text-ink` |
| `.table-frame thead` | `bg-slate-50/80 text-xs uppercase tracking-wide text-ink-muted` |
| `.table-frame th` / `td` | `px-4 py-2.5`; `th` com `font-medium`; `td` com `align-middle` |
| `.table-frame tbody` | `divide-y divide-slate-100` |
| `.table-frame tbody tr:hover` | `bg-slate-50` (templates com ênfase de status podem sobrescrever) |

```html
<div class="table-frame">
  <table>…</table>
</div>
```

Piloto: listas `templates/cycles/ciclo_list.html` / `ciclo_list_partial.html` (e demais listagens que já usam `.table-frame`). **Não** envolver cada célula em card; o frame é o único chrome de lista.

---

## Charts polish (DS v2)

**Status:** Parte do **Freeze v2**. Acabamento visual dos gráficos já existentes (feature `005`). **Só** options Chart.js, CSS de altura/ritmo e markup do bloco — **sem** novas métricas, endpoints, libs ou mudanças de shape JSON. Contrato: `specs/007-design-system-v2/contracts/chart-visual-polish.md`.

### Artefatos

| Camada | Path | Papel |
|---|---|---|
| Options Chart.js | `static/js/dashboard_charts.js` | Fonte UI, grid, radius/thickness, cutout, tooltip chrome, legend padding |
| Altura / ritmo | `static/src/input.css` (`.dashboard-chart-canvas`) | Altura fixa responsiva; Chart.js com `maintainAspectRatio: false` |
| Markup do bloco | `templates/dashboard/_chart_block.html` | Frame, título, canvas, figcaption, empty |
| Empty visual | `templates/components/empty_state.html` | Acabamento v2 quando `has_data` é falso |

### Bloco (`_chart_block.html`)

Frame alinhado a KPI/card (composição limpa, **sem** sombra):

| Aspecto | Padrão v2 |
|---|---|
| Container (`<figure>`) | `rounded-xl border border-line bg-surface-card p-4 sm:p-5` |
| Título | `font-display text-lg font-medium tracking-tight text-slate-800` (`h3`) |
| Canvas wrapper | `.dashboard-chart-canvas` (ver CSS abaixo) |
| Figcaption | `mt-4 border-t border-line pt-3.5`; lista `text-sm leading-snug text-slate-600` com rótulo **+** valor (e swatch `aria-hidden` opcional) |
| Empty | Ritmo `mt-3 py-4 sm:py-5` + include `empty_state` com `chart.empty_message` — **sem** séries inventadas |

```html
{% include "dashboard/_chart_block.html" with chart=chart_aderencia_distribuicao script_id="chart-aderencia-distribuicao" %}
```

### Altura CSS (`.dashboard-chart-canvas`)

| Viewport | `height` / `min-height` |
|---|---|
| default (abaixo de 640px) | `15.5rem` (~248px) |
| `sm` (≥ 640px) | `17rem` |
| `lg` (≥ 1024px) | `19rem` |

Também: `relative mt-5 w-full min-w-0`. Rótulos e legenda devem permanecer consultáveis em ~375px.

### Options Chart.js (só visual)

Constantes espelham tokens de `input.css` (`--font-ui`, ink-muted, line) — **não** alteram Status Triad de negócio (`#059669` / `#d97706` / `#e11d48`).

| Aspecto | Valor / comportamento |
|---|---|
| Família | Source Sans 3 (`FONT_UI`) — eixos, legenda, tooltips |
| Ticks / labels | `color` ink-muted `#64748b`; size 12 (10–11 no mobile) |
| Legenda | `position: bottom`; `usePointStyle`; padding 14 (10 no mobile); weight `500`; texto + valor (FR-007) |
| Grid (eixo de valor) | `#e2e8f0`, `lineWidth: 1`, sem ticks; eixo de categoria sem grid |
| Bordas de escala | ocultas |
| Barras | `borderRadius: 6`, `maxBarThickness: 40`, `borderWidth: 0` |
| Doughnut | `cutout: '68%'`, borda branca 2px entre fatias |
| Tooltip | fundo ink `#1e293b`, `cornerRadius: 8`, borda sutil, title semibold / body regular |
| Responsivo | `responsive: true` + `maintainAspectRatio: false` (altura no CSS); barras agrupadas podem virar `indexAxis: 'y'` em viewport estreito (max-width 639px) com mais de 2 labels |

### Intocado (regressão 005)

| Item | Regra |
|---|---|
| Shape JSON | `has_data`, `labels`, `values`, `series`, `colors`, `legend_items`, `type` |
| Negócio | `apps/dashboard/chart_payloads.py`, views e `apps/dashboard/urls.py` sem mudança de contrato |
| Lib | Chart.js **4.5.1** CDN — sem lib nova, sem plugin npm |
| Script load | Só admin / team / personal em `extra_js` — **nunca** em `base.html` |
| Empty | `has_data !== true` → sem Chart; empty honesto |

Pilotos: `templates/dashboard/{admin,team,personal}.html` via `_chart_block.html`.

---

## Ninebox polish (DS v2)

**Status:** Parte do **Freeze v2**. Acabamento visual da matriz 9-box já existente (feature `006`). **Só** tipografia/densidade/bordas/estados visuais em templates `talent` + feedback drag/ARIA de suporte em `ninebox_matrix.js` — **sem** alterar AuthZ, fórmulas, política drag=potencial-only, endpoints JSON, handlers de POST nem contratos HTMX (`hx-*` / targets / URLs). Contrato: `specs/007-design-system-v2/contracts/ninebox-visual-only.md`.

### Artefatos

| Camada | Path | Papel |
|---|---|---|
| Página / grade | `templates/talent/matrix.html` | Títulos display, filtros, frame `table-frame`, empty, shell do drawer |
| Células | `templates/talent/partials/_cell.html` | Densidade, bordas de grade, tipografia de quadrante, empty de célula |
| Person cards | `templates/talent/partials/_person_card.html` | Chrome leve, hover/focus, handle DnD visual |
| Drawer domínio | `templates/talent/partials/_drawer.html` | Tipografia/densidade/separadores; **hx-* intactos** |
| Feedback drag / ARIA | `static/js/ninebox_matrix.js` | opacity/ring/cursor + live region; sem mudança de regra de negócio |
| Empty visual | `templates/components/empty_state.html` | Empty honesto (ciclo, filtro, idle drawer) com acabamento v2 |

Drawer permanece **domínio `talent`** — **não** criar `templates/components/drawer.html` canônico nesta feature.

### Grade (`matrix.html` + `_cell.html`)

| Aspecto | Padrão v2 |
|---|---|
| Títulos de página / seção | `font-display` + `tracking-tight`; corpo/meta em `text-sm` / `text-ink-muted` |
| Labels de filtro | `text-xs font-medium uppercase tracking-wide text-ink-muted` + `.form-control` |
| Container da grade | `#ninebox-matrix` com `table-frame p-2.5 sm:p-3.5` |
| Grid interno | `rounded-lg border border-line`; eixos em `uppercase tracking-wide text-ink-muted` |
| Célula | `min-h-[7.5rem] sm:min-h-[8rem]`; `p-2.5 sm:p-3`; bordas `border-t border-l border-line` |
| Rótulo de quadrante | `font-display text-xs font-medium tracking-tight` + eixo por extenso (além da cor) |
| Tint semântico leve | `bg-emerald-50/60` (3×3) / `bg-rose-50/40` (1×1); demais `bg-surface-card` |
| Célula vazia | Placeholder dashed + “Vazio” (`aria-hidden`) — **não** fingir pessoas |
| Empty de escopo | `#ninebox-matrix-empty` + `empty_state` (loading/`aria-busy` ≠ empty definitivo) |

### Person cards (`_person_card.html`)

| Aspecto | Padrão v2 |
|---|---|
| Chrome | `rounded-md border border-line bg-surface-card` — **sem** sombra |
| Densidade | Botão `px-2.5 py-2`; nome `font-medium tracking-tight text-ink`; email `text-xs text-ink-muted` |
| Hover / focus | `hover:bg-slate-50`; `focus-visible:ring-2 focus-visible:ring-emerald-500` + offset surface |
| DnD (admin + ponteiro fino) | `cursor-grab` / `active:cursor-grabbing`; handle `ninebox-dnd-handle` com nome acessível |
| Gates | Server: `draggable` só admin; client: desliga em `pointer: coarse` / viewport estreito — drawer continua caminho completo |

### Drawer de domínio (`_drawer.html` + shell em `matrix.html`)

| Aspecto | Padrão v2 |
|---|---|
| Shell lateral | `rounded-lg border border-line bg-surface-card p-4`; sticky `xl:w-80` |
| Heading | `font-display text-lg font-medium tracking-tight text-ink` |
| Meta (área/cargo/ciclo) | Labels uppercase muted + valores `font-medium`; separadores `border-t border-line` |
| Hint read-only | `rounded-md border border-line bg-slate-50/80` — texto, sem novos controles |
| Controles | Continua consumindo `button`, `badge_status`, `.form-control`, `htmx_indicator` |
| Contrato HTMX | Targets `#matrix-drawer`, URLs drawer/move/toggle e partials **inalterados** |

### Feedback de drag (`ninebox_matrix.js`)

Tokens espelham o shell (emerald focus / amber alerta Status Triad) — **não** mudam política potencial-only nem o body do POST.

| Estado | Classes / comportamento |
|---|---|
| Card em arraste | `opacity-60 ring-2 ring-emerald-500 ring-offset-1 ring-offset-surface cursor-grabbing` |
| Drop válido (mesma linha desempenho) | `ring-2 ring-emerald-500 ring-inset bg-emerald-50/40` |
| Snap / alerta visual | `ring-2 ring-amber-500 ring-inset bg-amber-50/40` |
| POST pendente | `opacity-50` + `aria-busy` no card |
| Cancel (Esc / fora) | Restore visual; **zero POST** |
| ARIA suporte | Live region `#ninebox-drag-status` (`aria-live="polite"`); `aria-grabbed` nos cards com DnD |

### Intocado (regressão 006)

| Item | Regra |
|---|---|
| Drag persist | POST só `potencial`; desempenho ignorado na gravação; snap; cancel = zero POST; sem SortableJS |
| AuthZ / escopo | Admin write; gerente RO; líder 403; `get_visible_users`; IDOR 403 |
| HTMX drawer | Targets `#matrix-drawer`, URLs e partials HTML; filtros ciclo/área/cargo |
| A11y drawer | Focus trap, Escape, restore; loading ≠ empty; alternativa drawer ao drag |
| Drawer canônico | **Não** promover `templates/components/drawer.html` nesta feature |

Piloto: `templates/talent/matrix.html` (+ partials) com `static/js/ninebox_matrix.js` em `extra_js` — **nunca** em `base.html`.

---

## Focus-visible e a11y mínima do shell

Definido em `static/src/input.css` (`@layer base`) e contrato `a11y-shell.md`.

| Superfície | Comportamento |
|---|---|
| Links, botões, `[role=button]`, `summary`, tabindex ≥ 0 | `:focus-visible` → `ring-2 ring-emerald-500 ring-offset-2 ring-offset-surface` |
| Inputs / select / textarea | `:focus-visible` → `ring-2 ring-emerald-500` + `border-transparent` |
| Skip link | “Ir para o conteúdo” → `#main-content` no início do `body` (`base.html`); visível no foco |
| Modal | Focus trap Tab/Shift+Tab em `static/js/modal.js`; Escape + restore no trigger |
| Drawer in-matrix (9-box) | Mesmo contrato de foco/trap/Escape em `static/js/ninebox_matrix.js` sobre `#matrix-drawer` — ver **Matriz 9-box interativa** + **Ninebox polish (DS v2)** |
| HTMX | `#htmx-indicator` com `role="status"` e “Carregando…” anunciável em `.htmx-request` — não `aria-hidden="true"` permanente |

Preferir `:focus-visible` (não `:focus` agressivo) para não marcar clique de mouse.

---

## Layout base

### Menu lateral (sidebar)

- Sidebar fixa à esquerda (`bg-white border-r border-slate-200`), com logo no topo.
- Itens de navegação exibidos conforme as visões cumulativas do usuário (colaborador sempre, + time/estrutura/administração via `{% if %}`).
- Ver seção **Shell: hierarquia da navegação Admin** acima.

### Topbar

- Contexto mínimo de ciclo + nome do usuário e logout (ver Shell / Topbar).

## Componentes reutilizáveis

Templates parciais em `templates/components/`:

| Componente | Uso |
|---|---|
| `button.html` | Botões primário e secundário (+ HTMX modal) |
| `input.html` | Campos de formulário com erro/help |
| `card.html` | Cartões de conteúdo / KPI |
| `badge_status.html` | Status de ações do PDI, metas e aderência |
| `empty_state.html` | Lista/KPI vazio com CTA opcional |
| `sidebar.html` | Menu lateral |
| `nav_menu.html` | Itens de navegação (desktop + mobile) |
| `nav_link.html` | Link canônico da nav (ativo / ênfase P1) |
| `topbar.html` | Barra superior (ciclo, toggle mobile, logout) |
| `htmx_indicator.html` | Indicador de carregamento anunciável |
| `modal.html` | Container de dialog HTMX |

### HTMX

Usado para:

- Submissão de formulários sem reload.
- Atualização parcial de listas (ex.: lista de ações do PDI, paginação de ciclos/avaliações).
- Modais de criação/edição (`hx-target="#modal-container"`).

Preservar `hx-target` / swap / indicator das superfícies-piloto; polish visual não altera regiões de swap.

## Páginas de erro (404 / 403)

Templates customizados (`404.html`, `403.html`) seguindo a identidade visual do produto:

- Mesma sidebar/topbar quando o usuário está autenticado.
- Cartão central com ícone, mensagem em português e botão de voltar ao dashboard.
- Mensagem genérica: *"Você não tem acesso a este recurso ou ele não existe"* — sem indício visual de que o registro existe ou não.

## Responsividade

- Interface responsiva (desktop e mobile).
- Breakpoints Tailwind para mobile em todas as listagens.
- Sidebar fixa no desktop (`md+`); no mobile, drawer com overlay aberto pelo botão do topbar.
- Tabelas em wrappers com `overflow-x-auto` / `.table-frame` para scroll horizontal sem quebrar o layout.
- Filtros em `grid-cols-1` no mobile e `flex-wrap` a partir de `sm`.
- Fontes auto-hospedadas em `static/fonts/` (Inter, Fraunces, Source Sans 3 — sem CDN em runtime); tipografia v2 escopada em `.app-shell` (ver Tipografia).
