# Contract: Baseline vivo (pré-Foundational / pré-US1)

**Feature**: `018-auto-cycle-admission`  
**Task**: T002  
**Registrado**: 2026-09-10  
**Objetivo**: Congelar o estado **atual** dos pontos de extensão listados em T002 antes de multi-open, campos de coorte, calendário BR, predicado de marco, Beat diário, alerta e governança.

**Regra**: este documento descreve o *as-is*. Ampliações entram só a partir de T003+ — **sem** código de feature nesta task.

### Confirmação T002 (2026-09-10)

- [x] Paths allowlist existem e batem com o inventário abaixo
- [x] Extension points (`_validate_single_open`, `CycleAlreadyOpenError`, enrollment sem `ciclo=`, `get_open_ciclo` singular, Beat, notificações, audit, templates) identificados
- [x] Gaps vs plan/research registrados (o que **ainda não** existe)
- [x] Nenhuma alteração de feature code; ignore files do repo já cobrem Python/Node/Docker

---

## 1. Inventário de paths

| Path | Papel atual | Extensão prevista (feature) |
|------|-------------|-----------------------------|
| `apps/cycles/models.py` | `Ciclo` + invariante single-open | Remover/no-op `_validate_single_open`; +`origem`/`marco_competencia`; +`AutoCycleRun`/`AutoCycleEvent` |
| `apps/cycles/exceptions.py` | `CycleAlreadyOpenError` = single-open | Manter reabrir o **mesmo**; não bloquear outro aberto |
| `apps/cycles/services/cycle.py` | `open_cycle` / `close_cycle` (015) | Não levantar por outro `aberto`; manual intacto |
| `apps/cycles/services/eligibility.py` | Predicado 015 `admitidos_ate` | **Intacto**; predicado auto em `marco.py` |
| `apps/cycles/views.py` | Admin list/create/open/close | +governança admin-only; listagem multi-open |
| `apps/cycles/forms.py` | `CicloForm` (corte obrigatório) | Filtros leves de governança se necessário |
| `apps/reviews/services/enrollment.py` | `ensure_avaliacao_for_user` | Exigir `ciclo=` em criação ambígua; ramo auto recebe coorte |
| `apps/goals/forms.py` | `get_open_ciclo()` singular | +`get_open_ciclos()`; default = primeiro |
| `apps/core/context_processors.py` | `ciclo_aberto` singular | +`ciclos_abertos`; sem mentir singular |
| `apps/dashboard/services/ciclo_options.py` | Operacional ≤1 aberto | Operacional = **todos** os abertos |
| `apps/notifications/models.py` | 5 tipos de log | +`alerta_ciclo_ainda_aberto` |
| `apps/notifications/tasks.py` / `emails.py` | Lembretes etapa/PDI + digest | Task/e-mail alerta ciclo aberto + dedupe |
| `apps/audit/services.py` | `write_audit_log` append-only | Reuso na criação da coorte |
| `config/celery.py` | Beat PDI/lembretes/aderência | +`auto-cycle-admission-daily` (~00:30) |
| Templates ciclos + seletor | Copy “só um aberto” | Multi-open honesto + link governança |

**Ausentes hoje (gaps)**: `apps/core/calendar_br.py`, `apps/cycles/services/marco.py`, `apps/cycles/services/auto_cohort.py`, `apps/cycles/services/governance.py`, `apps/cycles/tasks.py`, templates de governança / e-mail alerta.

---

## 2. Single-open — `_validate_single_open` / `CycleAlreadyOpenError`

### `apps/cycles/models.py` — `Ciclo`

| Aspecto | Baseline atual |
|---------|----------------|
| Docstring | “at most one may be `aberto` at a time” |
| Campos | `nome`, `data_inicio`, `data_fim`, `status`, `solides_id`, `admitidos_ate` — **sem** `origem` / `marco_competencia` |
| `clean` / `save` | Ambos chamam `_validate_date_range` + `_validate_single_open` |
| `_validate_single_open` | Se `status=aberto` e existe outro `aberto` (exclui `self.pk`) → `ValidationError` em `status` |

**Gancho T003**: no-op / remoção de `_validate_single_open` em `clean`/`save`.

### `apps/cycles/exceptions.py`

| Exceção | Uso as-is |
|---------|-----------|
| `CycleAlreadyOpenError` | “opening would violate the single-open-cycle rule” |
| `CycleMissingCutoffError` | Abertura manual sem `admitidos_ate` |
| `CycleNotOpenError` / `CycleClosedError` / `StageTransitionError` | Encerrar / stage — fora do núcleo 018 |

