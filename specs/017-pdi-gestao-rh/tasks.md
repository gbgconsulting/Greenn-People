# Tasks: Gestão RH/Gestão de PDIs Atrasados

**Input**: Design documents from `/specs/017-pdi-gestao-rh/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme plan Project Structure + contratos (`pdi-overdue-list`, `pdi-overdue-notifications`, `pdi-complete-lifecycle`, `backend-scope-authz`) e quickstart smoke. Pytest-django; **sem** TDD obrigatório — testes na mesma fase da story após a fatia implementável.

**Organization**: Tasks por user story. Sequência obrigatória do plan: Fundação → US1 P1 (hub) → US2 P1 (alerta) → US3 P2 (tabela) → US4 P2 (digest) → US5 P3 (widget) → US6 P3 (board + concluir) → Polish. **MVP = Fundação + US1 + US2**.

## Escopo inválido (REJEITAR task/PR)

| Zona | Exemplos proibidos |
|------|--------------------|
| Papel RH novo | Novo `is_rh`, grupo Django, permissão dedicada |
| API / SPA | DRF, endpoints REST novos, lib UI/JS de grid |
| AuthZ no cliente | Filtrar lista/tabela só com Alpine/JS; confiar em `modo`/`visao` sem backend |
| Notificação fora do contrato | Push/in-app; e-mail a todos os admins por ação; alerta ao `responsavel` como canal próprio; cópia preventiva ao gestor |
| Domínio alheio | Aderência, ninebox, notas/etapas de avaliação, redesign tipografia/paleta do hub |
| CTA | Segundo botão primário competindo com “+ Novo PDI” no hub |

**Permitido**: estender `apps/pdi` (views/services/tasks/urls/forms/templates), `apps/notifications` (Tipo aditivo + tasks/emails/templates), `apps/dashboard` (KPI scoped), `config/celery.py` (schedule digest), testes em `tests/test_pdi_*.py`. Escopo sempre via `get_visible_users` / ownership / `ScopedObjectMixin` ([contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md)). UI só reusa canônicos ([contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md)).

**Teste de ouro**: manipular query string (`visao=equipe`, `modo=tabela`, `gestor=`, `atrasadas=1`) **não** vaza dados; esconder botão no HTML **não** é AuthZ; links de e-mail revalidam escopo na view.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US6 conforme spec.md
- Paths relativos à raiz do repositório

## Path Conventions

Monólito Django na raiz: `apps/pdi/`, `apps/notifications/`, `apps/dashboard/`, `templates/pdi/`, `templates/notifications/email/`, `templates/dashboard/`, `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar contratos e baseline de código antes de implementar

- [X] T001 Confirmar artefatos e gates em `specs/017-pdi-gestao-rh/{plan,spec,research,data-model,quickstart}.md` + `contracts/{backend-scope-authz,ui-visual-consistency,pdi-overdue-list,pdi-overdue-notifications,pdi-complete-lifecycle}.md` (sequência US1→US6; non-goals; AuthZ backend-only; visual Status Triad)
- [X] T002 [P] Mapear baseline vivo: `apps/pdi/views.py` (`PDIListView`, `_pdi_list_row`, `_group_acoes`), `apps/pdi/tasks.py` (`mark_overdue_pdi_actions`), `apps/pdi/services/{overdue,lifecycle,progress}.py`, `apps/notifications/{models,tasks,emails}.py` (`enviar_lembrete_acao_pdi_vencendo` / `_log_send` / `already_sent`), `config/celery.py`, templates `templates/pdi/{pdi_list,pdi_list_partial,partials/pdi_hub_card,acao_list_partial}.html` e canônicos `templates/components/{badge_status,ownership_visao_toggle,card,button}.html` — evidência: [contracts/baseline-vivo.md](./contracts/baseline-vivo.md)

**Checkpoint**: Contratos e pontos de extensão identificados; zero código de feature ainda

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Serviço de métricas de atraso + tipos `NotificacaoLog` aditivos — **BLOQUEIA** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase.

