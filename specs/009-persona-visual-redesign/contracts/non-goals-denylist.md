# Contract: Non-Goals / Denylist de lógica (FR-012 / FR-014)

**Feature**: `009-persona-visual-redesign`  
**Fonte**: [spec.md](../spec.md) FR-012/FR-014 + invariante do plano  
**Uso**: Qualquer PR/task que viole este contrato = **fora de escopo** / rejeitar.

---

## Declaração

Esta feature é **apresentação gerencial + composição leve de dados já autorizados**.

**Teste de ouro**: desligar CSS/charts/painel **não** deve mudar avanço de etapa, aprovação/reprovação, notas calculadas, conjunto de usuários visíveis, nem política de abrir/fechar ciclo.

### Confirmação T001 (2026-08-11)

- [x] Declaração = apresentação gerencial + composição leve de dados já autorizados
- [x] Denylist espelha FR-012 / FR-014 e paths sob vigilância batem com `path-allowlist.md`
- [x] Nenhuma zona de domínio (stage/approval/fórmulas/AuthZ/models/migrations) marcada como permitida

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|------|---------------------|
| Máquina de estados | `can_advance`, `advance_stage`, ordem/semântica de etapa |
| Aprovação / reprovação | `approve_*` / `reject_*`, reabertura, mid-cycle |
| Fórmulas | `nota_final_lider`, normalização, % aderência, 9-box |
| AuthZ / escopo | Alterar `get_visible_users`, `ScopedObjectMixin`, papéis |
| Persistência de regra | Models, migrations, campos novos de regra |
| Métricas inventadas | “Saúde do ciclo” ou scores sem definição de produto |
| Stack | SPA, DRF, nova lib de gráficos, Chart ≠ 4.5.1 |
| Shell / auth | Reabrir nav IA, login, tipografia display/UI além A/B/C |
| Async prematuro | Nova task Celery sem evidência de peso |

### Paths sob vigilância

- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py`
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py`
- Mutators em `apps/reviews/services/evaluation.py`
- `apps/dashboard/services/adherence.py` (fórmula/`compute_adherence`)

---

## Permitido (leitura / apresentação)

- Ampliar tipos Chart.js no JS local e payloads compatíveis
- Compor Counts (cobertura, rankings) a partir de QS já escopado
- `CicloDetailView` admin-only + template painel
- Atualizar Freeze A/B/C e `input.css`
- Polish P2/P3 de tipografia/table-frame/empty/CTA copy alinhada a 008
