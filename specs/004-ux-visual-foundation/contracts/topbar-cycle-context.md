# Contract: Contexto mínimo de ciclo na topbar

**Feature**: `004-ux-visual-foundation`  
**Superfície**: `templates/components/topbar.html`  
**Dados**: `get_open_ciclo()` (`apps.goals.forms`) via context processor `apps.core` (nome sugerido: `ciclo_aberto` ou `topbar_ciclo_aberto` documentado na implementação)

## Contrato de apresentação

| Estado | Conteúdo | Restrições |
|---|---|---|
| Há ciclo com `status=ABERTO` | Texto mínimo: identificador legível (ex.: nome do ciclo). Opcional: rótulo curto “Ciclo” | Uma linha; sem filtros, listas, dropdowns, CTAs secundários |
| Nenhum ciclo aberto | Fallback claro (ex.: “Sem ciclo aberto”) | Layout topbar não quebra; não some a navegação primária |

## Contrato de dados

- **Fonte**: `Ciclo.objects.filter(status=ABERTO).order_by('-data_inicio').first()` (já encapsulado).
- **Quando**: requests autenticados; anônimo → não exibir bloco de ciclo (topbar auth existente).
- **Não criar**: views/API HTMX/JSON para “ciclo atual”.
- **Não alterar**: regras de abertura/fechamento de ciclo.

## Densidade

- Contexto cabe entre identidade/menu e área do usuário **sem** empurrar logout para fora do viewport desktop padrão.
- Mobile: truncar com `title`/tooltip nativo se necessário; não adicionar segunda fileira de chrome.

## Compatibilidade

- Views que já passam `ciclo_aberto` continuam válidas; processor não deve contradizer seleção de ciclo de filtro em páginas (filtros de “ver outro ciclo” permanecem na página, não na topbar).
