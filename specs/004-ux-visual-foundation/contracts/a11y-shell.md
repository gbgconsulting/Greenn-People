# Contract: A11y mínima do shell / modal / HTMX

**Feature**: `004-ux-visual-foundation`  
**Stack**: HTML + Tailwind + `static/js/modal.js` + HTMX (sem libs a11y novas)

## Skip link

- Primeiro foco Tab útil: link “Ir para o conteúdo” (ou equivalente em PT) no `base.html`.
- `href="#main-content"`; elemento `#main-content` no `<main>` (ou wrapper único do conteúdo).
- Visível no foco (`focus-visible`); pode ser `sr-only` até focar.

## Página atual na nav

- Item correspondente a `request.path` (lógica atual de highlight): atributo `aria-current="page"`.
- Apenas um item “página atual” por nav renderizada (desktop e mobile compartilham o same include — ok duplicar visualmente nos dois DOMs desde que cada nav marque o ativo).

## Focus-visible

- Controles interativos do shell e components-piloto mostram anel de foco coerente com tokens (emerald/slate).
- Preferir `:focus-visible` para não marcar clique mouse de forma agressiva.

## Modal — focus trap

Extensão de `static/js/modal.js` (comportamento já existente: focus inicial, Escape, restore no trigger):

| Evento | Comportamento obrigatório |
|---|---|
| Modal aberto (`#modal-container [role=dialog][aria-modal=true]`) | Tab / Shift+Tab ciclam só entre focáveis do dialog |
| Escape | Fecha e restaura foco no trigger |
| Fechamento (`closeModal` / esvaziar container) | Restore previsível |

Sem dependência npm.

## Indicador HTMX

- Elemento usado com `hx-indicator` (ex.: `#htmx-indicator`) MUST expor estado de carregamento acessível quando a request está ativa.
- Contrato mínimo: `role="status"` + texto “Carregando…” (ou label param) perceptível a leitores de tela no estado request; não manter `aria-hidden="true"` o tempo todo se isso anular o anúncio.
- Preferência: togglear `aria-hidden` / live region alinhada a `.htmx-request` (listener pequeno em `base.html` ou no partial).

## Verificação

Checklist teclado em [quickstart.md](../quickstart.md) (SC-004).
