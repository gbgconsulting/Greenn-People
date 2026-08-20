# Contract: Predicado de elegibilidade + open_cycle + ensure

**Feature**: `015-cycle-admission-cutoff`  
**Apps**: `cycles`, `reviews`, `accounts`  
**Estende**: [mid-cycle-enrollment-contract.md](../../002-pos-mvp-hardening/contracts/mid-cycle-enrollment-contract.md)  
**Fonte**: FR-003…FR-006, FR-015, FR-024; [research.md](../research.md) R3/R4

---

## Interface

```python
# apps/cycles/services/eligibility.py (novo)

def user_eligible_for_ciclo(user: CustomUser, ciclo: Ciclo) -> bool:
    """
    True iff:
      user.is_active
      and user.data_entrada is not None
      and ciclo.admitidos_ate is not None
      and user.data_entrada <= ciclo.admitidos_ate  # date, inclusive
    """
```

```python
# apps/reviews/services/enrollment.py (ESTENDER)

def ensure_avaliacao_for_user(
    user: CustomUser,
    ciclo: Ciclo | None = None,
) -> Avaliacao | None:
    """
    Se user inativo → None.
    Resolve ciclo aberto (ou usa `ciclo` se aberto; se encerrado → None).
    Se já existir Avaliacao(ciclo, usuario) → retorna existente (não remove).
    Se not user_eligible_for_ciclo(user, ciclo) → None (no-op; não cria).
    Senão get_or_create Avaliacao(..., etapa=input_metas).
    """
```

```python
# apps/cycles/services/cycle.py (ESTENDER open_cycle)

def open_cycle(ciclo: Ciclo, *, admitidos_ate: date | None = None) -> Ciclo:
    """
    atomic:
      lock ciclo
      CycleAlreadyOpenError se já aberto / outro aberto (intacto)
      resolve admitidos_ate (arg ou locked.admitidos_ate)
      se ausente → CycleMissingCutoffError; status NÃO abre; 0 Avaliações
      persiste admitidos_ate; status=aberto; save
      para cada ativo: ensure_avaliacao_for_user(user, ciclo=locked)
      return locked
    """
```

`close_cycle` — **DIFF VAZIO** de comportamento (fora deste contract).

---

## Pontos de invocação

| Evento | Comportamento 015 |
|---|---|
| Abertura (`open_cycle`) | Batch via `ensure`; só elegíveis criam Avaliacao |
| Cadastro ativo / reativação | `ensure` (RegisterForm / UserUpdateForm) — mesma elegibilidade |
| Correção de `data_entrada` que passa a ≤ D, ciclo aberto, sem Avaliacao | `ensure` **pode** criar 1 |
| Edição de `data_entrada` após já matriculado | Avaliacao **permanece** |
| Ciclo encerrado | `ensure` → None |

---

## Invariantes

1. Predicado **único** — abertura e mid-cycle.
2. `NULL data_entrada` ⇒ nunca elegível.
3. `NULL admitidos_ate` no predicado ⇒ False; `open_cycle` falha **antes** de matricular.
4. Elegibilidade governa **criação** apenas — nunca remoção/desfazer etapa/fechar.
5. No máximo **uma** Avaliação por `(ciclo, usuario)`.
6. Backend é a fonte da regra; UI não decide.

---

## Contrato de teste

| Cenário | Esperado |
|---|---|
| Ativo entrada ≤ D, open | 1 Avaliacao |
| Ativo entrada > D / sem data / inativo | 0 |
| Mid-cycle elegível | 1 |
| Mid-cycle inelegível | None, 0 novas |
| Já existe + data muda para > D | Avaliacao permanece |
| Segundo ensure | mesma pk, count=1 |

---

## Atualização obrigatória do contrato 002

No merge desta feature, o arquivo  
`specs/002-pos-mvp-hardening/contracts/mid-cycle-enrollment-contract.md`  
MUST ser editado para:

- Remover a frase de abertura “todos ativos” / batch compatível “todos”.
- Documentar o predicado e o no-op por inelegibilidade.
- Manter pontos de invocação e invariante de unicidade.
