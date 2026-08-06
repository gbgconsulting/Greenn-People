# Evidence: before / after — Design System v2

**Feature**: `007-design-system-v2`  
**Padrão**: espelha `specs/004-ux-visual-foundation/evidence/before-after/`  
**Confirmação scaffold**: T001 · 2026-08-06

## Convenção de nomes (congelada)

```text
NN-<slug>-before.png
NN-<slug>-after.png
```

- IDs `01`–`08`, zero-padded.
- Todos os PNGs ficam **neste diretório**, ao lado deste README.
- Viewport desktop consistente (~1280px); anotar resolução no aceite se útil.
- Capturar **5 a 8** pares autenticados (SC-001 / FR-010).

### Login — isolamento (não conta para SC-001)

Login **não** usa ID `NN` nem conta como evidência de melhoria. Arquivos dedicados:

```text
login-unchanged-before.png
login-unchanged-after.png
```

## Pilotos (FR-010 / research R10)

| ID | Slug | Arquivo before | Arquivo after | Superfície | Template(s) | Obrigatório? |
|---|---|---|---|---|---|---|
| 01 | `dashboard-admin-charts` | `01-dashboard-admin-charts-before.png` | `01-dashboard-admin-charts-after.png` | Dashboard admin + charts | `templates/dashboard/admin.html` (+ `_chart_block`) | Sim |
| 02 | `dashboard-team` | `02-dashboard-team-before.png` | `02-dashboard-team-after.png` | Dashboard time | `templates/dashboard/team.html` | Sim |
| 03 | `dashboard-pessoal` | `03-dashboard-pessoal-before.png` | `03-dashboard-pessoal-after.png` | Dashboard pessoal / gaps | `templates/dashboard/personal.html` | Sim |
| 04 | `talent-matrix` | `04-talent-matrix-before.png` | `04-talent-matrix-after.png` | Matriz 9-box | `templates/talent/matrix.html` | Sim |
| 05 | `lista-ciclos` | `05-lista-ciclos-before.png` | `05-lista-ciclos-after.png` | Lista de ciclos | `templates/cycles/ciclo_list.html` | Sim |
| 06 | `pdi-detail` | `06-pdi-detail-before.png` | `06-pdi-detail-after.png` | PDI detalhe ou form | `templates/pdi/pdi_detail.html` / `pdi_form.html` | Sim |
| 07 | `avaliacoes-list` | `07-avaliacoes-list-before.png` | `07-avaliacoes-list-after.png` | Lista avaliações | `templates/reviews/avaliacao_list.html` | Opcional |
| 08 | `shell-chrome` | `08-shell-chrome-before.png` | `08-shell-chrome-after.png` | Shell sidebar/topbar | `base.html` + `sidebar` / `topbar` | Opcional (após P1–P4) |

**Conjunto mínimo para SC-001**: IDs `01`–`06` (6 pares). Completar até 8 com `07` e/ou `08` se capturados.

## Status de captura

Baseline **before** capturado em 2026-08-06 · viewport **1280×900** · stack Docker local · contas seed `admin@` / `lider@` / `colab@test.greenn.com.br`.

| Artefato | Before | After | Notas |
|---|---|---|---|
| 01 dashboard-admin-charts | ✓ T002 `01-…-before.png` | ✓ T039 `01-…-after.png` | Conta admin · `/dashboard/admin/` |
| 02 dashboard-team | ✓ T002 `02-…-before.png` | ✓ T039 `02-…-after.png` | Conta líder · `/dashboard/team/` |
| 03 dashboard-pessoal | ✓ T002 `03-…-before.png` | ✓ T039 `03-…-after.png` | Conta colab · `/` |
| 04 talent-matrix | ✓ T002 `04-…-before.png` | ✓ T039 `04-…-after.png` | Conta admin · `/talent/matrix/` |
| 05 lista-ciclos | ✓ T002 `05-…-before.png` | ✓ T039 `05-…-after.png` | Conta admin · `/cycles/` |
| 06 pdi-detail | ✓ T002 `06-…-before.png` | ✓ T039 `06-…-after.png` | Conta admin · `/pdi/9/` |
| 07 avaliacoes-list (opc.) | ☐ | ☐ | Não incluído no conjunto T002 |
| 08 shell-chrome (opc.) | ☐ | ☐ | Só se shell leve for feito (T044) |
| Login isolamento | ✓ T003 `login-unchanged-before.png` | ✓ T040 `login-unchanged-after.png` | **Não** conta para SC-001 · `/accounts/login/` · viewport 1280×900 · **indistinguível** (SHA256 idêntico) |

