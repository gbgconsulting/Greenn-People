# Research: 9-box Interativa (Matriz de Talentos)

**Branch**: `006-ninebox-interativa` | **Date**: 2026-07-31

Pesquisa consolidada a partir de [spec.md](./spec.md), constituição, Freeze em [`docs/design-system.md`](../../docs/design-system.md), código atual de `apps/talent` e padrões HTMX (PDI/goals). Todos os itens do Technical Context foram resolvidos (sem `NEEDS CLARIFICATION` remanescente).

---

## R1 — HTMX vs JS para o drawer

- **Decision**: **HTMX** para abrir drawer (`hx-get` → `#matrix-drawer`), salvar potencial (`hx-post`) e toggle de visibilidade (`hx-post`), retornando **partials HTML**. JS mínimo separado só para: (a) focus trap / Escape / restore foco no drawer (espelhar `static/js/modal.js`), (b) drag-and-drop (R2). Sem fetch JSON / SPA.
- **Rationale**: Alinha à stack (DTL + HTMX), reutiliza CSRF global (`hx-headers` em `base.html`), toasts `HX-Trigger` → `showMessage` (padrão PDI), e entrega MVP utilizável sem DnD (FR-014). Modal centrado existente **não** atende painel lateral in-matrix.
- **Alternatives considered**:
  - **Só JS + fetch JSON** — rejeitado: introduz superfície tipo-API e foge do padrão do monólito.
  - **Reusar `#modal-container` / `components/modal.html`** — rejeitado: shell centrado; spec pede drawer lateral.
  - **Full page forms** — rejeitado: é o status quo (`classify` / toggle redirect); não cumpre FR-002.

---

## R2 — Drag: HTML5 nativo vs lib leve

- **Decision**: **HTML5 Drag and Drop nativo** em `static/js/ninebox_matrix.js` (nome sugerido). Zero biblioteca (SortableJS etc.). Handles/`draggable` **somente** quando `is_admin_viewer`; em `pointer: coarse` / viewport estreito, desabilitar DnD e manter drawer (FR-010).
- **Rationale**: Escopo limitado (mover card entre células da grade 3×3); Princípio I exige justificar deps — nativo é suficiente; não há precedente de lib DnD no repo.
- **Alternatives considered**:
  - **SortableJS / DnD Kit** — rejeitado: dependência externa sem ganho claro no grid fixo 3×3.
  - **Pointer events custom sem HTML5** — possível depois se touch precisar de drag; fora do MVP (drawer cobre mobile).
  - **Só drawer, sem drag** — rejeitado como estado final (US2 P2); aceitável como slice 1 sozinho.

---

## R3 — Partials HTML vs JSON

- **Decision**: Respostas **HTML partial** (`_drawer.html`, `_person_card.html`, `_cell.html` ou grade parcial). Atualização pós-save/move via `hx-swap` / `HX-Retarget` (célula origem + destino ou fragmento da grade). **Sem** endpoints JSON públicos; **sem** DRF.
- **Rationale**: Consistência com PDI/goals; autorização continua na view; evita duplicar serialização.
- **Alternatives considered**:
  - JSON + client render — rejeitado (OUT SPA).
  - Sempre full `matrix.html` swap — funciona mas mais pesado; preferir partials de célula/card; full matrix swap aceitável como fallback técnico se IDs de célula forem frágeis no slice 1.

---

## R4 — Política de drop incompatível (FR-004)

- **Decision**: **Snap por potencial pretendido** — no drop, o cliente/servidor considera **apenas** o `potencial` da célula-alvo (1–3). O desempenho da célula-alvo é **ignorado**. Persistência chama `upsert_classification` com esse potencial; a posição visual final é sempre `(desempenho_derivado, potencial_novo)` após recálculo de quadrante. Se o usuário soltou numa célula cuja faixa de desempenho ≠ desempenho derivado, o card **não** permanece na célula sob o cursor: faz snap para a célula coerente e exibe feedback PT-BR (“Só o potencial é alterado por arraste; o desempenho continua derivado da nota do líder.”). Se `potencial_novo == potencial_atual`, **noop** (sem write) + feedback opcional suave. Cancelamento (Esc / soltar fora) → zero persistência + restore visual.
- **Rationale**: Única política alinhada a “drag = só potencial” sem inventar desempenho; rejeição dura na célula errada obrigaria o admin a mirar a linha correta — snap reduz fricção e ainda comunica a regra.
- **Alternatives considered**:
  - **Rejeição dura** (reverter sempre se desempenho da célula ≠ derivado) — rejeitada como default: pior UX quando o admin mira a coluna de potencial certa na linha errada.
  - **Alterar desempenho para “caber” na célula** — proibido (FR-003/FR-004/FR-009).

