# Contract: Baseline vivo (pré-Foundational / pré-US1)

**Feature**: `017-pdi-gestao-rh`  
**Task**: T002  
**Registrado**: 2026-09-09  
**Objetivo**: Congelar o estado **atual** dos pontos de extensão listados em T002 antes de annotate/métricas, tipos novos de `NotificacaoLog`, chip “Com atrasadas”, alertas de atraso, tabela, digest, KPI e coluna Atrasadas.

**Regra**: este documento descreve o *as-is*. Ampliações entram só a partir de T003+ — **sem** código de feature nesta task.

### Confirmação T002 (2026-09-09)

- [x] Paths allowlist existem e batem com o inventário abaixo
- [x] Extension points (annotate listagem, `_pdi_list_row`, `_group_acoes`, `mark_overdue_pdi_actions`, pipeline `_log_send`/`already_sent`, Beat) identificados
- [x] Gaps vs plan/research registrados (o que **ainda não** existe)
- [x] Nenhuma alteração de feature code; ignore files do repo já cobrem Python/Node/Docker

---

## 1. Inventário de paths

| Path | Papel atual | Extensão prevista (feature) |
|------|-------------|-----------------------------|
| `apps/pdi/views.py` | Hub list + board grouping | Annotate atrasadas; filtro; table mode; bucket Atrasadas; complete |
| `apps/pdi/tasks.py` | Job diário marca `atrasada` | Hook notificação atraso pós-marcação |
| `apps/pdi/services/overdue.py` | Recálculo ao editar prazo | Sem mudança obrigatória |
| `apps/pdi/services/lifecycle.py` | `archive_pdi` / mutações | `complete_pdi` (US6) |
| `apps/pdi/services/progress.py` | % ações concluídas | Intacta (Constitution V) |
| `apps/pdi/services/overdue_metrics.py` | **Ausente** | NOVO (T003) |
| `apps/notifications/models.py` | 3 tipos de log | + `atraso_pdi`, `digest_pdi_atrasos` |
| `apps/notifications/tasks.py` | Lembrete preventivo PDI | Tasks atraso + digest |
| `apps/notifications/emails.py` | `send_lembrete_pdi_email` | `send_*` atraso/digest |
| `config/celery.py` | Beat overdue + lembrete | + digest semanal |
| Templates PDI hub/board | Cards + 3 colunas | Chip, badge, tabela, 4ª coluna |
| Components canônicos | Badge/toggle/card/button | Reuso (sem ilha de estilo) |

---

## 2. `apps/pdi/views.py` (as-is)

### `PDIListView`

| Aspecto | Baseline atual |
|---------|----------------|
| Mixins | `LoginRequiredMixin`, `ScopedObjectMixin`, `HtmxPaginatedListMixin`, `ListView` |
| Templates | `pdi/pdi_list.html` + partial `pdi/pdi_list_partial.html` |
| Escopo | `scope_user_field = 'usuario'`; fatia `?visao=` via `resolve_ownership_visao` / `apply_ownership_visao` |
| Paginação | `paginate_by = 6` |
| Annotates | `total_acoes`, `acoes_concluidas` (status=`concluida`), `prazo_min`, `prazo_max` |
| Filtros GET | `status` ∈ `PDI.Status`; `q` (titulo/nome/email); **sem** `atrasadas` / faixa / gestor / área / mode tabela |
| Chips hub | `_HUB_FILTER_CHOICES`: Todos / Em andamento (`ativo`+`total_acoes>0`) / Concluídos / Arquivados |
| Contexto | `pdi_rows`, chips, busca, toggle visão (`can_view_team_ownership_list`), empty porta |

**Gap**: nenhum `Count`/`Max` de ações `atrasada`; sem modo tabela; arquivados só via chip de status (fora do fluxo operacional padrão do hub “Em andamento”).

### `_pdi_list_row(pdi, *, viewer_id)`

Retorna dict para o card: progresso, `hub_variant` (`concluido`/`arquivado`/`aguardando`/`em_andamento`), labels CTA/status, período, footer (gestor se self), `pode_arquivar`.

**Gap**: sem `acoes_atrasadas_count`, `dias_atraso_max`, `proximo_prazo`, nem flag para badge rose no card. Variant **não** muda por ações atrasadas (plano ativo com ações → sempre `em_andamento`).

### `_group_acoes(acoes)`

Três buckets:

| Bucket | Critério |
|--------|----------|
| `acoes_concluidas` | `status == concluida` |
| `acoes_proximas` | `status == pendente` |
| `acoes_em_andamento` | **else** — inclui `em_andamento` **e** `atrasada` |

Contexto: `total_em_andamento`, `total_acoes`.

**Gap**: coluna/bucket dedicado **Atrasadas** (US6); hoje atraso some no “Em andamento”.

---

## 3. `apps/pdi/tasks.py` — `mark_overdue_pdi_actions`

| Aspecto | Baseline atual |
|---------|----------------|
| Beat | `crontab(hour=0, minute=15)` em `config/celery.py` |
| Query | `prazo < today`; exclui `concluida` e já `atrasada`; exclui `pdi.status=arquivado` |
| Persistência | loop + `save(update_fields=['status','updated_at'])` por linha |
| Retorno | `int` (qtd atualizada) |
| Notificação | **Nenhuma** — só muta status |

