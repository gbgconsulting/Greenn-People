# Contract: Freeze Design System v2

**Feature**: `007-design-system-v2`  
**Canonical doc**: `docs/design-system.md`  
**CSS twin**: `static/src/input.css`

## Propósito

Definir o que a entrega **deve** declarar e materializar ao fechar o Freeze v2 (FR-009 / SC-004), sem reabrir produto.

## Mudanças obrigatórias no Freeze (doc)

| Área | Antes (004) | Depois (v2) |
|---|---|---|
| Status | Congelado 004 | **Freeze v2** (007) |
| Tipografia | Inter único (`font-sans`) | Display (**Fraunces**) + UI (**Source Sans 3**) no app autenticado; Inter permanece default global / auth |
| Botões | Variantes Freeze | Ritmo/pesos/hover/focus refinados; **mesmas** variantes semânticas |
| Cards / KPI / table-frame / empty | Baseline 004 | Densidade/hierarquia v2; preferir composição limpa a card excessivo |
| Charts | Consumo 005 Status Triad | Seção **charts polish**: options/CSS; sem novas métricas/libs |
| Ninebox | Consumo 006 domínio | Seção **ninebox polish**: visual-only; contratos 006 intactos |
| Shell | Governança/Cadastros/Sistema | Estrutura IA **inalterada**; densidade/tipo opcional |
| Auth | Login no piloto 004 | Login **OUT** desta feature — documentar isolamento |

## Tokens CSS (contrato técnico)

| Token / seletor | Contrato |
|---|---|
| `--font-sans` / `body { font-sans }` | **Não mudar** para família v2 (protege auth) |
| `--font-display` / `font-display` | Novo; uso display autenticado |
| `--font-ui` / `font-ui` | Novo; corpo/controles autenticados |
| `.app-shell` | Escopo onde UI v2 é default tipográfico |
| Status Triad hex | `#059669` / `#d97706` / `#e11d48` preservados como semântica |

## Dualidade

Toda mudança de token/padrão nesta lista atualiza **doc + CSS (+ component tocado)** na mesma PR. Fonte canônica humana = `docs/design-system.md`.

## Fora do Freeze v2 (não documentar como “entregue”)

- Redesign de marca/paleta completa  
- Drawer canônico global  
- Dark mode, WCAG formal, marketing Verdee completo, Impeccable baseline  
- Novas capacidades de negócio  

Ver [out-checklist.md](./out-checklist.md).
