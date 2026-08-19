# Contract: Model / Path Allowlist

**Feature**: `014-import-pdi-acoes-legado`  
**Fonte**: [plan.md](../plan.md), [data-model.md](../data-model.md)  
**Data**: 2026-08-19

Paths **permitidos** para alteração nesta fatia. Qualquer diff fora desta lista (exceto artefatos `specs/014-*` e `.specify/feature.json`) exige justificativa explícita no PR.

**Allowlist sem `models.py`**: persistência via ORM existente. **Sem** `AlterField`. **`requirements.txt` FORA** (sem lib nova).

### Confirmação T001 (2026-08-19)

Contratos congelados contra o monólito e o [plan.md](../plan.md). Diff fora desta lista (exceto `specs/014-*` e `.specify/feature.json`) = FAIL. Paths **Novo** ainda não existem no repo — scaffold é T002/T003.

- [x] Comando operacional = `importar_pdi` em `apps/pdi/management/commands/importar_pdi.py` (**Novo**)
- [x] Parse OOXML **somente** em `apps/accounts/services/legacy_import/parse_xlsx.py` (arquivo existe; único módulo com openpyxl)
- [x] Domínio em `apps/pdi/services/legacy_import/` (**Novo** — `resolve.py` / `importer.py`)
- [x] Extensões permitidas: `dates.py` e `report.py` (existem; **sem** openpyxl)
- [x] Reuso read-only: `canonical_key`/`display_name` (003); ORM `PDI`/`AcaoPDI`/`CustomUser`; hook de atraso **via** `AcaoPDI.save()` (**MUST NOT** editar `overdue.py`)
- [x] **Zero** migrations / **sem** editar `models.py` / **sem** nova lib (`openpyxl==3.1.5` já na 010; `requirements.txt` fora da allowlist)
- [x] Denylist espelhada em [non-goals-denylist.md](./non-goals-denylist.md): `stage.py` / `cycle.py` / `evaluation.py` / `scope.py` / urls 012 / `overdue.py` / `progress.py` / `tasks.py` / `views.py` / `models.py` / `talent`

---

## Migrations

**Nenhuma.** Ver [migration-safety.md](./migration-safety.md).

| Path | Alteração permitida |
|---|---|
| `apps/*/migrations/*.py` | **Nenhuma** nesta fatia |

---

## Parse / datas / relatório (accounts)

| Path | Alteração permitida |
|---|---|
| `apps/accounts/services/legacy_import/parse_xlsx.py` | **Estender** — `parse_pdi_xlsx`. **Único** módulo com openpyxl |
| `apps/accounts/services/legacy_import/dates.py` | **Estender** se necessário — `Data de Entrega` / `Criado em` (stdlib; sem openpyxl) |
| `apps/accounts/services/legacy_import/report.py` | **Estender** — seções `pdis_*` / `acoes_*` / `orfaos_usuario` / `orfaos_solicitacao` / `conflitos_*` |

---

## Domínio e comando (pdi)

| Path | Notas |
|---|---|
| `apps/pdi/services/legacy_import/**` | **Novo** — `resolve.py`, `importer.py` |
| `apps/pdi/management/__init__.py` | **Novo** se o pacote ainda não existir |
| `apps/pdi/management/commands/__init__.py` | **Novo** se o pacote ainda não existir |
| `apps/pdi/management/commands/importar_pdi.py` | **Novo** — CLI fino |

---

## Reuso read-only (IMPORTAR, não copiar, NÃO editar)

| Path | Uso |
|---|---|
| `apps/competencies/services/catalog_import/normalize.py` | `canonical_key`, `display_name` |
| `apps/pdi/models.py` | ORM `PDI` / `AcaoPDI` — **diff MUST be empty** |
| `apps/accounts/models.py` | ORM `CustomUser` lookup |
| `apps/pdi/services/overdue.py` | **CHAMAR via `AcaoPDI.save()`**. **MUST NOT edit**. **MUST NOT** `mark_overdue_pdi_actions` |
| `apps/accounts/services/legacy_import/dates.py` helpers | `parse_legacy_date` / `parse_legacy_datetime` |
| `apps/accounts/services/legacy_import/report.py` helpers | `mask_solides_id` / `mask_pii` |

---

## Testes, fixtures e specs

| Path | Notas |
|---|---|
| `tests/test_import_pdi_legado.py` | **Novo** |
| `data/legado-solides/samples/**` | `pdi_min.xlsx` + README samples (nunca `raw/`) |
| `specs/014-import-pdi-acoes-legado/**` | artefatos desta feature |
| `.specify/feature.json` | apontar o diretório da feature |

---

## Explicitamente FORA da allowlist

- Qualquer `models.py` **editado**
- Qualquer `migrations/`
- `apps/pdi/views.py`, `urls.py`, `forms.py`, `services/overdue.py`, `services/progress.py`, `tasks.py`
- `apps/cycles/services/stage.py`, `cycle.py`
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py`
- `apps/reviews/services/evaluation.py`
- `apps/dashboard/services/adherence.py`
- `apps/dashboard/urls.py`, `apps/cycles/urls.py`
- Templates da spec 012
- `apps/talent/`
- `requirements.txt` — **sem** nova lib
- `data/legado-solides/raw/**` (leitura operacional manual — nunca CI)

Ver também [non-goals-denylist.md](./non-goals-denylist.md).
