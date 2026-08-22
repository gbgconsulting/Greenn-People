# Contract: Non-Goals / Denylist (016)

**Feature**: `016-freeze-screen-conformity`  
**Fonte**: [spec.md](../spec.md) FR-002 / FR-014 + mandato Freeze do [plan.md](../plan.md)  
**Uso**: Qualquer PR/task que viole este contrato = **fora de escopo** / rejeitar.

---

## Declaração

Esta feature é **auditoria + remediação de conformidade visual** (apresentação).

**Teste de ouro**: desligar CSS/charts **não** deve mudar avanço de etapa, aprovação, notas calculadas, conjunto de usuários visíveis, open/close de ciclo, nem permissões.

**Teste Freeze**: se a UI precisar de cor, sombra, peso, componente, chart ou composição **ausente** de `docs/design-system.md` (exceto B1 já aprovada) → **ESCALATE / STOP**. Proibido adaptar, inventar ilha ou copiar Figma Verdee.

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|------|---------------------|
| AuthZ / escopo | Alterar `get_visible_users`, `ScopedObjectMixin`, mixins de papel, predicados, ampliar queryset “para a UI” |
| Máquina de estados | `stage.py` — `can_advance`, `advance_stage`, semântica de etapa |
| Abrir / fechar ciclo | `cycle.py` open/close; views open/close |
| Aprovação | `approval.py` |
| Fórmulas / mutators | `evaluation.py` mutators; `nota_final_lider`; `adherence.py` fórmula |
| Persistência | Models, migrations, campos novos de regra |
| Shell / auth | Reordenar nav; shell; login; `base_auth`; tipografia display fora do Freeze |
| Verdee / Figma | Adotar elementos do guia Figma Verdee |
| Charts inventados | Tipo fora do catálogo 009; barra HTML fake; série fictícia |
| Freeze reopen | Reabrir A/B/C/D; decisão visual nova além de B1 |
| Fora do inventário | Expectativas, metas, avaliações/PDI colaborador, minha classificação, listas de ciclo, objetivos, audit, notifications, escalas CRUD, `cargo_competencia_form` |
| Stack | SPA, DRF, lib nova de gráfico, Chart ≠ 4.5.1, plugin npm |
| Gold-plating | “Já que estamos aqui” em telas/contratos fora da spec |

### Paths sob vigilância (diff de comportamento = falha)

- `apps/accounts/services/scope.py`
- `apps/core/mixins.py` (semântica `ScopedObjectMixin`)
- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py`
- `apps/goals/services/approval.py`
- Mutators em `apps/reviews/services/evaluation.py`
- `apps/dashboard/services/adherence.py` (`compute_adherence`)
- `templates/accounts/**` / auth surfaces
- `templates/components/nav_menu.html` (grupos/ordem)
- Contratos 009/012 (não editar para “facilitar” 016)

---

## Permitido (leitura / apresentação)

- Templates e partials na [path-allowlist.md](./path-allowlist.md)
- Correção de token na fonte `pagination.html`
- Documentar B1 em `docs/design-system.md` (+ `input.css` se classe documentada)
- Ajuste presentation-only em `chart_payloads.py` / `dashboard_charts.js` / `_chart_block` se auditoria de progresso/painel A exigir — **sem** mudar significado de negócio
- Testes de superfície + regressão stage/scope/reject **sem** mudar regras

---

## Relação com contratos legados

| Contrato | Status nesta feature |
|----------|----------------------|
| `009` chart-catalog / managerial-panel / cycle-managerial-detail | **Intactos** — consumir |
| `012` density-history-empty | **Intacto** — consumir |
| `016` table-frame-listas-b | **Única** extensão documental prevista |

---

## Confirmação T001 (2026-08-21)

Inventário e denylist **fechados** — cruzados com [path-allowlist.md](./path-allowlist.md) e inventários A/B da [spec.md](../spec.md).

- [x] Domínio intocável: `scope.py`, `ScopedObjectMixin`, `stage.py`, `cycle.py`, `approval.py`, mutators/`adherence` fórmula, models/migrations
- [x] Verdee / shell / auth / nav / login / `base_auth` = proibidos
- [x] Fora do inventário A/B (mesmo que existam templates): listas/forms de ciclo, objetivos, escalas CRUD, `cargo_competencia_form`, `reassign_reports`, classify / minha classificação, expectativas/metas/PDI/avaliações colaborador, audit, notifications
- [x] Freeze reopen / charts inventados / stack SPA-DRF-lib nova = proibidos
- [x] Permitido = allowlist presentation-only + B1 no DS + testes de superfície sem mudar regras

**Regra operacional**: diff de comportamento em path sob vigilância ou tela fora do inventário = **rejeitar PR/task**.
