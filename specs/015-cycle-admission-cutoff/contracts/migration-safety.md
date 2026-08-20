# Contract: Migration Safety

**Feature**: `015-cycle-admission-cutoff`  
**Fonte**: FR-007, FR-009, FR-010; [data-model.md](../data-model.md); [research.md](../research.md) R1  
**Data**: 2026-08-20

---

## Permitido (exatamente)

**UMA** migration aditiva em `apps/cycles`:

```python
# apps/cycles/migrations/0003_ciclo_admitidos_ate.py  (nome ilustrativo)

migrations.AddField(
    model_name='ciclo',
    name='admitidos_ate',
    field=models.DateField(
        'admitidos até',
        null=True,
        blank=True,
    ),
)
```

- Reversível via `RemoveField` automático do Django.
- Compatível SQLite (dev) e PostgreSQL (prod).
- Sem default que invente datas em ciclos existentes (permanecem `NULL`).

---

## Proibido

| Proibição | Motivo |
|---|---|
| Segunda migration desta feature | FR-010 — um passo aditivo |
| `AlterField` em `CustomUser.data_entrada` | FR-009 — tipo/null/unique intactos |
| Segundo campo de admissão no User | FR-009 |
| `AddField` M2M / through table de participantes | FR-010 |
| Tabela nova de coorte / mapa | FR-010 |
| FK nova `Avaliacao`↔`Ciclo` além da existente | FR-010 |
| `RunPython` / `RunSQL` que invente elegibilidade histórica | FR-008 |
| Backfill de `admitidos_ate` em ciclos 011/arquivo | NULL válido; não reprocessar |
| `null=False` / `blank=False` no DB para `admitidos_ate` | quebraria histórico |
| Apagar/recriar Avaliações em data migration | Constituição III |

---

## Estado pós-migrate

| Ciclo | `admitidos_ate` | Válido? |
|---|---|---|
| 011 / arquivo encerrado | `NULL` | sim |
| Operacional ainda não aberto | `NULL` até Abrir com D | sim |
| Operacional aberto (após feature) | `D` não nulo | exigido pela regra de `open_cycle` |

---

## Checklist pré-merge

- [ ] Só `AddField` `admitidos_ate`
- [ ] `makemigrations` não gera AlterField em accounts
- [ ] Migrate em SQLite + Postgres smoke
- [ ] Ciclo 011 sample: count Avaliações inalterado após migrate
- [ ] Nenhum `RunPython` nesta migration
