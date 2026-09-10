# Implementation Plan: Abertura Automática de Ciclos por Admissão

**Branch**: `018-auto-cycle-admission` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/018-auto-cycle-admission/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). **Não** gera `tasks.md` (isso é `/speckit-tasks`). Clarifications Session 2026-09-09 são **decisões fechadas** — **NÃO** reabrir.

**Diretriz visual obrigatória**: [speckit_princ_pios_e_diretrizes_greenn_people.md](../../speckit_princ_pios_e_diretrizes_greenn_people.md) + `docs/design-system.md` (Freeze v2 shipado) + padrões vivos de ciclos / cadastros / PDI 017. Ver [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md).

## Summary

Abrir **automaticamente**, no **1º dia útil** de cada mês (calendário **Brasil nacional**), **um ciclo de coorte** para todos os ativos cujo **próximo marco futuro** (mês de admissão + múltiplos de 6 meses) é aquele mês — Opção A; exemplo: 10 no marco de julho → os 10. Prazo operacional: `data_fim` = ativação + **20 dias corridos**. Sem `data_entrada` = fora. Bootstrap legado = **só próximo marco futuro** (zero recuperação de atrasados). Ciclo ainda aberto no novo marco = **alerta RH**, **nunca** bloqueia o lote; a pessoa em alerta **não** recebe nova Avaliação automática naquele marco (FR-008). **Múltiplos ciclos `aberto`** passam a ser permitidos (quebra deliberada da regra 015). Abertura manual 015 permanece.

Abordagem técnica: serviço de marco + calendário BR + abertura de coorte idempotente em `apps/cycles`; matrícula via `ensure_avaliacao_for_user` com predicado de origem; **lote diário via Celery Beat** (HTTP não processa o mês); governança admin reusando shell/listagens de ciclos; auditoria/`NotificacaoLog` append-only; ajuste honesto de `get_open_ciclo` / seletor / topbar para N abertos.

## Sequenciamento (obrigatório)

```text
Fundação: multi-open (remover single-open) + origem/coorte + calendário BR + predicado marco
        │
        ▼
US1/US2 P1 — Task Beat diária + abertura idempotente da coorte + bootstrap só futuro
        │
        ▼
US3 P1 — Prazo 20 dias + alerta ciclo ainda aberto (não bloqueia; não matricula a pessoa)
        │
        ▼
US4 P1 — Governança RH (entrantes / sem admissão / alertas / falhas) + AuthZ admin
        │
        ▼
US5 P2 — Convivência manual 015 + regressão snapshot/histórico + polish multi-open UI
```

MVP = US1–US4. US5 é proteção de arquivo e compatibilidade.

## Non-Goals (decisões fechadas — não reabrir)

- Opção B (lote único sem ritmo por admissão)
- Recuperação em massa de marcos passados / bootstrap “atrasado”
- Feriados estaduais/municipais
- Matrícula forçada de inelegível / inativo / sem data
- Papel RH novo; DRF/SPA; app Django nova fora da constituição
- Redesign amplo de charts / dashboards além do necessário para não mentir com N abertos
- Relatórios analíticos além da governança operacional
- Segunda identidade visual “só para o automático”
- Bloquear lote por alerta de ciclo ainda aberto
- Processar o lote do mês em request HTTP (RH “disparar tela”)

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (alinhar `requirements.txt`; constituição cita 5.x — Complexity Tracking)

**Primary Dependencies**: Django full stack (DTL + HTMX + Tailwind CLI); Redis + Celery + Celery Beat; e-mail/`NotificacaoLog` via `apps/notifications`; auditoria `write_audit_log`. **Sem** DRF/SPA. **Sem** lib de feriados nova — calendário BR nacional em módulo puro do monólito (Princípio I).

**Storage**: SQLite (dev) / PostgreSQL (prod). Migrations aditivas em `Ciclo` (origem + chave de coorte) + modelos/eventos de governança se necessário; `CustomUser.data_entrada` **intacta** (sem segundo campo).

**Testing**: pytest-django — calendário/1º dia útil; predicado de marco/bootstrap; abertura idempotente; multi-open + manual 015; alerta não-bloqueante; AuthZ governança; regressão denylist (stage/fórmulas/PDI/escopo).

**Target Platform**: Web autenticado (admin = RH de ciclos) + worker Celery; locale `pt-BR`; timezone do projeto.

**Project Type**: Monólito Django (apps `cycles`, `reviews`, `accounts`, `notifications`, `audit`, `dashboard`, `core`)

**Performance Goals**: Lote mensal assíncrono; request HTTP da governança só lê/agrega scoped; sem agregação org pesada síncrona além de listagens admin já aceitas.

