# Contract: Checklist OUT (aceite)

**Feature**: `007-design-system-v2` · US5  
**Refs**: FR-015, SC-002, SC-003, SC-006  
**Preenchido**: T041 · 2026-08-06  
**Baseline de feature**: merge `006-ninebox-interativa` (`cdded62`) → `HEAD` (+ working tree allowlisted)

Itens críticos devem estar ✅.

## Login / auth (SC-002)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-LOGIN-DIFF | `templates/accounts/base_auth.html` e `login.html` sem diff nesta feature | `git diff` / `git log -p` | ✅ `git diff cdded62..HEAD -- templates/accounts/` vazio; working tree vs HEAD auth vazio (T011) |
| OUT-LOGIN-VISUAL | Login pixel/comportamento inalterado vs before | screenshot + revisão | ✅ T040 — `login-unchanged-after.png` byte-idêntico ao before (SHA256 `05193c9e…bd3dc`; 268523 bytes; 1280×900) |
| OUT-AUTH-ISOLATION | Tipografia v2 só sob `.app-shell`; login sem a classe | DevTools / CSS | ✅ T011 — login sem `app-shell`; Inter via `--font-sans`; v2 só em `templates/base.html` + `.app-shell` |

## Regressão 005 charts (SC-003)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-005-OPEN | Dashboard admin (e time) abrem com charts | smoke quickstart 005 | ✅ T031 + T041 smoke Docker (`Client` + `HTTP_HOST=localhost`): `/dashboard/admin/` e `/dashboard/team/` → **200**; Chart.js CDN **4.5.1**; `dashboard-chart-canvas` presente; evidência `01-…-after.png` / `02-…-after.png` |
| OUT-005-EMPTY | Empty honesto sem fake data | smoke | ✅ JS `has_data !== true` não cria Chart / não inventa zeros (`dashboard_charts.js`); admin smoke com `has_data: false` + `empty_message` no HTML; bloco usa empty honesto (`_chart_block.html`) |
| OUT-005-PAYLOAD | Sem mudança de shape/endpoints/métricas | review diff `apps/dashboard/**` | ✅ `git diff cdded62..HEAD -- apps/dashboard/chart_payloads.py urls.py views.py services models migrations` **vazio**; só options/CSS/markup (`static/js/dashboard_charts.js`, `_chart_block.html`, `input.css`) |
| OUT-005-TRIAD | Status Triad + labels textuais presentes | visual | ✅ Smoke: `figcaption` + `legend_items` no admin/team; doc Freeze mantém Triad `#059669` / `#d97706` / `#e11d48`; polish não altera cores de negócio |

## Regressão 006 ninebox (SC-003)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-006-OPEN | Matriz abre; empty correto | smoke quickstart 006 | ✅ T037 + T041: `/talent/matrix/` admin → **200**, root ninebox + cards; template empty `#ninebox-matrix-empty` preservado (empty quando zero classificados); after `04-talent-matrix-after.png` |
| OUT-006-DRAWER | Drawer HTMX carrega partial | smoke | ✅ `GET /talent/matrix/drawer/<pk>/` com `HX-Request: true` → **200**; partial com `hx-post` / `hx-target` intactos; sem `templates/components/drawer.html` canônico novo |
| OUT-006-DRAG | Drag potencial autorizado persiste; regras intactas | smoke admin | ✅ T041: `POST /talent/matrix/move/<pk>/` (HX) admin → **200** (move + restore); diff `ninebox_matrix.js` só ARIA/visual (sem mudança de `postMove` / potencial-only) |
| OUT-006-AUTHZ | Sem expansão de Authz; líder puro sem write | smoke / review | ✅ `lider@` → matriz **403** (sem write); zero diff em `apps/talent/views.py` / `urls.py` / `services/**` no delta 007 |

## Sem produto novo (SC-006)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-NO-ROUTES | Sem rotas/views/models/migrations novas de domínio | diff | ✅ Delta `cdded62..HEAD`: denylist `apps/**/models`, `migrations`, `urls`/`views`/`services` de domínio **vazia**; mudanças só allowlist (templates/static/docs/specs) |
| OUT-NO-DEPS | Sem lib front nova (Alpine/React/Sortable/chart lib) | package/CDN/diff | ✅ Sem `package.json` de app; CDN Chart.js permanece **4.5.1** em dashboards; HTMX 2.0.4 intacto; sem Alpine/React/Sortable |
| OUT-NO-NAV-IA | Grupos Governança/Cadastros/Sistema intactos | visual nav | ✅ `git diff cdded62..HEAD -- templates/components/nav_menu.html` **0 bytes**; smoke admin HTML contém os 3 grupos |
| OUT-NO-BUSINESS | Sem mudança AuthZ/fórmulas/queries de negócio | review `apps/**/services` | ✅ Diff `apps/**/services*` no delta 007 **vazio**; contratos 005/006 preservados (payloads/POST potencial-only) |

## Freeze / evidência

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-FREEZE-V2 | `docs/design-system.md` declara Freeze v2 cobrindo tipografia, botões, cards, charts, ninebox | review doc | ✅ Status **Freeze v2** (T038); tabela de cobertura: tipografia, botões, cards/KPI/table-frame/empty, charts polish, ninebox polish |
| OUT-EVIDENCE | 5–8 before/after autenticados (sem login como “melhoria”) | pasta evidence | ✅ **6** pares autenticados `01`–`06` (`*-before.png` + `*-after.png`); login só `login-unchanged-*` (isolamento, fora do SC-001) — ver `evidence/before-after/README.md` |

**Aceite US5 (OUT)**: todos os itens críticos ✅ (T041). Scan guiado SC-001/SC-005 ✅ (T042). Scan final de escopo ✅ (T043) — OUT-NO-* / accounts / nav IA reconfirmados; ver `evidence/before-after/README.md` § T043.

---

## Aceite final / denylist (T046)

**Data**: 2026-08-07 · **Baseline**: `cdded62` (merge 006) → `HEAD` + working tree allowlisted

| Checagem | Comando / escopo | Resultado |
|---|---|---|
| Auth templates | `git diff cdded62..HEAD -- templates/accounts/base_auth.html templates/accounts/login.html` (+ `templates/accounts/`) | **0 bytes** (HEAD e working tree) |
| Services | `apps/**/services*` | **sem diff** |
| Models | `apps/**/models.py`, `apps/**/models/**` | **sem diff** |
| Migrations | `**/migrations/**` | **sem diff** |
| Negócio 005 | `apps/dashboard/{chart_payloads,urls,views}.py` | **0 bytes** |
| Negócio 006 | `apps/talent/{views,urls}.py` | **0 bytes** |
| Nav IA | `templates/components/nav_menu.html` | **0 bytes** |
| Interseção denylist vs paths alterados (delta + WT) | grep `accounts/` / `services` / `models` / `migrations` | **(none)** |

**Working tree allowlisted remanescente** (não denylist): `docs/design-system.md`, `static/src/input.css`, `static/css/tailwind.css`, `templates/components/{sidebar,topbar}.html`, evidência `08-shell-chrome-*`, specs — coerente com T044/T045.

**Fechamento**: T046 ✅ — denylist limpa; OUT crítico permanece 100% ✅; feature `007-design-system-v2` aceitável formalmente (Freeze v2 + evidência + isolamento auth + zero diff de negócio na denylist).
