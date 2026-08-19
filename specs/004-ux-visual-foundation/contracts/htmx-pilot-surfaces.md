# Contract: HTMX nas telas-piloto (preservação)

**Feature**: `004-ux-visual-foundation`  
**Objetivo**: Polish visual **não** altera contratos HTMX existentes nas superfícies-piloto.

## Alvos e swaps a preservar (exemplos críticos)

| Superfície | Padrões típicos | Não quebrar |
|---|---|---|
| Listas (ciclos, reviews, PDI, metas) | `#list-container` / partial + pagination | `hx-target`, `hx-swap` vigentes |
| Modais PDI / forms | `hx-target="#modal-container"` | Abertura, submit, `closeModal` |
| Indicador | `hx-indicator="#htmx-indicator"` (ou id local) | Continua apontando a um indicador válido e acessível |

## Regras

- Mudanças de class/markup interno ok se atributos `hx-*` e ids de target permanecerem.
- Se um id de target precisar mudar, atualizar **todos** os produtores na mesma mudança scoped (uma superfície).
- Feedback: toasts `showMessage` / `aria-live` em `base.html` permanecem.

## Fora

- Migrar para SPA; trocar HTMX por fetch ad hoc; novos endpoints só “para UI”.
