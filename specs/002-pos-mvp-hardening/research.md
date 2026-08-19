# Research: Hardening Operacional Pós-MVP

**Branch**: `002-pos-mvp-hardening` | **Date**: 2026-07-14

Pesquisa consolidada a partir do estado atual do código (pós-MVP 001) e da [spec.md](./spec.md). Todos os itens que seriam `NEEDS CLARIFICATION` no Technical Context foram resolvidos.

---

## R1 — Semântica pós-reprovação (meta e resultado)

- **Decision**: Manter status `reprovada` / `reprovado` após `reject_*`; a correção do colaborador chama `Meta.reopen()` / `reopen_resultado()` (já existentes, hoje sem callers) e persiste `pendente`. A etapa agregada (`Avaliacao.etapa`) **nunca** é alterada por reprovação. UI deve exibir próximo passo (corrigir → reenviar → reaprovar). Para resultados, permitir edição de progresso/conteúdo elegível enquanto `status_resultado=reprovado` **e** etapa atual for `aprovacao_resultados` (hoje `meta_progress_editable` só libera em `resultados`, causando dead-end).
- **Rationale**: Contrato 001 dizia “reprovação → pendente” imediato, mas o código corretamente permanece em `reprovada` até correção — melhor para CTAs distintos. Princípio V e FR-001–004.
- **Alternatives considered**:
  - Retroceder etapa para `input_metas`/`resultados` — rejeitado (constituição + spec).
  - Auto-`reopen()` dentro de `reject_*` — rejeitado: apaga a distinção visual “reprovado” vs “pendente inicial” e confunde fluxo do gestor.
  - Novo status `em_correcao` — rejeitado por complexidade sem ganho (PENDENTE após reopen basta).

---

## R2 — Avaliação mid-cycle

- **Decision**: Serviço `reviews.services.enrollment.ensure_avaliacao_for_user(user, ciclo=None)` que, se `user.is_active` e existir ciclo `aberto`, faz `Avaliacao.objects.get_or_create(ciclo=..., usuario=..., defaults={etapa: input_metas})`. Invocar explicitamente nos caminhos de cadastro/ativação (ex.: `RegisterForm.save` / `UserUpdateForm` quando `is_active` torna-se True), reutilizando a mesma lógica de `open_cycle()` para idempotência. Sem criação se não houver ciclo aberto.
- **Rationale**: `unique_together`/`UniqueConstraint` em `(ciclo, usuario)` já impede duplicata; chamada explícita é testável e evita side effects surpresa em `post_save` de toda gravação de user.
- **Alternatives considered**:
  - Signal `post_save` global em `CustomUser` — rejeitado por acoplamento e dificuldade de desligar em fixtures/migrations.
  - Criar só via job Celery noturno — rejeitado: SCR-002 exige cobertura imediata no ativo.
  - Endpoints manuais RH — rejeitado: não resolve exclusão mid-cycle (problema da US2).

---

## R3 — Soft-delete e unicidade de catálogos

- **Decision**: Adicionar `is_active` a `Escala` e `Competencia` (Área/Cargo já têm). Trocar `DeleteView` hard-delete por inativação (`is_active=False`). `UniqueConstraint(fields=['nome'], condition=Q(is_active=True), name='...')` por entidade. Formulários de criação/edição de vínculos (seletores) filtram `is_active=True`. Inativos podem reutilizar nome (unicidade só entre ativos), conforme Assumptions da spec.
- **Rationale**: FR-008–010; `PROTECT` já impede hard-delete de registros referenciados — soft-delete evita o beco operacional e preserva histórico.
- **Alternatives considered**:
  - Hard-delete + mensagem de ProtectedError — status atual; rejeitado pela spec.
  - Unicidade global incluindo inativos — rejeitado pela Assumption (“unicidade entre ativos”).
  - Pacote django-safedelete — rejeitado (Princípio I).

---

## R4 — Reatribuição em lote no offboarding

- **Decision**: Serviço `accounts.services.offboarding.reassign_direct_reports(*, from_manager, to_manager, actor)` em transação: valida `to_manager` ativo e ≠ `from_manager`; atualiza `line_manager` de todos os liderados ativos; gera auditoria por usuário afetado (campo `line_manager_id` já tracked). UI: formulário/ação no fluxo de edição/desativação do gestor (lista de liderados + seletor do novo gestor + submit único). Desativação continua bloqueada por `CustomUser._validate_deactivation_without_active_reports` até lote completo.
- **Rationale**: Completa FR-011–013 sem afrouxar o bloqueio FR-028.
- **Alternatives considered**:
  - Só edição 1:1 (atual) — rejeitado (SC-003 / N liderados).
  - Cascata automática para gestor do gestor — rejeitado: escolha explícita do RH é requisito.

---

## R5 — Aprovação/reprovação por administrador

