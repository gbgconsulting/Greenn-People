# Research: Conformidade visual ao Freeze v2 (016)

**Branch**: `016-freeze-screen-conformity`  
**Date**: 2026-08-21  
**Spec**: [spec.md](./spec.md) (Clarifications 2026-08-21 + decisão B1 = fechadas)

Pesquisa consolidada a partir da spec, Constituição, `docs/design-system.md`, contratos 009/012, e mapeamento dos templates atuais no monólito. Todos os itens do Technical Context resolvidos — **zero** `NEEDS CLARIFICATION` remanescente.

Contratos visuais 009/012 **não se reabrem**. Única extensão documental: B1 ([contracts/table-frame-listas-b.md](./contracts/table-frame-listas-b.md)).

---

## R1 — Mapa template ↔ tela do inventário

- **Decision**: Inventário fechado mapeado para templates existentes (sem rota nova):

### Category A

| Tela (spec) | Template(s) | Persona |
|---|---|---|
| Painel admin | `templates/dashboard/admin.html` | Admin RH |
| Painel do time | `templates/dashboard/team.html` + `team_list_partial.html` | Gestor |
| Aderência | `templates/dashboard/adherence.html` + `adherence_list_partial.html` | Gestor |
| Estrutura | `templates/dashboard/structure.html` | Gestor |
| Matriz de talentos | `templates/talent/matrix.html` + `partials/_cell.html`, `_drawer.html`, `_person_card.html` | Admin / Gestor (AuthZ vigente) |
| Ciclo (detalhe) | `templates/cycles/ciclo_detail.html` | Admin RH |
| Meu painel | `templates/dashboard/personal.html` | Colaborador |

Partials compartilhados A (reuso, não “telas novas”): `_chart_block.html`, `_ciclo_selector.html`, `_visao_toggle.html`.

### Category B

| Entidade | Lista | Form | Colunas (lista) | Cap B1 |
|---|---|---|---|---|
| Áreas | `area_list.html` + `area_list_partial.html` | `area_form.html` | 4 | `max-w-5xl` |
| Cargos | `cargo_list.html` + `cargo_list_partial.html` | `cargo_form.html` | 4 | `max-w-5xl` |
| Usuários | `user_list.html` + `user_list_partial.html` | `user_form.html` | 7 | `max-w-6xl` |
| Usuários pendentes | `user_pending_list.html` + `user_pending_list_partial.html` | — | correlata do CTA em Usuários | mesma regra B1 por nº de cols |
| Competências | `competencia_list.html` + `competencia_list_partial.html` | `competencia_form.html` | 4 | `max-w-5xl` |

Forms B já usam `mx-auto max-w-lg` — **manter** (cap de form; não unificar com lista).

- **Rationale**: FR-001 / inventário fechado / mapa persona; evita gold-plating em telas 009-P2 ou CRUDs futuros.
- **Alternatives considered**:
  - Incluir listas de ciclo / escala / audit / notifications — rejeitado (clarification + FR-014).
  - Incluir `cargo_competencia_form` / `escala_*` — rejeitado (não inseparáveis do form de competência nesta rodada; STOP se produto exigir).

---

## R2 — Progresso fake do ciclo (P1): onde está e o que remediar

- **Decision**: Superfícies obrigatórias = **painel admin** e **detalhe de ciclo**. Estado atual no código:

  | Superfície | Markup atual | Payload |
  |---|---|---|
  | `admin.html` | Já inclui `dashboard/_chart_block.html` com `chart_ciclo_progresso` | `AdminDashboardView._chart_ciclo_progresso` → `categorical_counts_payload(..., highlight_max=True)`, `type=bar_horizontal` |
  | `ciclo_detail.html` | Idem `_chart_block` | `CicloDetailView._chart_ciclo_progresso` (espelho presentation) |

  **Não** há barra `style="width:…"` residual nesses dois templates hoje. A remediação P1 desta feature é **auditoria + conformidade Freeze A/D**, não inventar outro chart:

  1. Confirmar visual = barras horizontais mono teal/cyan; amber **só** no gargalo (`highlight_max`).
  2. Confirmar empty honesto (kinds Freeze D) — sem série inventada.
  3. Remover qualquer markup ad hoc residual se a auditoria encontrar (ou regressão visual em JS/`_chart_block`).
  4. **MUST NOT** mudar significado de counts/etapas.

  Arquivo `patch-progresso-etapas-ciclo.md` **ausente** — não bloquear; Freeze A/D + contratos 009/012 bastam.

- **Rationale**: Spec US1 / FR-004 / FR-005 / SC-003; clarification “sem depender de patch ausente”.
- **Alternatives considered**:
  - Assumir “já está ok, pular US1” — rejeitado (SC-003 exige inspeção; regressões recentes violaram Freeze).
  - Reintroduzir barra HTML fake “mais simples” — rejeitado (FR-004).

---

## R3 — Include canônico de paginação

