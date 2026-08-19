# Contract: Resolução de Escopo

**App**: `accounts` (serviço compartilhado) | **Consumidores**: todos os apps com dados sensíveis

## Interface

```python
# apps/accounts/services/scope.py

def get_visible_users(requesting_user: CustomUser) -> QuerySet[CustomUser]:
    """Retorna queryset de usuários visíveis ao requesting_user."""

def user_in_scope(requesting_user: CustomUser, target_user_id: int) -> bool:
    """True se target_user_id está no escopo de requesting_user."""

def get_scope_level(user: CustomUser) -> Literal['collaborator', 'leader', 'manager', 'admin']:
    """Nível máximo de visão cumulativa do usuário."""
```

## Regras de visibilidade

| Nível | Condição | Queryset retornado |
|---|---|---|
| `admin` | `user.is_admin=True` | Todos os usuários (`User.objects.all()`) |
| `manager` | `is_leader` e liderados também lideram | Self + todos descendentes via `line_manager` (BFS) |
| `leader` | Existe ≥1 usuário com `line_manager=user` | Self + liderados diretos |
| `collaborator` | Default | Apenas `pk=user.pk` |

**Importante**: papéis são cumulativos — um gerente também vê seus próprios dados como colaborador.

## ScopedObjectMixin

```python
# apps/core/mixins.py

class ScopedObjectMixin:
    scope_user_field: str = 'usuario'  # FK no model alvo

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        visible = get_visible_users(self.request.user)
        return qs.filter(**{f'{self.scope_user_field}__in': visible})

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not user_in_scope(self.request.user, getattr(obj, self.scope_user_field).pk):
            log_scope_denied(self.request.user, obj)  # audit
            raise Http404()
        return obj
```

## Apps e campos de escopo

| App | Model | `scope_user_field` |
|---|---|---|
| `reviews` | Avaliacao | `usuario` |
| `reviews` | Feedback | `avaliacao__usuario` |
| `goals` | Meta | `usuario` |
| `pdi` | PDI | `usuario` |
| `pdi` | AcaoPDI | `pdi__usuario` |
| `talent` | ClassificacaoTalento | `usuario` |

## Exceções

- **Admin-only**: `Ciclo`, `Area`, `Cargo`, `Competencia`, `AuditLog` — `UserPassesTestMixin` com `is_admin`.
- **Colaborador sem vínculo**: visível apenas ao admin (listagem "usuários pendentes").
- **Aprovação sem gestor**: usuário `is_admin=True` atua como aprovador (RF-16.3).

## Auditoria de acesso negado (RF-36)

- Registro em `AuditLog` **somente** quando o registro existe mas está fora do escopo.
- ID inexistente → `Http404` sem auditoria.
- Mensagem UI genérica: "Você não tem acesso a este recurso ou ele não existe."
