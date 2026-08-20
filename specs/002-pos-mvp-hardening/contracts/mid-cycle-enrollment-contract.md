# Contract: Avaliação mid-cycle

**Apps**: `reviews`, `cycles`, `accounts`  
**Estendido por**: [015 eligibility-predicate-contract](../../015-cycle-admission-cutoff/contracts/eligibility-predicate-contract.md)  
**Nota 015**: a elegibilidade de matrícula **não** é mais “todos os ativos”; ver predicado abaixo.

## Interface

```python
# apps/reviews/services/enrollment.py

def ensure_avaliacao_for_user(user: CustomUser, ciclo: Ciclo | None = None) -> Avaliacao | None:
    """
    Se user inativo → None.
    Resolve ciclo aberto (ou usa `ciclo` se aberto; se encerrado → None).
    Se já existir Avaliacao(ciclo, usuario) → retorna existente (não remove; snapshot).
    Se not user_eligible_for_ciclo(user, ciclo) → None (no-op; não cria).
    Senão get_or_create Avaliacao(..., etapa=input_metas).
    """
```

```python
# apps/cycles/services/eligibility.py (015)

def user_eligible_for_ciclo(user: CustomUser, ciclo: Ciclo) -> bool:
    """
    True iff:
      user.is_active
      and user.data_entrada is not None
      and ciclo.admitidos_ate is not None
      and user.data_entrada <= ciclo.admitidos_ate  # date, inclusive
    """
```

## Pontos de invocação

| Evento | Comportamento |
|---|---|
| Cadastro de colaborador ativo | Chamar após commit do user — cria só se elegível pelo predicado 015 |
| Ativação (`is_active` False→True) | Chamar após save — mesma elegibilidade |
| Correção de `data_entrada` que passa a ≤ `admitidos_ate`, ciclo aberto, sem Avaliacao | `ensure` **pode** criar 1 |
| Edição de `data_entrada` após já matriculado | Avaliacao **permanece** (snapshot; nunca remove) |
| Abertura de ciclo (`open_cycle`) | Batch via `ensure_avaliacao_for_user` — **somente elegíveis** (não mais “todos os ativos”) |
| User inativo / sem ciclo aberto / ciclo encerrado / inelegível | Não cria (`None`) |

## Invariantes

1. No máximo **uma** Avaliação por `(ciclo, usuario)`.
2. Não criar Avaliação em ciclo `encerrado` ou `rascunho` (somente `aberto`).
3. Reativação rápida no mesmo ciclo: se Avaliação já existe, não duplicar; se não existe e user elegível + ciclo aberto, criar.
4. Elegibilidade = predicado único `user_eligible_for_ciclo` (015) — abertura e mid-cycle.
5. Inelegibilidade governa **criação** apenas — nunca remoção / desfazer etapa / fechar ciclo.
6. `NULL data_entrada` ou `NULL admitidos_ate` ⇒ nunca elegível (fail-closed).

## Contrato de teste

- Ciclo aberto + ativo elegível (`data_entrada` ≤ `admitidos_ate`) → 1 Avaliação.
- Ciclo aberto + ativo com entrada > D ou sem `data_entrada` → `None`, 0 Avaliações novas.
- Segundo save / segundo `ensure` sem mudança de elegibilidade → ainda 1 (mesma pk).
- Já matriculado + `data_entrada` editada para > D → Avaliacao **permanece**.
- Sem ciclo aberto / ciclo encerrado → 0 Avaliações novas.
- `open_cycle` **não** matricula “todos os ativos”; só quem passa no predicado 015.
