# Quickstart: Validação — Visualizações Gráficas nos Dashboards

**Branch**: `005-dashboard-charts` | **Date**: 2026-07-30  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Guia de validação ponta a ponta (não é suite de implementação). Detalhes de payload: [contracts/](./contracts/).

---

## Pré-requisitos

- Stack local usual do Greenn People (venv, `migrate`, Redis/Celery se snapshots precisarem ser gerados).
- Usuários de teste: **admin (Marina)**, **líder** com subordinados, **colaborador** com competências/notas.
- Ciclo aberto (ou encerrado recente) com `AderenciaSnapshot` e `Avaliacao` para o caminho feliz; cenário sem dados para empty.
- Freeze 004 disponível (`docs/design-system.md`).

Comandos típicos (ajustar ao ambiente do projeto):

```bash
python manage.py runserver
# opcional: worker Celery para popular snapshots
# celery -A config worker -l info
```

---

## MVP — Slice 1 (Admin / US1)

| # | Passo | Esperado |
|---|---|---|
| 1 | Login admin → `/dashboard/admin/` | Página carrega sem erro |
| 2 | Com snapshots | Chart de **distribuição de aderência** (alta/média/baixa) + labels/legenda além da cor |
| 3 | Com avaliações no ciclo | Chart de **progresso/conclusão** coerente com totais dos cards |
| 4 | Tabela | “Líderes com menor aderência” ainda visível e alinhada aos mesmos snapshots |
| 5 | View-source / rede | Chart.js **não** está em `base.html`; script só nesta página (e depois team/personal) |
| 6 | Empty | Remover/ausentar snapshots ou avaliações → empty PT-BR, **sem** barras inventadas |
| 7 | Mobile | Viewport estreito: charts consultáveis por scroll; rótulos legíveis (SC-006) |

---

## Regressão de escopo — Slice 2 (Time / US2)

| # | Passo | Esperado |
|---|---|---|
| 1 | Login líder → `/dashboard/team/` | Chart de status do escopo alinhado às etapas já usadas na lista |
| 2 | Paginar lista HTMX | Lista atualiza; chart **não** some / não passa a refletir só a página |
| 3 | Contar pessoas no gráfico | ⊆ `get_visible_users(líder)`; zero vazamento de outro ramo |
| 4 | Escopo vazio / sem ciclo | Empty honesto |
| 5 | Rodar testes de escopo existentes | `tests/test_scope.py` (e correlatos) continuam passando (SC-004) |

---

## Slice 3 (Pessoal / US3) — smoke

| # | Passo | Esperado |
|---|---|---|
| 1 | Colaborador com notas | Barras esperado × nota coerentes com `competencias_resumo` |
| 2 | Sem notas | Empty na área do gráfico |
| 3 | 9-box | Continua oculta se `visivel_ao_colaborador` falso; sem UI interativa nova |

---

## Checklist Success Criteria

| ID | Critério | Como verificar |
|---|---|---|
| **SC-001** | Marina identifica distribuição + progresso ≤ 10 s | Revisão guiada admin |
| **SC-002** | ≥ 2 visualizações distintas no admin | Passos MVP 2–3 |
| **SC-003** | Líder compreende status do escopo ≤ 10 s | Revisão guiada time (pós slice 2) |
| **SC-004** | 100% permissão/escopo | Testes + passo time 3 |
| **SC-005** | Empty 100% honestos | Passos empty admin/time/pessoal |
| **SC-006** | Mobile scroll legível | Passo MVP 7 |
| **SC-007** | Lib documentada + páginas listadas | Nota em `docs/design-system.md` / entrega |

---

## OUT (não validar como entrega)

- 9-box interativa; novas métricas/snapshots; SPA/DRF; redesign shell/nav/topbar; Impeccable; export/relatórios; dashboard novo; chart em `structure` (métrica diferente).

---

## Registro T024 — validação quickstart (2026-07-30)

Percurso checklist (MVP admin + time + pessoal + SC-001–007): inspeção de markup/contratos + smoke HTTP no stack Docker (`web`) + `pytest tests/test_scope.py` (**8 passed**). Sem listagem de PII.

| Gate | Resultado | Evidência |
|---|---|---|
| **SC-001** | **PASS** (estrutural) | Admin: ≥2 charts + labels Status Triad; revisão humana ≤10 s permanece opcional |
| **SC-002** | **PASS** | `/dashboard/admin/`: `chart-aderencia-distribuicao` + `chart-ciclo-progresso` + CDN 4.5.1 |
| **SC-003** | **PASS** (estrutural) | `/dashboard/team/`: `chart-escopo-status` fora de `#list-container`; revisão humana ≤10 s opcional |
| **SC-004** | **PASS** | `pytest tests/test_scope.py` → 8 passed; chart agrega `get_queryset()` completo (não só página) |
| **SC-005** | **PASS** | Empty: `has_data: false` + `empty_message` PT-BR; JS não inita canvas; admin aderência empty + pessoal gaps empty exercitados no DB local |
| **SC-006** | **PASS** (T025) | Altura fixa `.dashboard-chart-canvas` (15rem @~375px); admin `grid-cols-1`; ticks/legenda móveis; gaps grouped em barras horizontais no narrow |
| **SC-007** | **PASS** | `docs/design-system.md`: Chart.js 4.5.1 + admin/team/personal; `base.html` e `structure.html` sem script |

