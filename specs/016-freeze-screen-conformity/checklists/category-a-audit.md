# Checklist operacional: Category A (auditoria US2)

**Feature**: `016-freeze-screen-conformity`  
**Uso**: Marcar Pass/Fail **tela a tela** nas tarefas US2 (T014–T023). Espelho de [quickstart.md](../quickstart.md) § Checklist Category A.  
**Referência visual (consumo only)**: contratos 009 chart/painel + 012 densidade-empty — **não editar**.  
**Gate**: path ∈ [path-allowlist.md](../contracts/path-allowlist.md); ∉ [non-goals-denylist.md](../contracts/non-goals-denylist.md).

---

## Critérios (espelho quickstart)

| # | Critério |
|---|----------|
| A1 | Ordem KPI(s) → visual → drill/tabela → ações |
| A2 | Charts = catálogo Freeze (`_chart_block`); sem markup fake |
| A3 | Aderência: só Status Triad (3 fatias) onde couber |
| A4 | Rankings longos: Top-N + “Outros” se Freeze D exigir; pipeline etapas sem Top-N |
| A5 | Badges = `badge_status`; CTAs = `button` |
| A6 | Cards/KPIs sem sombra; cores na paleta Freeze |
| A7 | Empty = kinds D (não “sem dados” genérico indevido) |
| A8 | ~375px: sem scroll horizontal da página / bleed |
| A9 | Full-bleed (sem cap B1) |

**N/A**: marcar quando o critério não se aplica à superfície (ex.: A3 fora de aderência; A4 se não houver ranking longo).

---

## Como auditar

1. Abrir a tela com dados **e** (quando possível) sem dados.
2. Percorrer A1–A9; registrar violação + path do template.
3. Remediação = presentation-only; se faltar token Freeze (exceto B1) → **ESCALATE / STOP**.
4. SC-001 = 100% das linhas abaixo com Pass (ou N/A justificado).

---

## Matriz por tela

### A · Painel admin

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/admin.html` (+ chrome `_ciclo_selector` / `_visao_toggle` se tocado) | Marina | T014 (+ progresso US1: T007/T009) |

- [ ] A1 Pass
- [ ] A2 Pass
- [ ] A3 N/A (não é aderência) / Pass se Triad aparecer indevido → Fail
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass (~375px)
- [ ] A9 Pass (full-bleed; sem `max-w-5xl`/`max-w-6xl` de B1 no conteúdo do painel)

Notas / violações:

---

### A · Painel do time

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/team.html`, `team_list_partial.html` | Bruno | T015 |

- [ ] A1 Pass
- [ ] A2 Pass (`_chart_block` **fora** do partial HTMX)
- [ ] A3 N/A / Fail se Triad indevido
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Aderência

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/adherence.html`, `adherence_list_partial.html` | Bruno | T016 |

- [ ] A1 Pass
- [ ] A2 Pass
- [ ] A3 Pass (Status Triad — 3 fatias only; sem recalcular `adherence.py`)
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Estrutura

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/structure.html` | Bruno | T017 |

- [ ] A1 Pass
- [ ] A2 Pass
- [ ] A3 N/A (cobertura ≠ aderência; sem Triad indevido)
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Matriz de talentos

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/talent/matrix.html`, `partials/_cell.html`, `_drawer.html`, `_person_card.html` | Marina / Bruno | T020 |

- [ ] A1 Pass (composição gerencial / polish Freeze; ninebox consome Freeze)
- [ ] A2 Pass / N/A se sem chart de catálogo
- [ ] A3 N/A
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Ciclo (detalhe)

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/cycles/ciclo_detail.html` | Marina | T019 (+ progresso US1: T008/T010) |

- [ ] A1 Pass
- [ ] A2 Pass (`bar_horizontal` / `_chart_block`; sem barra fake)
- [ ] A3 N/A
- [ ] A4 Pass / N/A (pipeline etapas **sem** Top-N indevido)
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

### A · Meu painel

| Paths | Persona | Tasks |
|-------|---------|-------|
| `templates/dashboard/personal.html` | Ana | T018 |

- [ ] A1 Pass
- [ ] A2 Pass (sem tendência/chart novo fora do catálogo)
- [ ] A3 N/A
- [ ] A4 Pass / N/A
- [ ] A5 Pass
- [ ] A6 Pass
- [ ] A7 Pass
- [ ] A8 Pass
- [ ] A9 Pass

Notas / violações:

---

## Chrome compartilhado (se auditoria exigir)

| Paths | Tasks |
|-------|-------|
| `templates/dashboard/_ciclo_selector.html`, `_visao_toggle.html` | T021 |

- [ ] Canônicos only (`button` / tokens Freeze); sem ilha de estilo
- [ ] ESCALATE se faltar token

Notas / violações:

---

## Fechamento US2 (T023)

- [ ] 7 superfícies A acima com A1–A9 Pass (ou N/A justificado) — SC-001
- [ ] Personas Marina / Bruno / Ana amostradas nas superfícies A do mapa
- [ ] SC-004 / SC-005 amostral (~375px; sem sombra/chip/cor ad hoc)
- [ ] Diff denylist vazio (AuthZ / stage / approval / fórmulas / fora-inventário)
- [ ] Contratos 009/012 **não** editados
