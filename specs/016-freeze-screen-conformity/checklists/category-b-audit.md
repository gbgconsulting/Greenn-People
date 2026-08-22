# Checklist operacional: Category B (auditoria US3)

**Feature**: `016-freeze-screen-conformity`  
**Uso**: Marcar Pass/Fail **entidade a entidade** (lista **e** form) nas tarefas US3 (T024–T034). Espelho de [quickstart.md](../quickstart.md) § Checklist Category B.  
**Contrato B1**: [table-frame-listas-b.md](../contracts/table-frame-listas-b.md) + seção DS (T004).  
**Referência visual (consumo only)**: contratos 009/012 — **não editar**.  
**Gate**: path ∈ [path-allowlist.md](../contracts/path-allowlist.md); ∉ [non-goals-denylist.md](../contracts/non-goals-denylist.md).

---

## Critérios (espelho quickstart)

| # | Critério | Onde |
|---|----------|------|
| B1 | Form: `mx-auto max-w-lg`, card/inputs/botões canônicos, sem sombra | Form |
| B2 | Lista: container cap `max-w-5xl` (≤4 cols) ou `max-w-6xl` (>4) | Lista |
| B3 | Tabela em `.table-frame`; sem cardificar linhas | Lista |
| B4 | `table-fixed` + colunas proporcionais; nome não afasta ações | Lista |
| B5 | Ações à direita; separador leve; **sem** `\|` | Lista |
| B6 | Sem KPI/chart/decoração indevida | Lista + form |
| B7 | Paginação via `components/pagination.html` apenas | Lista (se paginável) |
| B8 | ~375px: scroll só dentro do frame; página sem bleed | Lista (+ form sem bleed) |
| B9 | DS documenta B1 ([table-frame-listas-b.md](../contracts/table-frame-listas-b.md)) | Entrega (uma vez) |

**N/A**: critério de lista em form (e vice-versa), ou paginação ausente na tela.

---

## Como auditar

1. Abrir **lista** e **form** (create/edit) de cada entidade; pendentes = correlata do CTA Usuários.
2. Confirmar cap lista ≠ form; A **não** recebe cap B1.
3. Remediação = presentation-only; QS/AuthZ intocáveis.
4. SC-002 = 100% inventário B abaixo Pass (incl. B1 + B9).

---

## Gate documental (uma vez por entrega)

- [x] B9 Pass — `docs/design-system.md` tem seção Table-frame · listas B (T004); Freeze A/B/C/D intocados

---

## Matriz por entidade

### B · Áreas

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-5xl` | 4 | `area_list.html`, `area_list_partial.html`, `area_form.html` | T024, T025 |

**Lista**

- [x] B2 Pass (`mx-auto w-full max-w-5xl`)
- [x] B3 Pass (`.table-frame`)
- [x] B4 Pass (`table-fixed` + colgroup ~40/25/15/20)
- [x] B5 Pass (`text-right`; `·`; sem `\|`)
- [x] B6 Pass
- [x] B7 Pass / N/A
- [x] B8 Pass

**Form**

- [x] B1 Pass (`mx-auto max-w-lg`; canônicos; sem sombra)
- [x] B6 Pass
- [x] B8 Pass (página sem bleed)

Notas / violações:

**T025 (2026-08-22)**: Card chrome DS (`border-line`/`bg-surface-card`, sem sombra); `input.html` + `.form-control`; `button` primary/secondary; erros rose Freeze-only; `min-w-0` no cap (A8/B8). Sem KPI/chart. Views/forms intocados.

---

### B · Cargos

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-5xl` | 4 | `cargo_list.html`, `cargo_list_partial.html`, `cargo_form.html` | T026, T027 |

**Lista**

- [x] B2 Pass (`max-w-5xl`)
- [x] B3 Pass
- [x] B4 Pass
- [x] B5 Pass
- [x] B6 Pass
- [x] B7 Pass / N/A
- [x] B8 Pass

**Form**

- [x] B1 Pass (`mx-auto max-w-lg`; canônicos; sem sombra)
- [x] B6 Pass
- [x] B8 Pass (página sem bleed)

