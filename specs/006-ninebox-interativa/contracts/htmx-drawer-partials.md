# Contract: HTMX — Drawer e partials da matriz

**Feature**: `006-ninebox-interativa`  
**Stack**: DTL + HTMX 2.0.4 (CDN) + CSRF via `hx-headers` em `base.html`  
**Referência de padrão**: PDI (`HX-Trigger` → `showMessage`, partials HTML)

## Superfícies

| Ação | Método | Target sugerido | Resposta |
|---|---|---|---|
| Abrir drawer | `GET` | `#matrix-drawer` (`innerHTML`) | Partial `_drawer.html` (write ou read-only) |
| Salvar potencial | `POST` | drawer e/ou células afetadas | Partial drawer atualizado + swap de card/células; `HX-Trigger` sucesso/erro |
| Toggle visibilidade | `POST` | badge no drawer + card | Partials atualizados; toast |
| Refresh célula/grade | (após save/move) | `#cell-{desempenho}-{potencial}` ou fragmento grade | `_cell.html` / cards |

Nomes de rota finais em `apps/talent/urls.py` (internos, **não** API pública). Exemplos de intenção:

- `GET .../matrix/drawer/<user_pk>/?ciclo=`
- `POST .../matrix/potencial/<user_pk>/` (ciclo + potencial)
- `POST .../toggle-visibility/<pk>/` (existente, estendido para HTMX) **ou** action dedicada do drawer

## Regras

1. Request não-HTMX nos novos endpoints: redirect seguro para `talent:matrix` ou 405 — sem JSON.
2. Sucesso **nunca** reportado se persistência falhou (FR-005); erros em português no partial ou via `showMessage` level `error`.
3. Loading: usar `#htmx-indicator` (ou indicador local); não confundir loading com empty/sucesso.
4. Após save de potencial: quadrante refletido; card na célula `(desempenho_derivado, potencial_novo)`.
5. `classify` full-page permanece disponível como fallback (FR-013); não é o caminho HTMX principal.
6. Filtros GET da matriz (`ciclo`, `area`, `cargo`) devem ser propagados nos links/requests do drawer quando relevantes para coerência de refresh.

## AuthZ (detalhe em authz-scope)

- GET drawer: usuário com acesso à matriz + pessoa ∈ `get_visible_users`.
- POST potencial / toggle: **admin only**; 403/PermissionDenied caso contrário.
- Drawer read-only: sem controles de save/toggle no HTML para não-admin (UI); backend ainda nega POST.

## Fora

- Endpoints REST/DRF; payloads JSON como contrato principal; SPA; alterar fórmulas.