- [X] T003 Criar `apps/pdi/services/overdue_metrics.py` com annotate/helpers de `acoes_atrasadas_count`, `dias_atraso_max`, `proximo_prazo` e predicado/filtro de faixa `1-7` / `8-30` / `30+` conforme [data-model.md](./data-model.md) e [contracts/pdi-overdue-list.md](./contracts/pdi-overdue-list.md) (faixas inclusivas no limite inferior; `30+` aberto; ação sem prazo fora)
- [X] T004 [P] Estender `NotificacaoLog.Tipo` em `apps/notifications/models.py` com `atraso_pdi` e `digest_pdi_atrasos` (valores alinhados a [contracts/pdi-overdue-notifications.md](./contracts/pdi-overdue-notifications.md)); gerar migration aditiva em `apps/notifications/migrations/` — **sem** alterar tipos existentes `lembrete_pdi` / `lembrete_etapa` / `feedback_continuo`
- [X] T005 Expor helpers de annotate no queryset de listagem em `apps/pdi/views.py` (ou função compartilhada chamada por `PDIListView.get_queryset`) reutilizando T003 — ainda **sem** chip/UI de filtro; arquivados permanecem fora do fluxo operacional padrão

**Checkpoint**: Métricas calculáveis no backend; migration de tipos aplicável; foundation pronta para US1+

---

## Phase 3: User Story 1 — Ver e filtrar PDIs com atraso no hub (Priority: P1) 🎯 MVP

**Goal**: Hub mostra badge de ações atrasadas nos cards e chip “Com atrasadas”; filtro e contagem respeitam escopo  
**Independent Test**: PDIs com/sem atraso no escopo; chip filtra só com atraso; badge = contagem real; colaborador só vê os próprios; arquivado fora do operacional (quickstart §A; SC-001)

### Implementation for User Story 1

- [X] T006 [US1] Em `apps/pdi/views.py`, aplicar filtro query param `atrasadas=1` no `PDIListView` (e partial HTMX) sobre annotate de T003/T005 — só PDIs do escopo com ≥1 ação `atrasada`; combinar com `status`/`q`/`visao` vigentes; arquivados só se `status=arquivados` explícito ([contracts/pdi-overdue-list.md](./contracts/pdi-overdue-list.md))
- [X] T007 [US1] Estender `_pdi_list_row` em `apps/pdi/views.py` para expor `acoes_atrasadas_count` (e campos derivados necessários ao card) a partir do annotate — UI não recalcula
- [X] T008 [P] [US1] Adicionar chip “Com atrasadas” em `templates/pdi/pdi_list.html` no **mesmo estilo emerald** dos chips de status existentes (param `atrasadas=1`); preservar CTA primário “+ Novo PDI” soberano ([contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md))
- [X] T009 [P] [US1] Em `templates/pdi/partials/pdi_hub_card.html`, exibir `badge_status` `atrasada` (rose) com “N atrasada(s)” **somente** se N>0 — sem substituir variante do plano (`em_andamento` etc.)
- [X] T010 [US1] Garantir swap HTMX em `templates/pdi/pdi_list_partial.html` preserva `atrasadas` e demais query params no `#list-container`
- [X] T011 [US1] Cobrir contrato de listagem/escopo em `tests/test_pdi_overdue_list_filters.py` (casos: `atrasadas=1`, contagem no card, colaborador sem leak, arquivado fora) conforme [contracts/pdi-overdue-list.md](./contracts/pdi-overdue-list.md) + [contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md)

**Checkpoint**: US1 independentemente testável; MVP de visibilidade no hub pronto

---

## Phase 4: User Story 2 — Alertar dono e gestor quando a ação fica atrasada (Priority: P1) 🎯 MVP

**Goal**: Ao marcar ação como atrasada, e-mail ao dono + gestor direto (se ativo e distinto), com dedupe diário; lembrete preventivo intacto  
**Independent Test**: Rodar `mark_overdue_pdi_actions`; logs `atraso_pdi` para dono/gestor; 2ª run no mesmo dia = 0; arquivado/concluída = 0 (quickstart §B; SC-002)

### Implementation for User Story 2

- [X] T012 [P] [US2] Implementar `send_*` / `referencia_*` de atraso em `apps/notifications/emails.py` espelhando o pipeline de `lembrete_pdi` (assunto/corpo mínimos: ação/PDI, prazo, link detalhe)
- [X] T013 [P] [US2] Criar templates `templates/notifications/email/atraso_pdi_{subject,body}.{txt,html}` reusando `templates/emails/base.html` (marca emerald; sem rose de “erro de sistema”)
- [X] T014 [US2] Criar task `enviar_alerta_acao_pdi_atrasada` (ou nome equivalente) em `apps/notifications/tasks.py`: destinatários = dono ∪ `line_manager(dono)` se ativo e ≠ dono; skip inativo/arquivado/concluída; dedupe `already_sent(tipo=atraso_pdi, referencia=acao_pdi:{id}, janela=ISO do dia)`; `_log_send` append-only ([contracts/pdi-overdue-notifications.md](./contracts/pdi-overdue-notifications.md))
- [X] T015 [US2] Integrar disparo no fluxo de `apps/pdi/tasks.py` (`mark_overdue_pdi_actions`) e/ou `apps/pdi/services/overdue.py` **após** marcar `atrasada` — sem alterar `enviar_lembrete_acao_pdi_vencendo` / tipo `lembrete_pdi`
- [X] T016 [US2] Cobrir contrato de alerta em `tests/test_pdi_overdue_notifications.py` (dono+gestor, só dono, dedupe, arquivado=0, `lembrete_pdi` independente)

