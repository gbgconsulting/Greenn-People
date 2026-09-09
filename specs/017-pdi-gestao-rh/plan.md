# Implementation Plan: Gestão RH/Gestão de PDIs Atrasados

**Branch**: `017-pdi-gestao-rh` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-pdi-gestao-rh/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). **Não** gera `tasks.md` (isso é `/speckit-tasks`).

**Diretriz visual obrigatória**: [speckit_princ_pios_e_diretrizes_greenn_people.md](../../speckit_princ_pios_e_diretrizes_greenn_people.md) + padrões já implementados no hub PDI, listagens admin/avaliações e Status Triad. Ver [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md).

## Summary

Dar à RH/Gestão **visibilidade e escalonamento de ações de PDI atrasadas**: filtro + indicador no hub; alerta ao dono e gestor quando a ação fica atrasada; vista tabela operacional (equipe/organização) com filtros gerenciais; digest semanal para admin; widget no dashboard; coluna Atrasadas no board e conclusão explícita do plano.

Abordagem técnica: estender `PDIListView` / board / lifecycle em `apps/pdi`; espelhar pipeline de `enviar_lembrete_acao_pdi_vencendo` + `NotificacaoLog` para atraso e digest; **zero** papel RH novo; escopo via `get_visible_users` / ownership já existentes. UI **só** por reuso de componentes e padrões visuais canônicos (não inventar ilha de estilo).

## Sequenciamento (obrigatório)

```text
Fundação: annotate atrasadas + contrato UI + tipos NotificacaoLog
        │
        ▼
US1 P1 — Hub: chip “Com atrasadas” + badge no card
        │
        ▼
US2 P1 — Alerta de atraso (dono + gestor) no job de overdue
        │
        ▼
US3 P2 — Vista tabela + filtros gestor/área/faixa (visão equipe)
        │
        ▼
US4 P2 — Digest semanal admin
        │
        ▼
US5 P3 — Widget KPI no dashboard do escopo
        │
        ▼
US6 P3 — Coluna Atrasadas no board + concluir plano
```

US1 e US2 são o MVP gerencial. US3 depende do annotate/métricas de US1. US4/US5 reusam a mesma query de atraso. US6 é polish de detalhe + lifecycle.

## Non-Goals

- Novo papel “RH”; API REST; push/in-app.
- Notificar todos os admins a cada ação atrasada individualmente.
- Cópia do lembrete **preventivo** ao gestor (só atraso efetivo nesta fatia).
- Notificar o `responsavel` da ação como canal próprio (salvo coincidência com dono/gestor).
- Reescrever aderência de liderança / ninebox.
- Redesign do hub PDI ou nova tipografia/paleta.
- CTA primário extra competindo no hub (mantém “+ Novo PDI” soberano).

### Evidência T040 (confirmação non-goals)

Revisão 2026-09-09 — varredura estática + testes focados de `lembrete_pdi`:

| Non-goal | Resultado | Evidência |
|---|---|---|
| Zero papel RH | **OK** | Sem `is_rh` em `apps/accounts`; digest usa `CustomUser.objects.filter(is_admin=True)` (`enviar_digest_pdi_atrasos`); “RH” = admin existente |
| Zero DRF/SPA | **OK** | Sem `rest_framework` / `djangorestframework` em deps; `INSTALLED_APPS` só apps de domínio; `apps/pdi/urls.py` = CBVs Django (list/create/detail/archive/complete) |
| `lembrete_pdi` preventivo intacto | **OK** | Tipo `LEMBRETE_PDI` inalterado; task Beat `enviar_lembrete_acao_pdi_vencendo` intacta; atraso usa tipo separado `atraso_pdi`; `test_lembrete_pdi_permanece_independente_do_atraso` + `test_lembrete_pdi_duas_vezes_mesma_janela_um_envio` → **2 passed** |
| Um CTA primário no hub | **OK** | Único `variant="primary"` em `templates/pdi/pdi_list.html` = “Novo plano”; toggle/chips/filtros sem primário concorrente |
| Rose só para atraso real | **OK** | Badge rose no hub só se `acoes_atrasadas_count > 0`; chip “Com atrasadas” emerald; KPI zero com `accent="neutral"`; `badge_status` Status Triad (`atrasada`/`reprov*` = rose; pendência = amber/slate) |

## Technical Context

**Language/Version**: Python 3.x / Django (monólito vigente; constituição cita 5.x — sem novo desvio de stack)

**Primary Dependencies**: Django full stack (DTL + HTMX + Tailwind CLI); Celery + Celery Beat; e-mail via pipeline `apps/notifications`. Sem DRF, SPA, lib UI nova.

**Storage**: SQLite (dev) / PostgreSQL (prod). Evolução aditiva: novos valores em `NotificacaoLog.Tipo` (migration); possível serviço de annotate sem tabela nova. Models `PDI` / `AcaoPDI` já cobrem status necessários.

**Testing**: pytest-django — listagem/filtros/escopo, jobs de notificação (dedupe), lifecycle de conclusão, regressão visual de contratos (asserts de template/contexto onde já é padrão do repo).

**Target Platform**: Web autenticado; desktop-first; mobile sem quebrar (tabela com scroll interno no envelope existente).

