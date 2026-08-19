# Contract: Migration Safety — `Ciclo.solides_id`

**Feature**: `011-import-ciclos-avaliacoes-legado`  
**Fonte**: Clarification 2026-08-13 (#1); FR-001; [data-model.md](../data-model.md)  
**Data**: 2026-08-13

---

## 1. Estratégia: uma migration, um app

| App | Model | Migration |
|---|---|---|
| `cycles` | `Ciclo` | `AddField solides_id` |

**Única alteração de schema desta fatia.**  
`Avaliacao.solides_id` já foi adicionado na spec 010 — **não** regenerar/alterar.

### Definição (padrão 010)

```python
solides_id = models.CharField(
    'ID Sólides',
    max_length=50,
    blank=True,
    null=True,
    unique=True,
    db_index=True,
)
```

Valor persistido pela importação = `Identificador` da solicitação Sólides.

---

## 2. Rollback documentado

### Aplicar (forward)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py migrate cycles
```

### Reverter (backward)

```bash
python manage.py migrate cycles <previous_migration_name>
```

Django auto Reverse = `RemoveField` — remove coluna `solides_id` **sem** tocar outros campos de `Ciclo`.

**Dados**: rollback **descarta** valores `solides_id` — aceitável em staging; produção exige backup pré-migration.

---

## 3. Nullable — ciclos manuais permanecem válidos

- `null=True, blank=True` — ciclos criados pelo fluxo normal da app (sem legado) permanecem válidos.
- Unique aplica-se a valores non-null (múltiplos NULL ok em PostgreSQL/SQLite).
- Import preenche `solides_id` para todo ciclo criado a partir de solicitação com Identificador válido.

---

## 4. Teste de migration reversível

**Obrigatório** em `tests/test_import_ciclos_avaliacoes_legado.py` (ou módulo dedicado):

```python
@pytest.mark.django_db
def test_ciclo_solides_id_migration_reversible_and_preserves_existing(seed_ciclo):
    """Forward adds nullable field; reverse removes it; seed data intact."""
    # 1. Assert campos legados (nome, datas, status) intactos após forward
    # 2. Set solides_id; assert unique enforcement (dois non-null iguais → IntegrityError)
    # 3. migrate backward
    # 4. Assert ciclo seed ainda existe com nome/status originais
```

Critérios:
- Forward: coluna existe; CRUD/open-close manuais existentes passam.
- Unique: dois non-null iguais → IntegrityError.
- Reverse: coluna removida; **nenhum** outro campo alterado.
- Seed: contagem de ciclos inalterada após round-trip (exceto coluna removida).

---

## 5. Compatibilidade SQLite / PostgreSQL

- `CharField(50)` — paridade ok.
- `unique=True, null=True` — paridade ok (múltiplos NULL).
- `db_index=True` — paridade ok.
- **Proibido**: JSONField específico, partial indexes não suportados em SQLite, triggers raw, RunPython de domínio.

---

## 6. Ordem operacional recomendada

```text
1. 003 importar_competencias_cargo (se ainda não)
2. 010 migrate + importar_colaboradores
3. migrate cycles (Ciclo.solides_id)          ← esta feature
4. importar_ciclos_avaliacoes --dry-run
5. importar_ciclos_avaliacoes (persist)
6. pytest regressão denylist + novos testes
7. (futuro) 6.5.5 notas/comentários
```

---

## 7. Checklist pré-deploy

- [ ] Uma migration gerada (`makemigrations cycles`)
- [ ] `sqlmigrate` revisado — somente `ADD COLUMN`
- [ ] Teste reversível verde
- [ ] Nenhuma migration RunPython mutando domínio
- [ ] Nenhuma alteração em migrations de `reviews` nesta fatia
- [ ] Backup DB staging antes da primeira carga real

---

## Explicitamente proibido

| Proibição | Motivo |
|---|---|
| Alterar campos existentes de `Ciclo` | FR-001 aditivo only |
| Alterar `on_delete` / constraints de `Avaliacao` | Fora de escopo |
| RunPython backfill inventando ciclos | FR-011 |
| Raw SQL bypass | Constituição III |
