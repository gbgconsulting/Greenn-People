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