**Gap / gancho**: ponto natural pós-`save` para disparar alerta `atraso_pdi` (dono + `line_manager`), sem reutilizar `lembrete_pdi`.

---

## 4. Serviços PDI

### `overdue.recalculate_overdue_status`

Só **desfaz** atraso se `atrasada` e `prazo >= hoje` → `pendente`. Marcar atraso continua exclusivo do job diário.

### `lifecycle`

- `archive_pdi`: `ativo` → `arquivado`; rejeita `concluido`; idempotente se já arquivado.
- `pdi_allows_action_mutations`: `status != arquivado` (inclui `concluido` hoje — mutações ainda permitidas se não arquivado).

**Gap**: `complete_pdi` ausente (US6 / contrato lifecycle).

### `progress.calculate_pdi_progress`

`% = concluídas / total` (duas casas). Independente de atraso.

---

## 5. Notificações (as-is)

### `NotificacaoLog.Tipo`

| Valor | Uso |
|-------|-----|
| `lembrete_etapa` | Ciclo aberto, `data_fim = hoje+N` |
| `lembrete_pdi` | Ação PDI com `prazo = hoje+N` → **dono** |
| `feedback_continuo` | Evento único |

**Ausentes**: `atraso_pdi`, `digest_pdi_atrasos`.

Dedupe: índice `(destinatario, tipo, referencia, janela)` + `already_sent(..., status=enviado)`. Append-only (`save`/`delete` protegidos).

### Pipeline reutilizável

```text
already_sent(dest, tipo, ref, janela)? → skip
else → _log_send(send_fn) → NotificacaoLog enviado|falha
```

`enviar_lembrete_acao_pdi_vencendo`: elegibilidade `_is_pdi_eligible` (não concluída, prazo==target, dono ativo, PDI não arquivado); ref `acao_pdi:{id}` via `referencia_lembrete_pdi`; janela = data-alvo ISO; **só dono**.

`send_lembrete_pdi_email`: CTA `pdi:detail`; templates `notifications/email/lembrete_pdi_*`.

**Gap**: espelhar pipeline para atraso efetivo (multi-destinatário) e digest semanal admin; **não** alterar semântica de `lembrete_pdi`.

---

## 6. `config/celery.py` (Beat)

| Key | Task | Schedule |
|-----|------|----------|
| `mark-overdue-pdi-actions-daily` | `apps.pdi.tasks.mark_overdue_pdi_actions` | 00:15 |
| `enviar-lembrete-prazo-etapa-daily` | `...enviar_lembrete_prazo_etapa` | 08:00 |
| `enviar-lembrete-acao-pdi-vencendo-daily` | `...enviar_lembrete_acao_pdi_vencendo` | 08:15 |
| `calculate-adherence-snapshots-daily` | dashboard adherence | 01:00 |

**Gap**: entrada Beat **semanal** para digest `digest_pdi_atrasos`.

---

## 7. Templates PDI (as-is)

| Template | Baseline |
|----------|----------|
| `pdi_list.html` | H1 Fraunces; CTA primário único “Novo plano” (`button` primary); toggle ownership; include partial |
| `pdi_list_partial.html` | `#list-container`; busca HTMX; chips emerald; grid cards 1/2/3 cols; empty neutro; **sem** toggle Cards/Tabela; **sem** `<details>` filtros gerenciais |
| `partials/pdi_hub_card.html` | Faixa/status por `hub_variant` (emerald/amber/slate); progresso; **sem** badge rose de atraso |
| `acao_list_partial.html` | Board 8+4: Em andamento / Próximas / Concluídas; **sem** seção Atrasadas |

---

## 8. Components canônicos (reuso)

| Component | Baseline relevante à feature |
|-----------|------------------------------|
| `badge_status.html` | `atrasada` → **rose** (Status Triad) — pronto para badge no card/tabela |
| `ownership_visao_toggle.html` | Segment `bg-slate-100` + ativo `bg-brand-gradient`; preserva querystring |
| `card.html` | KPI frame; accents `primary\|warning\|neutral\|success` (faixa superior); footer link — alvo widget dashboard |
| `button.html` | `primary\|secondary\|outlined\|loading`; hub já usa primary soberano |

---

## 9. Mapa gap → tasks

| Gap as-is | Task |
|-----------|------|
| Serviço annotate/faixas | T003 (`overdue_metrics.py`) |
| Tipos `atraso_pdi` / `digest_pdi_atrasos` + migration | T004 |
| Annotate no queryset listagem | T005 |
| Chip + badge hub | US1 |
| Hook notificação no overdue job | US2 |
| Tabela + filtros gerenciais | US3 |
| Digest Beat + e-mail | US4 |
| Widget KPI dashboard | US5 |
| Coluna Atrasadas + `complete_pdi` | US6 |

---

## 10. Ignore / setup (verificação T002)

| Artefato | Status |
|----------|--------|
| Git repo | Sim (`.git`) |
| `.gitignore` | Presente — `.venv/`, `__pycache__/`, `.env*`, `node_modules/`, `dist/`, coverage |
| `Dockerfile` + `.dockerignore` | Presentes — `.git`, `.env*`, `node_modules`, coverage |
| ESLint / Prettier / Terraform / Helm | Não aplicáveis como ignore dedicado neste monólito Django |
