# Evidence: before / after — Redesign Visual por Persona (009)

**Feature**: `009-persona-visual-redesign`  
**Task**: T042 · **2026-08-12**  
**Padrão**: espelha `specs/007-design-system-v2/evidence/before-after/`  
**Confirma**: **SC-003** (hierarquia charts US1) · **SC-006** (DS A/B/C + painel gerencial)

## Convenção de nomes

```text
NN-<slug>-before.png
NN-<slug>-after.png
```

- IDs `01`–`06`, zero-padded.
- Viewport desktop **1280×900** (Playwright).
- Seed: `scripts/seed_evidence_007.py` · captura after: `scripts/capture_evidence_009.py`.

### Baseline **before**

| Origem | Uso |
|---|---|
| `specs/007-design-system-v2/evidence/before-after/*-after.png` | Pré-009 (DS v2 entregue, **antes** do polish de charts/painéis 009) para US1 (`01`–`03`) |
| `05-lista-ciclos-after.png` (007) | Pré-US3: RH só tinha lista de ciclos (`06` before) |
| Proxy team/admin (007) | `04`/`05` before = painel líder/admin **sem** `.managerial-panel` 009 / sem Chart.js em structure/adherence |

## Pilotos P1 (SC-003 / SC-006)

| ID | Slug | Superfície | Rota | Conta after | SC |
|---|---|---|---|---|---|
| 01 | `personal-charts` | Meu painel + gaps | `/` | colab | SC-003 |
| 02 | `team-panel` | Painel do time (KPI→chart→drill) | `/dashboard/team/` | líder | SC-003 + SC-001 |
| 03 | `admin-charts` | Painel admin + doughnut/progresso | `/dashboard/admin/` | admin | SC-003 |
| 04 | `structure-panel` | Estrutura cobertura (**Freeze B**) | `/dashboard/structure/` | admin | SC-003 + SC-001 |
| 05 | `adherence-panel` | Aderência doughnut + lista | `/dashboard/adherence/` | admin | SC-003 + SC-001 |
| 06 | `ciclo-detail-panel` | Detalhe ciclo RH (**US3**) | `/cycles/1/` | admin | SC-002 + SC-006 |

## Status de captura (T042 · 2026-08-12)

| Artefato | Before | After | Notas |
|---|---|---|---|
| 01 personal-charts | ✓ proxy 007 `03-dashboard-pessoal-after` | ✓ Playwright | `bar_horizontal` grouped esperado×nota; insight + figcaption |
| 02 team-panel | ✓ proxy 007 `02-dashboard-team-after` | ✓ Playwright | `.managerial-panel` KPI→`bar_horizontal` mono + highlight amber → destaque → tabela |
| 03 admin-charts | ✓ proxy 007 `01-dashboard-admin-charts-after` | ✓ Playwright | doughnut Status Triad + valor central + mini-KPI progresso |
| 04 structure-panel | ✓ proxy 007 `02-team-panel-after` | ✓ Playwright | KPI cobertura + charts área/cargo; lacunas secundárias (**B**) |
| 05 adherence-panel | ✓ proxy 007 `01-admin-charts-after` | ✓ Playwright | KPI + doughnut central + lista HTMX |
| 06 ciclo-detail-panel | ✓ proxy 007 `05-lista-ciclos-after` | ✓ Playwright | Página dedicada KPI→3 blocos chart→checklist 008 avisório |

## Scan guiado SC-003 — hierarquia charts (2026-08-12)

Comparação side-by-side before (pré-009) vs after (HEAD). Critério spec: gráficos com dados **não** são barra monocor única sem hierarquia; empty honesto quando `has_data` falso.

| ID | Hierarquia perceptível (≠ barra mono única)? | Empty honesto? | Notas 009 |
|---|---|---|---|
| 01 | ✓ | ✓ (cenário seed com dados) | Barras grouped + cores esperado/neutral vs nota/teal |
| 02 | ✓ | ✓ | `bar_horizontal` mono + amber no gargalo; KPI strip acima |
| 03 | ✓ | ✓ | Doughnut 3 fatias Triad + **total/% central**; progresso separado |
| 04 | ✓ | ✓ (seções vazias locais) | Cobertura mono teal; lacunas fora do chart principal |
| 05 | ✓ | ✓ | Rosca Triad + valor central; lista drill abaixo |
| 06 | ✓ | ✓ | Múltiplos `_chart_block` + empty por seção |

**Resultado SC-003:** **6/6** superfícies P1 com hierarquia visual perceptível nos gráficos com dados (meta 100% dos três painéis US1 + extensão painéis US2/US3).

## Confirmação SC-006 — Design System A/B/C (2026-08-12)

`docs/design-system.md` reflete explicitamente a reabertura formal (decisão Canvas 2026-08-11):

| Ponto | Seção DS | Evidência código/templates |
|---|---|---|
| **A** Charts polish | Reabertura A/B/C + **Charts polish (DS v2)** | `dashboard_charts.js` tipos expressivos; `_chart_block.html` insight/mini-KPI; Chart.js **4.5.1** |
| **B** Structure no slice | Reabertura A/B/C + tabela superfícies Chart.js | `structure.html` + `04-structure-panel-after.png` |
| **C** Painel gerencial | Reabertura A/B/C + **Painel gerencial (DS v2 · Freeze C)** | `.managerial-panel` em `input.css`; composição KPI→visual→drill em team/structure/adherence/ciclo_detail |

Cross-ref contratos: `contracts/chart-catalog.md`, `managerial-panel.md`, `cycle-managerial-detail.md`.

**Resultado SC-006:** ✓ documentação canônica + padrão referenciável; capturas `02`–`06` after demonstram composição **C** em produção.

## Como reproduzir

```bash
source .venv/bin/activate
python manage.py migrate
python scripts/seed_evidence_007.py
python manage.py runserver 127.0.0.1:8000
# outro terminal (Python 3.10 + playwright instalado):
python3.10 scripts/capture_evidence_009.py
```

## Fora

- Login / `base_auth` (isolamento Freeze v2 — sem evidência de “melhoria” aqui)
- Nav IA / shell (FR-008 intacto)
- US4/US5 P2/P3 (fora do escopo SC-003/006 desta pasta)

## Conclusão T042

| Critério | Meta | Resultado |
|---|---|---|
| SC-003 | 100% charts P1 com hierarquia + empty honesto | ✓ **6/6** |
| SC-006 | DS A/B/C + painel gerencial referenciável | ✓ `docs/design-system.md` + capturas |
| Evidências anexadas | before/after P1 | ✓ 6 pares PNG nesta pasta |
