# Data Model: Design System v2 (apresentação)

**Branch**: `007-design-system-v2` | **Date**: 2026-08-06  
**Spec**: [spec.md](./spec.md)

> **Zero models Django.** Este artefato modela entidades de *apresentação/documentação* para planejamento e aceite. Nenhuma migration, ORM ou tabela nova.

---

## Entities

### Freeze Design System v2

| Campo | Tipo | Descrição |
|---|---|---|
| `status` | enum | `Freeze v2` (substitui congelamento 004 para decisões listadas) |
| `document_path` | path | `docs/design-system.md` |
| `css_path` | path | `static/src/input.css` |
| `typography` | object | Display (Fraunces) + UI (Source Sans 3); Inter permanece default global auth |
| `components_covered` | list | button, cards/KPI, table-frame, empty_state, charts polish, ninebox polish |
| `pilot_surfaces` | list[SuperfíciePiloto] | 5–8 itens autenticados |
| `auth_isolation` | bool | MUST be true (FR-002) |
| `evidence_dir` | path | `specs/007-design-system-v2/evidence/before-after/` |

**Validation**:
- Doc e CSS atualizados na mesma entrega (FR-009)
- Declara tipografia, botões, cards/KPI, charts, ninebox (SC-004)
- Não inclui login como superfície de “melhoria”

**State**: `Draft freeze` → `Freeze v2 published` (fechamento US5)

---

### Superfície piloto

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | string | `01`…`08` |
| `slug` | string | ex. `dashboard-admin-charts` |
| `template_paths` | list[path] | Templates DTL envolvidas |
| `requires_auth` | bool | sempre `true` |
| `is_login` | bool | sempre `false` (OUT) |
| `before_artifact` | path? | `NN-slug-before.png` |
| `after_artifact` | path? | `NN-slug-after.png` |
| `scan_notes` | text? | Observação do revisor (SC-001/005) |

**Conjunto sugerido** (research R10): admin charts, team, pessoal, talent-matrix, lista-ciclos, pdi/form, (opcional) avaliações, (opcional) shell-chrome.

**Validation**: 5 ≤ count ≤ 8 com before+after; nenhuma é login.

---

### Componente de apresentação compartilhado

| Campo | Tipo | Descrição |
|---|---|---|
| `name` | string | `button` \| `badge_status` \| `empty_state` \| `card` (KPI) \| padrões table-frame |
| `template_path` | path | sob `templates/components/` |
| `variants` | list | Semântica existente (ex. button: primary/secondary/outlined/loading) |
| `allowed_changes` | list | classes, densidade, tipografia, hover/focus visual |
| `forbidden_changes` | list | novas actions, novos variants de negócio, AuthZ |

**Relationships**: Consumido por Superfície piloto; documentado no Freeze v2.

---

### Token tipográfico v2

| Campo | Tipo | Descrição |
|---|---|---|
| `token_name` | string | `--font-display`, `--font-ui`, (legado) `--font-sans` |
| `family` | string | Fraunces / Source Sans 3 / Inter |
| `scope` | enum | `app-shell` \| `global-body` |
| `files` | list | WOFF2 sob `static/fonts/` |
| `must_not_affect_auth` | bool | true para display/ui aplicados só em `.app-shell` |

**Validation**: `--font-sans` / `body` global permanecem Inter; display/ui não sobrescrevem auth.

---

### Checklist OUT

| Campo | Tipo | Descrição |
|---|---|---|
| `item_id` | string | ex. `OUT-LOGIN`, `OUT-005`, `OUT-006`, `OUT-DEPS` |
| `description` | text | Critério verificável |
| `verification_method` | enum | `git-diff` \| `visual` \| `smoke-path` \| `dep-scan` |
| `passed` | bool? | Preenchido no aceite US5 |
| `evidence` | text? | Link/nota |

**Items canônicos**: ver [contracts/out-checklist.md](./contracts/out-checklist.md) (FR-015, SC-002/003/006).

**State**: `empty` → `filled at acceptance` — aceite bloqueado se algum item crítico = false.

---

## Relationships (apresentação)

```text
Freeze v2
  ├── documents → Token tipográfico v2
  ├── documents → Componente de apresentação (N)
  ├── references → Superfície piloto (5–8)
  └── requires → Checklist OUT (pass)

Superfície piloto
  └── consumes → Componentes + tokens (via shell .app-shell)

Charts polish / Ninebox polish
  └── are facets of → Freeze v2 (não entidades de domínio)
```

## Estado / transições

| Entidade | Transições |
|---|---|
| Freeze | 004 frozen → (decisão 007) reaberto → **Freeze v2** na mesma entrega |
| Evidência piloto | before capturado → after capturado → revisado (SC-001) |
| Checklist OUT | rascunho → todos críticos ✅ no aceite |

## Fora deste modelo

Modelos Django de `accounts`, `cycles`, `reviews`, `talent`, `dashboard`, payloads de chart, fórmulas de potencial/desempenho — **intocados**.