---

## R5 — Mobile / touch (FR-010)

- **Decision**: Em viewports onde drag é inadequado (`max-width` típico mobile e/ou `pointer: coarse`), **não oferecer** handles de arraste (ou `draggable=false`). Calibração completa permanece via drawer. Matriz continua consultável (scroll).
- **Rationale**: Spec explicitamente aceita degradação de drag; evita DnD touch buggy.
- **Alternatives considered**: Polyfill touch-drag — fora de escopo / polish futuro.

---

## R6 — Página `classify` (FR-013)

- **Decision**: **Manter** `ClassifyTalentView` + rota `talent:classify` e link **secundário**/fallback (ex.: “Abrir classificação clássica” no drawer ou lista org). Caminho principal pós-006 = drawer in-matrix. **Não** deprecar nem remover nesta feature (OUT).
- **Rationale**: Spec Assumptions + OUT; classificar pessoa **ainda sem** `ClassificacaoTalento` na grade (matriz só lista classificados) continua coberto pelo fluxo clássico / links existentes (ex. lista de usuários).
- **Alternatives considered**:
  - Remover `classify` — OUT.
  - Expandir queryset da matriz para não-classificados no MVP — adiado; edge case da spec: drawer pode iniciar classificação **se** o produto já permitir; implementação preferida no slice 1 = drawer sobre cards existentes + `classify` para primeiro upsert. Slice posterior pode adicionar ação “classificar” no drawer sem migration.

---

## R7 — Toggle: service vs view inline

- **Decision**: Extrair **`toggle_classification_visibility(classificacao, admin) -> ClassificacaoTalento`** (ou equivalente) em `apps/talent/services/classification.py`, chamado por `ToggleVisibilityView` (compat redirect) e pela action HTMX do drawer. Continuar exigindo admin (`PermissionDenied` / mixin).
- **Rationale**: Hoje a lógica está só na view; drawer + testes unitários pedem reuso sem duplicar.
- **Alternatives considered**: Duplicar toggle na view HTMX — rejeitado (DRY / auditoria consistente).

---

## R8 — AuthZ: “líder” na spec vs `RequiresManagerOrAdminMixin`

- **Decision**: **Preservar** o gate atual da matriz: `LoginRequiredMixin` + `RequiresManagerOrAdminMixin` (somente `is_manager` **ou** `is_admin`). Escrita: somente `is_admin`. **Não** abrir a matriz para `is_leader` puro nesta feature (regressão T070 / nav atual). Na US3, “líder/gerente” = papéis que **já** acessam a matriz (gerente e admin em modo leitura; admin com escrita). Drawer read-only quando `not is_admin`.
- **Rationale**: Expandir acesso a líderes puros é mudança de produto de AuthZ fora do núcleo “matriz interativa”; spec Assumptions alinhadas ao comportamento atual de classify/toggle/matriz.
- **Alternatives considered**: Incluir `RequiresLeaderMixin` / líderes — rejeitado neste plan (escopo); se produto exigir depois, feature separada.

---

## R9 — Migrations

- **Decision**: **Zero migrations**. `ClassificacaoTalento` já possui `potencial`, `desempenho`, `quadrante`, `visivel_ao_colaborador`, FKs `PROTECT`, constraints 1–3.
- **Rationale**: Nenhum campo de negócio novo na spec; ordenação intra-célula / metadados de drag fora de escopo.
- **Alternatives considered**: Campos de “última calibração” / ordem — rejeitados (não pedidos).

---

## R10 — Freeze 004 / drawer canônico

- **Decision**: Consumir `button`, `badge_status`, `empty_state`, `input`/`form-control`, tokens emerald/slate. Introduzir shell de drawer lateral em `templates/talent/partials/` (ou `templates/components/drawer.html` se reutilizável). Documentar **padrão mínimo** em `docs/design-system.md` somente se o shell for canônico compartilhado — sem redesenhar sidebar/topbar/marca; sem Impeccable; sem polish amplo.
- **Rationale**: FR-012; Freeze já antecipa consumo pela 9-box interativa.
- **Alternatives considered**: Redesenhar shell — OUT.

---

## Resumo de decisões → contratos

| Tema | Artefato |
|---|---|
| Drawer HTMX open/save/toggle/refresh | [contracts/htmx-drawer-partials.md](./contracts/htmx-drawer-partials.md) |
| Drag potencial-only + snap + erros | [contracts/drag-persist.md](./contracts/drag-persist.md) |
| Admin write / manager read / colaborador gate / IDOR | [contracts/authz-scope.md](./contracts/authz-scope.md) |
| Teclado, foco, rótulos além da cor | [contracts/a11y-matrix-drawer.md](./contracts/a11y-matrix-drawer.md) |
