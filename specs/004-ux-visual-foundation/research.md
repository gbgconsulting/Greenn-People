# Research: Fundação Visual e UX Estável

**Branch**: `004-ux-visual-foundation` | **Date**: 2026-07-29

Pesquisa consolidada a partir de [spec.md](./spec.md), constituição, `docs/design-system.md`, shell atual (`base.html`, `nav_menu.html`, `topbar.html`, `modal.js`, `htmx_indicator.html`) e dashboards. Todos os itens do Technical Context foram resolvidos (sem `NEEDS CLARIFICATION` remanescente).

---

## R1 — Baseline e WIP Impeccable (OUT)

- **Decision**: Baseline = estado operacional em `development` / branch desta feature. **Não** reaplicar, mergear nem usar como dependência qualquer WIP Impeccable estacionado. Telas-piloto partem dos templates atuais no repo.
- **Rationale**: FR-017; Assumptions da spec; evita churn visual sem ganho perceptível.
- **Alternatives considered**:
  - Cherry-pick Impeccable — rejeitado (escopo OUT explícito).
  - Redesign de marca — rejeitado (FR-006: visual incumbente).

---

## R2 — Onde vivem tokens / freeze (docs vs DESIGN.md)

- **Decision**: Fonte da verdade = [`docs/design-system.md`](../../docs/design-system.md), alinhada a tokens CSS em [`static/src/input.css`](../../static/src/input.css) e componentes em `templates/components/`. Expandir a doc com hierarquia shell, badges, empty states, KPI/cards, focus-visible e regra de freeze. **Não** criar `DESIGN.md` na raiz nesta feature.
- **Rationale**: Já existe canal de design system no projeto; FR-007 permite `DESIGN.md` **e/ou** docs existentes — escolha única evita docs vs código divergentes. Tensão docs↔código mitiga-se atualizando **ambos** na mesma PR de freeze (utilitários/comentários em `input.css` + tabela em `docs/design-system.md`).
- **Alternatives considered**:
  - `DESIGN.md` na raiz — rejeitado (duplicação; não há exigência externa ativa).
  - Dual (`DESIGN.md` índice + docs) — rejeitado nesta feature por overhead sem benefício.
  - Tokens só em CSS sem doc — rejeitado (SC-006 exige freeze documentado).

---

## R3 — Agrupamento do shell Admin (Governança / Cadastros / Sistema)

- **Decision**: Reorganizar **apenas** o bloco `{% if user.is_admin %}` em [`templates/components/nav_menu.html`](../../templates/components/nav_menu.html) em três subgrupos com progressive disclosure (cabeçalhos + listas; no mobile o mesmo HTML via include). URLs e permissões **inalteradas**.

| Grupo | Itens (URLs existentes) | Ênfase |
|---|---|---|
| **Governança** | Ciclos; Aderência; Painel admin; Estrutura / Matriz (quando o template já os injeta no bloco admin) | Ciclos e Aderência com peso tipográfico / posição / classe documentada maior que Cadastros |
| **Cadastros** | Áreas; Cargos; Usuários; Competências | Estilo de item padrão |
| **Sistema** | Auditoria; Notificações | Estilo de item padrão (secundário) |

Seções Colaborador / Líder / Gerente fora do bloco Admin permanecem; Aderência sob Gerente não é removida (papéis cumulativos).

- **Rationale**: US1 / FR-003 / FR-004; máximo impacto com mudança scoped; UI não autoriza (FR-014).
- **Alternatives considered**:
  - Nested `<details>` multi-nível escondendo Governança — rejeitado (edge case mobile; “não mais de um nível desnecessário”).
  - Menu JS SPA — rejeitado (stack + OUT).
  - Mover Aderência só para Admin e tirar de Gerente — rejeitado (fora do escopo; muda descoberta de papel).

---

## R4 — Contexto de ciclo na topbar (sem API nova)

- **Decision**: Adicionar context processor Django em `apps/core` (ex.: `apps.core.context_processors.ciclo_aberto`) registrado em `TEMPLATES['OPTIONS']['context_processors']`, chamando `get_open_ciclo()` já existente (`apps.goals.forms.get_open_ciclo`). [`topbar.html`](../../templates/components/topbar.html) renderiza uma linha resumida: nome do ciclo aberto **ou** fallback “Sem ciclo aberto”. Sem filtros, CTAs ou endpoints novos.
- **Rationale**: FR-005; reutiliza query já usada em views; context processor é nativo Django (Princípio I); topbar incluída em `base.html` fica coberta em toda sessão autenticada.
- **Alternatives considered**:
  - Passar `ciclo_aberto` só em views — rejeitado: topbar quebraria inconsistência em páginas que hoje não injetam.
  - Inclusion tag com query — aceitável, mas processor centraliza e evita incluir tag em todo layout.
  - Endpoint HTMX para “ciclo atual” — rejeitado (API desnecessária; FR-001/017).
  - Mover `get_open_ciclo` para `cycles` agora — melhoria de domínio desejável depois; **fora do caminho crítico** desta feature (evitar refactor amplo).