Notas / violações:

**T026 (2026-08-22)**: Lista B1 — cap `mx-auto w-full max-w-5xl`; `table-fixed`+colgroup ~40/25/15/20; ações `text-right` com `·` (sem `\|`); `badge_status`/`empty_state`/`pagination` canônicos. Views intocados.

**T027 (2026-08-22)**: Card chrome DS (`border-line`/`bg-surface-card`, sem sombra); `input.html` para `nome`/`nivel`; `button` primary/secondary; erros rose Freeze-only; `min-w-0` no cap (A8/B8). Sem KPI/chart. Views/forms intocados.

---

### B · Usuários

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-6xl` | 7 | `user_list.html`, `user_list_partial.html`, `user_form.html` | T028, T029 |

**Lista**

- [x] B2 Pass (`mx-auto w-full max-w-6xl`)
- [x] B3 Pass (`.table-frame`)
- [x] B4 Pass (`table-fixed` + colgroup 19/19/12/12/11/12/15; ações ~15% à direita)
- [x] B5 Pass (`text-right`; `·`; sem `\|`)
- [x] B6 Pass
- [x] B7 Pass / N/A
- [x] B8 Pass

**Form**

- [x] B1 Pass (`mx-auto min-w-0 max-w-lg`; canônicos; sem sombra)
- [x] B6 Pass
- [x] B8 Pass (página sem bleed)

Notas / violações:

**T028 (2026-08-22)**: `user_list.html` — cap `mx-auto w-full max-w-6xl` (B2). `user_list_partial.html` — `.table-frame`, `table-fixed w-full` + colgroup 7 cols (B3/B4); ações `text-right` com `·` (B5); `badge_status`/`empty_state`/`pagination` canônicos (B6); sem KPI/chart (B7 N/A); scroll no frame (B8). Views intocados.

**T029 (2026-08-22)**: Card chrome DS (`border-line`/`bg-surface-card`, sem sombra); `input.html` para `nome`/`data_entrada`; selects `.form-control` (área/cargo/gestor); aviso amber com CTA `button` secondary; `button` primary/secondary; erros rose Freeze-only; `min-w-0` no cap (A8/B8). Sem KPI/chart. Views/forms.py intocados.

---

### B · Usuários pendentes (correlata CTA)

| Cap lista | Paths | Tasks |
|-----------|-------|-------|
| `max-w-6xl` | 6 | `user_pending_list.html`, `user_pending_list_partial.html` | T030 |

**Lista** (sem form nesta rodada)

- [x] B2 Pass (`mx-auto w-full max-w-6xl`)
- [x] B3 Pass (`.table-frame`)
- [x] B4 Pass (`table-fixed` + colgroup 19/19/12/12/18/15; ações ~15% à direita)
- [x] B5 Pass (`text-right`; ação única sem `\|`)
- [x] B6 Pass (`button` secondary no avisório/header; `badge_status`/`empty_state`/`pagination` canônicos)
- [x] B7 Pass / N/A
- [x] B8 Pass
- [x] B1 N/A (sem form dedicado)

Notas / violações:

**T030 (2026-08-22)**: `user_pending_list.html` — cap `mx-auto w-full max-w-6xl` (B2, 6 cols). CTAs avisório correlatos → `button` secondary; `data-blocker-kind` preservado. `user_pending_list_partial.html` — `.table-frame`, `table-fixed w-full` + colgroup 19/19/12/12/18/15 (B3/B4); ações `text-right` (B5); `badge_status`/`empty_state`/`pagination` canônicos (B6); sem KPI/chart (B7 N/A); scroll no frame (B8). Views intocados.

### B · Competências

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-5xl` | 4 | `competencia_list.html`, `competencia_list_partial.html`, `competencia_form.html` | T031, T032 |

**Lista**

- [x] B2 Pass (`mx-auto w-full max-w-5xl`)
- [x] B3 Pass (`.table-frame`)
- [x] B4 Pass (`table-fixed` + colgroup ~40/25/15/20)
- [x] B5 Pass (`text-right`; `·`; sem `\|`)
- [x] B6 Pass
- [x] B7 Pass / N/A
- [x] B8 Pass

