# Contract: Model / Path Allowlist

**Feature**: `013-import-notas-comentarios-legado`  
**Fonte**: [plan.md](../plan.md), [data-model.md](../data-model.md)  
**Data**: 2026-08-18

Paths **permitidos** para alteração nesta fatia. Qualquer diff fora desta lista (exceto artefatos `specs/013-*`) exige justificativa explícita no PR.

**Allowlist sem `models.py`**: persistência via ORM existente. Create de `Competencia` extra usa o model vigente — **sem** `AlterField`.

### Confirmação T001 (2026-08-18)

Contratos congelados contra o monólito e o [plan.md](../plan.md). Diff fora desta lista (exceto `specs/013-*`) = FAIL. Paths **Novo** ainda não existem no repo — scaffold é T002/T003.

- [x] Comando operacional = `importar_notas_comentarios` em `apps/reviews/management/commands/importar_notas_comentarios.py` (**Novo**)
- [x] Parse OOXML **somente** em `apps/accounts/services/legacy_import/parse_xlsx.py` (arquivo existe; único módulo com openpyxl)
- [x] Domínio em `apps/reviews/services/legacy_import/` (**Novo** — `resolve.py` / `importer.py` / `snapshots.py`)
- [x] Extensões permitidas: `dates.py` e `report.py` (existem; **sem** openpyxl)
- [x] Reuso read-only: `aggregate.py` (011, existe), `canonical_key`/`display_name`/`nivel_esperado_for`/`is_kpi`/`is_ambiguous`/`map_grupo_tipo`/`resolve_default_escala`; **CHAMAR** `calcular_nota_final_*` em `evaluation.py` (**MUST NOT edit**)
- [x] **Zero** migrations / **sem** editar `models.py` / **sem** nova lib (`openpyxl==3.1.5` já na 010; `requirements.txt` fora da allowlist)
- [x] Denylist espelhada em [non-goals-denylist.md](./non-goals-denylist.md): `stage.py` / `cycle.py` / `evaluation.py` (diff vazio) / `scope.py` / urls 012 / `pdi` / `talent`

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
| `apps/accounts/services/legacy_import/parse_xlsx.py` | **Estender** — sheets notas + comentários [+ habilidades opcional]. **Único** módulo com openpyxl |
| `apps/accounts/services/legacy_import/dates.py` | **Estender** se necessário — datetime `Criado em` (stdlib; sem openpyxl) |
| `apps/accounts/services/legacy_import/report.py` | **Estender** — seções `notas_*` / `comentarios_*` / `orfaos_*` / `conflitos_*` / `habilidades_extras_criadas` / `ids_colapsados_resolvidos` |

---

## Domínio e comando (reviews)

| Path | Notas |
|---|---|
| `apps/reviews/services/legacy_import/**` | **Novo** — `resolve.py`, `importer.py`, `snapshots.py` (opcional) |
| `apps/reviews/management/commands/importar_notas_comentarios.py` | **Novo** — CLI fino |
| `apps/reviews/management/__init__.py` | **Novo** se o pacote ainda não existir |
| `apps/reviews/management/commands/__init__.py` | **Novo** se o pacote ainda não existir |

---

## Reuso read-only (sem modificação)

| Path | Uso |
|---|---|
| `apps/cycles/services/legacy_import/aggregate.py` | IMPORTAR algoritmo 011 (`group_key`, `min_id`, `collapsed_ids`) |
| `apps/competencies/services/catalog_import/normalize.py` | `canonical_key`, `display_name` |
| `apps/competencies/services/catalog_import/mapping.py` | `nivel_esperado_for`, `is_kpi`, `is_ambiguous`, `map_grupo_tipo` |
| `apps/competencies/services/catalog_import/importer.py` | `resolve_default_escala` (extras) |
| `apps/reviews/services/evaluation.py` | **CHAMAR** `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao`. **MUST NOT edit** |
| `apps/reviews/models.py` | ORM `Avaliacao` (read-only cabeçalho + `nota_final_*` via `calcular_*`), `AvaliacaoCompetencia`, `Feedback` |
| `apps/competencies/models.py` | ORM `Competencia` create mínima; `Escala` lookup |
| `apps/accounts/models.py` | ORM `CustomUser` lookup (`solides_id`) |
| `apps/cycles/models.py` | ORM `Ciclo.status` read (aberto → skip) |
| `apps/organization/models.py` | ORM `Cargo.nivel` read |

---

## Testes e fixtures

| Path | Notas |
|---|---|
| `tests/test_import_notas_comentarios_legado.py` | **Novo** |
| `data/legado-solides/samples/**` | + fixtures notas/comentários anonimizadas (nunca `raw/`) |

---

## Explicitamente FORA da allowlist

- Qualquer `models.py` **editado** (schema)
- Qualquer `migrations/`
- `apps/cycles/services/stage.py`, `cycle.py`
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py`
- `apps/reviews/services/evaluation.py` (**diff vazio** — chamar ≠ editar)
- `apps/dashboard/services/adherence.py`
- `apps/dashboard/urls.py`, `apps/cycles/urls.py`
- Templates da spec 012
- `apps/pdi/**` mutators, `apps/talent/**` mutators
- `requirements.txt` — **sem** nova lib
- `data/legado-solides/raw/**` (leitura operacional manual — nunca CI)

Ver também [non-goals-denylist.md](./non-goals-denylist.md).