**Nota de performance**: um `Ciclo.objects.filter(status=ABERTO).order_by('-data_inicio').first()` por request autenticado é aceitável; sem Celery (não é agregado pesado — Princípio VI N/A).

---

## R5 — Hierarquia escaneável nos dashboards (sem novos KPIs)

- **Decision**: Polish tipográfico/espacial/badges nos indicadores **já renderizados** em dashboards-piloto (prioridade: `team` + espelho de clareza em `personal`). Reordenar/ agrupar first viewport; empty states via `empty_state.html`. **Proibido**: novos gráficos, novas métricas, mudanças de cálculo ou queries agregadas pesadas síncronas.
- **Rationale**: US2 / FR-001 / FR-017 / SC-002.
- **Alternatives considered**:
  - Cards de KPI novos calculados na request — rejeitado (métricas novas + risco Princípio VI).
  - Chart.js / libs — rejeitado (OUT + constituição).

---

## R6 — Telas-piloto e before/after

- **Decision**: Conjunto piloto **A** (7 telas) para before/after desde o início:

| # | Tela-piloto | Path / artefato típico |
|---|---|---|
| 1 | Shell / nav Admin | qualquer sessão admin + sidebar |
| 2 | Dashboard time | `/dashboard/team/` |
| 3 | Dashboard pessoal | `/` |
| 4 | Login | `/accounts/login/` (ou rota accounts vigente) |
| 5 | Lista de ciclos | `/cycles/` |
| 6 | PDI detail | detalhe PDI no escopo |
| 7 | Avaliações list | `/reviews/` |

Evidências em [`evidence/before-after/`](./evidence/before-after/) (screenshots + `README.md` com critérios objetivos). Captura **before** antes do polish de cada superfície (ordem US).

- **Rationale**: US6 / SC-003 (5–8; inclui dashboard + autoatendimento).
- **Alternatives considered**: Seleção adiada à implementação — rejeitado pelo pedido de planejar captura cedo. Conjunto B (admin dash + modal) — válido, mas A cobre melhor US2 pessoal + time.

---

## R7 — Consistência login / PDI / avaliações / formulários + HTMX

- **Decision**: Aplicar tokens/padrões dos components existentes (`button`, `input`, `badge_status`, `empty_state`, `card`, `table-frame`) nas telas-piloto P2; preservar `hx-target` / `hx-swap` / `#list-container` / `#modal-container`. Sem mudança de URLs ou payloads.
- **Rationale**: US3 / FR-015 / FR-016.
- **Alternatives considered**: Extrair design system React — rejeitado. Refactor massivo de todos os templates — rejeitado (FR-016).

---

## R8 — A11y mínima sem libs novas

- **Decision**:
  1. Skip link no início de `body` → `#main-content` (id em `<main>`).
  2. `aria-current="page"` no item ativo de `nav_menu.html` (além das classes visuais).
  3. `:focus-visible` utilitário/base em `input.css` (Tailwind/`@layer base`) nos controles do shell e componentes.
  4. Focus trap Tab no modal: estender [`static/js/modal.js`](../../static/js/modal.js) (já tem focus inicial, Escape, restore) — **sem** lib externa.
  5. Indicador HTMX: ajustar [`htmx_indicator.html`](../../templates/components/htmx_indicator.html) para rótulo acessível coerente quando visível (hoje `aria-hidden="true"` fixo conflita com `role="status"`); preferir JS mínimo + `aria-busy`/`aria-hidden` dinâmico ou texto `sr-only` sempre anunciável via `aria-live` quando `.htmx-request`.
- **Rationale**: US5 / FR-009–013; Princípio I.
- **Alternatives considered**: focus-trap npm / Alpine — rejeitado sem necessidade. axe CI — opcional depois; SC-004 é checklist manual teclado.

---

## R9 — Stack e escopo de segurança

- **Decision**: Django + DTL + HTMX + Tailwind CLI apenas. Escopo/`ScopedObjectMixin`/flags `is_admin|is_leader|is_manager` inalterados. UI não autoriza.
- **Rationale**: Constituição I–II; FR-014; FR-017.
- **Alternatives considered**: DRF/SPA, Chart libs — rejeitados (gate).

---

## R10 — Ordem de implementação sugerida (P1→P2)

Alinhada ao pedido do plan (não redefine prioridades da spec; operacionaliza dependências):

1. Evidência **before** das 7 telas (US6 scaffolding)
2. Shell Admin progressive disclosure + destaque Ciclos/Aderência (US1)
3. Hierarquia dashboards time + pessoal (US2)
4. Documentar tokens parciais → freeze ao final (US6)
5. Consistência login/PDI/avaliações/forms + HTMX check (US3)
6. Topbar contexto ciclo (US4)
7. A11y shell/modal/indicator (US5)
8. Captura **after** + freeze em `docs/design-system.md` (US6)

Dependência fraca: tokens documentados podem começar após US1–2 (padrões descobertos no polish); freeze só no fim.

---

## OUT explícito (confirmado na research)

- Gráficos novos; 9-box interativa; SPA/DRF; novas métricas/cálculos; WIP Impeccable; landing/marketing redesign.