### `apps/cycles/services/cycle.py` — `open_cycle`

| Gate | Comportamento as-is |
|------|---------------------|
| Mesmo ciclo já `aberto` | `CycleAlreadyOpenError('Este ciclo já está aberto.')` — **manter** na feature |
| **Outro** ciclo `aberto` | `CycleAlreadyOpenError('Já existe um ciclo aberto…')` — **remover** (T003) |
| Corte | `CycleMissingCutoffError` se `admitidos_ate` ausente |
| Matrícula | `ensure_avaliacao_for_user(user, ciclo=locked)` — **com** `ciclo=` explícito |

`close_cycle`: exige status `aberto`; não toca single-open de outros.

### `apps/cycles/views.py` — consumidores de `CycleAlreadyOpenError`

| View | Comportamento |
|------|---------------|
| `CicloCreateView.form_valid` | Cria `encerrado` → `open_cycle`; captura `CycleAlreadyOpenError` → warning “criado, mas não aberto” |
| `CicloOpenView.post` | `open_cycle` + override opcional de corte; `CycleAlreadyOpenError` → `messages.error` |
| `CicloListView` | `ciclo_operacional = get_open_ciclo()` — **um** card operacional |
| AuthZ | `AdminCyclesMixin` = `LoginRequired` + `RequiresAdminMixin` (`is_admin`) |

**Teste de ouro a quebrar (US5/T028)**: `tests/test_open_cycle_admission_cutoff.py` asserta `CycleAlreadyOpenError` ao abrir segundo ciclo.

---

## 3. Enrollment — `ensure_avaliacao_for_user` e caminhos sem `ciclo=`

### `apps/reviews/services/enrollment.py` (as-is)

```text
ciclo is None → Ciclo.objects.filter(status=aberto).order_by('-data_inicio').first()
ciclo passado e ≠ aberto → None
elegibilidade → user_eligible_for_ciclo (015)
idempotência → get_or_create Avaliacao
```

**Risco multi-open**: sem `ciclo=`, escolhe silenciosamente o aberto mais recente por `-data_inicio`.

### Callers de produção

| Caller | Passa `ciclo=`? |
|--------|-----------------|
| `apps/cycles/services/cycle.py` (`open_cycle`) | **Sim** (`locked`) |
| `apps/accounts/forms.py` (mid-cycle pós-save user) | **Não** — `ensure_avaliacao_for_user(u)` |
| `apps/organization/forms.py` (idem) | **Não** — `ensure_avaliacao_for_user(u)` |

**Gancho T009**: criação nova com ambiguidade multi-open deve exigir `ciclo=`; ramo automático sempre recebe a coorte; mid-cycle sem `ciclo=` não pode matricular no ciclo “errado”.

### Predicado 015 — `apps/cycles/services/eligibility.py`

`user_eligible_for_ciclo`: ativo ∧ `data_entrada` ∧ `admitidos_ate` ∧ `data_entrada ≤ admitidos_ate`. Fail-closed se corte NULL.

**Regra da feature**: este módulo permanece **intacto**; predicado automático vive em `apps/cycles/services/marco.py` (T006).

---

## 4. Singular “ciclo aberto” — `get_open_ciclo` e consumidores

### `apps/goals/forms.py`

```python
def get_open_ciclo() -> Ciclo | None:
    return Ciclo.objects.filter(status=ABERTO).order_by('-data_inicio').first()
```

Também usado por `get_avaliacao_for_user` e formulários de meta quando `ciclo` omisso.

### Consumidores relevantes (allowlist + spill)

| Path | Uso |
|------|-----|
| `apps/core/context_processors.py` | Expõe só `ciclo_aberto` (singular) |
| `apps/dashboard/services/ciclo_options.py` | Default operacional / pessoal; `grouped_ciclo_options` → lista operacional com **no máximo 1** aberto |
| `apps/cycles/views.py` | `ciclo_operacional` na listagem |
| `apps/goals/views.py`, `apps/reviews/views.py`, `apps/dashboard/views.py`, `apps/talent/*` | Homes/painéis leem singular (fora do escopo mínimo 018, mas quebram honestidade multi-open se só o “primeiro” existir na UI de ciclos/seletor) |

**Gancho T008**: introduzir `get_open_ciclos()`; `get_open_ciclo()` = default (primeiro de `get_open_ciclos()`); operacional = todos os abertos; context processor + `ciclos_abertos`.

