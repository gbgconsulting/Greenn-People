# Contract: Non-Goals / Denylist

**Feature**: `015-cycle-admission-cutoff`  
**Fonte**: FR-018…FR-023, US5, SC-009; decisões fechadas do plan  
**Data**: 2026-08-20

---

## Declaração

Esta feature altera **somente**:

1. Schema aditivo `Ciclo.admitidos_ate`
2. `open_cycle` + UI mínima de abertura (campo + preview + mensagem)
3. `ensure_avaliacao_for_user` (predicado)
4. Comando operacional de backfill de `data_entrada` vazia

**Teste de ouro**: após a feature, gold **DIFF VAZIO de comportamento** em stage, approval, evaluation (fórmula), adherence, talent, pdi (produto), scope/hierarquia, URLs 012, `close_cycle`, imports 010/011/013/014 (exceto backfill estrito desta feature).

**Teste de ouro II**: líder no escopo vigente continua vendo o mesmo conjunto de objetos que o scope permite; inelegível simplesmente **não tem** Avaliacao — sem mudança de `get_visible_users`.

FAIL se: hard-block do checklist 008; M2M de exceções; apagar Avaliacao por data; Celery/DRF/SPA; AlterField em `data_entrada`.

---

## Non-goals (produto)

- Filtros novos de cadastro
- Paginação 15
- Redesign / Freeze visual
- Lista manual / M2M de exceções / forçar inelegível no ciclo
- Desfazer / apagar Avaliacao por mudança de `data_entrada`
- Hard-block do checklist 008 (área/cargo/competências)
- Celery novo **só** para o corte
- Tornar `data_entrada` obrigatória no banco ou no `RegisterForm` (default: NÃO)
- UI de upload para backfill
- Reprocessar ciclos 011 / backfill de `admitidos_ate` histórico
- Papel AuthZ novo; preview para líder/colaborador

---

## Denylist (PROIBIDO alterar comportamento)

| Zona | Proibição |
|---|---|
| Máquina de etapas | `can_advance`, `advance_stage`, `stage.py` |
| Encerramento | `close_cycle` (regra vigente intacta) |
| Aprovação | `approval.py` approve/reject |
| Fórmulas | `evaluation.py` (nota_final_*) |
| Aderência | `adherence.py` / tasks de aderência |
| Talent / 9-box | mutators `apps/talent/` |
| PDI produto | views/urls/forms/overdue/progress (backfill **não** toca) |
| Escopo / hierarquia | `get_visible_users`, `ScopedObjectMixin`, `scope.py` |
| Visão histórica 012 | urls/templates dashboard/cycles da 012 |
| Imports legado | `importar_colaboradores` / ciclos / notas / pdi — **não** exigir corte nem abrir ciclo |
| Checklist 008 | continuar avisório; não condicionar Abrir ao checklist |
| Schema | M2M; tabela participantes; FK nova Avaliacao↔Ciclo; AlterField `data_entrada`; RunPython elegibilidade |
| Stack | DRF, SPA, lib nova, Celery task nova para corte |

### Paths sob vigilância (diff de comportamento MUST be empty)

```text
apps/cycles/services/stage.py
apps/cycles/services/cycle.py::close_cycle
apps/goals/services/approval.py
apps/reviews/services/evaluation.py
apps/dashboard/services/adherence.py
apps/accounts/services/scope.py
apps/talent/
apps/pdi/views.py
apps/pdi/urls.py
apps/pdi/forms.py
apps/pdi/services/overdue.py
apps/pdi/services/progress.py
apps/pdi/tasks.py
apps/dashboard/urls.py
```

**Allowlist explícita (pode mudar)**:

```text
apps/cycles/models.py
apps/cycles/migrations/0003_*admitidos_ate*
apps/cycles/forms.py
apps/cycles/views.py          # Open + preview; Close intacto em regra
apps/cycles/exceptions.py
apps/cycles/services/cycle.py # open_cycle apenas (+ imports)
apps/cycles/services/eligibility.py   # NOVO
templates/cycles/ciclo_list*.html (+ partials preview se houver)
apps/reviews/services/enrollment.py
apps/accounts/services/admission_backfill/   # NOVO
apps/accounts/management/commands/backfill_data_entrada.py
apps/accounts/services/legacy_import/parse_xlsx.py  # mínimo p/ coluna Data admissão
apps/accounts/services/legacy_import/report.py      # seções backfill se necessário
specs/002-pos-mvp-hardening/contracts/mid-cycle-enrollment-contract.md
tests/conftest.py
tests/test_mid_cycle_enrollment.py
tests/test_open_cycle_admission_cutoff.py          # NOVO
tests/test_backfill_data_entrada.py                # NOVO
```

`apps/cycles/urls.py` — permitido **somente** se necessário para rota de preview HTMX admin; **MUST NOT** alterar rotas 012 / histórico.

---

## Imports 010–014

| Comando | Exige `admitidos_ate`? | Chama `open_cycle`? |
|---|---|---|
| `importar_colaboradores` (010) | não | não |
| import ciclos/avaliações (011) | não | não |
| import notas (013) | não | não |
| `importar_pdi` (014) | não | não |
| `backfill_data_entrada` (015) | N/A | **não** |

Ciclos 011: `encerrado`, `admitidos_ate=NULL` válido.

---

## Asserts de regressão (não alterar)

- `tests/test_stage_machine.py`
- `tests/test_scope.py` (e equivalentes de escopo)
- testes de rejeição / invariante de etapa
- asserts de fórmula em evaluation

Fixtures que chamam `open_cycle` **podem** ser atualizadas para setar `admitidos_ate` + `data_entrada` — isso **não** é mudança de assert de negócio alheio.