**Form**

- [x] B1 Pass
- [x] B6 Pass
- [x] B8 Pass

**Fora desta rodada** (não marcar remediação): `escala_*`, `cargo_competencia_form.html`

Notas / violações:

**T031 (2026-08-22)**: `competencia_list.html` — cap `mx-auto w-full max-w-5xl` (B2). `competencia_list_partial.html` — `.table-frame`, `table-fixed w-full` + colgroup ~40/25/15/20 (B3/B4); ações `text-right` com `·` (B5); `empty_state`/`pagination`/`button` canônicos (B6); sem KPI/chart (B7 N/A); scroll no frame (B8). `escala_*` / `cargo_competencia_form` intocados. Views intocados.

**T032 (2026-08-22)**: `competencia_form.html` — cap `mx-auto min-w-0 max-w-lg` (B1/B8); card chrome DS (`border-line`/`bg-surface-card`, sem sombra) separado do `<form>`; `input.html` + textarea + selects `.form-control`; `button` primary/secondary; erros rose Freeze-only. Sem KPI/chart (B6). Views/forms.py intocados.

---

## Canônicos compartilhados B (T033)

- [x] `badge_status` / `empty_state` / `button` / `input` / `card` nas listas/forms remediadas
- [x] Sem chip/botão solto
- [x] Views `apps/organization/views.py` / `apps/competencies/views.py`: sem mudança QS/AuthZ (só context presentation se inevitável)

Notas / violações:

**T033 (2026-08-22)**: Sweep 9 listas + 5 forms (T024–T032). Pass em todos os canônicos; forms usam card chrome DS documentado (não `card.html` KPI). Ações de tabela = links tipográficos DS (B5). **Fix**: chip “Admin” solto em `user_list_partial.html` → `badge_status` neutro (`status="admin"` + `label="Admin"`). Views organization/competencies: diff vazio.

---

## Explicitamente fora (não remediar nesta feature)

- [x] Confirmado: **não** remediou listas de ciclo / audit / notifications / escalas CRUD

---

## Fechamento US3 (T034)

- [x] Áreas, Cargos, Usuários (+ pendentes), Competências — lista+form Pass no checklist B — SC-002
- [x] Quickstart Admin 1.5 amostrado
- [x] SC-004 / SC-005 amostral
- [x] B9 / DS B1 confirmado (T004)
- [x] Contratos 009/012 **não** editados
- [x] Diff denylist vazio

**T034 (2026-08-22) — gate US3 / Category B 100% + B1**:

| Gate | Evidência |
|------|-----------|
| SC-002 | 5 entidades B (Áreas, Cargos, Usuários, Pendentes, Competências) — listas B2–B8 Pass; forms B1/B6/B8 Pass (pendentes B1 N/A); canônicos T033 Pass |
| Admin 1.5 | Caps: áreas/cargos/competências `max-w-5xl`; usuários/pendentes `max-w-6xl`; forms `max-w-lg`; `.table-frame` + `table-fixed`+colgroup; ações `text-right` com `·` |
| SC-004 | Forms: `min-w-0` no cap; listas: scroll no `.table-frame` (`overflow-x`); `w-full` + caps B1; sem bleed de página amostral |
| SC-005 | Grep inventário B: 0× `shadow-`; 0× `\|` em ações; CTAs via `button.html`; `badge_status`/`empty_state`/`input` canônicos; chip “Admin” → badge (T033) |
| B9 / T004 | `docs/design-system.md` § Table-frame · listas de cadastro (Category B / decisão B1) presente; Freeze A/B/C/D não reabertos neste WT |
| Fora inventário | WT sem diff em `ciclo_list*`, audit, notifications, `escala_*`, `cargo_competencia_form` (escala ainda com `\|` — intocado de propósito) |
| Denylist | Diff vazio em `scope.py` / `stage.py` / `cycle.py` / approval / views organization+competencies; templates só allowlist B |
| 009/012 | Contratos 009/012 **fora** do diff |

Checkpoint: Category B 100% decente + B1 — US4 pode auditar `pagination.html` na fonte.
