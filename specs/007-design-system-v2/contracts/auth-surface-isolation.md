# Contract: Isolamento da superfície Auth

**Feature**: `007-design-system-v2`  
**Refs**: FR-002, SC-002, research R2

## Regra dura

Tipografia e tokens v2 **MUST NOT** alterar a tela de login nem templates baseados em `accounts/base_auth`.

## Arquivos intocados (diff vazio no aceite)

| Path | Motivo |
|---|---|
| `templates/accounts/base_auth.html` | Base auth |
| `templates/accounts/login.html` | Login produzido |
| Demais extends de `base_auth` (register, password reset, verify, …) | Herdam isolamento |

Qualquer “fix” visual de login nesta feature = **falha de aceite**, não trade-off.

## Como tokens v2 não vazam

1. `base_auth.html` e `base.html` continuam linkando o mesmo `tailwind.css` (fato atual).
2. `--font-sans` e `@layer base { body { font-sans } }` permanecem **Inter**.
3. Famílias v2 entram como tokens adicionais + aplicação sob **`.app-shell`** (classe no `<body>` de `templates/base.html` apenas).
4. Components tipograficamente refinados vivem no path autenticado; login **não** inclui `button.html`/shell (já monta markup próprio).
5. Não usar mudança global de `body` para “ativar” v2.

## Verificação

| Método | Esperado |
|---|---|
| `git diff` nos paths auth | Vazio |
| Screenshot login before vs after | Visualmente igual (prova SC-002) |
| Inspecionar CSS aplicado no login | Continua Inter / sem `app-shell` |

**T011 (2026-08-06)**: `git diff` auth vazio vs HEAD; login sem `app-shell`; `body` permanece `font-sans`/Inter; `.app-shell` apenas em `templates/base.html`. Evidência: [evidence/before-after/README.md](../evidence/before-after/README.md#verificação-de-isolamento-auth-t011--2026-08-06).

**T018 (2026-08-06)**: revalidação US1 (quickstart §1) — admin/team/lista com hierarquia `font-display` + `.app-shell`; login sem vazamento v2; diff auth continua vazio. Evidência: [evidence/before-after/README.md](../evidence/before-after/README.md#validação-us1--quickstart-1-t018--2026-08-06).

## Anti-padrões (proibidos)

- Alterar `--font-sans` para Source Sans 3 / Fraunces  
- `@apply font-ui` no `body` global  
- Editar `login.html` “só um pouquinho” para alinhar  
- Carregar CSS que redefine `body { font-family }` sem escopo  

Detalhes: [auth research R2](../research.md#r2--isolamento-tipográfico-login--base_auth-não-herdam).