**Checkpoint**: US1+US2 = MVP gerencial (visibilidade + alerta); pronto para demo

---

## Phase 5: User Story 3 — Vista tabela operacional para RH/Gestão (Priority: P2)

**Goal**: Em visão equipe/organização, toggle Cards|Tabela com colunas operacionais e filtros gestor/área/faixa em `<details>`  
**Independent Test**: Admin/gestor alterna tabela; filtros batem escopo; colaborador não vê toggle/tabela (quickstart §C; SC-003)  
**Dependência**: Annotate/métricas de US1 (T003/T005/T007)

### Implementation for User Story 3

- [X] T017 [US3] Em `apps/pdi/views.py`, aceitar `modo=cards|tabela` e filtros `gestor` / `area` / `faixa_atraso`; se `not can_view_team_ownership_list`, **forçar** cards e ignorar filtros gerenciais no backend ([contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md)); opções de select limitadas ao escopo
- [X] T018 [P] [US3] Se necessário, Form leve em `apps/pdi/forms.py` para filtros gerenciais (gestor/área/faixa) — validação server-side; IDs fora do escopo ignorados/seguros
- [X] T019 [P] [US3] Criar `templates/pdi/partials/pdi_table.html` no envelope registry / classes `leader-team-table` (colunas: colaborador, gestor, área, progresso, nº atrasadas, dias max, próximo prazo); zero/empty claro quando sem atraso ([contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md))
- [X] T020 [US3] Em `templates/pdi/pdi_list.html` + `pdi_list_partial.html`, toggle Cards|Tabela (DNA de `ownership_visao_toggle`: segment `bg-slate-100` + ativo `bg-brand-gradient`) **só** quando visão equipe permitida; incluir parcial de tabela; filtros profundos em `<details>` “Filtros” (padrão `user_list_filters` / avaliações) — **não** empilhar como chips no hub
- [X] T021 [US3] Estender `_pdi_list_row` / context em `apps/pdi/views.py` com `dias_atraso_max`, `proximo_prazo`, gestor/área do dono para linhas da tabela
- [X] T022 [US3] Estender `tests/test_pdi_overdue_list_filters.py` (ou arquivo dedicado) com casos tabela: colunas, `faixa_atraso`, colaborador sem toggle/leak, `modo=tabela` forçado a cards sem permissão

**Checkpoint**: US3 independentemente testável sobre a base de métricas da US1

---

## Phase 6: User Story 4 — Digest periódico para RH/Admin (Priority: P2)

**Goal**: Beat semanal envia digest agregado só a admins ativos quando há ≥1 atraso elegível; silêncio se zero  
**Independent Test**: Com atrasos → 1 e-mail/admin/semana + CTA; sem atrasos → 0; não-admin não recebe (quickstart §D; SC-004)

### Implementation for User Story 4

- [X] T023 [P] [US4] Implementar agregação org de atrasos (totais PDIs/ações + top áreas/gestores) em `apps/pdi/services/overdue_metrics.py` (ou helper dedicado no mesmo módulo) — só PDIs não arquivados
- [X] T024 [P] [US4] Criar templates `templates/notifications/email/digest_pdi_atrasos_{subject,body}.{txt,html}` com totais, focos e CTA para `/pdi/?visao=equipe&atrasadas=1` (modo tabela opcional)
- [X] T025 [US4] Implementar task Beat `enviar_digest_pdi_atrasos` em `apps/notifications/tasks.py`: se contagem org == 0 → exit silencioso; senão loop `is_admin` ativos + dedupe `digest_pdi_atrasos` / `referencia=org:pdi_atrasos` / `janela=YYYY-Www`; reusar `_log_send` + send em `apps/notifications/emails.py`
- [X] T026 [US4] Registrar schedule semanal em `config/celery.py` alinhado ao horário operacional dos lembretes existentes — **sem** remover jobs diários de overdue/lembrete
- [X] T027 [US4] Cobrir digest em `tests/test_pdi_digest.py` (com atrasos, silêncio zero, não-admin excluído, dedupe semanal)

