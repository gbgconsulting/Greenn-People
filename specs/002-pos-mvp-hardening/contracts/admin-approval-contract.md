# Contract: Aprovação administrativa (gestor ausente)

**Apps**: `goals`, `audit`, `accounts`

## Regra de aprovador

```python
# apps/goals/services/approval.py — _ensure_approver

def _ensure_approver(meta: Meta, approver: CustomUser) -> None:
    if getattr(approver, 'is_admin', False):
        return  # exceção RH — FR-014
    manager_id = meta.usuario.line_manager_id
    if manager_id is None:
        raise PermissionDenied(...)  # sem gestor e sem admin
    if approver.pk != manager_id:
        raise PermissionDenied(...)
```

## Escopo de visibilidade (não muda)

- Líderes comuns: `get_visible_users` + `ScopedObjectMixin` — fora do escopo → 403/404.
- Admin: já possui visão administrativa; override é **só** de ação de aprovação, não concede power a não-admins.

## Auditoria

- Toda mudança de `Meta.status` / `Meta.status_resultado` gera `AuditLog` com `actor` = usuário autenticado no request (`audit_actor`), inclusive admin.
- Aprovar item já aprovado / fora de etapa elegível: rejeitar sem escrever “sucesso” falso.

## UI

- Partials de meta/resultado: se `request.user.is_admin` e item `pendente`, exibir ações de aprovar/reprovar (além do gestor).
- Não criar surface de “aprovar qualquer um da empresa” para `is_leader` sem admin.

## Contratos de teste

- Admin aprova com gestor presente → status aprovado + AuditLog.actor = admin.
- Líder fora do escopo → PermissionDenied / 403.
- Líder do colaborador continua podendo aprovar (fluxo feliz).
