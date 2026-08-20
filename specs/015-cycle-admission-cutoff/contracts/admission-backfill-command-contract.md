# Contract: Management command — backfill `data_entrada`

**Feature**: `015-cycle-admission-cutoff`  
**App**: `accounts`  
**Fonte**: FR-016, FR-017, FR-018; US4; [research.md](../research.md) R6  
**Padrão operacional**: espelha dry-run / report / atomic das fatias 010+

---

## CLI

```bash
python manage.py backfill_data_entrada \
  --colaboradores PATH \
  [--dry-run] \
  [--report-file PATH]
```

| Flag | Obrigatório | Comportamento |
|---|---|---|
| `--colaboradores` | sim | Path do `backup_colaboradores_*.xlsx` |
| `--dry-run` | não | Zero writes; relatório com totais esperados |
| `--report-file` | não | Grava o mesmo UTF-8 do stdout |

Exit: `0` sucesso operacional; `1` erro fatal (arquivo/OOXML/coluna ausente).

**Sem UI de upload.**

---

## Fonte e parse

| Item | Regra |
|---|---|
| Coluna | **“Data admissão”** |
| Parse | `apps.accounts.services.legacy_import.dates.parse_legacy_date` (serial Excel + ISO) |
| XLSX | openpyxl **somente** via `parse_xlsx` (extensão mínima ou parser dedicado no mesmo módulo) |
| Importer 010 full | **MUST NOT** ser o path de persistência desta carga |

---

## Match de pessoa (chave natural 010)

Ordem alinhada ao importer 010:

1. E-mail (`email` / e-mail empresarial do backup) — `email__iexact` (normalização vigente).
2. Complementar: `solides_id` / Identificador canônico (`canonicalize_id`) quando e-mail não resolve.

- Match único → candidato a update.
- Sem match → órfão no relatório; **NÃO** inventar `User`.
- Ambíguo → conflito no relatório; **NÃO** gravar.

---

## Persistência

| Regra | Obrigatório |
|---|---|
| Só preenche `data_entrada` quando `NULL`/vazio | sim |
| NÃO sobrescreve data já preenchida | sim |
| NÃO toca nome, email, área, cargo, gestor, `is_active` | sim |
| `transaction.atomic` no persist | sim |
| Idempotente (2ª run: delta preenchimento = 0) | sim |
| Dry-run: zero `save`/`update` | sim |

---

## Denylist do comando (MUST NOT chamar)

```text
open_cycle
close_cycle
ensure_avaliacao_for_user
advance_stage
can_advance
approve_* / reject_*
```

Imports 010/011/013/014 **não** passam a exigir `admitidos_ate` nem a chamar abertura por causa deste comando.

---

## Relatório

- Totais: lidos, matched, preenchidos, já preenchidos (skip), órfãos, conflitos, datas ilegíveis, dry-run flag.
- Amostra mascarada: padrão `report.py` 010 (`mask_email` / `mask_pii` / truncagem máx. ~5).
- Sem PII completa em claro no stdout além do padrão já aceito nas fatias legado.

---

## Layout de código

```text
apps/accounts/services/admission_backfill/
  __init__.py
  resolve.py      # match pessoa + parse data
  importer.py     # orquestração dry-run/persist/report
apps/accounts/management/commands/backfill_data_entrada.py
```

---

## Contrato de teste

| Cenário | Esperado |
|---|---|
| Dry-run | 0 writes; totais coerentes |
| Persist + entrada vazia + data parseável | preenche |
| Entrada já preenchida | intacta |
| 2ª execução | delta 0 |
| Sem data no Excel / só auto-cadastro | permanece NULL |
| Spies | open/close/ensure/advance **não** chamados |
| Relatório | amostra mascarada |
