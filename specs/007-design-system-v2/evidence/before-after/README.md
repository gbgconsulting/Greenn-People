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
| 01 dashboard-admin-charts | ✓ T002 `01-…-before.png` | ☐ T039 | Conta admin · `/dashboard/admin/` |
| 02 dashboard-team | ✓ T002 `02-…-before.png` | ☐ T039 | Conta líder · `/dashboard/team/` |
| 03 dashboard-pessoal | ✓ T002 `03-…-before.png` | ☐ T039 | Conta colab · `/` |
| 04 talent-matrix | ✓ T002 `04-…-before.png` | ☐ T039 | Conta admin · `/talent/matrix/` |
| 05 lista-ciclos | ✓ T002 `05-…-before.png` | ☐ T039 | Conta admin · `/cycles/` |
| 06 pdi-detail | ✓ T002 `06-…-before.png` | ☐ T039 | Conta admin · `/pdi/9/` |
| 07 avaliacoes-list (opc.) | ☐ | ☐ | Não incluído no conjunto T002 |
| 08 shell-chrome (opc.) | ☐ | ☐ | Só se shell leve for feito (T044) |
| Login isolamento | ✓ T003 `login-unchanged-before.png` | ☐ T040 | **Não** conta para SC-001 · `/accounts/login/` · viewport 1280×900 |

## Verificação de isolamento auth (T011) — 2026-08-06

| Checagem | Resultado |
|---|---|
| `git diff` `templates/accounts/base_auth.html` `templates/accounts/login.html` (working tree vs HEAD) | ✓ vazio |
| Classe `app-shell` em templates auth | ✓ ausente |
| Body efetivo do login (`base_auth` + `body_class`) | `min-h-screen bg-white text-slate-800 antialiased …` (sem `app-shell`) |
| Tipografia efetiva | ✓ Inter via `--font-sans` + `body { font-family: var(--font-sans) }`; v2 só sob `.app-shell` em `base.html` |
| OUT checklist | `OUT-LOGIN-DIFF` + `OUT-AUTH-ISOLATION` ✅; visual after ainda em T040 |

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