**Checkpoint**: Oversight RH sem ruído por ação; US2 permanece o canal pontual

---

## Phase 7: User Story 5 — Widget de atrasos no dashboard do escopo (Priority: P3)

**Goal**: Card KPI nos dashboards time/admin com contagem scoped e link para listagem filtrada  
**Independent Test**: Contagem coerente + link `atrasadas=1`; zero neutro sem rose de erro; colaborador sem bloco gerencial (quickstart §E; SC-005)

### Implementation for User Story 5

- [X] T028 [US5] Expor contagem scoped de atrasos (PDIs e/ou ações) via serviço em `apps/pdi/services/overdue_metrics.py` consumida por `apps/dashboard/views.py` (`TeamDashboardView` / `AdminDashboardView`) — AuthZ no backend; template só renderiza flags/números
- [X] T029 [P] [US5] Adicionar bloco KPI em `templates/dashboard/team.html` e `templates/dashboard/admin.html` via `templates/components/card.html` (accent atenção crítica conforme DS do card; link para `/pdi/?…&atrasadas=1`); zero = estado neutro, **não** erro vermelho ([contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md))
- [X] T030 [US5] Teste de superfície/escopo do widget (estender teste dashboard existente ou `tests/test_pdi_overdue_list_filters.py`): contagem scoped; colaborador sem dados de terceiros via link

**Checkpoint**: Awareness no dashboard sem substituir a tabela US3

---

## Phase 8: User Story 6 — Board com coluna Atrasadas e conclusão do plano (Priority: P3)

**Goal**: Coluna Atrasadas no board; `complete_pdi` explícito quando 100% ações concluídas → status `concluido`  
**Independent Test**: Ação atrasada só na coluna Atrasadas; concluir 100% OK; pendente rejeita; arquivado bloqueado (quickstart §F; SC-006)

### Implementation for User Story 6

- [X] T031 [US6] Estender `_group_acoes` em `apps/pdi/views.py` com bucket `atrasadas` (`status == atrasada`) separado de em andamento ([contracts/pdi-complete-lifecycle.md](./contracts/pdi-complete-lifecycle.md))
- [X] T032 [P] [US6] Atualizar `templates/pdi/acao_list_partial.html` (+ partials de card se necessário) para renderizar coluna **Atrasadas** com `badge_status` rose
- [X] T033 [US6] Implementar `complete_pdi` em `apps/pdi/services/lifecycle.py`: exige `ativo` + ≥1 ação + todas `concluida`; senão raise com mensagem clara; arquivado/concluído rejeitados
- [X] T034 [US6] Adicionar view/rota POST de conclusão em `apps/pdi/views.py` + `apps/pdi/urls.py` com `ScopedObjectMixin` / `_get_scoped_pdi`; revalidar no serviço; feedback HTMX/messages
- [X] T035 [P] [US6] CTA “Concluir plano” em `templates/pdi/pdi_detail.html` (secundário/outline via `button.html`) **só** quando context flag `can_complete` vier do backend; **não** roubar CTA primário de criar ação
- [X] T036 [US6] Cobrir lifecycle + board em `tests/test_pdi_complete.py` (100% → concluído; pendente rejeita; arquivado rejeita; coluna Atrasadas; POST fora de escopo 403/404)

**Checkpoint**: Todas as user stories independentemente funcionais

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validação E2E, regressão visual/AuthZ e limpeza

