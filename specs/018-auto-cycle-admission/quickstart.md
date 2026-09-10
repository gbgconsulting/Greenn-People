# Quickstart: Validação — 018 Abertura automática por admissão

Guia de validação end-to-end. Detalhes de predicado/abertura/UI/AuthZ: [contracts/](./contracts/), [data-model.md](./data-model.md).

## Prerequisites

- Branch/feature `018-auto-cycle-admission` implementada (pós `/speckit-tasks` + implement).
- Redis + Celery worker/beat **ou** invocação direta da task em testes.
- DB migrada; usuários admin + colaboradores de fixture.
- `data_entrada` preenchida nos casos elegíveis (backfill 015 se legado).

## Setup

```bash
# na raiz do repo
python -m pytest tests/test_calendar_br.py tests/test_marco_eligibility.py \
  tests/test_auto_cohort_open.py tests/test_auto_bootstrap_no_backfill.py \
  tests/test_auto_open_cycle_alert.py tests/test_multi_open_ciclo.py \
  tests/test_auto_governance_authz.py -q
```

(Ajuste nomes finais se `tasks.md` padronizar outros módulos de teste.)

## Cenários de validação

### V1 — Lote do 1º dia útil (US1 / SC-001)

1. Fixar clock no **1º dia útil** de julho (pular se 1º civil for fim de semana/feriado nacional).
2. Seed: 10 ativos com próximo marco = julho; 2 sem `data_entrada`; 2 com marco = agosto.
3. Rodar `run_auto_cycle_admission_daily`.
4. **Esperado**: 1 ciclo `origem=automatico` com `marco_competencia=YYYY-07-01`; exatamente 10 Avaliações; 0 nos sem data / agosto; `data_fim = data_inicio + 20`.

### V2 — Idempotência (SC-005)

1. Reexecutar a task no mesmo dia.
2. **Esperado**: ainda 1 ciclo da coorte; ainda 10 Avaliações; sem e-mail duplicado na janela.

### V3 — Bootstrap legado (US2 / SC-002)

1. Usuário admitido em 2022-01; `ref=2026-09` (após feature on).
2. Rodar task em dias que não são o 1º dia útil do próximo marco futuro.
3. **Esperado**: 0 ciclos/Avaliações “atrasados”; próximo marco = 2027-01; entra só no 1º dia útil de jan/2027.

### V4 — Alerta sem travar (US3 / SC-004)

1. Coorte A aberta; 1 pessoa ainda com ciclo aberto; ≥1 outro elegível no novo marco.
2. Rodar task no 1º dia útil do novo marco.
3. **Esperado**: alerta RH (event + e-mail admin); coorte B criada; demais matriculados; pessoa alertada **sem** nova Avaliação automática; lote não adiado.

### V5 — Governança + AuthZ (US4 / SC-006 / SC-007)

1. Como admin: abrir superfície de governança do período da V1/V4.
2. **Esperado**: ver entrantes, pendências sem admissão, alertas, status do run em linguagem RH (&lt;3s situação).
3. Como líder/colaborador: GET mesma URL → 403; sem fila org.

### V6 — Manual 015 + multi-open (US5 / SC-009)

1. Com ciclo automático aberto, admin abre ciclo manual com `admitidos_ate` válido.
2. **Esperado**: abertura manual OK; dois `aberto`; seletor/topbar não mentem singular falso.

### V7 — Snapshot (SC-008)

1. Editar `data_entrada` de alguém já matriculado.
2. Rodar task / abrir manual.
3. **Esperado**: Avaliação existente intacta; sem delete.

### V8 — Visual (gate)

1. Revisar templates contra [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md).
2. **Esperado**: Fraunces h1; Source Sans 3; um CTA primário; rose só atraso 20d/falha; alerta ciclo aberto ≠ rose; empty slate.

## Non-goals check

Confirmar ausência de: Opção B, backfill de marcos passados, feriado municipal, papel RH novo, lote disparado só por pageview.

## Done when

- [ ] V1–V8 passam em base de teste controlada
- [ ] Constitution gates do [plan.md](./plan.md) continuam PASS
- [ ] Denylist [non-goals-denylist.md](./contracts/non-goals-denylist.md) respeitada
