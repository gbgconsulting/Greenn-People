# Quickstart: Validação 016 — Conformidade Freeze (A/B + B1)

**Branch**: `016-freeze-screen-conformity`  
**Pré-requisitos**: ambiente Django local; usuários Admin (Marina), Líder (Bruno), Colaborador (Ana); ciclo aberto com avaliações em etapas distintas **e** cenário sem dados; Tailwind rebuild se `input.css` mudar.

Contratos: [contracts/](./contracts/). Mapa lógico: [data-model.md](./data-model.md). Referência visual intacta: 009 chart/painel + 012 densidade-empty.

## Setup

```bash
# na raiz do repo
source .venv/bin/activate  # se aplicável
python manage.py migrate
python manage.py runserver
# se input.css alterado:
# npx --yes @tailwindcss/cli -i static/src/input.css -o static/css/tailwind.css
```

---

## 0) Gate de escopo inválido (antes de olhar UI)

- Diff ∈ [path-allowlist.md](./contracts/path-allowlist.md); ∉ [non-goals-denylist.md](./contracts/non-goals-denylist.md).
- Sem alteração em AuthZ/escopo/stage/approval/fórmulas.
- Regressão de domínio (asserts intactos):

```bash
pytest tests/test_stage_machine.py tests/test_scope.py \
  tests/test_reject_stage_invariant.py
```

- Se a remediação pediu token/componente **ausente** do Freeze (exceto B1) → deve ter **parado** (ESCALATE), não “adaptado”.

---

## Checklist Category A (excelente)

**Operacional (tela a tela, US2)**: [checklists/category-a-audit.md](./checklists/category-a-audit.md).

Para **cada** tela A: admin, time, aderência, estrutura, matriz, ciclo detalhe, meu painel.

| # | Critério | Pass? |
|---|----------|-------|
| A1 | Ordem KPI(s) → visual → drill/tabela → ações | |
| A2 | Charts = catálogo Freeze (`_chart_block`); sem markup fake | |
| A3 | Aderência: só Status Triad (3 fatias) onde couber | |
| A4 | Rankings longos: Top-N + “Outros” se Freeze D exigir; pipeline etapas sem Top-N | |
| A5 | Badges = `badge_status`; CTAs = `button` | |
| A6 | Cards/KPIs sem sombra; cores na paleta Freeze | |
| A7 | Empty = kinds D (não “sem dados” genérico indevido) | |
| A8 | ~375px: sem scroll horizontal da página / bleed | |
| A9 | Full-bleed (sem cap B1) | |

---

## Checklist Category B (decente + B1)

**Operacional (entidade a entidade, US3)**: [checklists/category-b-audit.md](./checklists/category-b-audit.md).

Para **cada** entidade: Áreas, Cargos, Usuários (+ pendentes), Competências — lista **e** form.

| # | Critério | Pass? |
|---|----------|-------|
| B1 | Form: `mx-auto max-w-lg`, card/inputs/botões canônicos, sem sombra | |
| B2 | Lista: container cap `max-w-5xl` (≤4 cols) ou `max-w-6xl` (>4) | |
| B3 | Tabela em `.table-frame`; sem cardificar linhas | |
| B4 | `table-fixed` + colunas proporcionais; nome não afasta ações | |
| B5 | Ações à direita; separador leve; **sem** `\|` | |
| B6 | Sem KPI/chart/decoração indevida | |
| B7 | Paginação via `components/pagination.html` apenas | |
| B8 | ~375px: scroll só dentro do frame; página sem bleed | |
| B9 | DS documenta B1 ([table-frame-listas-b.md](./contracts/table-frame-listas-b.md)) | |

---

## Validação por persona

### Admin RH (Marina)

| # | Ação | Esperado |
|---|------|----------|
| 1.1 | `/dashboard/admin/` com ciclo em andamento | Progresso por etapa = `bar_horizontal` Freeze; amber só no gargalo; sem barra fake |
| 1.2 | Admin sem dados de progresso | Empty Freeze D; sem série inventada |
| 1.3 | `cycles/<pk>/` detalhe | Mesmo critério de progresso (SC-003 ≤ 5 min/inspeção) |
| 1.4 | Matriz (se acessar) | Checklist A; ninebox consome Freeze |
| 1.5 | Áreas / Cargos / Usuários / Competências | Checklist B (+ pendentes via CTA Usuários) |
| 1.6 | Confirmar **não** remediou listas de ciclo / audit / notifications | Fora do inventário |

### Gestor / líder (Bruno)

| # | Ação | Esperado |
|---|------|----------|
| 2.1 | `/dashboard/team/` | Checklist A; só escopo já autorizado |
| 2.2 | Aderência / Estrutura | Checklist A; Triad / cobertura ≠ aderência |
| 2.3 | Matriz | Checklist A |
| 2.4 | Cadastros B | **Não** são fluxo desta rodada — não exigir |

### Colaborador (Ana)

| # | Ação | Esperado |
|---|------|----------|
| 3.1 | Meu painel (`/`) | Checklist A |
| 3.2 | Expectativas / metas / PDI / avaliações / minha classificação | **Fora** — não reabertos |

---

## US4 — Paginação na fonte

| # | Ação | Esperado |
|---|------|----------|
| 4.1 | Inspecionar `templates/components/pagination.html` | Única implementação; tokens/canônicos Freeze |
| 4.2 | Lista B paginável | Consome o include; sem HTML paralelo |
| 4.3 | HTMX swap `#list-container` | Canvas A (se na mesma sessão) intacto |

---

## Aceite mensurável (espelha SC)

- [x] SC-001: 100% inventário A no checklist A (T023 · 2026-08-22)
- [x] SC-002: 100% inventário B no checklist B (incl. B1) (T034 · 2026-08-22)
- [x] SC-003: progresso admin + detalhe sem barra fake (T013 · 2026-08-21)
- [x] SC-004: 0 scroll horizontal de página em ~375px (T023 A + T034 B amostral · 2026-08-22 — `min-w-0` forms B / `.table-frame` listas; canvas A; caps B1 só em B)
- [x] SC-005: 0 sombra card/KPI, chip ad hoc ou cor fora da paleta na amostragem (T023 A + T034 B + T038 paginação · 2026-08-22)
- [ ] SC-006: DS só +B1; A/B/C/D não reabertos (B1 já em DS — confirmação formal em T042)

## Quando parar e perguntar

Implementador **STOP** se:

1. Precisar de token/cor/componente/chart ausente do Freeze e de B1.
2. Diff exigir mudança em AuthZ/escopo/domínio.
3. Tela alvo não estiver no inventário A/B (ou correlata Usuários pendentes).
