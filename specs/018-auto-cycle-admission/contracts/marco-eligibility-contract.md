# Contract: Elegibilidade por marco de admissão

**Refs**: FR-001…FR-005, FR-008, FR-017; [data-model.md](../data-model.md); 015 [eligibility-predicate-contract.md](../../015-cycle-admission-cutoff/contracts/eligibility-predicate-contract.md)

## Predicado manual (015) — INTACTO

```text
user_eligible_for_ciclo(user, ciclo)  # admitidos_ate
  = ativo ∧ data_entrada ∧ data_entrada ≤ ciclo.admitidos_ate
```

Usado por abertura manual e mid-cycle em ciclos **manuais**.

## Predicado automático (018)

```text
next_future_marco(data_entrada, ref_date) -> (year, month)
  # menor mês na série admissão+6k que é >= mês(ref_date)

user_is_auto_candidate(user, *, year, month, ref_date) -> bool
  = user.is_active
    ∧ user.data_entrada is not None
    ∧ next_future_marco(user.data_entrada, ref_date) == (year, month)

user_blocked_by_open_cycle(user) -> bool
  = exists Avaliacao(usuario=user, ciclo__status=aberto)
    # default FR-008

user_eligible_for_auto_enrollment(user, *, year, month, ref_date) -> bool
  = user_is_auto_candidate(...) ∧ ¬ user_blocked_by_open_cycle(user)
```

## Bootstrap

- `next_future_marco` **nunca** retorna mês < mês(ref) na série passada “para recuperar”.
- Go-live / rotina em dia que não é 1º dia útil: **0** aberturas atrasadas daquele mês.

## Mudança de `data_entrada`

| Situação | Efeito |
|---|---|
| Avaliacao já existe | Permanece (snapshot) |
| Correção antes/no dia da janela idempotente do lote e ainda candidata | Pode entrar no ensure da coorte existente se elegível |
| Após janela / marco passado | Espera **próximo** marco futuro — sem backfill |

## Inativos / sem data

- Inativo: nunca candidato.
- Sem data: nunca candidato; visível como pendência de cadastro na governança (contagem/eventos), não como “erro vermelho” de sistema.

## Separação de caminhos

| Ciclo.origem | Predicado de ensure |
|---|---|
| `manual` | 015 `user_eligible_for_ciclo` |
| `automatico` | elegibilidade da coorte daquele `marco_competencia` (+ ¬ FR-008 na criação do lote; ensure posterior não “cura” bloqueio do dia sem regra explícita) |
