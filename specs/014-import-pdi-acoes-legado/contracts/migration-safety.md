# Contract: Migration Safety — Zero Migrations

**Feature**: `014-import-pdi-acoes-legado`  
**Fonte**: FR-019; [data-model.md](../data-model.md)  
**Data**: 2026-08-19

---

## 1. Estratégia: NENHUMA migration

| App | Model | Migration desta fatia |
|---|---|---|
| `pdi` | `PDI`, `AcaoPDI` | **Nenhuma** |
| `accounts` / `cycles` / `reviews` / `organization` / `talent` | — | **Nenhuma** |

Schema vigente é suficiente:

- `PDI.solides_id` (010, `CharField(max_length=50, unique=True, null=True, blank=True, db_index=True)`)
- `PDI.usuario` / `titulo` / `status` (`ativo` / `concluido` / `arquivado` — import não usa arquivado)
- `AcaoPDI.descricao` / `responsavel` / `prazo` / `status`
- FKs `on_delete=PROTECT`
- `CustomUser` 010 (lookup)

**Sem** `AddField`. **Sem** `solides_id` em `AcaoPDI`. **Sem** FK Ciclo/Avaliação. **Sem** `AlterField` em `max_length`/unicidade/nullability.

---

## 2. `sqlmigrate` não se aplica

Não há migration para gerar nem revisar. Checklist desta fatia **não** inclui `makemigrations`.

Se um PR desta feature introduzir arquivo em `*/migrations/*` → **FAIL**.

---

## 3. Sem RunPython de domínio

**Proibido**: `RunPython` backfill, raw SQL, data migration “para popular digest”, `AddField` de mapa.

Digest = computado em memória na carga (R-digest) e gravado no campo **já existente**.

---

## 4. Compatibilidade SQLite / PostgreSQL

Sem DDL novo. Escritas via ORM `full_clean()` + `save()` — paridade já garantida pelo produto.

**Proibido** `bulk_create` que pule `AcaoPDI.save()` (hook de atraso vive ali).

---

## 5. Ordem operacional recomendada

```text
1. 003 importar_competencias_cargo          (já aplicado)
2. 010 importar_colaboradores               (já aplicado)
3. 011 / 013                                (opcionais — NÃO bloqueiam)
4. (esta feature) ZERO migrate
5. importar_pdi --dry-run                   (staging primeiro)
6. importar_pdi (persist)
7. pytest denylist + test_import_pdi_legado
```

README passo 7 / PRD 6.5.6.

---

## 6. Checklist pré-deploy

- [ ] `git diff` **não** contém `*/migrations/*`
- [ ] Nenhuma migration RunPython
- [ ] Nenhuma alteração em `apps/pdi/models.py`
- [ ] Backup DB staging antes da primeira carga real
- [ ] Homologação `raw/` **manual** (nunca CI); `--dry-run` primeiro

---

## Explicitamente proibido

| Proibição | Motivo |
|---|---|
| Migration “por precaução” (unique de ação, índice extra, campo mapa) | FR-019 |
| `AddField` PII / `solides_id` na ação | FR-009/FR-019 |
| Alterar `on_delete` / constraints existentes | Constituição III |
| `sqlmigrate` como evidência desta fatia | Não há SQL a revisar |
| `bulk_create` bypass `save()` | FR-016; hook de atraso |
