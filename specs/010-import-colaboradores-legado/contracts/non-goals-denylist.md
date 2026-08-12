# Contract: Non-Goals / Denylist de Domínio

**Feature**: `010-import-colaboradores-legado`  
**Fonte**: [spec.md](../spec.md) FR-016/FR-017 + [data/legado-solides/README.md](../../../data/legado-solides/README.md) § Denylist  
**Padrão**: espelha [spec 009](../../009-persona-visual-redesign/contracts/non-goals-denylist.md)  
**Data**: 2026-08-12

---

## Declaração

Esta feature **persiste histórico organizacional** (colaboradores, áreas, cargos faltantes, hierarquia) via comando operacional one-shot.

**Teste de ouro**: executar `importar_colaboradores` **não** deve alterar avanço de etapa, aprovação/reprovação, notas calculadas, aderência, conjunto de usuários visíveis (regras AuthZ), nem mutar avaliações/PDI existentes.

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|---|---|
| Máquina de estados | `can_advance`, `advance_stage`, ordem/semântica de etapa |
| Ciclos | Comportamento open/close em `cycle.py` |
| Aprovação / reprovação | `approve_*` / `reject_*`, reabertura, mid-cycle |
| Fórmulas | `nota_final_lider`, normalização, % aderência, 9-box |
| AuthZ / escopo | Alterar `get_visible_users`, `ScopedObjectMixin`, `scope.py` |
| Avaliações na import colaboradores | Mutar `Avaliacao.etapa`, `concluida`, `nota_final_*` |
| Snapshots | `peso_utilizado`, `nivel_esperado_utilizado` write-once |
| Persistência de regra extra | Campos novos além de `solides_id`; PII |
| UI / stack | Views upload, DRF, Celery tasks novas |
| Simulação de ciclo | POSTs de ciclo / abertura de ciclo ativo |

### Paths sob vigilância (diff MUST be empty)

- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py`
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py`
- `apps/reviews/services/evaluation.py` (+ mutators de nota)
- `apps/dashboard/services/adherence.py`

---

## Permitido

| Ação | Escopo |
|---|---|
| Migration aditiva `solides_id` | Cinco models (allowlist) |
| CRUD organizacional via import | Area, Cargo (faltantes), CustomUser |
| Set `email_confirmado_em` na importação | Decisão #21 |
| Set `line_manager` com validação acíclica | RF-04.1 via model `clean()` |
| Relatório CLI mascarado | stdout / `--report-file` |
| Reuso read-only `normalize.py` | spec 003 |

---

## Gate de regressão (obrigatório)

Antes de merge:

```bash
# Diff denylist = vazio (comparar contra allowlist em model-allowlist.md)
git diff main -- apps/cycles/services/stage.py apps/cycles/services/cycle.py \
  apps/goals/services/approval.py apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py apps/dashboard/services/adherence.py

pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q
pytest tests/test_import_colaboradores_legado.py -q
```

Qualquer diff não justificado em path da denylist = **FAIL**.

---

## Checklist de revisão de PR

- [ ] Nenhum arquivo denylist alterado
- [ ] `scope.py` diff vazio
- [ ] Sem alteração de `Avaliacao.etapa` / snapshots
- [ ] Sem UI/DRF/Celery
- [ ] Testes CI não referenciam `raw/`
- [ ] Relatório sem PII completa
