# Quickstart: Validação 009 — Redesign Visual por Persona

**Branch**: `009-redesign-ux-persona`  
**Pré-requisitos**: ambiente Django local com dados de demo (admin, líder com subordinados, ciclo com avaliações/snapshots); Tailwind rebuild se `input.css` mudar.

## Setup

```bash
# na raiz do repo
source .venv/bin/activate  # se aplicável
python manage.py migrate
python manage.py runserver
# se input.css alterado:
# npx --yes @tailwindcss/cli@x -i static/src/input.css -o static/css/tailwind.css
```

Contratos: [contracts/](./contracts/). Modelo lógico: [data-model.md](./data-model.md).

---

## Sequência de validação (espelha prioridade)

### 0) Gate de escopo inválido

- Confirmar que o diff **não** toca denylist ([path-allowlist.md](./contracts/path-allowlist.md)).
- Rodar regressão de negócio (stage/scope/approval) — deve permanecer verde sem asserts alterados.

### 1) US1 — Charts fundação (bloquear US2/US3 se falhar)

| # | Ação | Esperado |
|---|------|----------|
| 1.1 | Abrir Meu painel / Time / Admin com dados | Gráficos com hierarquia (não só barra monocor); mini-KPI/legenda; Chart.js 4.5.1 |
| 1.2 | Comparar categorias/valores vs baseline | Mesmo significado Status Triad / shape |
| 1.3 | Cenário sem dados | Empty honesto, sem série inventada |
| 1.4 | Viewport ~375px | Rótulos/valor central consultáveis |

### 2) US2 — Painéis líder

| # | Ação | Esperado |
|---|------|----------|
| 2.1 | Líder → Painel do time | KPI + visual + ação **antes** de depender da tabela |
| 2.2 | Estrutura | Cobertura área/cargo como visual principal; lacunas secundárias; Chart carregado |
| 2.3 | Aderência | Doughnut/KPI + lista drill-down; só líderes no escopo |
| 2.4 | Clique em ação/drill-down | Destino já existente; sem vazamento de escopo |

### 3) US3 — Detalhe ciclo RH

| # | Ação | Esperado |
|---|------|----------|
| 3.1 | Admin → lista ciclos → abrir detalhe | ` /cycles/<pk>/ ` (página dedicada) |
| 3.2 | Ciclo com dados | Progresso + cobertura + aderência + checklist 008 no painel |
| 3.3 | Blockers presentes | Checklist avisório com links; abrir ciclo **não** fica mais hard-bloqueado |
| 3.4 | Seção sem dado | Empty local |
| 3.5 | Usuário não-admin | Acesso negado (mesmo gate admin) |

### 4) US4 — Colaborador P2

Percorrer: expectativas, metas, avaliações, PDI, minha classificação → tipografia/card/table-frame/empty Freeze; CTA claro **sem** segundo “Próximo passo” conflitante com hub 008.

### 5) US5 — P3 (opcional)

Se houver tempo até **03/09**: áreas/cargos/usuários/competências/auditoria/notificações com polish. Se omitido → **não** falha o release desde que US1–4 (P1+P2) ok.

---

## Evidências sugeridas

- Capturas before/after US1 (SC-003) e painéis US2/US3 (SC-001/002).
- Confirmar `docs/design-system.md` reflete A/B/C (SC-006).
- Network: Chart.js **4.5.1**; sem lib de gráfico adicional — **OK (T043 · 2026-08-12)**: 6 superfícies P1 pinadas `@4.5.1`; `base.html`/`nav_menu.html` diff 0 vs `373134d`; plugins inline em `dashboard_charts.js`.

---

## Comandos de teste (orientação)

```bash
# Preferir pytest (pytest.ini → config.settings.dev)
pytest tests/test_chart_payloads.py tests/test_structure_coverage.py \
  tests/test_ciclo_detail.py tests/test_stage_machine.py tests/test_scope.py \
  tests/test_reject_stage_invariant.py tests/test_can_advance_post_correction.py \
  tests/test_post_rejection.py tests/test_production_ux.py tests/test_guidance_mapping.py -q
```

---

## Matriz SC — percurso completo (T040 · 2026-08-12)

Percurso quickstart §0–§5 (US1–US4 + US5 entregue). Todos os SC-001…SC-007 são **aplicáveis** a esta feature.

| SC | Aplicável | Mapeamento quickstart | Status T040 | Evidência / residual |
|----|-----------|----------------------|-------------|----------------------|
| **SC-001** | Sim | §2 US2 (painel time / estrutura / aderência) | Pré-condições OK | `managerial-panel` KPI→visual→destaque→tabela; drill-down só URLs existentes; T021 |
| **SC-002** | Sim | §3 US3 (detalhe ciclo RH) | Pré-condições OK | `/cycles/<pk>/` + progresso/cobertura/aderência/checklist 008 avisório; AuthZ admin; T028 |
| **SC-003** | Sim | §1 US1 (+ evidências) | **OK (T042)** | Hierarquia Chart.js 4.5.1 + empty `has_data` falso; 6 pares before/after em `evidence/before-after/` (scan 6/6) |
| **SC-004** | Sim | §0 gate + regressão | **OK (T044)** | Denylist serviços domínio diff **vazio** vs `373134d` (exceção ciente rótulo `input_metas`); pytest stage/scope/payload/cobertura/ciclo_detail **83 PASS**; gate formal T044 **PASS** 2026-08-12 |
| **SC-005** | Sim | §4 US4 (5 superfícies P2) | OK | Freeze tipografia/table-frame/empty; CTA sem 2º hub conflitante; T035 |
| **SC-006** | Sim | Evidências DS | **OK (T042)** | `docs/design-system.md` reabertura A/B/C + painel gerencial; capturas painéis `02`–`06` em `evidence/before-after/` |
| **SC-007** | Sim | §1.4 + superfícies P1 | **OK (T041)** | Empilhamento KPI→visual→tabela em personal/team/admin/structure/adherence/ciclo_detail; KPIs `grid-cols-1`→sm/lg; mini-KPI `w-full` @mobile; `.managerial-panel > *` min-w-0; canvas 15.5rem; `.table-frame` overflow só no drill |

**§5 US5**: P3 entregue (não omitido) — Freeze chrome em organization/competencies/audit/notifications; **sem** SC dedicado; não bloqueia aceite.

**§0 Denylist (2026-08-12)**: `stage.py` / `cycle.py` / `approval.py` / `scope.py` / `evaluation.py` / `adherence.py` = 0 linhas vs `373134d`. Exceção ciente (já T029): rótulo UI `input_metas` → «Metas» em `apps/reviews/models.py` + `migrations/0006_*`.
