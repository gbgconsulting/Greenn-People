# Contract: Model / Migration Allowlist

**Feature**: `010-import-colaboradores-legado`  
**Fonte**: [plan.md](../plan.md), [data-model.md](../data-model.md)  
**Data**: 2026-08-12

Paths **permitidos** para alteração nesta fatia. Qualquer diff fora desta lista (exceto artefatos `specs/010-*`, `data/legado-solides/samples/`, `requirements.txt` para openpyxl) exige justificativa explícita no PR.

---

## Migrations (aditivas — somente `solides_id`)

| Path | Alteração permitida |
|---|---|
| `apps/accounts/migrations/*.py` | Add `solides_id` to `CustomUser` |
| `apps/organization/migrations/*.py` | Add `solides_id` to `Cargo` |
| `apps/competencies/migrations/*.py` | Add `solides_id` to `Competencia` |
| `apps/reviews/migrations/*.py` | Add `solides_id` to `Avaliacao` |
| `apps/pdi/migrations/*.py` | Add `solides_id` to `PDI` |

**Proibido em migrations**: alterar campos existentes; remover constraints; alterar `on_delete`; RunPython que muta dados de domínio.

---

## Models (somente campo `solides_id`)

| Path | Alteração permitida |
|---|---|
| `apps/accounts/models.py` | `CustomUser.solides_id` field definition |
| `apps/organization/models.py` | `Cargo.solides_id` |
| `apps/competencies/models.py` | `Competencia.solides_id` |
| `apps/reviews/models.py` | `Avaliacao.solides_id` |
| `apps/pdi/models.py` | `PDI.solides_id` |

**Proibido**: novos campos PII; alterar `clean()`/`save()` semantics além do já existente; mudar `UserManager` behavior global.

---

## Serviço e comando de import

| Path | Notas |
|---|---|
| `apps/accounts/services/legacy_import/**` | **Novo** — parse, crosswalk, resolve, hierarchy, report, importer |
| `apps/accounts/management/commands/importar_colaboradores.py` | **Novo** — CLI fino |

---

## Reuso read-only (sem modificação)

| Path | Uso |
|---|---|
| `apps/competencies/services/catalog_import/normalize.py` | `canonical_key`, `display_name` |

---

## Testes e fixtures

| Path | Notas |
|---|---|
| `tests/test_import_colaboradores_legado.py` | **Novo** |
| `data/legado-solides/samples/**` | Fixtures anonimizadas XLSX mínimas |

---

## Dependências

| Path | Alteração |
|---|---|
| `requirements.txt` | Adicionar `openpyxl` (justificado em Complexity Tracking) |

---

## Explicitamente FORA da allowlist

- `apps/accounts/services/scope.py`
- `apps/accounts/forms.py` (denylist domínio permanece)
- `apps/cycles/**`, `apps/goals/**`, `apps/reviews/services/evaluation.py`, `apps/dashboard/services/adherence.py`
- Qualquer `templates/**`, `static/**`, views, urls
- `data/legado-solides/raw/**` (somente leitura manual operacional — nunca commit de alterações)

Ver também [non-goals-denylist.md](./non-goals-denylist.md).
