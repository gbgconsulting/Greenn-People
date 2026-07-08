# Design System

Identidade visual moderna, clara e responsiva, aplicada de forma consistente em todas as telas via Tailwind CSS dentro do Django Template Language (template base + componentes reutilizáveis via `{% include %}`).

## Paleta de cores

| Uso | Tailwind | Hex aproximado |
|---|---|---|
| Primária (gradiente) | `from-emerald-600 to-teal-500` | #059669 → #14b8a6 |
| Primária hover | `from-emerald-700 to-teal-600` | #047857 → #0d9488 |
| Fundo principal | `bg-slate-50` | #f8fafc |
| Fundo de cartões | `bg-white` | #ffffff |
| Texto principal | `text-slate-800` | #1e293b |
| Texto secundário | `text-slate-500` | #64748b |
| Bordas | `border-slate-200` | #e2e8f0 |
| Sucesso / aderência alta | `text-emerald-600` / `bg-emerald-50` | — |
| Alerta / aderência média | `text-amber-600` / `bg-amber-50` | — |
| Crítico / aderência baixa | `text-rose-600` / `bg-rose-50` | — |

## Tipografia

- **Fonte:** Inter (Google Fonts, carregada localmente para evitar dependência externa em runtime).
- **Hierarquia:**
  - `text-2xl font-semibold` — títulos de página
  - `text-lg font-medium` — títulos de cartão
  - `text-sm` — corpo
  - `text-xs text-slate-500` — auxiliar

## Botões

```html
<!-- Botão primário -->
<button class="bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-700 hover:to-teal-600
               text-white font-medium rounded-lg px-4 py-2 shadow-sm transition-colors">
  Salvar
</button>

<!-- Botão secundário -->
<button class="bg-white border border-slate-200 text-slate-700 hover:bg-slate-50
               font-medium rounded-lg px-4 py-2 transition-colors">
  Cancelar
</button>
```

## Inputs e formulários

```html
<div class="mb-4">
  <label class="block text-sm font-medium text-slate-700 mb-1">E-mail</label>
  <input type="email" name="email"
         class="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm
                focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent" />
</div>
```

## Cartões e grid

```html
<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
  <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
    <p class="text-xs text-slate-500 uppercase tracking-wide">Aderência</p>
    <p class="text-2xl font-semibold text-slate-800">86%</p>
  </div>
</div>
```

## Layout base

### Menu lateral (sidebar)

- Sidebar fixa à esquerda (`bg-white border-r border-slate-200`), com logo no topo.
- Itens de navegação exibidos conforme as visões cumulativas do usuário (colaborador sempre, + time/estrutura/administração via `{% if %}` no template base).
- Item ativo: fundo `bg-emerald-50 text-emerald-700 font-medium`.

### Topbar

- Nome do usuário e botão de logout.

## Componentes reutilizáveis

Templates parciais em `templates/components/`:

| Componente | Uso |
|---|---|
| `button.html` | Botões primário e secundário |
| `input.html` | Campos de formulário |
| `card.html` | Cartões de conteúdo |
| `badge_status.html` | Status de ações do PDI e aderência |
| `sidebar.html` | Menu lateral |
| `topbar.html` | Barra superior |

### HTMX

Usado para:

- Submissão de formulários sem reload.
- Atualização parcial de listas (ex.: lista de ações do PDI).
- Modais de criação/edição.

## Páginas de erro (404 / 403)

Templates customizados (`404.html`, `403.html`) seguindo a identidade visual do produto:

- Mesma sidebar/topbar quando o usuário está autenticado.
- Cartão central com ícone, mensagem em português e botão de voltar ao dashboard.
- Mensagem genérica: *"Você não tem acesso a este recurso ou ele não existe"* — sem indício visual de que o registro existe ou não.

## Responsividade

- Interface responsiva (desktop e mobile).
- Breakpoints Tailwind para mobile em todas as listagens.
