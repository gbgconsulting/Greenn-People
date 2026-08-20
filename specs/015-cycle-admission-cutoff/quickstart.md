# Quickstart: Validação E2E — Admitidos até (015)

**Feature**: `015-cycle-admission-cutoff`  
**Date**: 2026-08-20  
**Pré-req**: migrate da AddField aplicada; admin `is_admin`; backup sample de colaboradores (não `raw/` em CI)

Contratos: [eligibility](./contracts/eligibility-predicate-contract.md) · [open](./contracts/open-cycle-cutoff-contract.md) · [preview](./contracts/preview-counts-contract.md) · [backfill](./contracts/admission-backfill-command-contract.md) · [denylist](./contracts/non-goals-denylist.md)

---

## Ordem de validação

### 1) Backfill dry-run

```bash
python manage.py backfill_data_entrada \
  --colaboradores path/para/backup_colaboradores_sample.xlsx \
  --dry-run
```

**Esperado**: exit 0; zero mudanças em `CustomUser.data_entrada`; relatório com totais + amostra mascarada.

### 2) Backfill persist + idempotência

```bash
python manage.py backfill_data_entrada \
  --colaboradores path/para/backup_colaboradores_sample.xlsx

python manage.py backfill_data_entrada \
  --colaboradores path/para/backup_colaboradores_sample.xlsx
```

**Esperado**: 1ª run preenche só `NULL`; demais campos intactos; 2ª run delta 0; **não** abre/fecha ciclo; **não** cria Avaliações.

### 3) Criar ciclo (ainda encerrado)

Via UI admin de ciclos (`CicloCreateView`) — nome + `data_inicio`/`data_fim`.  
**Esperado**: status `encerrado`; `admitidos_ate` pode ser NULL.

### 4) Abrir com corte + preview

1. Como admin, no fluxo de abertura: informar **Admitidos até = D**.
2. Conferir preview: 3 contagens (elegíveis / posterior / sem data).
3. POST **Abrir**.

**Esperado**:
- Ciclo `aberto` com `admitidos_ate = D`
- 1 Avaliacao por ativo elegível; 0 para posterior / sem data / inativos
- Mensagem **sem** “todos os ativos” / “colaboradores ativos” genérico
- Sem corte: erro visível; ciclo não abre; 0 Avaliações novas

### 5) Mid-cycle elegível / inelegível

Com ciclo aberto:

| Ação | Esperado |
|---|---|
| Cadastro/reativação ativo com entrada ≤ D | 1 Avaliacao |
| Ativo entrada > D ou sem data | 0 |
| Corrigir data de inelegível sem Avaliacao para ≤ D | pode criar 1 |
| Editar data de já matriculado para > D | Avaliacao **permanece** |

### 6) Ciclo 011 / arquivo intacto

Selecionar ciclo encerrado importado (`admitidos_ate IS NULL`).

**Esperado**: mesmo conjunto de Avaliações; zero criações/remoções por “reler” elegibilidade; imports 010/011/013/014 não exigem corte.

### 7) Gold denylist

```bash
# Exemplos — suite vigente sem mudar asserts alheios
pytest tests/test_stage_machine.py tests/test_scope.py -q
# + testes de rejeição / fórmula já existentes no repo
```

**Esperado**: verdes. `git diff` de comportamento vazio nos paths da [denylist](./contracts/non-goals-denylist.md) (exceto allowlist 015).

### 8) AuthZ preview

| Ator | Preview / Abrir |
|---|---|
| Admin | 200 / sucesso |
| Líder / colaborador | 403 |
| Anônimo | login |

Resposta do preview: **somente** contagens — sem lista de pessoas.

---

## Pytest focado (após implementação)

```bash
pytest \
  tests/test_open_cycle_admission_cutoff.py \
  tests/test_mid_cycle_enrollment.py \
  tests/test_backfill_data_entrada.py \
  -q
```

---

## Critérios SC (smoke)

| SC | Como ver |
|---|---|
| SC-001 / SC-002 | passo 4 |
| SC-003 / SC-004 | passo 5 |
| SC-005 | passo 6 |
| SC-006 | preview no passo 4 |
| SC-007 | passos 1–2 |
| SC-008 | mensagem no passo 4 |
| SC-009 | passo 7 |