---

## 5. Notificações / audit / Celery

### `NotificacaoLog.Tipo` (as-is)

| Valor | Uso |
|-------|-----|
| `lembrete_etapa` | Ciclo aberto, `data_fim` alvo |
| `lembrete_pdi` | Ação PDI vencendo |
| `feedback_continuo` | Evento único |
| `atraso_pdi` | Atraso de ação PDI |
| `digest_pdi_atrasos` | Digest semanal admins |

**Ausente**: `alerta_ciclo_ainda_aberto` (T010). Pipeline `_log_send` + `already_sent(destinatario, tipo, referencia, janela)` pronto para reuso (T019).

### `apps/audit/services.py`

`write_audit_log(...)` append-only; `cycles` **não** chama hoje na abertura. Gancho T011/T026: auditar criação da coorte automática.

### `config/celery.py` — Beat as-is

| Key | Schedule | Task |
|-----|----------|------|
| `mark-overdue-pdi-actions-daily` | 00:15 | `apps.pdi.tasks.mark_overdue_pdi_actions` |
| `calculate-adherence-snapshots-daily` | 01:00 | dashboard adherence |
| lembretes etapa/PDI | 08:00 / 08:15 | notifications |
| digest PDI | seg 08:30 | notifications |

**Ausente**: `auto-cycle-admission-daily` (~00:30 após overdue PDI) → `apps.cycles.tasks.run_auto_cycle_admission_daily` (T012/T013). HTTP **não** é disparo.

---

## 6. Forms / templates (copy e superfície)

### `apps/cycles/forms.py`

`CicloForm`: campos `nome`, `data_inicio`, `data_fim`, `admitidos_ate` (required). Sem `origem`/`marco_competencia`. Create → view chama `open_cycle`.

### Templates — pontos de copy single-open / UI

| Template | Baseline relevante |
|----------|-------------------|
| `templates/cycles/ciclo_list.html` | Copy: “Só um ciclo pode estar aberto por vez.” CTA primário “Novo ciclo” |
| `templates/cycles/ciclo_list_partial.html` | Um `ciclo_operacional` + arquivo paginado; empty “Nenhum ciclo aberto” |
| `templates/cycles/_ciclo_card.html` | Card operacional/arquivo; Abrir/Encerrar; DNA Lush (Fraunces/Source Sans via shell) |
| `templates/cycles/ciclo_detail.html` | Badge ativo/arquivado; KPIs; sem badge de origem |
| `templates/dashboard/_ciclo_selector.html` | Optgroups Operacional/Arquivo; pill “Em andamento” vs `ciclo_aberto` singular; “Nenhum ciclo aberto” |

**Ganchos**: T024/T025 governança + link na listagem; T029 copy multi-open honesta (sem mentir “só um vigente”).

---

## 7. Mapa de impacto por fase (referência rápida)

| Fase / task | Baseline a tocar |
|-------------|------------------|
| T003 | `models._validate_single_open`, `cycle.open_cycle` (outro aberto), exceptions docstring |
| T004 / T007 | `Ciclo` campos + `AutoCycleRun`/`AutoCycleEvent` + migrations |
| T005 | **novo** `calendar_br.py` |
| T006 | **novo** `marco.py` (eligibility 015 intacto) |
| T008 | `get_open_ciclo(s)`, `ciclo_options`, context processor |
| T009 | `enrollment.py` + callers sem `ciclo=` |
| T010 / T019 | `NotificacaoLog.Tipo` + emails/tasks |
| T011–T014 | **novo** `auto_cohort` + `tasks` + Beat |
| T022–T027 | governança views/templates + audit |
| T028–T030 | testes 015 + UI multi-open |

---

## 8. Checklist de ouro (baseline → expectativa pós-feature)

| Afirmação as-is | Expectativa 018 |
|-----------------|-----------------|
| No máximo 1 `Ciclo` `aberto` | N abertos (manual + auto) |
| `open_cycle` falha se já existe outro aberto | Só falha se reabrir o **mesmo** |
| Enrollment sem `ciclo=` pega `.first()` aberto | Não escolher silenciosamente o errado sob multi-open |
| Operacional / topbar = 1 ciclo | Listar / expor todos os abertos com default explícito |
| Beat sem admission | Beat diário é o disparo; HTTP governança só lê |
| Sem tipo alerta ciclo aberto | Tipo + e-mail + dedupe; não bloqueia lote |

---

**Fim T002** — contratos e pontos de extensão identificados; zero código de feature.
