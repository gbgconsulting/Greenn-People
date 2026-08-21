# Data Model: Conformidade visual ao Freeze v2 (016)

**Branch**: `016-freeze-screen-conformity`  
**Date**: 2026-08-21

## Declaração

Esta feature **não introduz models Django novos**, **não cria migrations** e **não altera** campos, FKs, `on_delete`, snapshots, máquina de estados, fórmulas nem predicados de escopo.

As Key Entities da [spec.md](./spec.md) são **conceitos de auditoria/apresentação** mapeados para templates, includes e contratos Freeze. Persistência inalterada.

Contratos: [contracts/](./contracts/). Referência visual reusada (não reaberta): 009 chart/painel + 012 densidade-histórico-empty.

---

## Entidades de apresentação

### Inventário Category A

Conjunto fechado de superfícies gerenciais desta rodada.

| Campo lógico | Valor |
|---|---|
| Membros | admin, team, aderência, estrutura, matriz, ciclo detalhe, meu painel |
| Padrão de qualidade | Conformidade **excelente** |
| Composição | KPI(s) → visual (`_chart_block`) → drill (`.table-frame`) → ações |
| Largura | Full-bleed no conteúdo do painel (**sem** cap B1) |
| Charts | Catálogo Freeze A + densidade/empty D; proibido markup fake |

**Validação**: checklist A em [quickstart.md](./quickstart.md); SC-001.

### Inventário Category B

Conjunto fechado de cadastros desta rodada.

| Campo lógico | Valor |
|---|---|
| Membros | Áreas, Cargos, Usuários (+ pendentes correlatos), Competências |
| Padrão | Conformidade **decente** + B1 |
| Proibido | KPI/chart/decoração que a tela não pedia |
| Form cap | `max-w-lg` centralizado (já vigente) |
| Lista cap | `max-w-5xl` (≤4 cols) / `max-w-6xl` (>4 cols) |

**Fora**: listas de ciclo, escalas (CRUD), audit, notifications, demais CRUDs.

### Violação visual

| Campo | Descrição |
|---|---|
| Observável | Desvio vs contrato Freeze (token, componente, composição, chart) |
| Ação | Remediação presentation-only até zero violações na tela |
| Escala | Se o Freeze/B1 não cobrir → STOP (não “adaptar”) |

### Componente canônico

Includes existentes: `button`, `input`/`.form-control`, `card`, `badge_status`, `empty_state`, `.table-frame`, `_chart_block`, `pagination`.

### Largura de tabela B (decisão B1)

| Campo | Regra |
|---|---|
| Container | Cap médio-largo / degrau maior conforme nº de colunas |
| Colunas | `table-fixed` + proporções via `colgroup` |
| Ações | Direita; separador leve; sem `\|` denso |
| Mobile | Scroll horizontal só dentro do frame |
| Documentação | `docs/design-system.md` na mesma entrega |

Detalhe normativo: [contracts/table-frame-listas-b.md](./contracts/table-frame-listas-b.md).

### Progresso de ciclo (presentation)

| Campo | Origem |
|---|---|
| Counts por etapa | `Avaliacao` do ciclo já autorizado (views existentes) |
| Tipo visual | `bar_horizontal` mono + amber no gargalo |
| Empty | Freeze D via `has_data` / `empty_kind` |
| Proibido | Barra HTML ad hoc; série inventada; mudar semântica de etapa |

---

## State transitions

Nenhuma. Esta feature não altera estados de domínio.

---

## Relationships (lógicas)

```text
Inventário A ──consome──► Freeze A/C/D + managerial-panel + chart-catalog
Inventário B ──consome──► Freeze (components) + B1 Table-frame listas
Violação ──remedia──► Componente canônico / token DS
Paginação B ──usa──► pagination.html (fonte única)
AuthZ ──intocável──► get_visible_users / ScopedObjectMixin
```

---

## Validation rules (aceitação)

1. Path editado ∈ allowlist; ∉ denylist de domínio/Verdee/fora-inventário.
2. Diff em `scope.py` / predicados AuthZ = falha.
3. Tela A: ordem KPI → visual → drill → ações; charts reais; badges canônicos; sem sombra card/KPI.
4. Tela B: form `max-w-lg`; lista com cap B1 + colunas + ações; sem chart/KPI indevido.
5. Progresso admin/`ciclo_detail`: Freeze-compliant (SC-003).
6. ~375px: 0 scroll horizontal de página (SC-004).
7. DS atualizado **somente** com B1 (SC-006).
