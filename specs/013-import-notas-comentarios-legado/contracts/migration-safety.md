# Contract: Migration Safety — Zero Migrations

**Feature**: `013-import-notas-comentarios-legado`  
**Fonte**: FR-019; [data-model.md](../data-model.md)  
**Data**: 2026-08-18

---

## 1. Estratégia: NENHUMA migration

| App | Model | Migration desta fatia |
|---|---|---|
| `reviews` | `Avaliacao`, `AvaliacaoCompetencia`, `Feedback` | **Nenhuma** |
| `competencies` | `Competencia`, `Escala`, `CargoCompetencia` | **Nenhuma** |
| `accounts` / `cycles` / `organization` / `pdi` / `talent` | — | **Nenhuma** |

Schema vigente é suficiente:

- `Avaliacao.solides_id` (010) + unique `(ciclo, usuario)` (pré-011)
- `AvaliacaoCompetencia` unique `(avaliacao, competencia)` + snapshots write-once no `save()`
- `Feedback.tipo` / `ciente_em` / `conteudo` / `autor`
- `Competencia.solides_id` (010)
- `CustomUser.solides_id` (010)

Create de `Competencia` extra = ORM no schema **existente** (`nome`, `tipo`, `escala`, `solides_id`). **Sem** `AlterField`.

---

## 2. `sqlmigrate` não se aplica

Não há migration para gerar nem revisar. Checklist desta fatia **não** inclui `makemigrations`.

Se um PR desta feature introduzir arquivo em `*/migrations/` → **FAIL** (salvo revert explícito fora de escopo, o que não é o caso).

---

## 3. Sem RunPython de domínio

**Proibido**: `RunPython` backfill, raw SQL, data migration “para popular mapa”, `AddField` de mapa de IDs.

Mapa de colapsados = memória (FR-003).

---

## 4. Compatibilidade SQLite / PostgreSQL

Sem DDL novo. Escritas via ORM `full_clean()` + `save()` — paridade já garantida pelo produto. **Proibido** `bulk_create` que pule `AvaliacaoCompetencia.save()` (write-once vive ali).

`QuerySet.update(created_at=...)` pontual em `Feedback` após create (honrar `Criado em`) é permitido e portável.

---

## 5. Ordem operacional recomendada

```text
1. 003 importar_competencias_cargo          (já aplicado)
2. 010 importar_colaboradores               (já aplicado)
3. 011 importar_ciclos_avaliacoes           (já aplicado)
4. (esta feature) ZERO migrate
5. importar_notas_comentarios --dry-run
6. importar_notas_comentarios (persist)
7. pytest denylist + test_import_notas_comentarios_legado
```

---

## 6. Checklist pré-deploy

- [ ] `git diff` **não** contém `*/migrations/*`
- [ ] Nenhuma migration RunPython
- [ ] Nenhuma alteração em `models.py` (schema)
- [ ] Backup DB staging antes da primeira carga real
- [ ] Homologação `raw/` **manual** (nunca CI)

---

## Explicitamente proibido

| Proibição | Motivo |
|---|---|
| Migration “por precaução” (unique Feedback, campo mapa, índice extra) | FR-019; pedido do plan |
| `AddField` PII | FR-019 |
| Alterar `on_delete` / constraints existentes | Constituição III |
| `sqlmigrate` como evidência desta fatia | Não há SQL a revisar |
