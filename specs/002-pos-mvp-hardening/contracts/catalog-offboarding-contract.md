# Contract: Catálogos soft-delete, unicidade e offboarding

**Apps**: `organization`, `competencies`, `accounts`, `audit`

## Soft-delete de catálogos

| Entidade | Remoção | Unicidade |
|---|---|---|
| `Area` | `is_active=False` | `UniqueConstraint(nome, condition=is_active)` |
| `Cargo` | `is_active=False` | idem |
| `Escala` | `is_active=False` (campo novo) | idem |
| `Competencia` | `is_active=False` (campo novo) | idem |

```python
# Views de “exclusão” → soft delete
def perform_destroy / post:
    instance.is_active = False
    instance.save(update_fields=['is_active', 'updated_at'])
```

**Seletores** (forms de criação de vínculos): queryset `filter(is_active=True)`.

**PROTECT**: hard-delete físico permanece proibido para registros referenciados; a UI padrão não oferece hard-delete.

## Reatribuição em lote

```python
# apps/accounts/services/offboarding.py

def reassign_direct_reports(
    *,
    from_manager: CustomUser,
    to_manager: CustomUser,
    actor: CustomUser,
) -> int:
    """
    Atualiza line_manager de todos os liderados ativos de from_manager → to_manager.
    Valida: to_manager.is_active; to_manager != from_manager; actor autorizado (admin/RH).
    Retorna quantidade atualizada.
    Auditoria: N AuditLog (line_manager_id) com actor.
    """
```

## Desativação (FR-028 preservado)

```text
IF user.direct_reports_active.exists():
    RAISE ValidationError  # desativação bloqueada
# após reassign completo (0 liderados ativos) → permitido
```

Reassign parcial (se UI filtrar subset) **não** libera desativação até zerar liderados ativos — serviço canônico reatribui **todos**.

## Contratos de teste

- Soft-delete de Área em uso: registro inativo; FK histórica ok.
- Criar segunda Área ativa com mesmo nome → ValidationError.
- Nome de inativo pode ser reutilizado por novo ativo.
- Gestor com N liderados: desativar falha; após lote, sucede.
- `to_manager` inativo → rejeita; liderados inalterados.
