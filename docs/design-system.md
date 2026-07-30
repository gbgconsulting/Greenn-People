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

**Status:** congelado (feature `004-ux-visual-foundation` · SC-006).

Este documento é a **fonte da verdade** de tokens e padrões de UI do Greenn People. Features seguintes — em especial **gráficos / visualizações no dashboard** e **9-box interativa** — devem **consumir** o conjunto documentado abaixo (e os includes em `templates/components/`), sem reabrir redesign de marca nem inventar ilhas de estilo.

### Escopo congelado

| Área | Onde está definido |
|---|---|
| Paleta e tokens semânticos | Seção Paleta + `@theme` em `static/src/input.css` |
| Tipografia | Seção Tipografia (`font-sans` / Inter) |
| Shell Admin (Governança / Cadastros / Sistema) + destaque Ciclos/Aderência | Seção Shell |
| Topbar (ciclo aberto / fallback) | Seção Shell / Topbar |
| Botões, inputs, badges, empty states, KPI/cards, tabelas | Seções e componentes correspondentes |
| Focus-visible, skip link, modal trap, indicador HTMX | Seção Focus-visible e a11y |

Evidência before/after das telas-piloto: `specs/004-ux-visual-foundation/evidence/before-after/`.

### Regras após o freeze

1. **Consumir, não reinventar** — novos gráficos, matriz 9-box e demais telas reutilizam tokens, hierarquia tipográfica/espacial e componentes canônicos deste doc.
2. **Doc ↔ CSS juntos** — mudança de token ou padrão atualiza `docs/design-system.md` e `static/src/input.css` (e components afetados) na mesma entrega.
3. **Sem reabrir baseline** — não reaplicar WIP Impeccable nem redesenhar o chrome incumbente como pré-requisito de features de visualização.
4. **Exceções** — só com decisão explícita de produto que atualize este Freeze (status + tabela) na mesma mudança.

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

- **Fonte:** Inter (Google Fonts, carregada localmente para evitar dependência externa em runtime) — `--font-sans` / `font-sans`.
- **Hierarquia:**
  - `text-2xl font-semibold` — títulos de página / valores KPI
  - `text-lg font-medium` — títulos de cartão
  - `text-sm` — corpo (default em `body`)
  - `text-xs text-slate-500` — auxiliar / labels de KPI (`uppercase tracking-wide`)

---

## Shell: hierarquia da navegação Admin

Superfície: `templates/components/nav_menu.html` (include em `sidebar.html` desktop + drawer mobile). Autorização continua no backend / `{% if user.is_* %}` — a UI só organiza e destaca.

### Seções cumulativas (fora de Admin)

Ordem vertical: **Colaborador** → **Líder** → **Gerente** → grupos Admin (se `user.is_admin`).

Cabeçalhos de seção: `text-xs font-medium uppercase tracking-wide text-slate-400`.

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

---

## Botões

Componente canônico: `templates/components/button.html`.

| Variante | Uso | Classes-base |
|---|---|---|
| `primary` (default) | Ação principal / CTA | `bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-700 hover:to-teal-600 text-white shadow-sm` |
| `secondary` | Cancelar / ação secundária | `bg-white border border-slate-200 text-slate-700 hover:bg-slate-50` |

Comum a ambos: `inline-flex items-center justify-center font-medium rounded-lg px-4 py-2 transition-colors`.

Parâmetros úteis: `label`, `variant`, `type`, `href` (renderiza `<a>`), `disabled`, `hx_get` / `hx_target` / `hx_swap` / `hx_indicator` (defaults para modal + `#htmx-indicator`), `attrs`, `extra_class`.

```html
{% include "components/button.html" with label="Salvar" variant="primary" type="submit" %}
{% include "components/button.html" with label="Cancelar" variant="secondary" %}
```

Não inventar ilhas de estilo de botão nas superfícies-piloto — preferir o include.

---

## Inputs e formulários

Componente canônico: `templates/components/input.html`.

| Elemento | Classes / padrão |
|---|---|
| Label | `block text-sm font-medium text-slate-700 mb-1` |
| Campo | `w-full rounded-lg border border-slate-200 px-3 py-2 text-sm` |
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

Forma: `inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium`.

| Semântica | Status aceitos | Classes |
|---|---|---|
| Positivo / alto | `concluida`, `concluido`, `aprovada`, `aprovado`, `alta`, `ativo` | `bg-emerald-50 text-emerald-700` |
| Atenção / médio | `em_andamento`, `pendente`, `media` | `bg-amber-50 text-amber-700` |
| Crítico / baixo | `atrasada`, `reprovada`, `reprovado`, `baixa` | `bg-rose-50 text-rose-700` |
| Neutro | `arquivado` e demais | `bg-slate-100 text-slate-600` |

`label` opcional sobrescreve o texto padrão em português. Usar o include em listas, PDI e KPIs — não duplicar chips ad hoc.

---

## Empty states

Componente: `templates/components/empty_state.html`.

- Container: `flex flex-col items-center justify-center gap-3 text-center` com `role="status"`.
- Título opcional: `text-sm font-medium text-slate-800`.
- Mensagem: `text-sm text-slate-500` (obrigatória).
- CTA opcional via `cta_label` + `cta_href` **ou** `cta_hx_get` (botão primary do componente `button.html`); o caller decide permissão — o empty state não autoriza.

Preferir empty states acionáveis onde a lista/KPI vazio já tem ação de domínio (ex.: criar meta/ação), sem inventar dados.

---

## KPI / cartões

Componente: `templates/components/card.html`.

| Aspecto | Padrão |
|---|---|
| Container | `rounded-xl border border-slate-200 bg-white p-5 shadow-sm` |
| Label KPI | `text-xs uppercase tracking-wide text-slate-500` |
| Valor | `text-2xl font-semibold tabular-nums text-slate-800` |
| Título de bloco | `text-lg font-medium text-slate-800` |
| Body auxiliar | `text-sm text-slate-500` |
| Badge no KPI | `badge_status` + `badge_label` ao lado do label (com `value`) ou como conteúdo principal |

Grid típico first viewport: `grid grid-cols-1 md:grid-cols-3 gap-4` com cards KPI — **sem** novos gráficos, métricas ou queries agregadas; só hierarquia tipográfica/espacial dos dados já expostos.

```html
{% include "components/card.html" with label="Aderência" value="86%" badge_status="alta" %}
```

Listagens usam `.table-frame` (`overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm`).

---

## Focus-visible e a11y mínima do shell

Definido em `static/src/input.css` (`@layer base`) e contrato `a11y-shell.md`.

| Superfície | Comportamento |
|---|---|
| Links, botões, `[role=button]`, `summary`, tabindex ≥ 0 | `:focus-visible` → `ring-2 ring-emerald-500 ring-offset-2 ring-offset-surface` |
| Inputs / select / textarea | `:focus-visible` → `ring-2 ring-emerald-500` + `border-transparent` |
| Skip link | “Ir para o conteúdo” → `#main-content` no início do `body` (`base.html`); visível no foco |
| Modal | Focus trap Tab/Shift+Tab em `static/js/modal.js`; Escape + restore no trigger |
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
- Fonte Inter auto-hospedada em `static/fonts/InterVariable.woff2` (sem CDN em runtime).