- **Decision**: Em `goals.services.approval._ensure_approver`, permitir `approver.is_admin` **sempre** (com ou sem `line_manager`); líderes não-admin continuam restritos ao gestor direto. Incluir `Meta.status` e `Meta.status_resultado` em `audit.signals` tracked fields (ou log explícito no service com `audit_actor`). UI: botões de aprovar/reprovar visíveis ao admin nas mesmas partials, sem novas listagens cross-hierarchy genéricas — admin já tem visão ampla; líderes fora do escopo permanecem 403 via `ScopedObjectMixin`.
- **Rationale**: FR-014–016; exceção de governança RH, não bypass de escopo para líderes.
- **Alternatives considered**:
  - Delegar “aprovador substituto” por período — over-engineering para escala atual.
  - Permitir qualquer `is_leader` — rejeitado (enfraquece modelo hierárquico).

---

## R6 — Dedupe de lembretes

- **Decision**: Estender `NotificacaoLog` com chave lógica estável: campos `referencia` (CharField, ex. `meta:42` / `acao_pdi:7` / `avaliacao:3`) e `janela` (CharField/Date, ex. data-alvo do lembrete `YYYY-MM-DD`). Antes de enviar, task verifica existência de log `status=enviado` com mesmo `(destinatario, tipo, referencia, janela)`. Falhas não bloqueiam reintento (só `enviado` deduplica). Índice composto para lookup.
- **Rationale**: Spec Assumption: destinatário + tipo + referência + janela; modelo atual não tem referência — sem isso o job reenvia sempre.
- **Alternatives considered**:
  - Cache Redis TTL — rejeitado: perde dedupe em restart e não audita.
  - UniqueConstraint hard no log — rejeitado: impedir reintento após falha legítima.

---

## R7 — Recálculo de atraso de PDI

- **Decision**: Ao salvar alteração de `prazo` em `AcaoPDI`, se `status == atrasada` e `prazo >= hoje`, recalcular para `pendente` (ou `em_andamento` se havia progresso explícito — default: `pendente`). Se novo prazo ainda no passado, manter `atrasada`. Incluir `prazo` em `ACAO_PDI_TRACKED_FIELDS`. Job `mark_overdue_pdi_actions` permanece one-way para marcar atrasos.
- **Rationale**: FR-018–019; evita status inconsistente após extensão de prazo.
- **Alternatives considered**:
  - Só o job diário “desmarca” atraso — rejeitado: SC-006 exige coerência imediata na extensão.
  - Novo status `reagendada` — rejeitado por proliferação de estados.

---

## R8 — Prontidão de produção

- **Decision**: Endpoint `GET /health/` (ou `/healthz/`) retornando 200 com checagens leves (DB `SELECT 1`; opcionalmente Redis ping). `STATIC_ROOT` + `collectstatic` documentados; servir static via WhiteNoise **ou** reverse-proxy (escolher na implementação conforme deploy — ver Complexity Tracking). Documento `docs/ops/backup.md` com frequência/retenção mínimas para PostgreSQL (pg_dump/snapshots) aplicável pela operação.
- **Rationale**: FR-020–021; monitoramento e go-live sem reinventar stack.
- **Alternatives considered**:
  - django-health-check package — rejeitado na v1 se view nativa bastar.
  - Omitir backup doc — rejeitado pela spec.

---

## R9 — Testes automatizados de escopo e stage machine

- **Decision**: Introduzir `pytest` + `pytest-django` com `tests/` na raiz; helpers sem factory_boy; priorizar: `get_visible_users` / IDOR em DetailView; `can_advance`/`advance_stage`; pós-reprovação (etapa inalterada; reopen; 100% regra); mid-cycle `ensure_avaliacao`; admin approve com actor no AuditLog; bloqueio de desativação sem reassign.
- **Rationale**: FR-022 / SC-008; T073 da 001 ainda aberto — esta feature materializa a suíte crítica.
- **Alternatives considered**:
  - Só Django TestCase sem pytest — aceitável como fallback; preferir pytest-django por fixtures.
  - Cobertura E2E Selenium — fora do escopo desta feature.

---

## R10 — Polish HTMX (loading / empty / modal a11y)

- **Decision**: Padrão de componente: `hx-indicator` + spinner compartilhado; partial `empty_state` com CTA condicional à permissão; modal com focus no primeiro controle, fechamento Escape, restore de foco no trigger (JS mínimo inline ou `static/js/modal.js` sem framework). Aplicar primeiro nas telas críticas de metas/PDI/listas de catálogo.
- **Rationale**: FR-023–025 sem Alpine/SPA.
- **Alternatives considered**:
  - Alpine.js — rejeitado (restrição SPA-adjacente / dependência).
  - Só CSS `:empty` — insuficiente para CTAs contextuais.

---

## Gaps confirmados no código atual (entrada)

| Área | Gap principal |
|---|---|
| Pós-reprovação | `reopen*` mortos; resultado stuck em `aprovacao_resultados` |
| Mid-cycle | Só batch em `open_cycle` |
| Catálogos | Hard-delete; Escala/Competência sem `is_active`; sem UniqueConstraint ativos |
| Offboarding | Bloqueio OK; lote ausente |
| Admin approve | Só se `line_manager` nulo |
| Lembretes / PDI | Sem chave de dedupe; prazo não recalcula nem audita |
| Prod / testes / UX | Sem health/STATIC_ROOT formal; sem `tests/`; loading/empty/a11y incompletos |