**Constraints**:
- Constitution **II**: elegibilidade, abertura, alerta, visibilidade **só** no backend — [contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md)
- Constitution **III**: snapshot Avaliação; auditoria append-only; histórico encerrado intocado
- Constitution **VI**: lote agendado (Beat); HTTP não abre a coorte do mês
- Visual: Fraunces + Source Sans 3; Lush Professional; `rounded-lg`; um CTA primário; rose só atraso/falha real — [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md)
- Compatível com 015 (manual + `admitidos_ate`); automação = caminho adicional
- Bootstrap legado essencial: zero marcos atrasados

**Scale/Scope**: 5 user stories (P1×4 + P2×1); FR-001…FR-022; SC-001…SC-009; superfícies: task Beat, lista/governança de ciclos, alertas RH, ajustes multi-open (context processor / seletor / enrollment sem `ciclo=`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Violação não justificada BLOQUEIA.*

| Princípio / Gate | Status | Evidência no design |
|---|---|---|
| **I. Simplicidade Django-First** | ✅ PASS | DTL/HTMX/Tailwind; serviços Django; calendário BR **sem** lib nova; sem DRF/SPA. |
| **II. Segurança e Escopo no Backend** | ✅ PASS | Gate [backend-scope-authz.md](./contracts/backend-scope-authz.md): predicado/abertura/alerta/listagens só server-side; governança = `RequiresAdminMixin`/`is_admin`; líder/colaborador sem fila org; `get_visible_users` intacto para avaliações. |
| **III. Imutabilidade e Integridade** | ✅ PASS | Avaliação = snapshot; mudança de `data_entrada` não apaga; ciclos encerrados não reprocessados; eventos de abertura/alerta/falha append-only (`AuditLog` / `NotificacaoLog` / log de rotina). |
| **IV. Modularidade por Domínio** | ✅ PASS | Domínio em `cycles` (+ eligibility/auto); matrícula `reviews`; data em `accounts`; canal `notifications`/`audit`; KPI/contexto `dashboard`/`core`. Sem app nova. |
| **V. Reprodutibilidade de Cálculos** | ✅ PASS | Stage/fórmulas/9-box/PDI **fora** do corte (salvo convivência multi-open). |
| **VI. Performance Assíncrona** | ✅ PASS | Lote diário/mensal via Celery Beat; HTTP não processa coorte. |
| **Stack obrigatória** | ✅ PASS | Django + DTL + HTMX + Tailwind + Redis/Celery; Django 6.x já no repo (Complexity Tracking). |
| **Visual / DS (feature gate)** | ✅ PASS | [ui-visual-consistency.md](./contracts/ui-visual-consistency.md) amarra princípios Greenn People + Freeze v2 + reuso de ciclos/PDI 017. |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Multi-open é **mudança deliberada de regra de negócio** (FR-010), não violação constitucional — documentada em research R-multi-open + Complexity Tracking. Zero `NEEDS CLARIFICATION` residual (decisões 2026-09-09 fechadas).

**FAIL do plan se**: UI decide elegibilidade/abertura/alerta; HTTP processa o lote do mês; bootstrap recupera atrasados; alerta bloqueia lote; Opção B; lib de feriados sem justificativa; segunda paleta/fonte “só automático”.

### Evidência T031 (smoke denylist)

Revisão 2026-09-10 — varredura estática + asserts de superfície + predicado de marco:

| Non-goal / path | Resultado | Evidência |
|---|---|---|
| Stage / approval / scope / PDI / 9-box | **OK** | Diff vazio desde início 018 nos paths do contrato; smoke de superfície + limiares 0.33/0.66 |
| Opção B | **OK** | Elegibilidade por série +6m (`next_future_marco` / `user_is_auto_candidate`) |
| Backfill de marcos | **OK** | `next_future_marco(jan/2022, set/2026) == jan/2027`; suite `test_auto_bootstrap_no_backfill` |
| Feriado municipal | **OK** | `calendar_br.national_holidays` sem SP/RJ/BH municipais; sem `holidays`/`workalendar` em deps |
| Papel RH novo / `is_rh` | **OK** | Sem campo `is_rh`; RH = `is_admin`; sem DRF/app nova |
| Lote via pageview HTTP | **OK** | `AutoGovernanceView.http_method_names` = GET/HEAD/OPTIONS; sem import da task Beat |

Suite: `pytest tests/test_auto_denylist_smoke.py` → **13 passed**. Checklist em [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md).

### Evidência T034 (Constitution Check pós-implementação)

Revisão 2026-09-10 — re-check I–VI + Visual/DS contra código vivo (não só design):

| Gate | Status | Evidência no código |
|---|---|---|
| **I. Django-First** | ✅ PASS | `apps/core/calendar_br.py` local (Páscoa + federais); sem `holidays`/`workalendar`/`djangorestframework` em `requirements.txt`; DTL/HTMX governança |
| **II. Escopo backend** | ✅ PASS | `AutoGovernanceView` ⊂ `AdminCyclesMixin`/`RequiresAdminMixin`; AuthZ em view, não em template |
| **III. Imutabilidade** | ✅ PASS | Snapshot Avaliação preservado (US5); events/`AuditLog` append-only; encerrados fora da rotina |
| **IV. Modularidade** | ✅ PASS | Domínio em `cycles` + `core.calendar_br` + `notifications`/`audit`/`reviews`; sem app Django nova |
| **V. Reprodutibilidade** | ✅ PASS | Stage/fórmulas/9-box/PDI fora do corte 018 (T031 denylist) |
| **VI. Assíncrono** | ✅ PASS | Beat `auto-cycle-admission-daily` → `run_auto_cycle_admission_daily` em `config/celery.py` (00:30) |
| **Visual / DS** | ✅ PASS | `auto_governance.html` + partials: Fraunces/Source Sans 3, Status Triad emerald/amber/rose, Lush Professional |
| **HTTP só lê** | ✅ PASS | `AutoGovernanceView.http_method_names = ['get','head','options']`; `views.py` **sem** import de `open_auto_cohort` / task Beat |
| **Zero lib feriados** | ✅ PASS | Assert denylist + inspeção `requirements.txt` |

Smoke estático: `pytest tests/test_auto_denylist_smoke.py` → **13 passed** (incl. GET-only governança + deps).

## Project Structure

### Documentation (this feature)

```text
specs/018-auto-cycle-admission/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── backend-scope-authz.md
│   ├── ui-visual-consistency.md
│   ├── auto-cohort-open-contract.md
│   ├── marco-eligibility-contract.md
│   ├── multi-open-ciclo-contract.md
│   ├── governance-surface-contract.md
│   └── non-goals-denylist.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks — NÃO criado aqui
```

### Source Code (repository root)

```text
apps/core/
└── calendar_br.py              # NOVO: feriados nacionais + is_business_day + first_business_day

apps/cycles/
├── models.py                   # + origem, chave_coorte/marco; remover single-open
├── exceptions.py               # exceções de coorte/idempotência (sem bloquear multi-open)
├── views.py                    # governança admin (lista/detalhe período)
├── forms.py                    # filtros governança (leve)
├── tasks.py                    # NOVO: run_auto_cycle_admission_daily
├── services/
│   ├── cycle.py                # open_cycle manual: permitir N abertos; sem CycleAlreadyOpenError de “único”
│   ├── eligibility.py          # predicado manual 015 intacto + ramo/helpers auto
│   ├── marco.py                # NOVO: próximo marco futuro; elegíveis do mês
│   ├── auto_cohort.py          # NOVO: abrir coorte idempotente + alertas individuais
│   └── governance.py           # NOVO: queries entrantes / sem data / alertas / falhas
├── migrations/                 # aditivas
└── templates cycles/           # governança no shell existente

apps/reviews/
└── services/enrollment.py      # ciclo= obrigatório em caminhos ambíguos; predicado por origem

apps/notifications/
├── models.py                   # Tipo(s) alerta ciclo aberto / digest governança se necessário
├── tasks.py / emails.py        # e-mail RH admin (padrão digest PDI)
└── templates/...

apps/audit/
└── services.py                 # write_audit_log explícito na abertura automática

apps/dashboard/ / apps/core/
├── context_processors.py       # ciclo(s) aberto(s) honestos
├── services/ciclo_options.py   # operacional = lista de abertos
└── goals/forms.get_open_ciclo  # semântica multi-open (ver contrato)

apps/goals/forms.py             # get_open_ciclo / get_open_ciclos

config/celery.py                # beat: auto-cycle-admission-daily

templates/cycles/
├── ciclo_list*.html            # copy multi-open + link governança
├── auto_governance*.html       # NOVO — mesmo DNA visual listagens
└── partials/...

tests/
├── test_calendar_br.py
├── test_marco_eligibility.py
├── test_auto_cohort_open.py
├── test_auto_bootstrap_no_backfill.py
├── test_auto_open_cycle_alert.py
├── test_multi_open_ciclo.py
├── test_auto_governance_authz.py
├── test_auto_denylist_smoke.py   # T031 — non-goals / denylist
└── regressões 015 / mid-cycle
```

**Structure Decision**: Monólito por apps de domínio existentes. Sem app nova. UI = extensão da governança de ciclos (admin), não ilha visual.

## Complexity Tracking

| Violation / desvio | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Django 6.x vs constituição “5.x” | Já é a versão do `requirements.txt` (precedente 015/017) | Downgrade fora do escopo desta feature |
| Quebra de “só um ciclo aberto” | FR-010; lote mensal + alerta sem trava exigem coexistência | Manter um aberto forçaria bloquear lote ou serializar meses — contradiz spec |
| Novo módulo calendário BR | Spec exige 1º dia útil + feriados nacionais; zero utilitário no repo | Lib externa (`holidays`/`workalendar`) = dependência nova sem necessidade (Princípio I) |
| Ajuste amplo de `get_open_ciclo` consumidores | Singular vira mentira operacional com N abertos | Ignorar → topbar/dashboards/enrollment ambíguos e regressões silenciosas |
