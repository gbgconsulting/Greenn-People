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
- Network: Chart.js **4.5.1**; sem lib de gráfico adicional.

---

## Comandos de teste (orientação)

```bash
python manage.py test tests.test_scope tests.test_stage_machine
# + testes novos de payload/cobertura/ciclo_detail quando criados em /speckit-tasks
```
