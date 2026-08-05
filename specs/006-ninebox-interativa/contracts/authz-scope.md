# Contract: AuthZ e escopo — matriz interativa

**Feature**: `006-ninebox-interativa`  
**Princípio**: Constituição II — segurança no backend; UI não autoriza (FR-006, FR-008).

## Matriz de papéis

| Ação | Admin (`is_admin`) | Gerente (`is_manager`) | Líder puro (`is_leader` only) | Colaborador |
|---|---|---|---|---|
| `GET /talent/matrix/` | ✅ (escopo = todos via `get_visible_users`) | ✅ (escopo hierárquico) | ❌ 403 (gate atual — research R8) | ❌ 403 |
| Abrir drawer (leitura) | ✅ | ✅ no escopo | ❌ | ❌ |
| Salvar potencial / drag persist | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |
| Toggle `visivel_ao_colaborador` | ✅ | ❌ 403 | ❌ 403 | ❌ 403 |
| Ver própria 9-box (`/talent/mine/`) | conforme regras mine | conforme mine | conforme mine | ✅ **somente se** `visivel_ao_colaborador=True` |

Papéis cumulativos (admin + manager): escrita segue poder **admin**.

## Escopo de leitura

- Queryset da matriz: `ClassificacaoTalento` filtrado por ciclo + `usuario__in=get_visible_users(request.user).filter(is_active=True)` + filtros área/cargo.
- Drawer GET: MUST negar ou 404 se a pessoa **não** ∈ escopo do viewer (mesmo admin “global” já está no escopo; gerente não vê fora da hierarquia).
- Interações MUST NOT revelar pessoas fora do escopo (FR-007).

## Escrita e IDOR

| Tentativa | Resultado esperado |
|---|---|
| Não-admin POST potencial / toggle / move | 403 / `PermissionDenied`; zero mudança |
| Admin POST com `user_pk` inválido | 404 |
| Gerente forja POST com HTML/curl | 403 mesmo se UI omitir controles |
| Colaborador tenta inferir 9-box oculta via matriz | Sem acesso à matriz; mine não vaza dados se oculto |

Enforcement mínimo:

- Mixins: `RequiresAdminMixin` (writes), `RequiresManagerOrAdminMixin` (matrix page).
- Service: `upsert_classification(..., admin=)` → `PermissionDenied` se `not admin.is_admin`.
- Toggle: mesmo padrão no service/view.

## Gate colaborador (inalterado)

- Default `visivel_ao_colaborador=False`.
- Feature MUST NOT tornar 9-box visível por padrão (FR-009 / SC-007).
- `get_visible_classification_for_collaborator` permanece a fonte para `/talent/mine/`.

## Fora

- Expandir matriz a líderes puros; afrouxar gate de visibilidade; AuthZ só no frontend.
