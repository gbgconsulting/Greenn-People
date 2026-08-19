# Contract: Non-Goals / Denylist de Domínio

**Feature**: `011-import-ciclos-avaliacoes-legado`  
**Fonte**: [spec.md](../spec.md) FR-010/FR-012/FR-017/FR-020 + [data/legado-solides/README.md](../../../data/legado-solides/README.md) § Denylist  
**Padrão**: espelha [spec 010](../../010-import-colaboradores-legado/contracts/non-goals-denylist.md)  
**Data**: 2026-08-13

---

## Declaração

Esta feature **persiste histórico** de ciclos encerrados e cabeçalhos de avaliação via comando operacional one-shot.

**Teste de ouro**: executar `importar_ciclos_avaliacoes` **não** deve avançar etapa via máquina de estados, abrir/fechar ciclo via serviços de domínio, aprovar/reprovar itens, calcular notas/aderência, alterar AuthZ/escopo, nem preencher notas/competências/Feedback/PDI.

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|---|---|
| Máquina de estados | `can_advance`, `advance_stage`, ordem/semântica de etapa via `stage.py` |
| Ciclos (serviços) | `open_cycle`, `close_cycle` e qualquer mutação comportamental em `cycle.py` |
| Aprovação / reprovação | `approve_*` / `reject_*`, reabertura mid-cycle |
| Fórmulas | `nota_final_*`, normalização, % aderência, 9-box (`evaluation.py`, `adherence.py`) |
| AuthZ / escopo | Alterar `get_visible_users`, `ScopedObjectMixin`, `scope.py` |
| Snapshots | Mutar `peso_utilizado`, `nivel_esperado_utilizado` write-once |
| Conteúdo 6.5.5+ | `AvaliacaoCompetencia`, `Feedback`, PDI, comentários, notas |
| Schema | Alterar campos existentes Ciclo/Avaliacao; inventar User/Ciclo |
| UI / stack | Views upload, DRF, Celery tasks novas |
| Persistência | Raw SQL / `bulk_create` bypass `clean`; RunPython de domínio |

### Paths sob vigilância (diff MUST be empty)

- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py` ← **open/close explícitos**
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py`
- `apps/reviews/services/evaluation.py` (+ mutators de nota)
- `apps/dashboard/services/adherence.py`

---

## Permitido (contraste)

| Ação | Escopo |
|---|---|
| Migration aditiva `Ciclo.solides_id` | Só `apps/cycles` |
| ORM create/update `Ciclo` com `status=encerrado` | Sem chamar `cycle.py` |
| ORM create/update `Avaliacao` com `etapa=feedback`, `concluida=True` | Sem chamar `stage.py` |
| Estender parse/dates/report da 010 | openpyxl só no parser |
| Relatório CLI mascarado + ids_colapsados | stdout / `--report-file` |

---

## Gate de regressão (obrigatório)

Antes de merge:

```bash
# Diff denylist = vazio
git diff main -- \
  apps/cycles/services/stage.py \
  apps/cycles/services/cycle.py \
  apps/goals/services/approval.py \
  apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py \
  apps/dashboard/services/adherence.py

pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q
pytest tests/test_import_ciclos_avaliacoes_legado.py -q
```

Qualquer diff não justificado em path da denylist = **FAIL**.

---

## Checklist de revisão de PR

- [ ] Nenhum arquivo denylist alterado (`stage.py` e `cycle.py` inclusive)
- [ ] `scope.py` diff vazio
- [ ] Sem chamada a open/close/advance/approve/calcular
- [ ] Sem preenchimento de `nota_final_*` / AvaliacaoCompetencia / Feedback
- [ ] Sem UI/DRF/Celery
- [ ] Testes CI não referenciam `raw/`
- [ ] Relatório sem dump completo de PII
- [ ] Única migration de schema = `Ciclo.solides_id`