**Project Type**: Monólito Django (templates servidor + HTMX)

**Performance Goals**: Annotates/aggregates no queryset da listagem (leve); digest e alertas **assíncronos** (Beat). Sem agregação pesada síncrona no dashboard além de contagem scoped simples (ou reuso de annotate).

**Constraints**:
- Constitution II: escopo sempre no backend (`get_visible_users`, ownership, `ScopedObjectMixin`); ver [contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md) — UI/HTMX só apresentam; lógica de quem vê/muta/conta/conclui/notifica no server
- Visual: Fraunces + Source Sans 3; emerald brand; Status Triad (`atrasada` = rose crítico); `rounded-lg`; um CTA primário
- Filtros gerenciais profundos em `<details>` / segment bar (padrão cadastros), não poluir o hub
- Vermelho/rose **só** para atraso/reprovação real — não para empty/pendência neutra

**Scale/Scope**: 6 user stories; superfícies: hub PDI, detalhe/board PDI, e-mails, dashboards líder/gestor/admin; ~2 tipos novos de notificação + 1 task digest.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio / Gate | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | DTL/HTMX/Tailwind; Celery Beat já usado; sem lib nova. |
| II. Segurança e Escopo no Backend | ✅ PASS | Gate explícito: [contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md) — matriz por US; UI nunca autoriza; queryset/`ScopedObjectMixin`/tasks resolvem escopo; links de e-mail não expandem AuthZ. |
| III. Imutabilidade e Integridade | ✅ PASS | `NotificacaoLog` append-only; archive/concluir sem apagar histórico; FKs existentes preservadas. |
| IV. Modularidade por Domínio | ✅ PASS | Domínio em `pdi`; envio em `notifications`; KPI em `dashboard` consumindo serviço PDI. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Sem tocar notas/etapas de avaliação; progresso PDI continua % de ações concluídas. |
| VI. Performance Assíncrona | ✅ PASS | Alertas + digest via Celery; listagem só annotate scoped. |
| Stack obrigatória | ✅ PASS | Sem DRF/SPA. |
| **Visual / DS (feature gate)** | ✅ PASS | Contrato [ui-visual-consistency.md](./contracts/ui-visual-consistency.md) amarra diretrizes Greenn People + padrões já shipped. |

**Post-design re-check (Phase 1)**: Gates permanecem ✅ PASS. Sem repository pattern extra; sem papel novo; tipos de notificação aditivos.

## Project Structure

### Documentation (this feature)

```text
specs/017-pdi-gestao-rh/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── baseline-vivo.md         # T002 — as-is dos pontos de extensão
│   ├── backend-scope-authz.md   # Gate AuthZ — backend-authoritative
│   ├── ui-visual-consistency.md
│   ├── pdi-overdue-list.md
│   ├── pdi-overdue-notifications.md
│   └── pdi-complete-lifecycle.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks — NÃO criado aqui
```

### Source Code (repository root)

```text
apps/pdi/
├── models.py                 # status já existentes (sem breaking)
├── views.py                  # list annotate/filtros, table mode, board group, complete
├── tasks.py                  # mark_overdue (+ hook notificação)
├── services/
│   ├── overdue.py            # recálculo existente
│   ├── lifecycle.py          # + complete_pdi
│   ├── progress.py
│   └── overdue_metrics.py    # NOVO: annotate/contagens/faixas (ou nome equivalente)
├── urls.py                   # rota complete (+ modal se necessário)
└── forms.py                  # se filtros precisarem de Form leve

apps/notifications/
├── models.py                 # Tipo: ATRASO_PDI, DIGEST_PDI_ATRASOS
├── tasks.py                  # notificar atraso; digest semanal
├── emails.py                 # send_* + referencia_*
└── templates/notifications/email/
    ├── atraso_pdi_*.{txt,html}
    └── digest_pdi_atrasos_*.{txt,html}

apps/dashboard/
├── views.py / services       # contagem scoped + card KPI
└── templates/dashboard/      # admin.html / team.html (bloco KPI)

templates/pdi/
├── pdi_list.html
├── pdi_list_partial.html
├── partials/pdi_hub_card.html
├── partials/pdi_list_filters.html   # se extrair filtros avançados
├── partials/pdi_table.html          # NOVO — leader-team-table / registry
├── acao_list_partial.html           # coluna Atrasadas
└── partials/acao_card_*.html

templates/components/
├── badge_status.html         # reuso status=atrasada
├── ownership_visao_toggle.html
├── card.html                 # KPI dashboard
└── button.html

config/celery.py              # schedule digest + integrar notificação no overdue

tests/
├── test_pdi_overdue_list_filters.py
├── test_pdi_overdue_notifications.py
├── test_pdi_digest.py
├── test_pdi_complete.py
└── (extensões dos testes de hub/board existentes)
```

**Structure Decision**: Monólito Django por apps de domínio (`pdi`, `notifications`, `dashboard`). Sem app novo. UI em templates existentes + partials no padrão HTMX `#list-container`.

## Complexity Tracking

> Nenhuma violação constitucional a justificar. Extensão de `NotificacaoLog.Tipo` e partials de tabela são o mínimo necessário alinhado a padrões já presentes.