- [X] T037 [P] Rodar validação guiada de `specs/017-pdi-gestao-rh/quickstart.md` (cenários A–F) + checklist visual de [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md) — evidência: `scripts/validate_quickstart_017_pdi.py` (16/16) + pytest smoke 30 passed + gate visual marcado em `contracts/ui-visual-consistency.md`
- [X] T038 [P] Suite smoke: `pytest tests/test_pdi_overdue_list_filters.py tests/test_pdi_overdue_notifications.py tests/test_pdi_digest.py tests/test_pdi_complete.py` (+ regressão hub/board existente se aplicável) -q — evidência: 37 passed (`test_pdi_hub_variant` incluído)
- [X] T039 Revisar anti-padrões AuthZ de [contracts/backend-scope-authz.md](./contracts/backend-scope-authz.md) (query string não autoriza; filtros gestor/área scoped; digest só admin; concluir no serviço) — evidência: §Evidência T039 em `contracts/backend-scope-authz.md` + `test_lider_gestor_e_area_fora_do_escopo_ignorados_sem_leak` (5 AuthZ checks passed)
- [X] T040 [P] Confirmar non-goals: zero papel RH, zero DRF/SPA, `lembrete_pdi` preventivo intacto, um CTA primário no hub, rose só para atraso real — evidência: §Evidência T040 em `plan.md` + pytest `test_lembrete_pdi_permanece_independente_do_atraso` / `test_lembrete_pdi_duas_vezes_mesma_janela_um_envio` (2 passed)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências
- **Foundational (Phase 2)**: Depende do Setup — **BLOQUEIA** todas as stories
- **US1 (Phase 3)**: Após Foundational
- **US2 (Phase 4)**: Após Foundational (pode paralelizar com US1 se staffed; MVP recomenda US1→US2)
- **US3 (Phase 5)**: Após Foundational + annotate/métricas US1 (T003/T005/T007)
- **US4 (Phase 6)**: Após Foundational + tipos notificação (T004); reusa query de atraso
- **US5 (Phase 7)**: Após métricas (T003); link útil após US1 (filtro); ideal após US3
- **US6 (Phase 8)**: Após Foundational; independente de US3–US5
- **Polish (Phase 9)**: Após stories desejadas

### User Story Dependencies

- **US1 (P1)**: Sem dependência de outras stories
- **US2 (P1)**: Independente de US1 (mesmo foundation); juntos = MVP
- **US3 (P2)**: Depende das métricas/annotate introduzidas para US1
- **US4 (P2)**: Independente de UI; precisa tipos + agregação de atraso
- **US5 (P3)**: Consome contagem scoped; destino do link = filtro US1
- **US6 (P3)**: Independente (board + lifecycle)

### Within Each User Story

- Serviço/annotate antes de template
- Backend AuthZ antes de ocultar controles na UI
- Task/e-mail antes de agendar Beat (US4)
- Story validável no checkpoint antes da próxima prioridade (salvo paralelismo consciente)

### Parallel Opportunities

- T001 ∥ T002 (Setup)
- T003 → depois T004 ∥ preparação; T004 ∥ leitura de templates canônicos
- US1: T008 ∥ T009 (templates)
- US2: T012 ∥ T013 (e-mail + templates) antes de T014
- US3: T018 ∥ T019 (form + partial tabela)
- US4: T023 ∥ T024 antes de T025
- US5: T029 templates em paralelo após T028
- US6: T032 ∥ T035 após flags/serviço
- Após Foundational: US1 e US2 podem avançar em paralelo; US4 paralelo a US3 se capacity

---

## Parallel Example: User Story 1

```bash
# Templates em paralelo após views/annotate:
Task: "Chip Com atrasadas em templates/pdi/pdi_list.html"
Task: "Badge rose no card em templates/pdi/partials/pdi_hub_card.html"
```

## Parallel Example: User Story 2

```bash
# Conteúdo de e-mail em paralelo antes da task Celery:
Task: "send_* atraso em apps/notifications/emails.py"
Task: "Templates atraso_pdi_* em templates/notifications/email/"
```

## Parallel Example: User Story 3

```bash
Task: "Form filtros em apps/pdi/forms.py"
Task: "Partial tabela em templates/pdi/partials/pdi_table.html"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Phase 1 Setup  
2. Phase 2 Foundational (métricas + tipos NotificacaoLog)  
3. Phase 3 US1 — hub filtro/badge  
4. Phase 4 US2 — alerta dono/gestor  
5. **STOP and VALIDATE** — quickstart A+B + SC-001/SC-002  

### Incremental Delivery

1. + US3 tabela operacional → demo RH diária  
2. + US4 digest semanal → oversight sem ruído  
3. + US5 widget dashboard → descoberta  
4. + US6 board + concluir → fecha ciclo do plano  
5. Polish / quickstart completo  

### Parallel Team Strategy

1. Time fecha Setup + Foundational junto  
2. Dev A: US1 → US3 → US5  
3. Dev B: US2 → US4  
4. Dev C: US6 (após foundation)  
5. Integrar e rodar Phase 9  

---

## Notes

- [P] = arquivos diferentes, sem depender de task incompleta na mesma fatia  
- Labels [US1]…[US6] = rastreio à spec  
- AuthZ e métricas **sempre** no backend; template só apresenta  
- Commit por task ou grupo lógico; validar checkpoint de cada story  
- Evitar: segundo hub, lib de grid, notificar admin por ação, rose em empty state  
