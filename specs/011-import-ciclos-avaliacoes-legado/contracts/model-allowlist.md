# Contract: Model / Migration Allowlist

**Feature**: `011-import-ciclos-avaliacoes-legado`  
**Fonte**: [plan.md](../plan.md), [data-model.md](../data-model.md)  
**Data**: 2026-08-13

Paths **permitidos** para alteração nesta fatia. Qualquer diff fora desta lista (exceto artefatos `specs/011-*`, samples) exige justificativa explícita no PR.

---

## Migrations (aditivas — somente `Ciclo.solides_id`)

| Path | Alteração permitida |
|---|---|
| `apps/cycles/migrations/*.py` | Add `solides_id` to `Ciclo` — **única** migration de schema desta fatia |

**Proibido em migrations**: alterar campos existentes; remover constraints; alterar `on_delete`; RunPython que muta dados de domínio; migrations em `reviews`/`accounts`/`organization`/`competencies`/`pdi` nesta fatia.

---

## Models

| Path | Alteração permitida |
|---|---|
| `apps/cycles/models.py` | **Somente** field definition `Ciclo.solides_id` |

**Proibido**: alterar `Ciclo.status` choices/semântica além do uso na import; alterar `Avaliacao` model (já tem `solides_id`); mudar `on_delete`; novos campos PII.

---

## Serviço e comando de import

| Path | Notas |
|---|---|
| `apps/cycles/services/legacy_import/**` | **Novo** — aggregate, resolve, importer |
| `apps/cycles/management/commands/importar_ciclos_avaliacoes.py` | **Novo** — CLI fino |
| `apps/accounts/services/legacy_import/parse_xlsx.py` | **Estender** — sheets solicitações + avaliações cabeçalho |
| `apps/accounts/services/legacy_import/dates.py` | **Estender** se necessário — rótulo nome serial (stdlib) |
| `apps/accounts/services/legacy_import/report.py` | **Estender** — seções grupos/ids_colapsados |

---

## Reuso read-only (sem modificação obrigatória)

| Path | Uso |
|---|---|
| `apps/accounts/services/legacy_import/crosswalk.py` | Padrão de `canonical_key` / índice se reaproveitado |
| `apps/competencies/services/catalog_import/normalize.py` | `canonical_key`, `display_name` |
| `apps/reviews/models.py` | Persistência ORM — **sem** alteração de schema |

---

## Testes e fixtures

| Path | Notas |
|---|---|
| `tests/test_import_ciclos_avaliacoes_legado.py` | **Novo** |
| `data/legado-solides/samples/**` | + fixtures solicitações/avaliações anonimizadas |

---

## Explicitamente FORA da allowlist

- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py` (open/close)
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py`
- `apps/reviews/services/evaluation.py`
- `apps/dashboard/services/adherence.py`
- Alterar campos existentes de `Ciclo` / `Avaliacao` (tipo, constraints)
- Qualquer `templates/**`, `static/**`, views, urls, DRF, Celery
- `data/legado-solides/raw/**` (somente leitura operacional — nunca CI)
- `requirements.txt` — **sem** nova lib (openpyxl já na 010)

Ver também [non-goals-denylist.md](./non-goals-denylist.md).
