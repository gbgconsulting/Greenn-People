# Contract: Abertura automática da coorte (lote)

**Refs**: [spec.md](../spec.md) FR-001, FR-006, FR-009, FR-021; [data-model.md](../data-model.md); [research.md](../research.md) R1/R4/R10

## Entrada

- Task Celery Beat diária: `run_auto_cycle_admission_daily` (nome estável em `apps.cycles.tasks`).
- `data_referencia = timezone.localdate()` (ou clock injetável em testes).

## Algoritmo (autoritativo)

```text
1. Criar AutoCycleRun(data_referencia)
2. Se data_referencia != first_business_day_of_month(y, m):
     status=noop; event noop_dia; return
3. Candidatos = ativos com data_entrada cujo next_future_marco == (y, m)
4. Particionar:
     - alertados = candidatos com ≥1 ciclo status=aberto (qualquer origem)
     - matriculáveis = candidatos − alertados
5. Persist events alerta_ciclo_aberto (+ e-mail RH deduped) para alertados
6. get_or_create Ciclo(origem=automatico, marco_competencia=date(y,m,1)):
     - create path: set nome, data_inicio=data_referencia,
       data_fim=data_inicio+20 days, status=aberto; audit log
     - exists path: reutilizar; NÃO duplicar; NÃO alterar snapshot de
       Avaliações já criadas; data_fim só se política explícita de create-only
7. Para cada matriculável: ensure_avaliacao_for_user(user, ciclo=coorte)
8. Contar ativos sem data_entrada → events/contagem pendencia_sem_admissao
   (não matricula)
9. Fechar run: sucesso | parcial | falha
```

## Idempotência (MUST)

| Ação | Resultado na reexecução no mesmo marco |
|---|---|
| Segundo ciclo automático do mesmo `marco_competencia` | **0** (UniqueConstraint / get_or_create) |
| Segunda Avaliação mesmo user+ciclo | **0** (unique + ensure) |
| Reenvio de e-mail de alerta mesma janela | **0** (NotificacaoLog dedupe) |

## Não-responsabilidades

- HTTP request do RH como disparo primário do mês.
- Recuperar marcos passados.
- Fechar automaticamente todos os ciclos na `data_fim` (pode ser fase posterior; atraso deve estar **visível**).
- Alterar predicado 015 / `admitidos_ate`.

## Erros

- Falha ao matricular um user: event `falha` parcial; continua demais; run `parcial`.
- Falha ao criar ciclo: run `falha`; sem Avaliações órfãs do marco.

## Observabilidade

- Todo run deixa `AutoCycleRun` + events suficientes para RH reconstruir quem/quando/por quê (FR-016).
- `write_audit_log` na criação do ciclo automático.
