# Contract: Path allowlist / denylist (referência de implementação)

**Feature**: `007-design-system-v2`  
**Task**: T004  
**Fonte**: [plan.md](../plan.md) (Source Code allowlist) + [research.md R4](../research.md#r4--components-e-superfícies-piloto-allowlist-de-código)  
**Uso**: Antes de editar qualquer arquivo nesta feature, confirmar que o path está na **allowlist**. Diff em path da **denylist** = falha de aceite (não trade-off).

---

## Allowlist (permitido)

### Freeze e tokens

| Path | Notas |
|---|---|
| `docs/design-system.md` | Freeze → v2 (draft na Phase 2; fechamento US5) |
| `static/src/input.css` | Tokens display/ui, `.app-shell`, table-frame, ritmo charts |
| `static/fonts/*` | Inter existente + novos WOFF2 Fraunces / Source Sans 3 (OFL) |
| `static/css/tailwind.css` | Apenas via rebuild CLI (`tailwindcss -i … -o …`) |

### Shell autenticado

| Path | Notas |
|---|---|
| `templates/base.html` | Classe `app-shell` no `<body>` (+ head tipografia se preciso) |

### Components compartilhados

| Path | Notas |
|---|---|
| `templates/components/button.html` | Variantes existentes only |
| `templates/components/card.html` | KPI / densidade |
| `templates/components/empty_state.html` | Acabamento visual |
| `templates/components/badge_status.html` | Tipografia/densidade; Status Triad hex intacto |
| `templates/components/sidebar.html` | Opcional pós P1–P4 — só densidade/tipografia (T044); sem redesign IA nav |
| `templates/components/topbar.html` | Idem sidebar |

### Superfícies piloto (templates)

| Área | Paths |
|---|---|
| Dashboard | `templates/dashboard/admin.html`, `team.html`, `personal.html`, `_chart_block.html` |
| Talent / 9-box | `templates/talent/matrix.html`, `partials/_cell.html`, `_person_card.html`, `_drawer.html` |
| Ciclos | `templates/cycles/ciclo_list.html`, `ciclo_list_partial.html` |
| Avaliações | `templates/reviews/avaliacao_list.html`, `avaliacao_list_partial.html` (se no conjunto de evidência) |
| PDI | `templates/pdi/pdi_detail.html`, `pdi_form.html` |

### JS de apresentação (visual only)

| Path | Escopo permitido |
|---|---|
| `static/js/dashboard_charts.js` | Options visuais Chart.js only (ver [chart-visual-polish.md](./chart-visual-polish.md)) |
| `static/js/ninebox_matrix.js` | Feedback visual / ARIA suporte only (ver [ninebox-visual-only.md](./ninebox-visual-only.md)) |

### Artefatos da feature (docs / evidência)

Paths sob `specs/007-design-system-v2/` (tasks, contracts, evidence, quickstart) — manutenção da própria feature, não código de produto.

---

## Denylist (proibido)

### Auth (isolamento duro)

| Path | Motivo |
|---|---|
| `templates/accounts/base_auth.html` | Base auth — diff MUST ser vazio |
| `templates/accounts/login.html` | Login — diff MUST ser vazio |
| Demais templates sob `templates/accounts/` que extendem `base_auth` | Herdam isolamento; não “alinhar” tipografia |

Ver [auth-surface-isolation.md](./auth-surface-isolation.md).

### Negócio / backend

| Padrão / área | Motivo |
|---|---|
| `apps/*/services*` | Lógica de negócio |
| `apps/*/models.py`, models em geral | Schema |
| `**/migrations/**` | Schema |
| Urls / views de negócio (novas ou alteração de contrato) | Rotas, AuthZ, payloads |
| Queries / AuthZ / fórmulas 005–006 | Contratos de produto intactos |
| Novas deps front / libs de chart | FR-012 |
| Redesign de grupos nav Governança / Cadastros / Sistema | FR-008 |

### Específico 006 (além do visual)

Denylist detalhada em [ninebox-visual-only.md](./ninebox-visual-only.md) (POST potencial-only, AuthZ, HTMX targets/URLs, a11y trap). Não criar `templates/components/drawer.html` canônico nesta feature.

---

## Árvore compacta (allowlist de código de produto)

```text
docs/design-system.md

static/
├── src/input.css
├── fonts/*                         # + novos WOFF2
├── css/tailwind.css                # rebuild only
└── js/
    ├── dashboard_charts.js         # options visuais
    └── ninebox_matrix.js           # feedback / ARIA

templates/
├── base.html                       # body.app-shell
├── components/
│   ├── button.html
│   ├── card.html
│   ├── empty_state.html
│   ├── badge_status.html
│   ├── sidebar.html                # opcional T044
│   └── topbar.html                 # opcional T044
├── dashboard/  admin|team|personal|_chart_block
├── talent/     matrix + partials (_cell|_person_card|_drawer)
├── cycles/     ciclo_list*.html
├── reviews/    avaliacao_list*.html
└── pdi/        pdi_detail.html | pdi_form.html
```

**Explicitamente fora**: `templates/accounts/base_auth.html`, `templates/accounts/login.html`, `apps/*/services`, models, migrations, urls/views de negócio.

---

## Verificação rápida (aceitação / T046)

```bash
# Diff auth — MUST vazio
git diff -- templates/accounts/base_auth.html templates/accounts/login.html

# Diff negócio sensível — MUST vazio (ajustar globs conforme mudanças staged)
git diff -- 'apps/*/services*' '**/migrations/**' 'apps/*/models.py'
```

Se um arquivo necessário **não** estiver na allowlist, **parar** e atualizar plan/research/contrato antes de editar — não “esticar” escopo ad hoc.
