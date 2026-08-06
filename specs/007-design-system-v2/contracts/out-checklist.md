# Contract: Checklist OUT (aceite)

**Feature**: `007-design-system-v2` · US5  
**Refs**: FR-015, SC-002, SC-003, SC-006

Preencher no aceite. Itens críticos devem estar ✅.

## Login / auth (SC-002)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-LOGIN-DIFF | `templates/accounts/base_auth.html` e `login.html` sem diff nesta feature | `git diff` / `git log -p` | ✅ T011 (working tree vs HEAD vazio; sem edições 007) |
| OUT-LOGIN-VISUAL | Login pixel/comportamento inalterado vs before | screenshot + revisão | ☐ (before ✓ T003; after em T040) |
| OUT-AUTH-ISOLATION | Tipografia v2 só sob `.app-shell`; login sem a classe | DevTools / CSS | ✅ T011 (`body` = Inter/`font-sans`; `.app-shell` só em `base.html`) |

## Regressão 005 charts (SC-003)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-005-OPEN | Dashboard admin (e time) abrem com charts | smoke quickstart 005 | ☐ |
| OUT-005-EMPTY | Empty honesto sem fake data | smoke | ☐ |
| OUT-005-PAYLOAD | Sem mudança de shape/endpoints/métricas | review diff `apps/dashboard/**` | ☐ |
| OUT-005-TRIAD | Status Triad + labels textuais presentes | visual | ☐ |

## Regressão 006 ninebox (SC-003)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-006-OPEN | Matriz abre; empty correto | smoke quickstart 006 | ☐ |
| OUT-006-DRAWER | Drawer HTMX carrega partial | smoke | ☐ |
| OUT-006-DRAG | Drag potencial autorizado persiste; regras intactas | smoke admin | ☐ |
| OUT-006-AUTHZ | Sem expansão de Authz; líder puro sem write | smoke / review | ☐ |

## Sem produto novo (SC-006)

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-NO-ROUTES | Sem rotas/views/models/migrations novas de domínio | diff | ☐ |
| OUT-NO-DEPS | Sem lib front nova (Alpine/React/Sortable/chart lib) | package/CDN/diff | ☐ |
| OUT-NO-NAV-IA | Grupos Governança/Cadastros/Sistema intactos | visual nav | ☐ |
| OUT-NO-BUSINESS | Sem mudança AuthZ/fórmulas/queries de negócio | review `apps/**/services` | ☐ |

## Freeze / evidência

| ID | Critério | Método | Pass |
|---|---|---|---|
| OUT-FREEZE-V2 | `docs/design-system.md` declara Freeze v2 cobrindo tipografia, botões, cards, charts, ninebox | review doc | ☐ |
| OUT-EVIDENCE | 5–8 before/after autenticados (sem login como “melhoria”) | pasta evidence | ☐ |

**Aceite US5**: todos os itens críticos ☑.