### Checklist quickstart (marcação T024)

| Slice | # | Checagem | Status |
|---|---|---|---|
| MVP admin | 1 | `/dashboard/admin/` 200 | ✓ |
| MVP admin | 2 | Distribuição aderência + labels | ✓ (empty honesto neste DB; builder/labels OK) |
| MVP admin | 3 | Progresso coerente com ciclo | ✓ (`has_data=true` no smoke) |
| MVP admin | 4 | Tabela menor aderência | ✓ |
| MVP admin | 5 | Chart.js só na página (não `base.html`) | ✓ |
| MVP admin | 6 | Empty PT-BR sem série fictícia | ✓ |
| MVP admin | 7 | Mobile scroll legível | ✓ T025 |
| Time | 1 | Chart status do escopo | ✓ |
| Time | 2 | HTMX lista não destrói chart | ✓ (chart fora de `#list-container`; multi-página N/A com 1 membro) |
| Time | 3 | Contagens ⊆ escopo | ✓ (total chart = queryset completo) |
| Time | 4 | Empty escopo/ciclo | ✓ (builders) |
| Time | 5 | `test_scope.py` | ✓ 8 passed |
| Pessoal | 1 | Barras esperado × nota | ✓ (empty neste DB; payload grouped + `null` preservado no código) |
| Pessoal | 2 | Sem notas → empty | ✓ |
| Pessoal | 3 | 9-box gate inalterada | ✓ (`classificacao` condicional; sem UI interativa nova) |

### Gaps / follow-ups

1. **Caminho feliz visual** — DB local sem snapshots de aderência e sem notas pessoais no usuário smoke; empty paths cobertos; happy path gráfico depende de dados de seed/revisão guiada no browser.
2. **Paginação HTMX multi-página** — arquitetura OK; smoke com escopo > `paginate_by` não exercitado (só 1 membro no líder de teste).

### Registro T025 — viewport móvel SC-006 (2026-07-30)

| Superfície | Ajuste | Evidência |
|---|---|---|
| `_chart_block.html` | `.dashboard-chart-canvas` 15rem (sm 16 / lg 18); `p-4 sm:p-5`; `min-w-0` | CSS regenerado em `static/css/tailwind.css` |
| `admin.html` | `grid-cols-1 lg:grid-cols-2` — empilha no ~375px (scroll) | Markup |
| `team.html` / `personal.html` | `min-w-0` nas seções de visualização | Markup |
| `dashboard_charts.js` | `maintainAspectRatio: false`; ticks/legenda menores no narrow; `bar_grouped` → `indexAxis: 'y'` se >2 labels | Init local |
| Shell/nav/topbar | **Não alterados** | Freeze 004 intacto |

### Registro T027 — FR-007 texto além da cor (2026-07-30)

| Superfície | Ajuste | Evidência |
|---|---|---|
| `chart_payloads.py` | `legend_items` em série única e grouped (label + valor + cor) | Helpers |
| `_chart_block.html` | `figcaption` com resumo textual (admin/time/pessoal via include) | Markup |
| `dashboard_charts.js` | Doughnut: legenda `Faixa: N`; barras categóricas: eixo + figcaption; grouped: legendas de série | Init local |
| Status Triad | Swatches + labels Alta/Média/Baixa (não só cor) | Aderência |

### Registro T028 — revisão OUT (2026-07-30)

| Critério OUT | Resultado | Evidência |
|---|---|---|
| Zero endpoints REST novos | **PASS** | `apps/dashboard/urls.py` inalterado na feature; sem DRF/`APIView`/`JsonResponse` de série; `dashboard_charts.js` sem `fetch` — payloads via `json_script` |
| Zero migrations | **PASS** | Diff feature (`7f868c7...HEAD`): nenhum arquivo em `**/migrations/**` nem alteração de `models.py` |
| `structure` sem chart | **PASS** | `structure.html` / `StructureDashboardView` / `services/structure.py` sem chart/CDN; `base.html` e `adherence.html` sem Chart.js |
| 9-box sem interação nova | **PASS** | `get_visible_classification_for_collaborator` + `{% if classificacao %}` somente leitura; sem drag/drawer; `apps/talent/` intacto |
