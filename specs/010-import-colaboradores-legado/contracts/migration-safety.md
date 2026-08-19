# Contract: Migration Safety — `solides_id`

**Feature**: `010-import-colaboradores-legado` (Sprint 6.5.1)  
**Fonte**: PRD §6.5.1, [data-model.md](../data-model.md)  
**Data**: 2026-08-12

---

## 1. Estratégia: uma migration por app

| App | Model | Migration |
|---|---|---|
| `accounts` | `CustomUser` | `AddField solides_id` |
| `organization` | `Cargo` | `AddField solides_id` |
| `competencies` | `Competencia` | `AddField solides_id` |
| `reviews` | `Avaliacao` | `AddField solides_id` |
| `pdi` | `PDI` | `AddField solides_id` |

**Justificativa**: PRD lista cinco models em apps distintas (Princípio IV). Migration consolidada cross-app violaria modularidade Django.

**Alternativa rejeitada**: migration única manual — acoplamento e ordem de dependência entre apps.

### Definição idêntica em todos

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

---

## 2. Rollback documentado

### Aplicar (forward)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py migrate accounts organization competencies reviews pdi
```

### Reverter (backward)

```bash
# Reverter na ordem inversa de dependência de app (ou migrate app zero)
python manage.py migrate pdi <previous_migration_name>
python manage.py migrate reviews <previous_migration_name>
python manage.py migrate competencies <previous_migration_name>
python manage.py migrate organization <previous_migration_name>
python manage.py migrate accounts <previous_migration_name>
```

Cada migration MUST implementar `RemoveField` em `Reverse` (Django auto) — remove coluna `solides_id` sem tocar outros campos.

**Dados**: rollback **descarta** valores `solides_id` persistidos — aceitável em staging; em produção exige backup pré-migration.

---

## 3. Nullable — import não exige 100% preenchido

- Campo `null=True, blank=True` — registros existentes e novos sem legado permanecem válidos.
- Unique constraint aplica-se **apenas** a valores non-null (PostgreSQL/SQLite: múltiplos NULL permitidos em unique — verificar paridade; Django `unique=True` em nullable CharField: múltiplos NULL ok em PostgreSQL; SQLite idem).
- Import colaboradores preenche `solides_id` em User/Cargo quando resolvível; Competencia/Avaliacao/PDI ficam null nesta fatia.

---

## 4. Teste de migration reversível

**Obrigatório** em `tests/test_import_colaboradores_legado.py` (ou módulo dedicado):

```python
@pytest.mark.django_db
def test_solides_id_migration_reversible_and_preserves_existing(seed_users):
    """Forward migrate adds nullable field; reverse removes it; seed data intact."""
    # Pré: fixtures/seed com CustomUser, Cargo, Avaliacao existentes SEM solides_id
    # 1. Assert campos legados intactos após migrate forward
    # 2. Opcional: set solides_id em um registro; assert unique enforcement
    # 3. migrate backward última migration solides_id
    # 4. Assert registros seed ainda existem com email/nome originais
```

Critérios:
- Forward: coluna existe; queries CRUD existentes passam.
- Unique: dois non-null iguais → IntegrityError.
- Reverse: coluna removida; **nenhum** outro campo alterado.
- Seed/fixtures: contagem de usuários/cargos/avaliações inalterada após round-trip (exceto coluna removida).

---

## 5. Compatibilidade SQLite / PostgreSQL

- `CharField(50)` — paridade ok.
- `unique=True, null=True` — paridade ok (múltiplos NULL).
- `db_index=True` — paridade ok.
- **Proibido**: `JSONField` específico, partial indexes não suportados em SQLite, triggers raw.

---

## 6. Ordem operacional recomendada

```text
1. migrate (6.5.1)
2. importar_competencias_cargo (003) — se ainda não executado
3. importar_colaboradores --dry-run
4. importar_colaboradores (persist)
5. pytest regressão denylist
```

---

## Checklist pré-deploy

- [ ] Cinco migrations geradas (`makemigrations` por app)
- [ ] `sqlmigrate` revisado — somente `ADD COLUMN`
- [ ] Teste reversível verde
- [ ] Nenhuma migration RunPython mutando domínio
- [ ] Backup DB staging antes da primeira carga real
