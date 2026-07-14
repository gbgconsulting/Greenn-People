# Contract: Avaliação mid-cycle

**Apps**: `reviews`, `cycles`, `accounts`

## Interface

```python
# apps/reviews/services/enrollment.py (novo)

def ensure_avaliacao_for_user(user: CustomUser, ciclo: Ciclo | None = None) -> Avaliacao | None:
    """
    Se user.is_active e existir ciclo aberto (ou `ciclo` passado e aberto):
      get_or_create Avaliacao(ciclo, usuario) com etapa=input_metas.
    Se já existir: retorna existente (sem duplicar).
    Se sem ciclo aberto / user inativo: retorna None (no-op).
    """
```

## Pontos de invocação

| Evento | Comportamento |
|---|---|
| Cadastro de colaborador ativo | Chamar após commit do user |
| Ativação (`is_active` False→True) | Chamar após save |
| Abertura de ciclo (`open_cycle`) | Continua batch `get_or_create` para todos ativos (compatível) |
| User inativo / sem ciclo aberto | Não cria |

## Invariantes

1. No máximo **uma** Avaliação por `(ciclo, usuario)`.
2. Não criar Avaliação em ciclo `encerrado` ou `rascunho` (somente `aberto`).
3. Reativação rápida no mesmo ciclo: se Avaliação já existe, não duplicar; se não existe e user ativo + ciclo aberto, criar.

## Contrato de teste

- Ciclo aberto + novo ativo → 1 Avaliação.
- Segundo save sem mudança de elegibilidade → ainda 1.
- Sem ciclo aberto → 0 Avaliações novas.