### After (T039) — 2026-08-06

Pós-polish Design System v2 · viewport **1280×900** · Docker local · mesmas contas/rotas do before · seed `scripts/seed_evidence_007.py` (idempotente; PDI `/pdi/9/`).

### Login unchanged after (T040) — 2026-08-06

| Checagem | Resultado |
|---|---|
| Arquivo | `login-unchanged-after.png` · `/accounts/login/` · viewport **1280×900** |
| Comparação vs before | ✓ **byte-idêntico** (SHA256 `05193c9e…bd3dc`; 268523 bytes; max Δ canal = 0) |
| Conclusão | Isolamento visual confirmado — login indistinguível pós Design System v2 |

## Scan guiado SC-001 / SC-005 (T042) — 2026-08-06

Revisor de aceite (único) · ≤ ~10 s por piloto · pares `01`–`06` + controle login · viewport **1280×900**.

### SC-001 — melhoria perceptível (≥5 superfícies autenticadas; login fora)

| ID | Superfície | Distingue ≤10s? | Melhoria perceptível (notas) |
|---|---|---|---|
| 01 | Dashboard admin + charts | ✓ | Título display (serif) vs Inter plano; KPIs + bloco de charts com ritmo/chrome; empty honest intacto |
| 02 | Dashboard time | ✓ | Hierarquia display no H1; bloco chart + table-frame mais definidos |
| 03 | Dashboard pessoal | ✓ | Títulos display (página + seção chart); KPIs com densificação v2 |
| 04 | Matriz 9-box | ✓ | Células vazias (`VAZIO` + ícone vs `—`); person card e densidade da grade refinados |
| 05 | Lista de ciclos | ✓ | Título display; table-frame (bordas/ritmo) mais limpo |
| 06 | PDI detalhe | ✓ | H1 display + KPIs/table com densidade v2; CTAs alinhados ao botão Freeze |
| — | Login (controle) | ✗ (esperado) | **Indistinguível** — não conta como melhoria |

**Resultado SC-001:** **6/6** pilotos autenticados com melhoria perceptível (meta ≥5). Login excluído.

### SC-005 — tipografia citada (≥3 superfícies, revisor único)

Tipografia (Fraunces **display** em títulos vs Source Sans 3 / stack UI no corpo) citada explicitamente em:

| # | Superfície | Citação tipográfica |
|---|---|---|
| 1 | 01 admin | H1 “Painel administrativo” em display serif — contraste imediato vs before sans |
| 2 | 02 team | H1 “Painel do time” em display |
| 3 | 03 pessoal | H1 “Meu painel” + título do bloco chart em display |
| 4 | 05 ciclos | H1 “Ciclos de avaliação” em display |
| 5 | 06 PDI | H1 “PDI Evidência DS v2” em display (também perceptível; reforço) |

**Resultado SC-005:** tipografia citada em **≥5** superfícies (meta ≥3). Superfície 04 (matriz) contribui mais por empty/cards do que por display headline no first glance.

### Conclusão T042

| Critério | Meta | Resultado |
|---|---|---|
| SC-001 | ≥5 superfícies autenticadas | ✓ **6** |
| SC-005 | tipografia em ≥3 | ✓ **≥5** |
| Login | não conta / inalterado | ✓ |

## Scan final de escopo (T043) — 2026-08-06

Baseline feature: merge `006-ninebox-interativa` (`cdded62`) → `HEAD` + working tree allowlisted. Contratos: OUT-NO-* / FR-008 / path-allowlist.

| Critério | Método | Resultado |
|---|---|---|
| Sem libs front novas | `package.json`/lockfiles; CDN; busca Alpine/React/Sortable/Vue | ✓ PASS · sem lock/package de app no delta; Chart.js CDN **4.5.1** inalterado; HTMX **2.0.4** em `base.html`; zero Alpine/React/SortableJS; `static/` só fonts WOFF2 + CSS/JS allowlisted (sem `vendor/`/`lib/` novos) |
| Sem rotas/models/migrations | `git diff cdded62 -- apps/` | ✓ PASS · **vazio** (models, migrations, urls, views, services) |
| `templates/accounts/*` intocados | `git diff cdded62 -- templates/accounts/` (+ WT vs HEAD) | ✓ PASS · **vazio**; árvore accounts sem mudanças |
| Nav Governança/Cadastros/Sistema | `git diff` `nav_menu.html` + labels | ✓ PASS · **0 bytes**; labels `Governança` / `Cadastros` / `Sistema` presentes (FR-008) |