- **Decision**: Fonte única = `templates/components/pagination.html`. Já reusado por listas B (área/cargo/user/competência) e várias A (team/adherence/ciclo list — lista de ciclo **fora** do inventário de remediação, mas o include é compartilhado).

  Violação conhecida na fonte: links Anterior/Próxima usam classes ad hoc (`rounded-lg border border-slate-200…`) em vez de `components/button.html` / tokens Freeze.

  Correção US4: **somente** em `pagination.html` (e rebuild CSS se necessário). Telas B consomem o include — proibido segunda implementação.

  Busca/filtros: `input` / `.form-control` + `button` canônicos onde já existirem; não criar componente novo.

- **Rationale**: FR-012 / US4.
- **Alternatives considered**: Corrigir por tela — rejeitado (proliferação). Novo partial de paginação — rejeitado.

---

## R4 — Proporções default B1 a registrar no DS

- **Decision**: Tokens concretos (Tailwind já no monólito) para documentar em `docs/design-system.md` § Table-frame · listas de cadastro:

  | Caso | Container lista | Tabela | Ações |
  |---|---|---|---|
  | ≤ 4 colunas | `mx-auto w-full max-w-5xl` | `.table-frame` + `table` com `table-fixed w-full` + `<colgroup>` proporcional | `td/th` `text-right`; separador leve `·` ou espaço muted — **proibido** `\|` |
  | > 4 colunas | `mx-auto w-full max-w-6xl` | idem | idem |
  | Form B (mesma entidade) | `mx-auto max-w-lg` (já vigente) | N/A | N/A |
  | Category A | **sem** este cap (full-bleed no conteúdo do painel) | drill `.table-frame` sem cap B1 | — |

  Defaults de colgroup sugeridos (ajustáveis por tela sem nova decisão de produto, desde que nome não “coma” ações):

  | Entidade | Colunas | Proporção inicial |
  |---|---|---|
  | Áreas / Cargos / Competências | 4 | nome ~40% · meta ~25% · status ~15% · ações ~20% |
  | Usuários | 7 | nome+email maiores; ações fixas ~12–15% à direita |

  Mobile ~375px: overflow-x **dentro** de `.table-frame` (já no chrome Freeze); página sem bleed.

- **Rationale**: Spec B1 / FR-015 / FR-016 / FR-017 / Assumptions (`max-w-5xl` / `max-w-6xl`, `table-fixed`, `colgroup`).
- **Alternatives considered**:
  - Unificar cap lista↔form — rejeitado (B1).
  - Cap em A — rejeitado (A full-bleed).
  - Inventar breakpoints novos fora do Tailwind do DS — rejeitado (ESCALATE).

---

## R5 — Componentes canônicos only + política ESCALATE

- **Decision**: Remediação só via includes: `button`, `input` / `.form-control`, `card`, `badge_status`, `empty_state`, `.table-frame`, `_chart_block`, `pagination`. HTML solto equivalente = violação.

  Se faltar token/componente/tipo de chart/composição no Freeze **e** não for B1: **STOP** → escalar produto. Não copiar Verdee; não “aproximar”.

- **Rationale**: Mandato não-negociável + FR-002.
- **Alternatives considered**: “Adaptar Figma” — rejeitado (FR-014).

---

## R6 — AuthZ / domínio intactos

- **Decision**: Zero alteração semântica em:

  - `apps/accounts/services/scope.py` / `get_visible_users`
  - `ScopedObjectMixin` / mixins Admin* / Leader*
  - `stage.py`, `cycle.py` (open/close), `approval.py`, mutators `evaluation.py`, fórmula `adherence.py`

  Views allowlisted só podem mudar **markup context** de apresentação (ex.: flags de UI) sem ampliar QS.

- **Rationale**: Constitution II + FR implícito de apresentação; teste de ouro do denylist.
- **Alternatives considered**: “Facilitar empty escondendo dado” no front — rejeitado.

---

## R7 — Contratos 009/012 intactos

- **Decision**: Reusar como referência de aceite visual A:

  - `specs/009-persona-visual-redesign/contracts/chart-catalog.md`
  - `specs/009-persona-visual-redesign/contracts/managerial-panel.md`
  - `specs/009-persona-visual-redesign/contracts/cycle-managerial-detail.md`
  - `specs/012-gerencial-historico-legado/contracts/density-history-empty.md`

  Esta feature **não** edita esses arquivos. Só acrescenta contratos 016 (allowlist/denylist/B1).

- **Rationale**: Spec Dependencies + SC-006.
- **Alternatives considered**: Reabrir catálogo de charts — rejeitado.

---

## Resolução do Technical Context

| Item | Resolução |
|---|---|
| Language/stack | Django 6.0.7 + DTL/HTMX/Tailwind; Chart.js 4.5.1 |
| Storage | N/A schema — zero migrations |
| Testing | pytest regressão domínio + quickstart visual por persona |
| Scope | Inventário R1 + allowlist |
| Progresso fake | R2 — audit admin + ciclo_detail |
| Paginação | R3 — `components/pagination.html` |
| B1 proporções | R4 — `max-w-5xl` / `max-w-6xl` + `table-fixed` |
| Freeze gap | R5 — ESCALATE / STOP |
| AuthZ | R6 — intocável |
