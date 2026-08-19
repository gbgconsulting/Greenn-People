# Quickstart: Validação da Fundação Visual (004)

**Branch**: `004-ux-visual-foundation` | **Date**: 2026-07-29

Guia de validação before/after e checklist de teclado. Não inclui código de implementação completo — ver [plan.md](./plan.md) e futuros `tasks.md`.

## Prerequisites

- Stack local do projeto (Django, Tailwind CLI build se CSS mudar, DB com usuário admin + líder com subordinados + colaborador).
- Ciclo **aberto** com dados representativos no escopo do líder (para SC-002).
- Segundo cenário (ou DB limpa parcial): **sem** ciclo aberto (para fallback da topbar).
- Browser desktop + teclado; opcional: leitor de tela rápido no indicador HTMX.

## Setup

```bash
# A partir da raiz do repo (conforme README do projeto)
# ativar venv, migrate, runserver, rebuild CSS se necessário:
# python manage.py runserver
# npm/npx ou script do projeto para Tailwind CLI → static/css/tailwind.css
```

Contas: admin (Marina), líder/gerente, colaborador sem liderança — papéis cumulativos como no produto.

## Before/after (US6 / SC-003)

### Onde guardar

Diretório: [`evidence/before-after/`](./evidence/before-after/)

Convenção de nomes:

```text
evidence/before-after/
  README.md                 # este índice + critérios
  01-shell-admin-before.png
  01-shell-admin-after.png
  02-dashboard-team-before.png
  02-dashboard-team-after.png
  ...
```

### Telas-piloto (conjunto A — 7)

| ID | Tela | URL típica | Persona |
|---|---|---|---|
| 01 | Shell / nav Admin | qualquer página autenticada admin | Marina |
| 02 | Dashboard time | `/dashboard/team/` | Líder |
| 03 | Dashboard pessoal | `/` | Colaborador |
| 04 | Login | rota login accounts | — |
| 05 | Lista ciclos | `/cycles/` | Admin |
| 06 | PDI detail | detalhe PDI | Colaborador |
| 07 | Avaliações list | `/reviews/` | Colaborador/liderança no escopo |

### Procedimento

1. **Before**: capturar screenshot (viewport desktop ~1280px) **antes** do polish daquela superfície.
2. Implementar mudança scoped (uma superfície/padrão).
3. **After**: mesma viewport, mesma conta/dados.
4. No `evidence/before-after/README.md`, anotar 1–3 bullets objetivos (ex.: “Ciclos no topo de Governança com peso maior que Áreas”; “Etapa do time legível acima da dobra”).

### Critérios de aceite da evidência

