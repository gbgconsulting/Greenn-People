# Contract: Drag — persistência potencial-only

**Feature**: `006-ninebox-interativa`  
**Cliente**: `static/js/ninebox_matrix.js` (HTML5 DnD)  
**Servidor**: action POST interna (HTMX ou `fetch` + HTML/headers) chamando `upsert_classification`

## Payload lógico

| Campo | Obrigatório | Semântica |
|---|---|---|
| Identificador da pessoa | sim | `user_pk` e/ou `classificacao_pk` |
| `ciclo_id` | sim | Ciclo da matriz filtrada |
| `potencial` | sim | Inteiro 1–3 da **coluna** da célula-alvo |
| `desempenho` (célula) | **ignorado** | Cliente pode enviar para debug; servidor **não** usa para mutar desempenho |

**MUST NOT**: aceitar desempenho livre para gravação; MUST NOT “pintar” desempenho pela célula de destino.

## Comportamento (research R4 — snap)

1. Servidor resolve desempenho via avaliação + `derive_desempenho` (dentro de `upsert_classification`).
2. Persiste `potencial` solicitado; recalcula `quadrante`.
3. Resposta posiciona o card em `(desempenho_derivado, potencial_novo)` — **snap** se a célula sob o cursor tinha desempenho diferente.
4. Feedback PT-BR explícito quando houve snap de linha (só potencial editável).
5. Se `potencial` == valor atual → noop (200/204 sem mudança material) + opcional mensagem suave.
6. Cancelamento client-side (Esc / drop fora) → **nenhum** POST.

## Erros

| Caso | HTTP / UX | Estado visual |
|---|---|---|
| Não autenticado / não admin | 403 | Revert posição + toast erro |
| Pessoa fora do que admin pode operar / IDOR | 403 | Revert + toast |
| Potencial inválido | 400 / form error | Revert + toast |
| Sem avaliação / sem `nota_final_lider` | 400 (ValidationError) | Revert + mensagem vigente |
| Rede / 5xx | erro | Revert + toast; **sem** sucesso silencioso |

## UI gates (não autorizam)

- `draggable` / handles apenas se template renderizou para admin.
- Mobile / `pointer: coarse`: DnD desligado; drawer permanece caminho completo (FR-010).
- Não-admin: zero handles; POST direto ainda 403.

## Fora

- Alterar desempenho; multi-select lote; histórico visual de moves; lib SortableJS.