**Notas:** `tailwind.config.js` (+1 content glob `./static/js/**/*.js`) não adiciona plugin/lib. Artefatos `specs/007-design-system-v2/**`, `scripts/seed_evidence_007.py` e PNGs de evidência estão fora do código de produto. OUT-NO-DEPS / OUT-NO-ROUTES / OUT-NO-NAV-IA / OUT-LOGIN-DIFF reconfirmados — ver `contracts/out-checklist.md`.

**Conclusão T043:** escopo da feature **dentro** da allowlist; denylist de produto/auth/nav IA intacta.

## Verificação de isolamento auth (T011) — 2026-08-06

| Checagem | Resultado |
|---|---|
| `git diff` `templates/accounts/base_auth.html` `templates/accounts/login.html` (working tree vs HEAD) | ✓ vazio |
| Classe `app-shell` em templates auth | ✓ ausente |
| Body efetivo do login (`base_auth` + `body_class`) | `min-h-screen bg-white text-slate-800 antialiased …` (sem `app-shell`) |
| Tipografia efetiva | ✓ Inter via `--font-sans` + `body { font-family: var(--font-sans) }`; v2 só sob `.app-shell` em `base.html` |
| OUT checklist | T041 — todos os itens OUT ✅ (`contracts/out-checklist.md`) |

## Validação US1 — quickstart §1 (T018) — 2026-08-06

Stack Docker local; markup via `Client.force_login` (sem alterar senhas seed).

| # | Passo (quickstart §1) | Resultado |
|---|---|---|
| 1 | Dashboard admin — hierarquia display vs UI | ✓ PASS · `font-display` em h1 + 3/3 h2; corpo sob `.app-shell` (Source Sans 3); `font-display` count=7 |
| 2 | Team + lista ciclos — mesma hierarquia | ✓ PASS · team h1+2/2 h2 display; cycles h1 display + ênfases; ambos com `app-shell` |
| 3 | `/accounts/login/` visual/markup isolado | ✓ PASS · body sem `app-shell`; sem `font-display`/`font-ui` no HTML; HTTP 200 |
| 4 | `git diff` auth templates | ✓ PASS · working tree + staged = 0 bytes |
| 5 | Tipografia efetiva no login | ✓ PASS · `body { font-family: var(--font-sans) }` = Inter; `.app-shell` / `--font-display` só no app autenticado |

**Conclusão T018:** US1 aceite via quickstart §1 — tipografia v2 nos pilotos autenticados; auth intacto. Pares `*-after.png` / `login-unchanged-after.png` ficam para T039/T040 (US5).

## Confirmação de scaffold (T001)

Verificado em 2026-08-06:

| Checagem | Resultado |
|---|---|
| Pasta `evidence/before-after/` presente | ✓ |
| Convenção `NN-<slug>-before\|after.png` documentada | ✓ |
| Pilotos `01`–`08` com slugs alinhados a tasks/plan/spec | ✓ |
| Login só como prova de isolamento (arquivos `login-unchanged-*`) | ✓ |
| Contagem alvo 5–8 autenticados; login fora do SC-001 | ✓ |

**Gate**: T002/T003 podem capturar befores; polish de templates aguarda Phase 2 (T005+).

## Como capturar

1. **Before** (T002/T003): estado pré-implementação (ou commit base), autenticar e fotografar cada piloto; login unchanged à parte.
2. **After** (T039/T040): mesma conta, mesmos dados/filtros quando possível, pós polish.
3. Login unchanged: mesma viewport; após deve ser indistinguível do before.
4. Marcar checklist OUT (`contracts/out-checklist.md`) e anexar esta pasta no aceite US5.

## Fora

- Landing marketing  
- Telas não autenticadas como “prova de premium”  
- Login como evidência de melhoria (SC-001)  
- Expectativa de suite Percy/Chromatic (aceite é revisão guiada)