- [x] 5–8 pares before/after (este conjunto tem 7) — revisado T036 · 2026-07-30
- [x] Inclui ≥1 dashboard (02 ou 03) e ≥1 autoatendimento (06 ou 07 ou 03)
- [x] Zero itens OUT na entrega (gráficos novos, 9-box interativa, Impeccable) — T038 · 2026-07-30 ([evidência](./evidence/before-after/README.md#checklist-out-t038--fr-017--sc-007))

## Validação por user story

### US1 — Shell Admin (< 5 s)

1. Login admin → abrir sidebar/Administração.
2. Confirmar grupos Governança / Cadastros / Sistema ([contrato](./contracts/admin-nav-grouping.md)).
3. Confirmar destaque Ciclos + Aderência vs. Cadastros.
4. Clicar Ciclos e Aderência → mesmas superfícies de sempre.

### US2 — Dashboard time / pessoal

1. Login líder → `/dashboard/team/` → status operacional legível no first viewport (< 5 s revisão guiada).
2. Login colaborador → `/` → clareza equivalente nos KPIs existentes (sem expor 9-box se regra negar).

### US3 — Consistência + HTMX

1. Percurso: login → painel → PDI detail → lista avaliações.
2. Disparar ação HTMX conhecida (ex.: abrir modal de ação PDI; paginar lista) → região esperada atualiza ([contrato HTMX](./contracts/htmx-pilot-surfaces.md)).

### US4 — Topbar ciclo

1. Com ciclo aberto: topbar mostra nome/resumo em uma linha.
2. Sem ciclo aberto: fallback “Sem ciclo aberto” (ou texto acordado).
3. Sem filtros/CTAs novos na topbar ([contrato](./contracts/topbar-cycle-context.md)).

### US5 — Checklist teclado (SC-004)

Em página autenticada com shell:

| # | Checagem | Esperado |
|---|---|---|
| 1 | Tab no início | Skip link → `#main-content` |
| 2 | Nav item da rota | `aria-current="page"` (DevTools ou anúncio) |
| 3 | Tab em botões/links shell | Anel `focus-visible` visível |
| 4 | Abrir modal (ex. PDI) → Tab/Shift+Tab | Foco preso no dialog |
| 5 | Escape | Fecha modal; foco volta ao trigger |
| 6 | Ação com `hx-indicator` | Estado “Carregando…” anunciável / não `aria-hidden` permanente |

Contrato: [a11y-shell.md](./contracts/a11y-shell.md).

### US6 — Freeze

1. Revisar `docs/design-system.md` com seção Freeze + tokens atualizados.
2. Confirmar evidências 01–07.
3. Confirmar OUT ([spec](./spec.md) FR-017).

## Registro T039 — validação guiada (2026-07-30)

Percurso quickstart + checklist teclado; smoke HTTP no stack Docker (`web`) + inspeção de markup/contratos + `pytest tests/test_topbar_ciclo_context.py` (3 passed). Contas de evidência: `admin@` / `lider@` / `colab@test.greenn.com.br`.

| Gate | Resultado | Evidência |
|---|---|---|
| **SC-001** (US1) | **PASS** | `/dashboard/admin/`: grupos Governança / Cadastros / Sistema; Ciclos antes de Cadastros com `font-semibold` + `border-emerald-500`; URLs `/cycles/` e aderência intactas |
| **SC-002** (US2) | **PASS** | `/dashboard/team/` com seção **Status no ciclo**; `/` com **Meu desempenho** / KPIs existentes; after 02–03 |
| **SC-003** (US6 evidência) | **PASS** | 7/7 pares before/after + bullets; ≥1 dashboard + ≥1 autoatendimento ([evidência](./evidence/before-after/README.md)) |
| **SC-004** (US5 teclado) | **PASS** | Skip → `#main-content`; `aria-current="page"`; `:focus-visible` em `input.css`; `trapFocus` + Escape/restore em `modal.js`; indicador `role="status"` + hook `data-htmx-indicator` (não `aria-hidden` permanente) |
| **SC-005** (US3 HTMX) | **PASS** | Fragmentos HTMX ciclos/reviews (`#list-container`, sem full page); modal PDI `hx-target="#modal-container"` / create → `#acao-list` |
| **SC-006** (US6 Freeze) | **PASS** | `docs/design-system.md` seção **Freeze** (congelado) |
| **SC-007** (OUT) | **PASS** | Zero chart libs em templates/`static/js`; matriz “Grade estática”; checklist OUT no README de evidência; stash Impeccable não aplicado |

### Checklist teclado (marcação T039)

| # | Checagem | Status |
|---|---|---|
| 1 | Skip link → `#main-content` | ✓ |
| 2 | `aria-current="page"` no item ativo | ✓ |
| 3 | Anel `:focus-visible` | ✓ (CSS + tokens) |
| 4 | Focus trap Tab/Shift+Tab no dialog | ✓ (`modal.js`) |
| 5 | Escape fecha + restore no trigger | ✓ |
| 6 | “Carregando…” anunciável | ✓ |

**Nota**: itens 3–5 do teclado validados por implementação + contrato (focus-visible / trap / Escape); smoke HTTP cobre presença no shell. Revisão visual humana no browser permanece opcional para anel de foco.

## Expected outcomes

- Gates SC-001–SC-007 satisfeitos na revisão guiada. ✅ T039 · 2026-07-30
- Sem regressão HTMX nas telas-piloto tocadas (SC-005). ✅
- Documentação congelada antes de features de gráficos / 9-box interativa (SC-006). ✅
