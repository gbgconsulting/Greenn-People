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

- [ ] B9 Pass — `docs/design-system.md` tem seção Table-frame · listas B (T004); Freeze A/B/C/D intocados

---

## Matriz por entidade

### B · Áreas

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-5xl` | 4 | `area_list.html`, `area_list_partial.html`, `area_form.html` | T024, T025 |

**Lista**

- [ ] B2 Pass (`mx-auto w-full max-w-5xl`)
- [ ] B3 Pass (`.table-frame`)
- [ ] B4 Pass (`table-fixed` + colgroup ~40/25/15/20)
- [ ] B5 Pass (`text-right`; `·`; sem `\|`)
- [ ] B6 Pass
- [ ] B7 Pass / N/A
- [ ] B8 Pass

**Form**

- [ ] B1 Pass (`mx-auto max-w-lg`; canônicos; sem sombra)
- [ ] B6 Pass
- [ ] B8 Pass (página sem bleed)

Notas / violações:

---

### B · Cargos

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-5xl` | 4 | `cargo_list.html`, `cargo_list_partial.html`, `cargo_form.html` | T026, T027 |

**Lista**

- [ ] B2 Pass (`max-w-5xl`)
- [ ] B3 Pass
- [ ] B4 Pass
- [ ] B5 Pass
- [ ] B6 Pass
- [ ] B7 Pass / N/A
- [ ] B8 Pass

**Form**

- [ ] B1 Pass
- [ ] B6 Pass
- [ ] B8 Pass

Notas / violações:

---

### B · Usuários

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-6xl` | 7 | `user_list.html`, `user_list_partial.html`, `user_form.html` | T028, T029 |

**Lista**

- [ ] B2 Pass (`mx-auto w-full max-w-6xl`)
- [ ] B3 Pass
- [ ] B4 Pass (ações ~12–15% à direita)
- [ ] B5 Pass
- [ ] B6 Pass
- [ ] B7 Pass / N/A
- [ ] B8 Pass

**Form**

- [ ] B1 Pass
- [ ] B6 Pass
- [ ] B8 Pass

Notas / violações:

---

### B · Usuários pendentes (correlata CTA)

| Cap lista | Paths | Tasks |
|-----------|-------|-------|
| conforme nº de cols (≤4 → `max-w-5xl`; >4 → `max-w-6xl`) | `user_pending_list.html`, `user_pending_list_partial.html` | T030 |

**Lista** (sem form nesta rodada)

- [ ] B2 Pass (cap pela regra de colunas)
- [ ] B3 Pass
- [ ] B4 Pass
- [ ] B5 Pass
- [ ] B6 Pass
- [ ] B7 Pass / N/A
- [ ] B8 Pass
- [ ] B1 N/A (sem form dedicado)

Notas / violações:

---

### B · Competências

| Cap lista | Colunas | Paths | Tasks |
|-----------|---------|-------|-------|
| `max-w-5xl` | 4 | `competencia_list.html`, `competencia_list_partial.html`, `competencia_form.html` | T031, T032 |

**Lista**

- [ ] B2 Pass (`max-w-5xl`)
- [ ] B3 Pass
- [ ] B4 Pass
- [ ] B5 Pass
- [ ] B6 Pass
- [ ] B7 Pass / N/A
- [ ] B8 Pass

**Form**

- [ ] B1 Pass
- [ ] B6 Pass
- [ ] B8 Pass

**Fora desta rodada** (não marcar remediação): `escala_*`, `cargo_competencia_form.html`

Notas / violações:

---

## Canônicos compartilhados B (T033)

- [ ] `badge_status` / `empty_state` / `button` / `input` / `card` nas listas/forms remediadas
- [ ] Sem chip/botão solto
- [ ] Views `apps/organization/views.py` / `apps/competencies/views.py`: sem mudança QS/AuthZ (só context presentation se inevitável)

---

## Explicitamente fora (não remediar nesta feature)

- [ ] Confirmado: **não** remediou listas de ciclo / audit / notifications / escalas CRUD

---

## Fechamento US3 (T034)

- [ ] Áreas, Cargos, Usuários (+ pendentes), Competências — lista+form Pass no checklist B — SC-002
- [ ] Quickstart Admin 1.5 amostrado
- [ ] SC-004 / SC-005 amostral
- [ ] B9 / DS B1 confirmado (T004)
- [ ] Contratos 009/012 **não** editados
- [ ] Diff denylist vazio
